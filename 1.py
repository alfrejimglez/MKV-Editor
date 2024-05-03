import sys
import subprocess
import os
import json
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QLabel, QVBoxLayout, QCheckBox, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class EditorMKV(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
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
        self.label_audio = None
        self.label_subtitle = None
        
        self.button_edit = QPushButton('Editar', self)  
        self.button_edit.clicked.connect(self.editFile)  
        self.button_edit.hide()  # Ocultar el botón "Editar" al inicio
        
        self.layout.addWidget(self.button_edit)  
        
        self.setLayout(self.layout)
    
    def selectFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Selecciona un archivo', '', 'Archivos MKV (*.mkv)')
        if filename:
            # Limpiar las listas de pistas de audio y subtítulos
            self.clearAudioAndSubtitleSelection()
            # Limpiar los labels de pistas de audio y subtítulos
            self.clearAudioAndSubtitleLabels()
            
            self.selected_file = filename
            self.label_selected_file.setText(os.path.basename(self.selected_file))  # Mostrar el nombre del archivo seleccionado
            self.showAudioAndSubtitleSelection()
            self.button_edit.show()  # Mostrar el botón "Editar"
    
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

            output_file = os.path.splitext(self.selected_file)[0] + "_edited.mkv"

            args = ["mkvmerge", "-o", output_file] + audio_args + subtitle_args + [self.selected_file]

            print("Argumentos pasados a mkvmerge:")
            print(args)

            subprocess.run(args)
            print("Archivo editado correctamente.")
        else:
            print("Por favor, selecciona un archivo MKV primero.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = EditorMKV()
    editor.show()
    sys.exit(app.exec_())
