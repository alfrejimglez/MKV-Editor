import os
import sys
import subprocess
import re
import time
import concurrent.futures
from pathlib import Path
from typing import Optional

# ✅ 1. Cambio de preset a p3
NVENC_PRESET = "p3"

def script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def ffmpeg_bin() -> str:
    # 1. Buscar en la carpeta del script/ejecutable actual
    p = script_dir() / "ffmpeg.exe"
    if p.exists(): return str(p)
    
    # 2. Buscar en la carpeta temporal de PyInstaller (si estamos en una)
    if getattr(sys, "_MEIPASS", None):
        p_meipass = Path(sys._MEIPASS) / "ffmpeg.exe"
        if p_meipass.exists(): return str(p_meipass)

    return "ffmpeg"

def ffprobe_bin() -> str:
    # 1. Buscar en la carpeta del script/ejecutable actual
    p = script_dir() / "ffprobe.exe"
    if p.exists(): return str(p)
    
    # 2. Buscar en la carpeta temporal de PyInstaller
    if getattr(sys, "_MEIPASS", None):
        p_meipass = Path(sys._MEIPASS) / "ffprobe.exe"
        if p_meipass.exists(): return str(p_meipass)

    return "ffprobe"

def has_nvenc(ffmpeg: str) -> bool:
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return "h264_nvenc" in out
    except:
        return False

# ✅ 4. Detección automática de procesos (2-3 FFmpeg simultáneos)
def get_optimal_workers() -> int:
    cores = os.cpu_count() or 2
    return min(3, max(2, cores // 2))

def format_time(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"

def probe_bitrate_kbps(ffprobe: str, file: Path) -> Optional[int]:
    try:
        r = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=bit_rate",
                "-of", "default=nokey=1:noprint_wrappers=1",
                str(file),
            ],
            capture_output=True,
            text=True,
        )
        v = (r.stdout or "").strip()
        if v.isdigit():
            return int(v) // 1000
    except:
        pass
    return None

def has_internal_subs(ffprobe: str, file: Path) -> bool:
    try:
        r = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-select_streams", "s",
                "-show_entries", "stream=index",
                "-of", "csv=p=0",
                str(file),
            ],
            capture_output=True,
            text=True,
        )
        return bool(r.stdout.strip())
    except:
        return False

def build_style(style: str) -> str:
    if style == "rojo":
        return (
            "force_style='PrimaryColour=&H000000FF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,Outline=1,Shadow=0'"
        )
    elif style == "gris":
        return (
            "force_style='PrimaryColour=&H00FFFFFF,"
            "BackColour=&H66383838,"
            "OutlineColour=&H66383838,"
            "BorderStyle=3,Bold=1,Outline=1,Shadow=0'"
        )
    return ""

# ✅ 2. Añadir hwaccel cuda y refactorizar burn
def burn(ffmpeg: str, input_file: Path, vf: str, output: Path, bitrate: Optional[int], use_nvenc: bool):
    cmd = [ffmpeg, "-y"]
    
    if use_nvenc:
        cmd += ["-hwaccel", "cuda"]
        
    cmd += [
        "-i", str(input_file),
        "-vf", vf,
        "-c:a", "copy",
        "-movflags", "+faststart",
    ]

    if use_nvenc:
        cmd += [
            "-c:v", "h264_nvenc",
            "-preset", NVENC_PRESET,
            "-rc", "vbr",
        ]
        if bitrate:
            cmd += [
                "-b:v", f"{bitrate}k",
                "-maxrate", f"{int(bitrate * 1.2)}k",
                "-bufsize", f"{int(bitrate * 2)}k",
            ]
        else:
            cmd += [
                "-cq", "20",
                "-b:v", "0",
            ]
    else:
        # Fallback de CPU si no hay GPU
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]

    cmd.append(str(output))
    return subprocess.run(cmd, capture_output=True).returncode == 0

def find_matching_srt(file: Path, srts: list):
    base_name = file.stem.lower()

    # Coincidencia exacta
    for srt in srts:
        if srt.stem.lower() == base_name:
            return srt, True  # True = match perfecto

    # fallback (no exacto)
    for srt in srts:
        srt_name = srt.name.lower()
        if srt_name.startswith(base_name + ".") and srt.suffix.lower() == ".srt":
            return srt, True

    # si hay solo 1 srt en carpeta -> posible match manual
    if len(srts) == 1:
        return srts[0], False  # False = NO seguro

    return None, False

# Función encapsulada para el hilo paralelo
def process_single_task(ffmpeg: str, ffprobe: str, video: Path, subtitle_path: Path, style: str, use_nvenc: bool):
    output = video.with_name(f"{video.stem}_subburn.mp4")
    bitrate = probe_bitrate_kbps(ffprobe, video)
    
    sub = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:")
    style_str = build_style(style)
    vf = f"subtitles='{sub}'"

    if style_str:
        vf += f":{style_str}"

    success = burn(ffmpeg, video, vf, output, bitrate, use_nvenc)
    return "OK" if success else "FAIL"


def main():
    base = script_dir()
    ffmpeg = ffmpeg_bin()
    ffprobe = ffprobe_bin()
    nvenc = has_nvenc(ffmpeg)
    
    print("="*50)
    print(f"MODO: {'⚡ NVENC GPU (Acelerado)' if nvenc else '🐌 CPU Fallback'}")
    print("="*50)

    # Procesar argumentos y estilos
    file_arg = None
    if len(sys.argv) > 1:
        file_arg = Path(sys.argv[1])
        if not file_arg.exists():
            print(f"[ERROR] El archivo no existe: {file_arg}")
            return
        
        if len(sys.argv) > 2:
            style_raw = sys.argv[2].strip().lower()
            style = "rojo" if style_raw in ["r", "rojo"] else "gris" if style_raw in ["g", "gris"] else "blanco"
        else:
            # Si se llama desde la GUI pero falta el estilo, no bloquear con input
            style = "blanco"
        
        print(f"Estilo usado: {style}\n")
        videos_to_check = [file_arg]
    else:
        # Modo interactivo (solo si no hay argumentos)
        try:
            style = input("Estilo [B]lanco, [R]ojo, [G]ris: ").strip().lower()
            style = "rojo" if style in ["r", "rojo"] else "gris" if style in ["g", "gris"] else "blanco"
        except EOFError:
            style = "blanco"
            
        videos_to_check = sorted(base.glob("*.mp4")) + sorted(base.glob("*.mkv"))
        print("\nBuscando vídeos en la carpeta...")

    srts = sorted(base.glob("*.srt"))
    
    # 📝 FASE 1: Recopilar tareas (Secuencial para permitir inputs interactivos)
    tasks = []
    skip_count = 0

    for f in videos_to_check:
        if "_subburn" in f.name.lower():
            continue
            
        srt, auto_ok = find_matching_srt(f, srts)
        
        # si no hay srt ni subtítulos internos -> skip
        if not srt and not has_internal_subs(ffprobe, f):
            print(f"[SKIP] {f.name} (Sin subtítulos)")
            skip_count += 1
            continue
            
        # ⚠️ CASO DURO: 1 srt pero no match claro → pedir confirmación
        if srt and not auto_ok:
            print("\n⚠️ POSIBLE MATCH MANUAL")
            print(f"🎬 Vídeo: {f.name}")
            print(f"📝 Sub:   {srt.name}")
            resp = input("¿Quieres quemarlo? [y/n]: ").strip().lower()
            if resp != "y":
                print("[SKIP MANUAL]")
                skip_count += 1
                continue
                
        subtitle = srt if srt else f
        tasks.append((f, subtitle))

    if not tasks:
        print("\nNo hay vídeos listos para procesar.")
        return

    # 🚀 FASE 2: Procesamiento Paralelo
    total = len(tasks)
    workers = get_optimal_workers() if total > 1 else 1
    print(f"\nIniciando renderizado de {total} vídeos con {workers} procesos concurrentes...\n" + "-"*50)

    ok_count, fail_count, completed = 0, 0, 0
    start_time = time.time()

    # ✅ 3. ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_video = {
            executor.submit(process_single_task, ffmpeg, ffprobe, video, sub, style, nvenc): video
            for video, sub in tasks
        }
        
        for future in concurrent.futures.as_completed(future_to_video):
            video = future_to_video[future]
            completed += 1
            
            try:
                status = future.result()
                if status == "OK":
                    ok_count += 1
                    icon = "✅"
                else:
                    fail_count += 1
                    icon = "❌"
            except Exception:
                fail_count += 1
                icon = "❌ (Error Fatal)"
            
            # Limpiar barra y mostrar archivo completado
            sys.stdout.write("\r" + " " * 80 + "\r")
            print(f"{icon} {video.name}")

            # ✅ 5 y 6. Barra de progreso y ETA
            if completed < total:
                elapsed = time.time() - start_time
                avg_time = elapsed / completed
                remaining_videos = total - completed
                eta = avg_time * remaining_videos
                
                percent = int((completed / total) * 100)
                bar_len = 30
                filled_len = int(bar_len * completed / total)
                bar = "█" * filled_len + "-" * (bar_len - filled_len)
                
                sys.stdout.write(f"\rProgreso: [{bar}] {percent}% | {completed}/{total} | ETA: {format_time(eta)}")
                sys.stdout.flush()

    total_time = time.time() - start_time
    avg_per_video = total_time / total if total > 0 else 0

    # ✅ 7. Resumen final mejorado
    sys.stdout.write("\r" + " " * 80 + "\r")
    print("="*50)
    print("🎬 RESUMEN FINAL DEL PROCESAMIENTO")
    print("="*50)
    print(f"⏱️ Tiempo Total   : {format_time(total_time)}")
    print(f"⚡ Tiempo Medio   : {format_time(avg_per_video)} por vídeo")
    print(f"✅ Completados    : {ok_count}")
    print(f"❌ Fallidos       : {fail_count}")
    print(f"⏭️ Omitidos       : {skip_count}")
    print("="*50)

if __name__ == "__main__":
    main()