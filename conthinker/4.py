import sys
import subprocess
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import simpledialog
import winsound  # Importar winsound para reproducir sonidos

class EditorMKV(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Editor MKV')
        self.geometry('400x400')

        self.label_selected_file = tk.Label(self, text="", fg="red", font=("Arial", 12))
        self.label_selected_file.pack(pady=10)

        self.label_file = tk.Label(self, text="Selecciona un archivo MKV:", font=("Arial", 12))
        self.label_file.pack(pady=10)

        self.button_select = tk.Button(self, text='Seleccionar MKV', command=self.select_file)
        self.button_select.pack(pady=10)

        self.audio_checkboxes = []  # List to store (checkbox, IntVar) tuples
        self.subtitle_checkboxes = []  # List to store (checkbox, IntVar) tuples
        self.subtitle_buttons = []  # List for "Extract" buttons
        
        self.button_edit = tk.Button(self, text='Editar', command=self.edit_file)
        self.button_edit.pack(pady=10)
        self.button_edit.config(state=tk.DISABLED)  # Disable edit button initially

        self.button_convert_mp4 = tk.Button(self, text='Convertir a MP4', command=self.convert_to_mp4)
        self.button_convert_mp4.pack(pady=10)
        self.button_convert_mp4.config(state=tk.DISABLED)  # Disable convert button initially

        self.selected_file = None
        self.output_file = None  # Variable to store edited file name

    def select_file(self):
        filename = filedialog.askopenfilename(title='Selecciona un archivo', filetypes=[('Archivos MKV', '*.mkv')])
        if filename:
            self.clear_audio_and_subtitle_selection()
            self.selected_file = filename
            self.label_selected_file.config(text=os.path.basename(self.selected_file))  # Show selected file name
            self.show_audio_and_subtitle_selection()
            self.button_edit.config(state=tk.NORMAL)  # Enable edit button
            self.button_convert_mp4.config(state=tk.DISABLED)  # Disable convert button

    def show_audio_and_subtitle_selection(self):
        tk.Label(self, text="Pistas de audio:", font=("Arial", 12, "bold")).pack()
        self.audio_frame = tk.Frame(self)
        self.audio_frame.pack()

        tk.Label(self, text="Pistas de subtítulos:", font=("Arial", 12, "bold")).pack()
        self.subtitle_frame = tk.Frame(self)
        self.subtitle_frame.pack()

        mkvmerge_output = subprocess.check_output(["mkvmerge", "-i", "-F", "json", self.selected_file]).decode("utf-8")
        track_info = json.loads(mkvmerge_output)

        for track in track_info["tracks"]:
            if track["type"] == "audio":
                language = track["properties"].get("language", "Desconocido")
                track_id = track["id"]
                var = tk.IntVar()
                checkbox = tk.Checkbutton(self.audio_frame, text=f"Idioma: {language}", variable=var)
                checkbox.track_id = track_id  
                self.audio_checkboxes.append((checkbox, var))  # Store checkbox and IntVar as a tuple
                checkbox.pack(anchor='w')
            elif track["type"] == "subtitles":
                language = track["properties"].get("language", "Desconocido")
                track_id = track["id"]
                var = tk.IntVar()
                checkbox = tk.Checkbutton(self.subtitle_frame, text=f"Idioma: {language}", variable=var)
                checkbox.track_id = track_id  
                extract_button = tk.Button(self.subtitle_frame, text="Extraer", command=lambda tid=track_id: self.extract_subtitle(tid))
                extract_button.pack(anchor='w')
                checkbox.pack(anchor='w')
                self.subtitle_checkboxes.append((checkbox, var))  # Store checkbox and IntVar as a tuple

    def extract_subtitle(self, track_id):
        output_file = os.path.splitext(self.selected_file)[0] + f"_subtitle_{track_id}.srt"
        args = ["mkvextract", "tracks", self.selected_file, f"{track_id}:{output_file}"]
        subprocess.run(args)
        print(f"Subtítulo extraído correctamente como '{output_file}'.")

    def clear_audio_and_subtitle_selection(self):
        # Clear the lists of audio and subtitle tracks
        for checkbox, _ in self.audio_checkboxes:
            checkbox.destroy()
        self.audio_checkboxes = []
        
        for checkbox, _ in self.subtitle_checkboxes:
            checkbox.destroy()
        self.subtitle_checkboxes = []

    def edit_file(self):
        if self.selected_file:
            selected_audio_tracks = [checkbox.track_id for checkbox, var in self.audio_checkboxes if var.get() == 1]
            selected_subtitle_tracks = [checkbox.track_id for checkbox, var in self.subtitle_checkboxes if var.get() == 1]

            # Create arguments for mkvmerge
            audio_args = [f"--audio-tracks", ",".join(map(str, selected_audio_tracks))]
            subtitle_args = [f"--subtitle-tracks", ",".join(map(str, selected_subtitle_tracks))] if selected_subtitle_tracks else ["--no-subtitles"]

            # Get new filename from user
            new_filename = simpledialog.askstring("Editar Nombre de Archivo", "Ingrese el nuevo nombre de archivo:", initialvalue=os.path.basename(self.selected_file))
            if new_filename:
                if not new_filename.endswith(".mkv"):
                    new_filename += ".mkv"
                output_file = new_filename
            else:
                output_file = os.path.splitext(self.selected_file)[0] + "_edited.mkv"

            args = ["mkvmerge", "-o", output_file] + audio_args + subtitle_args + [self.selected_file]

            print("Argumentos pasados a mkvmerge:")
            print(args)

            subprocess.run(args)
            print("Archivo editado correctamente.")
            
            # Reproducir sonido al finalizar la edición
            winsound.PlaySound("finish.wav", winsound.SND_FILENAME)  # Reemplaza con la ruta de tu archivo de sonido
            
            # Store the edited file name in the instance variable
            self.output_file = output_file
            
            self.button_convert_mp4.config(state=tk.NORMAL)  # Enable convert button
        else:
            print("Por favor, selecciona un archivo MKV primero.")

    def convert_to_mp4(self):
        if self.output_file:  # Use the edited file if available
            output_file = os.path.splitext(self.output_file)[0] + ".mp4"
            args = [
                "ffmpeg",
                "-i", self.output_file,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ac", "2",
                "-c:s", "mov_text",
                "-metadata:s:s:0", "language=spa",
                "-metadata:s:a:0", "language=spa",
                output_file
            ]
            
            # Add quotes around the output file name if it contains spaces
            if ' ' in output_file:
                output_file = f'"{output_file}"'
            
            print(f"Argumentos para ffmpeg: {args}")
            
            # Execute ffmpeg with the arguments
            subprocess.run(args)
            print(f"Archivo convertido a MP4 correctamente como '{output_file}' con subtítulos incrustados y audio/subtítulos en español.")
            
            # Reproducir sonido al finalizar la conversión
            winsound.PlaySound("ruta/a/tu/sonido.wav", winsound.SND_FILENAME)  # Reemplaza con la ruta de tu archivo de sonido
            
            self.button_convert_mp4.config(state=tk.DISABLED)  # Disable convert button
        else:
            print("Por favor, edita un archivo MKV primero.")

if __name__ == '__main__':
    app = EditorMKV()
    app.mainloop()
