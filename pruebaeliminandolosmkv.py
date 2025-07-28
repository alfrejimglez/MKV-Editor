import sys
import subprocess
import os
import json
import pygame
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QLabel, QVBoxLayout, QCheckBox, QHBoxLayout, QLineEdit, QDialog, QDialogButtonBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class FilenameInputDialog(QDialog):
    def __init__(self, current_filename="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Nombre de Archivo")
        
        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("Ingrese el nuevo nombre de archivo")
        self.input_line.setText(current_filename)  # Establecer el texto inicial con el nombre de archivo actual

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        button_box = QDialogButtonBox(buttons, Qt.Horizontal, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.input_line)
        layout.addWidget(button_box)

    def getFilename(self):
        if self.exec_() == QDialog.Accepted:
            return self.input_line.text()
        else:
            return None

class EditorMKV(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.output_file = None  # Variable de instancia para almacenar el nombre del archivo editado
        self.original_file = None  # NUEVO: para almacenar el archivo original

    def initUI(self):
        self.setWindowTitle('Editor MKV')
        self.setGeometry(100, 100, 400, 400)
        
        self.label_selected_file = QLabel(self)
        self.label_selected_file.setAlignment(Qt.AlignCenter)
        self.label_selected_file.setFont(QFont("Arial", 12))
        self.label_selected_file.setStyleSheet("color: red;")

        self.label_file = QLabel(self)
        self.label_file.setText("Selecciona un archivo MKV:")
        self.label_file.setAlignment(Qt.AlignCenter)
        self.label_file.setFont(QFont("Arial", 12))

        self.button_select = QPushButton('Seleccionar MKV', self)
        self.button_select.clicked.connect(self.selectFile)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label_selected_file)
        self.layout.addWidget(self.label_file)
        self.layout.addWidget(self.button_select)
        
        self.selected_file = None
        self.audio_checkboxes = []
        self.subtitle_checkboxes = []
        self.subtitle_buttons = []  # Lista para almacenar los botones "Extraer"
        self.label_audio = None
        self.label_subtitle = None
        
        self.button_edit = QPushButton('Editar', self)  
        self.button_edit.clicked.connect(self.editFile)  
        self.button_edit.hide()  # Ocultar el botón "Editar" al inicio
        
        self.layout.addWidget(self.button_edit)  
        
        self.button_convert_mp4 = QPushButton('Convertir a MP4', self)
        self.button_convert_mp4.clicked.connect(self.convertToMP4)
        self.button_convert_mp4.hide()  # Ocultar el botón "Convertir a MP4" al inicio
        self.layout.addWidget(self.button_convert_mp4)

        self.setLayout(self.layout)
    
    def selectFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Selecciona un archivo', '', 'Archivos MKV (*.mkv)')
        if filename:
            # Limpiar las listas de pistas de audio y subtítulos
            self.clearAudioAndSubtitleSelection()
            self.clearAudioAndSubtitleLabels()
            self.clearSubtitleButtons()
            
            self.selected_file = filename
            self.original_file = filename  # Guardar el archivo original
            self.label_selected_file.setText(os.path.basename(self.selected_file))
            self.showAudioAndSubtitleSelection()
            self.button_edit.show()
            self.button_convert_mp4.hide()

    def showAudioAndSubtitleSelection(self):
        self.label_audio = QLabel(self)
        self.label_audio.setText("<b>Pistas de audio:</b>")
        self.label_audio.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(self.label_audio)
        
        self.audio_layout = QVBoxLayout()
        self.layout.addLayout(self.audio_layout)
        
        self.label_subtitle = QLabel(self)
        self.label_subtitle.setText("<b>Pistas de subtítulos:</b>")
        self.label_subtitle.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(self.label_subtitle)
        
        self.subtitle_layout = QVBoxLayout()
        self.layout.addLayout(self.subtitle_layout)
        
        mkvmerge_output = subprocess.check_output(["mkvmerge", "-i", "-F", "json", self.selected_file]).decode("utf-8")
        track_info = json.loads(mkvmerge_output)

        for track in track_info["tracks"]:
            if track["type"] == "audio":
                language = track["properties"].get("language", "Desconocido")
                track_id = track["id"]
                checkbox = QCheckBox(f"Idioma: {language}", self)
                checkbox.track_id = track_id  
                self.audio_checkboxes.append(checkbox)
                self.audio_layout.addWidget(checkbox)
            elif track["type"] == "subtitles":
                language = track["properties"].get("language", "Desconocido")
                track_id = track["id"]
                checkbox = QCheckBox(f"Idioma: {language}", self)
                checkbox.track_id = track_id  
                self.subtitle_checkboxes.append(checkbox)
                extract_button = QPushButton("Extraer", self)
                extract_button.clicked.connect(lambda _, tid=track_id: self.extractSubtitle(tid))
                # Conectar el clic del botón a la función extractSubtitle con el ID de la pista de subtítulos como argumento
                layout = QHBoxLayout()
                layout.addWidget(checkbox)
                layout.addWidget(extract_button)
                self.subtitle_layout.addLayout(layout)
                self.subtitle_buttons.append(extract_button)  # Agregar el botón a la lista

    def extractSubtitle(self, track_id):
        output_file = os.path.splitext(self.selected_file)[0] + f"_subtitle_{track_id}.srt"
        args = ["mkvextract", "tracks", self.selected_file, f"{track_id}:{output_file}"]
        subprocess.run(args)
        print(f"Subtítulo extraído correctamente como '{output_file}'.")

    def clearAudioAndSubtitleSelection(self):
        # Limpiar las listas de pistas de audio y subtítulos
        for checkbox in self.audio_checkboxes:
            checkbox.deleteLater()
        self.audio_checkboxes = []
        
        for checkbox in self.subtitle_checkboxes:
            checkbox.deleteLater()
        self.subtitle_checkboxes = []
    
    def clearAudioAndSubtitleLabels(self):
        # Eliminar los labels de pistas de audio y subtítulos si existen
        if self.label_audio:
            self.label_audio.deleteLater()
            self.label_audio = None
        
        if self.label_subtitle:
            self.label_subtitle.deleteLater()
            self.label_subtitle = None

    def clearSubtitleButtons(self):
        # Limpiar los botones "Extraer" si existen
        for button in self.subtitle_buttons:
            button.deleteLater()
        self.subtitle_buttons = []
    
    def editFile(self):
        if self.selected_file:
            selected_audio_tracks = [checkbox for checkbox in self.audio_checkboxes if checkbox.isChecked()]
            selected_subtitle_tracks = [checkbox for checkbox in self.subtitle_checkboxes if checkbox.isChecked()]

            # Obtener los ID de las pistas de audio seleccionadas
            audio_ids = [str(checkbox.track_id) for checkbox in selected_audio_tracks]
            audio_args = [f"--audio-tracks", ",".join(audio_ids)]

            # Verificar si se han seleccionado pistas de subtítulos
            if selected_subtitle_tracks:
                subtitle_ids = [str(checkbox.track_id) for checkbox in selected_subtitle_tracks]
                subtitle_args = [f"--subtitle-tracks", ",".join(subtitle_ids)]
            else:
                subtitle_args = ["--no-subtitles"]  # Agregar el parámetro --no-subtitles si no se seleccionaron subtítulos

            # Obtener el nuevo nombre de archivo del usuario
            new_filename = self.getNewFilename()
            if new_filename:
                # Si el usuario ingresó un nuevo nombre, usarlo para el archivo editado
                if not new_filename.endswith(".mkv"):  # Verificar si ya contiene la extensión .mkv
                    new_filename += ".mkv"  # Si no, agregarla
                output_file = new_filename
            else:
                # Si el usuario canceló, usar el nombre predeterminado
                output_file = os.path.splitext(self.selected_file)[0] + "_edited.mkv"

            args = ["mkvmerge", "-o", output_file] + audio_args + subtitle_args + [self.selected_file]

            print("Argumentos pasados a mkvmerge:")
            print(args)

            subprocess.run(args)
            print("Archivo editado correctamente.")
            
            # Almacenar el nombre del archivo editado en la variable de instancia
            self.output_file = output_file
            
            self.button_convert_mp4.show()  # Mostrar el botón "Convertir a MP4"
        else:
            print("Por favor, selecciona un archivo MKV primero.")


    def getNewFilename(self):
        dialog = FilenameInputDialog(os.path.basename(self.selected_file), self)
        return dialog.getFilename()

    def convertToMP4(self):
        if self.output_file:
            output_file = os.path.splitext(self.output_file)[0] + ".mp4"
            # Guardar los nombres antes de la conversión
            original_mkv = self.original_file
            edited_mkv = self.output_file

            args = ["ffmpeg", "-i", edited_mkv, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-c:s", "mov_text", "-metadata:s:s:0", "language=spa", "-metadata:s:a:0", "language=spa", output_file]
            subprocess.run(args)
            print(f"Archivo convertido a MP4 correctamente como '{output_file}' con subtítulos incrustados y audio/subtítulos en español.")
            self.button_convert_mp4.hide()
            self.playSound()
            try:
                # Eliminar ambos archivos MKV si existen y son distintos
                if original_mkv and os.path.exists(original_mkv):
                    os.remove(original_mkv)
                    print(f"Archivo original '{original_mkv}' eliminado.")
                if edited_mkv and os.path.exists(edited_mkv) and edited_mkv != original_mkv:
                    os.remove(edited_mkv)
                    print(f"Archivo editado '{edited_mkv}' eliminado.")
            except Exception as e:
                print(f"Error al eliminar archivos MKV: {e}")
        else:
            print("Por favor, edita un archivo MKV primero.")

    def playSound(self):
            # Cargar el archivo de sonido
            pygame.mixer.init()
            pygame.mixer.music.load("finish.wav")  # sonifdo
            # Reproducir el sonido
            pygame.mixer.music.play()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = EditorMKV()
    editor.show()
    sys.exit(app.exec_())
