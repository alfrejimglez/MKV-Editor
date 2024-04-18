from tkinter import filedialog, messagebox, simpledialog
import tkinter as tk
import subprocess
import os
import json

info_dict = None

def select_file():
    filename = filedialog.askopenfilename(filetypes=[("MKV files", "*.mkv")])
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
        
        # Verificar si hay múltiples pistas de subtítulos
        subtitle_tracks = [track for track in info_dict['tracks'] if track['type'] == 'subtitles']
        if len(subtitle_tracks) > 1:
            # Si hay múltiples pistas de subtítulos, solicitar al usuario que elija una
            subtitle_options = [f"{track['properties']['language']} (Track {track['properties']['number']})" for track in subtitle_tracks]
            selected_subtitle = simpledialog.askstring("Choose Subtitle Track", "Multiple subtitle tracks found. Please choose one:\n" + "\n".join(subtitle_options))
            # Obtener el número de pista de subtítulo seleccionado
            selected_subtitle_number = int(selected_subtitle.split(" ")[-1])
            # Buscar el índice de la pista de subtítulos seleccionada en la lista subtitle_tracks
            selected_subtitle_index = next((index for index, track in enumerate(subtitle_tracks) if track['properties']['number'] == selected_subtitle_number), None)
        else:
            # Si solo hay una pista de subtítulos, seleccionarla automáticamente
            selected_subtitle_number = subtitle_tracks[0]['properties']['number']
            selected_subtitle_index = 0  # El índice es 0 ya que solo hay una pista de subtítulos
        
        if selected_subtitle_index is not None:
            # Convertir el archivo de subtítulos SRT al formato SSA
            subtitle_file = input_file.replace('.mkv', f'.{selected_subtitle_number}.srt')
            subprocess.run(['ffmpeg', '-i', input_file, '-map', f'0:s:{selected_subtitle_index}', subtitle_file])
            
            # Ejecutar ffmpeg para exportar a MP4, especificando el archivo de subtítulos SSA
            subprocess.run(['ffmpeg', '-hwaccel', 'auto', '-i', input_file, '-i', subtitle_file, '-y', '-v', 'error', '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=spa', '-map', '0:v?', '-map', '0:a?', '-map', '1:s:0', '-stats', '-threads', '0', output_file])
            
            # Eliminar el archivo de subtítulos temporal
            os.remove(subtitle_file)
            
            messagebox.showinfo("Export Complete", "The file has been exported successfully.")
        else:
            messagebox.showerror("Error", "Selected subtitle track not found.")


# Crear la ventana principal
root = tk.Tk()
root.title("MKV Editor")

# Marco para la selección de archivos
frame_file_select = tk.Frame(root)
frame_file_select.pack(pady=10)

lbl_select_file = tk.Label(frame_file_select, text="Select MKV File:")
lbl_select_file.grid(row=0, column=0)

btn_browse = tk.Button(frame_file_select, text="Browse", command=select_file)
btn_browse.grid(row=0, column=1)

txt_selected_file = tk.Text(frame_file_select, width=50, height=1)
txt_selected_file.grid(row=0, column=2)

# Marco para mostrar información del archivo
frame_info = tk.Frame(root)
frame_info.pack(pady=10)

lbl_info = tk.Label(frame_info, text="File Information:")
lbl_info.pack()

txt_info = tk.Text(frame_info, width=80, height=10)
txt_info.pack()

# Botón para exportar a MP4
btn_export = tk.Button(root, text="Export to MP4", command=export_to_mp4)
btn_export.pack(pady=10)

root.mainloop()
