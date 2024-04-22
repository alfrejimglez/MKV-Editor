from tkinter import filedialog, messagebox, simpledialog, Text
import tkinter as tk
import subprocess
import os
import re
import json
import tkinter.font as font

info_dict = None

def select_files():
    filenames = filedialog.askopenfilenames(filetypes=[("Videos en MKV", "*.mkv")])
    for filename in filenames:
        if filename:
            txt_selected_file.delete(1.0, tk.END)
            txt_selected_file.insert(tk.END, filename)
            # Obtener información del archivo MKV
            get_info(filename)
            # Exportar a MP4 con las opciones seleccionadas
            export_to_mp4(filename)

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
    subtitle_info = "\n".join([f"Subtitle Track {track['properties']['number']}: {track['properties'].get('track_name', 'N/A')} - {track['codec']} - {track['properties']['language']}" for track in subtitle_tracks])
    # Mostrar la información en el cuadro de texto
    txt_info.delete(1.0, tk.END)
    txt_info.tag_configure("bold", font=("Helvetica", 10, "bold"))
    txt_info.tag_configure("red", foreground="red")  # Etiqueta de estilo para texto en rojo
    # Insertar los títulos en negrita
    txt_info.insert(tk.END, "Audio Tracks:\n", "bold")
    txt_info.insert(tk.END, audio_info + "\n\n")
    txt_info.insert(tk.END, "Subtitle Tracks:\n", "bold")
    # Insertar la información de las pistas de audio y subtítulos
    txt_info.insert(tk.END, subtitle_info)

    # Establecer el color rojo para el nombre del subtítulo
    for track in subtitle_tracks:
        start_index = txt_info.search(track['properties'].get('track_name', 'N/A'), 1.0, tk.END)
        end_index = f"{start_index}+{len(track['properties'].get('track_name', 'N/A'))}c"
        txt_info.tag_add("red", start_index, end_index)

def export_to_mp4(input_file):
    global info_dict
    if input_file and info_dict:
        # Extraer el nombre de la película y el año del archivo de entrada usando expresiones regulares
        match = re.search(r'^(.*?)\s*\((\d{4})\)', os.path.basename(input_file))
        if match:
            movie_name = match.group(1).strip()
            year = match.group(2)
            # Generar el nombre del archivo de salida
            output_folder = os.path.join("C:\\Users", os.environ['USERNAME'], "Videos")
            output_file = os.path.join(output_folder, f"{movie_name} ({year}).mp4")
        else:
            # Si no se encuentra un nombre de película y año válido, simplemente usar el nombre del archivo de entrada sin cambios
            output_file = input_file.replace('.mkv', '.mp4')
        
        # Verificar si hay múltiples pistas de audio y subtítulos antes de continuar
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
        
        # Verificar si hay pistas de subtítulos antes de continuar
        if subtitle_tracks:
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
        else:
            # Si no hay pistas de subtítulos, establecer el nombre del archivo temporal como None
            subtitle_file = None
        
        # Ejecutar ffmpeg para exportar a MP4, especificando el archivo de subtítulos SSA (si existe) y la pista de audio seleccionada
        command = ['ffmpeg', '-hwaccel', 'auto', '-i', input_file]
        if subtitle_file:
            command.extend(['-i', subtitle_file])
        command.extend(['-y', '-v', 'error', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=spa', '-metadata:s:a:0', 'language=spa', '-map', '0:v?'])
        if selected_audio_index is not None:
            command.extend(['-map', f'0:a:{selected_audio_index}'])
        if subtitle_file:
            command.extend(['-map', '1:s:0'])
        command.extend(['-stats', '-threads', '0', output_file])
        
        subprocess.run(command)
        
        # Eliminar el archivo de subtítulos temporal si existe
        if subtitle_file:
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

btn_browse = tk.Button(frame_file_select, text="Seleccionar", command=select_files)
btn_browse.grid(row=0, column=1)

txt_selected_file = tk.Text(frame_file_select, width=50, height=1)
txt_selected_file.grid(row=0, column=2)

# Marco para mostrar información del archivo
frame_info = tk.Frame(root)
frame_info.pack(pady=10)

lbl_info = tk.Label(frame_info, text="Fuentes")
lbl_info.pack()

txt_info = Text(frame_info, width=80, height=10)
txt_info.pack()

root.mainloop()
