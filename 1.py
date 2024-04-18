from tkinter import filedialog, messagebox, simpledialog
import tkinter as tk
import subprocess
import os
import json

info_dict = None

def select_file():
    filename = filedialog.askopenfilename(filetypes=[("Videos en MKV", "*.mkv")])
    if filename:
        txt_selected_file.delete(1.0, tk.END)
        txt_selected_file.insert(tk.END, filename)
        # Obtener información del archivo MKV
        get_info(filename)

def get_info(filename):
    global info_dict
    # Ejecutar mkvmerge para obtener información del archivo MKV
    result = subprocess.run(['mkvmerge', '-i', '-F', 'json', filename], capture_output=True, text=True)
    info = result.stdout
    # Convertir la salida JSON en un diccionario
    info_dict = json.loads(info)
    # Filtrar las pistas de audio y subtítulos
    audio_tracks = [track for track in info_dict['tracks'] if track['type'] == 'audio']
    subtitle_tracks = [track for track in info_dict['tracks'] if track['type'] == 'subtitles']
    # Crear una cadena de texto con la información de las pistas
    audio_info = "\n".join([f"Audio Track {track['properties']['number']}: {track['codec']} - {track['properties']['language']}" for track in audio_tracks])
    subtitle_info = "\n".join([f"Subtitle Track {track['properties']['number']}: {track['codec']} - {track['properties']['language']}" for track in subtitle_tracks])
    # Mostrar la información en el cuadro de texto
    txt_info.delete(1.0, tk.END)
    txt_info.tag_configure("bold", font=("Helvetica", 10, "bold"))
    # Insertar los títulos en negrita
    txt_info.insert(tk.END, "Audio Tracks:\n", "bold")
    txt_info.insert(tk.END, audio_info + "\n\n")
    txt_info.insert(tk.END, "Subtitle Tracks:\n", "bold")
    # Insertar la información de las pistas de audio y subtítulos
    txt_info.insert(tk.END, subtitle_info)


def export_to_mp4():
    global info_dict
    input_file = txt_selected_file.get(1.0, tk.END).strip()
    if input_file and info_dict:
        output_file = input_file.replace('.mkv', '.mp4')
        
        # Verificar si hay múltiples pistas de audio
        audio_tracks = [track for track in info_dict['tracks'] if track['type'] == 'audio']
        subtitle_tracks = [track for track in info_dict['tracks'] if track['type'] == 'subtitles']
        
        # Preguntar al usuario qué pista de audio desea utilizar si hay más de una
        if len(audio_tracks) > 1:
            audio_options = [f"{track['properties']['language']} (Track {track['properties']['number']})" for track in audio_tracks]
            selected_audio = simpledialog.askstring("Elija Pista de audio", "Se encontraron varias pistas de audio. Por favor elige uno:\n" + "\n".join(audio_options))
            selected_audio_number = int(selected_audio.split(" ")[-1])
            selected_audio_index = next((index for index, track in enumerate(audio_tracks) if track['properties']['number'] == selected_audio_number), None)
            
            if selected_audio_index is None:
                messagebox.showerror("Error", "No se encontró la pista de audio seleccionada.")
                return
        else:
            selected_audio_number = audio_tracks[0]['properties']['number']
            selected_audio_index = 0
        
        # Preguntar al usuario qué pista de subtítulos desea utilizar si hay más de una
        if len(subtitle_tracks) > 1:
            subtitle_options = [f"{track['properties']['language']} (Track {track['properties']['number']})" for track in subtitle_tracks]
            selected_subtitle = simpledialog.askstring("Elija Pista de subtítulos", "Se encontraron varias pistas de subtítulos. Por favor elige uno:\n" + "\n".join(subtitle_options))
            selected_subtitle_number = int(selected_subtitle.split(" ")[-1])
            selected_subtitle_index = next((index for index, track in enumerate(subtitle_tracks) if track['properties']['number'] == selected_subtitle_number), None)
            
            if selected_subtitle_index is None:
                messagebox.showerror("Error", "No se encontró la pista de subtítulos seleccionada.")
                return
        else:
            selected_subtitle_number = subtitle_tracks[0]['properties']['number']
            selected_subtitle_index = 0
        
        # Convertir el archivo de subtítulos SRT al formato SSA
        subtitle_file = input_file.replace('.mkv', f'.{selected_subtitle_number}.srt')
        subprocess.run(['ffmpeg', '-i', input_file, '-map', f'0:s:{selected_subtitle_index}', subtitle_file])
        
        # Ejecutar ffmpeg para exportar a MP4, especificando el archivo de subtítulos SSA y la pista de audio seleccionada
        subprocess.run(['ffmpeg', '-hwaccel', 'auto', '-i', input_file, '-i', subtitle_file, '-y', '-v', 'error', '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=spa', '-metadata:s:a:0', 'language=spa', '-map', '0:v?', '-map', f'0:a:{selected_audio_index}', '-map', '1:s:0', '-stats', '-threads', '0', output_file])
        
        # Eliminar el archivo de subtítulos temporal
        os.remove(subtitle_file)
        
        messagebox.showinfo("Exportación completa", "El archivo se ha exportado correctamente.")

# Crear la ventana principal
root = tk.Tk()
root.title("MKV Editor")

# Marco para la selección de archivos
frame_file_select = tk.Frame(root)
frame_file_select.pack(pady=10)

lbl_select_file = tk.Label(frame_file_select, text="Seleccione el archivo MKV:")
lbl_select_file.grid(row=0, column=0)

btn_browse = tk.Button(frame_file_select, text="Seleccionar", command=select_file)
btn_browse.grid(row=0, column=1)

txt_selected_file = tk.Text(frame_file_select, width=50, height=1)
txt_selected_file.grid(row=0, column=2)

# Marco para mostrar información del archivo
frame_info = tk.Frame(root)
frame_info.pack(pady=10)

lbl_info = tk.Label(frame_info, text="Fuentes")
lbl_info.pack()

txt_info = tk.Text(frame_info, width=80, height=10)
txt_info.pack()

# Botón para exportar a MP4
btn_export = tk.Button(root, text="Exportar", command=export_to_mp4)
btn_export.pack(pady=10)

root.mainloop()
