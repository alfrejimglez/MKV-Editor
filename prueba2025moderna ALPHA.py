import sys
import os
import subprocess
import json
import pygame
import warnings

# Ocultar warnings de deprecación y bienvenida de pygame
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QLabel, QVBoxLayout,
    QCheckBox, QHBoxLayout, QLineEdit, QDialog, QDialogButtonBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

def resource_path(relative_path):
    """Obtiene la ruta absoluta de un recurso empaquetado con PyInstaller."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class FilenameInputDialog(QDialog):
    def __init__(self, current_filename="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Nombre de Archivo")
        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("Ingrese el nuevo nombre de archivo")
        self.input_line.setText(current_filename)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.input_line)
        layout.addWidget(button_box)

    def getFilename(self):
        return self.input_line.text() if self.exec_() == QDialog.Accepted else None

class EditorMKV(QWidget):
    def __init__(self):
        super().__init__()
        self.output_file = None
        self.original_file = None
        self.selected_file = None
        self.audio_checkboxes = []
        self.subtitle_checkboxes = []
        self.subtitle_buttons = []
        self.label_audio = None
        self.label_subtitle = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Editor MKV')
        self.setGeometry(100, 100, 400, 400)
        layout = QVBoxLayout(self)
        self.label_selected_file = QLabel(self)
        self.label_selected_file.setAlignment(Qt.AlignCenter)
        self.label_selected_file.setFont(QFont("Arial", 12))
        self.label_selected_file.setStyleSheet("color: red;")
        layout.addWidget(self.label_selected_file)

        label_file = QLabel("Selecciona un archivo MKV:", self)
        label_file.setAlignment(Qt.AlignCenter)
        label_file.setFont(QFont("Arial", 12))
        layout.addWidget(label_file)

        button_select = QPushButton('Seleccionar MKV', self)
        button_select.clicked.connect(self.selectFile)
        layout.addWidget(button_select)

        self.button_edit = QPushButton('Editar', self)
        self.button_edit.clicked.connect(self.editFile)
        self.button_edit.hide()
        layout.addWidget(self.button_edit)

        self.button_convert_mp4 = QPushButton('Convertir a MP4', self)
        self.button_convert_mp4.clicked.connect(self.convertToMP4)
        self.button_convert_mp4.hide()
        layout.addWidget(self.button_convert_mp4)

        self.setLayout(layout)

    def selectFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Selecciona un archivo', '', 'Archivos MKV (*.mkv)')
        if filename:
            self.clearAudioAndSubtitleSelection()
            self.clearAudioAndSubtitleLabels()
            self.clearSubtitleButtons()
            self.selected_file = filename
            self.original_file = filename
            self.label_selected_file.setText(os.path.basename(filename))
            self.showAudioAndSubtitleSelection()
            self.button_edit.show()
            self.button_convert_mp4.hide()

    def showAudioAndSubtitleSelection(self):
        self.label_audio = QLabel("<b>Pistas de audio:</b>", self)
        self.label_audio.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout().addWidget(self.label_audio)
        self.audio_layout = QVBoxLayout()
        self.layout().addLayout(self.audio_layout)

        self.label_subtitle = QLabel("<b>Pistas de subtítulos:</b>", self)
        self.label_subtitle.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout().addWidget(self.label_subtitle)
        self.subtitle_layout = QVBoxLayout()
        self.layout().addLayout(self.subtitle_layout)

        mkvmerge_path = resource_path("mkvmerge.exe")
        mkvmerge_output = subprocess.check_output([mkvmerge_path, "-i", "-F", "json", self.selected_file]).decode("utf-8")
        track_info = json.loads(mkvmerge_output)

        for track in track_info.get("tracks", []):
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
                layout = QHBoxLayout()
                layout.addWidget(checkbox)
                layout.addWidget(extract_button)
                self.subtitle_layout.addLayout(layout)
                self.subtitle_buttons.append(extract_button)

    def extractSubtitle(self, track_id):
        output_file = os.path.splitext(self.selected_file)[0] + f"_subtitle_{track_id}.srt"
        args = [resource_path("mkvextract.exe"), "tracks", self.selected_file, f"{track_id}:{output_file}"]
        subprocess.run(args)
        print(f"Subtítulo extraído correctamente como '{output_file}'.")

    def clearAudioAndSubtitleSelection(self):
        for checkbox in self.audio_checkboxes:
            checkbox.deleteLater()
        self.audio_checkboxes.clear()
        for checkbox in self.subtitle_checkboxes:
            checkbox.deleteLater()
        self.subtitle_checkboxes.clear()

    def clearAudioAndSubtitleLabels(self):
        if self.label_audio:
            self.label_audio.deleteLater()
            self.label_audio = None
        if self.label_subtitle:
            self.label_subtitle.deleteLater()
            self.label_subtitle = None

    def clearSubtitleButtons(self):
        for button in self.subtitle_buttons:
            button.deleteLater()
        self.subtitle_buttons.clear()

    def editFile(self):
        if not self.selected_file:
            print("Por favor, selecciona un archivo MKV primero.")
            return

        selected_audio_tracks = [cb for cb in self.audio_checkboxes if cb.isChecked()]
        selected_subtitle_tracks = [cb for cb in self.subtitle_checkboxes if cb.isChecked()]
        audio_ids = [str(cb.track_id) for cb in selected_audio_tracks]
        audio_args = ["--audio-tracks", ",".join(audio_ids)] if audio_ids else ["--no-audio"]
        subtitle_args = (["--subtitle-tracks", ",".join(str(cb.track_id) for cb in selected_subtitle_tracks)]
                         if selected_subtitle_tracks else ["--no-subtitles"])

        new_filename = self.getNewFilename()
        output_file = (new_filename + ".mkv" if new_filename and not new_filename.endswith(".mkv")
                       else new_filename) if new_filename else os.path.splitext(self.selected_file)[0] + "_edited.mkv"

        mkvmerge_path = resource_path("mkvmerge.exe")
        args = [mkvmerge_path, "-o", output_file] + audio_args + subtitle_args + [self.selected_file]
        print("Argumentos pasados a mkvmerge:", args)
        subprocess.run(args)
        print("Archivo editado correctamente.")
        self.output_file = output_file
        self.button_convert_mp4.show()

    def getNewFilename(self):
        dialog = FilenameInputDialog(os.path.basename(self.selected_file), self)
        return dialog.getFilename()

    def convertToMP4(self):
        if not self.output_file:
            print("Por favor, edita un archivo MKV primero.")
            return

        output_file = os.path.splitext(self.output_file)[0] + ".mp4"
        original_mkv = self.original_file
        edited_mkv = self.output_file
        args = [
            "ffmpeg", "-i", edited_mkv, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-c:s", "mov_text", "-metadata:s:s:0", "language=spa", "-metadata:s:a:0", "language=spa", output_file
        ]
        subprocess.run(args)
        print(f"Archivo convertido a MP4 correctamente como '{output_file}' con subtítulos incrustados y audio/subtítulos en español.")
        self.button_convert_mp4.hide()
        self.playSound()
        try:
            if original_mkv and os.path.exists(original_mkv):
                os.remove(original_mkv)
                print(f"Archivo original '{original_mkv}' eliminado.")
            if edited_mkv and os.path.exists(edited_mkv) and edited_mkv != original_mkv:
                os.remove(edited_mkv)
                print(f"Archivo editado '{edited_mkv}' eliminado.")
        except Exception as e:
            print(f"Error al eliminar archivos MKV: {e}")

    def playSound(self):
        sound_path = resource_path("finish.wav")
        pygame.mixer.init()
        pygame.mixer.music.load(sound_path)
        pygame.mixer.music.play()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = EditorMKV()
    editor.show()
    sys.exit(app.exec_())