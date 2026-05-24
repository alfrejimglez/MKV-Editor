import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

NVENC_PRESET = "p4"


def script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def ffmpeg_bin() -> str:
    p = script_dir() / "ffmpeg.exe"
    return str(p) if p.exists() else "ffmpeg"


def ffprobe_bin() -> str:
    p = script_dir() / "ffprobe.exe"
    return str(p) if p.exists() else "ffprobe"


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


def encode_nvenc(cmd, bitrate: Optional[int]):

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


def burn(ffmpeg, input_file, vf, output, bitrate):

    cmd = [
        ffmpeg,
        "-y",
        "-i", str(input_file),
        "-vf", vf,
        "-c:a", "copy",
        "-movflags", "+faststart",
    ]

    encode_nvenc(cmd, bitrate)

    cmd.append(str(output))

    return subprocess.run(cmd).returncode == 0


def find_matching_srt(file: Path, srts):
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


def process_file(ffmpeg, ffprobe, file, subtitle_path, style):

    output = file.with_name(f"{file.stem}_subburn.mp4")

    bitrate = probe_bitrate_kbps(ffprobe, file)

    sub = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:")

    style_str = build_style(style)

    vf = f"subtitles='{sub}'"

    if style_str:
        vf += f":{style_str}"

    print(f"[PROC] {file.name}")

    return burn(ffmpeg, file, vf, output, bitrate)


def main():

    base = script_dir()

    ffmpeg = ffmpeg_bin()
    ffprobe = ffprobe_bin()

    nvenc = has_nvenc(ffmpeg)

    print(f"Modo: {'NVENC' if nvenc else 'CPU fallback'}")

    style = input("Estilo [B]lanco, [R]ojo, [G]ris: ").strip().lower()

    style = (
        "rojo" if style in ["r", "rojo"]
        else "gris" if style in ["g", "gris"]
        else "blanco"
    )

    # SOLO carpeta actual (NO subcarpetas)
    mp4s = sorted(base.glob("*.mp4"))
    mkvs = sorted(base.glob("*.mkv"))
    srts = sorted(base.glob("*.srt"))

    ok = 0
    fail = 0

    for f in mp4s + mkvs:

        # evitar reprocesar subburn
        if "_subburn" in f.name.lower():
            continue

        # buscar srt compatible
        srt, auto_ok = find_matching_srt(f, srts)

        # si no hay srt ni subtítulos internos -> skip
        if not srt and not has_internal_subs(ffprobe, f):
            print(f"[SKIP] {f.name}")
            continue
        # ⚠️ CASO DURO: 1 srt pero no match claro → pedir confirmación
        if srt and not auto_ok:
            print("\n⚠️ POSIBLE MATCH MANUAL")
            print(f"🎬 Vídeo: {f.name}")
            print(f"📝 Sub:   {srt.name}")

            resp = input("¿Quieres quemarlo? [y/n]: ").strip().lower()

            if resp != "y":
                print("[SKIP MANUAL]")
                continue

        subtitle = srt if srt else f

        if process_file(ffmpeg, ffprobe, f, subtitle, style):
            ok += 1
        else:
            fail += 1

    print("\nResumen:")
    print("OK:", ok)
    print("FAIL:", fail)


if __name__ == "__main__":
    main()

