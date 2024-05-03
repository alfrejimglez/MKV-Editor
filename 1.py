import sys
import subprocess
import os
import json
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QLabel, QVBoxLayout, QCheckBox

class EditorMKV(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Editor MKV')
        self.setGeometry(100, 100, 400, 400)
        
        self.label_file = QLabel(self)
        
        self.button_select = QPushButton('Seleccionar MKV', self)
        self.button_select.clicked.connect(self.selectFile)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label_file)
        self.layout.addWidget(self.button_select)
        
        self.selected_file = None
        self.audio_checkboxes = []
        self.subtitle_checkboxes = []
        
        self.button_edit = QPushButton('Editar', self)  
        self.button_edit.clicked.connect(self.editFile)  
        
        self.layout.addWidget(self.button_edit)  
        
        self.setLayout(self.layout)
    
    def selectFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Selecciona un archivo', '', 'Archivos MKV (*.mkv)')
        if filename:
            self.selected_file = filename
            self.showAudioAndSubtitleSelection()
    
    def showAudioAndSubtitleSelection(self):
        self.label_audio = QLabel(self)
        self.label_audio.setText("<b>Pistas de audio:</b>")
        self.layout.addWidget(self.label_audio)
        
        self.audio_layout = QVBoxLayout()
        self.layout.addLayout(self.audio_layout)
        
        self.label_subtitle = QLabel(self)
        self.label_subtitle.setText("<b>Pistas de subtítulos:</b>")
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
                self.subtitle_layout.addWidget(checkbox)


    def editFile(self):
        if self.selected_file:
            selected_audio_tracks = [checkbox for checkbox in self.audio_checkboxes if checkbox.isChecked()]
            selected_subtitle_tracks = [checkbox for checkbox in self.subtitle_checkboxes if checkbox.isChecked()]

            if selected_audio_tracks or selected_subtitle_tracks:
                # Obtener los ID de las pistas de audio seleccionadas
                audio_ids = [str(checkbox.track_id) for checkbox in selected_audio_tracks]
                audio_args = [f"--audio-tracks", ",".join(audio_ids)]

                # Obtener los ID de las pistas de subtítulos seleccionadas
                subtitle_ids = [str(checkbox.track_id) for checkbox in selected_subtitle_tracks]
                subtitle_args = [f"--subtitle-tracks", ",".join(subtitle_ids)]

                output_file = os.path.splitext(self.selected_file)[0] + "_edited.mkv"

                args = ["mkvmerge", "-o", output_file] + audio_args + subtitle_args + [self.selected_file]

                print("Argumentos pasados a mkvmerge:")
                print(args)

                subprocess.run(args)
                print("Archivo editado correctamente.")
            else:
                print("Por favor, selecciona al menos una pista de audio o subtítulos.")
        else:
            print("Por favor, selecciona un archivo MKV primero.")


    def get_track_id(self, track):
        return track["id"]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = EditorMKV()
    editor.show()
    sys.exit(app.exec_())
