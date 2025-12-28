import sys
import os
import re # Importante para tu función de limpieza
import subprocess
import json
import pygame
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QFileDialog, 
                             QLabel, QVBoxLayout, QCheckBox, QHBoxLayout, 
                             QLineEdit, QDialog, QDialogButtonBox, QFrame, QScrollArea)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt

# --- CONFIGURACIÓN PYINSTALLER (TU LÓGICA) ---
if getattr(sys, 'frozen', False):
    # Si está empaquetado con PyInstaller
    os.chdir(os.path.dirname(sys.executable))
else:
    # Si se ejecuta como script normal
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

def resource_path(relative_path):
    """Obtiene la ruta absoluta de un recurso empaquetado con PyInstaller."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# --- HOJA DE ESTILO (DISEÑO PREMIUM 2026) ---
STYLESHEET = """
    QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
    }
    QLabel { color: #cdd6f4; }
    QLabel#Title {
        font-size: 16px;
        font-weight: bold;
        color: #89b4fa;
        margin-bottom: 5px;
    }
    QLabel#SelectedFile {
        color: #f38ba8;
        font-weight: bold;
        background-color: #313244;
        border-radius: 5px;
        padding: 8px;
        border: 1px solid #45475a;
    }
    QPushButton {
        background-color: #313244;
        border: 1px solid #45475a;
        color: #cdd6f4;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: #45475a;
        border-color: #585b70;
    }
    QPushButton:pressed { background-color: #1e1e2e; }

    /* Botones Específicos */
    QPushButton#PrimaryAction { background-color: #89b4fa; color: #1e1e2e; border: none; }
    QPushButton#PrimaryAction:hover { background-color: #b4befe; }
    
    QPushButton#SuccessAction { background-color: #a6e3a1; color: #1e1e2e; border: none; }
    QPushButton#SuccessAction:hover { background-color: #94e2d5; }

    QPushButton#ToolButton { background-color: #fab387; color: #1e1e2e; border: none; }
    QPushButton#ToolButton:hover { background-color: #f9e2af; }

    QPushButton#SmallButton { padding: 4px 10px; font-size: 12px; background-color: #45475a; }
    
    QCheckBox { spacing: 8px; }
    QCheckBox::indicator {
        width: 18px; height: 18px; border-radius: 4px;
        border: 1px solid #585b70; background-color: #313244;
    }
    QCheckBox::indicator:checked { background-color: #89b4fa; border-color: #89b4fa; }

    QLineEdit {
        background-color: #313244; border: 1px solid #45475a;
        border-radius: 4px; color: #cdd6f4; padding: 5px;
    }
    QDialog { background-color: #1e1e2e; }
"""

class FilenameInputDialog(QDialog):
    def __init__(self, current_filename="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Nombre de Archivo")
        self.setMinimumWidth(450)
        self.setStyleSheet(STYLESHEET) # Aplicar estilo
        
        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("Ingrese el nuevo nombre de archivo")
        self.input_line.setText(current_filename)

        # Botón Auto Clean (Estilizado)
        self.button_auto = QPushButton("✨ Auto Limpiar Nombre (Título + Año)", self)
        self.button_auto.setObjectName("ToolButton") # Estilo Naranja
        self.button_auto.setCursor(Qt.PointingHandCursor)
        self.button_auto.clicked.connect(self.autoCleanFilename)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        button_box = QDialogButtonBox(buttons, Qt.Horizontal, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Cursor mano para botones del dialog
        for button in button_box.buttons():
            button.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel("Nombre del archivo final:", self))
        layout.addWidget(self.input_line)
        layout.addWidget(self.button_auto)
        layout.addWidget(button_box)

    def getFilename(self):
        if self.exec_() == QDialog.Accepted:
            return self.input_line.text()
        else:
            return None

    # --- TU MÉTODO DE LIMPIEZA INTACTO ---
    def autoCleanFilename(self):
        """
        Detecta el título y el año (en cualquier posición), lo limpia y elimina todo lo demás.
        Formato final: 'Título (AÑO).ext'
        """
        original_name = self.input_line.text()
        name, ext = os.path.splitext(original_name)

        # Reemplazar puntos, guiones bajos o múltiples espacios por un solo espacio
        name_clean = re.sub(r'[._]+', ' ', name).strip()

        # 1️⃣ Buscar patrón 'Título (AÑO)' (año entre paréntesis)
        match = re.search(r'^(.*?)\s*\(\s*(19\d{2}|20\d{2})\s*\)', name_clean)
        if match:
            title = match.group(1).strip()
            year = match.group(2)
        else:
            # 2️⃣ Buscar título + año sin paréntesis
            match = re.search(r'^(.*?)(19\d{2}|20\d{2})$', name_clean)
            if not match:
                match = re.search(r'^(.*?)(19\d{2}|20\d{2})\D', name_clean)
            if match:
                title = match.group(1).strip()
                year = match.group(2)
            else:
                self.input_line.setText(name_clean + ext)
                return

        # Limpiar espacios dobles y dejar formato correcto
        title = re.sub(r'\s{2,}', ' ', title).strip()
        clean_name = f"{title} ({year}){ext}"
        self.input_line.setText(clean_name)

class EditorMKV(QWidget):
    def __init__(self):
        super().__init__()
        self.output_file = None 
        self.original_file = None # Variable importante para el borrado
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Editor MKV')
        self.setGeometry(100, 100, 500, 650)
        self.setStyleSheet(STYLESHEET)
        
        # --- UI LAYOUT ---
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        # Header
        self.label_file = QLabel("1. Selecciona tu archivo MKV origen:", self)
        self.label_file.setObjectName("Title")
        self.label_file.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.label_file)

        # Botón Seleccionar
        self.button_select = QPushButton('Seleccionar MKV', self)
        self.button_select.setObjectName("PrimaryAction")
        self.button_select.setCursor(Qt.PointingHandCursor)
        self.button_select.setMinimumHeight(40)
        self.button_select.clicked.connect(self.selectFile)
        self.main_layout.addWidget(self.button_select)

        # Label Archivo Seleccionado
        self.label_selected_file = QLabel("Ningún archivo seleccionado", self)
        self.label_selected_file.setObjectName("SelectedFile")
        self.label_selected_file.setAlignment(Qt.AlignCenter)
        self.label_selected_file.setWordWrap(True)
        self.main_layout.addWidget(self.label_selected_file)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #45475a;")
        self.main_layout.addWidget(line)

        # Área de Scroll para Pistas
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")
        
        self.tracks_container = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setSpacing(10)
        self.tracks_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.tracks_container)
        
        self.main_layout.addWidget(self.scroll_area)

        # Botones Finales
        self.main_layout.addStretch()
        
        self.button_edit = QPushButton('Procesar y Editar MKV', self)  
        self.button_edit.setObjectName("PrimaryAction")
        self.button_edit.setMinimumHeight(45)
        self.button_edit.setCursor(Qt.PointingHandCursor)
        self.button_edit.clicked.connect(self.editFile)  
        self.button_edit.hide() 
        self.main_layout.addWidget(self.button_edit)
        
        self.button_convert_mp4 = QPushButton('Convertir a MP4 (Borra originales)', self)
        self.button_convert_mp4.setObjectName("SuccessAction")
        self.button_convert_mp4.setMinimumHeight(45)
        self.button_convert_mp4.setCursor(Qt.PointingHandCursor)
        self.button_convert_mp4.clicked.connect(self.convertToMP4)
        self.button_convert_mp4.hide() 
        self.main_layout.addWidget(self.button_convert_mp4)

        self.setLayout(self.main_layout)

        # Variables lógicas
        self.selected_file = None
        self.audio_checkboxes = []
        self.subtitle_checkboxes = []
        self.subtitle_buttons = []
        self.label_audio = None
        self.label_subtitle = None
        self.audio_layout = None
        self.subtitle_layout = None
    
    def selectFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Selecciona un archivo', '', 'Archivos MKV (*.mkv)')
        if filename:
            self.clearAudioAndSubtitleSelection()
            self.clearAudioAndSubtitleLabels()
            self.clearSubtitleButtons()
            
            self.selected_file = filename
            self.original_file = filename # TU LÓGICA
            
            # Solo mostrar nombre base para limpieza visual
            self.label_selected_file.setText(f"📄 {os.path.basename(self.selected_file)}")
            self.showAudioAndSubtitleSelection()
            self.button_edit.show()
            self.button_convert_mp4.hide()

    def showAudioAndSubtitleSelection(self):
        # Crear headers dentro del scroll
        self.label_audio = QLabel("🔊 Pistas de Audio:", self)
        self.label_audio.setObjectName("Title")
        self.tracks_layout.addWidget(self.label_audio)
        
        self.audio_layout = QVBoxLayout()
        self.tracks_layout.addLayout(self.audio_layout)
        
        self.tracks_layout.addSpacing(15)

        self.label_subtitle = QLabel("💬 Pistas de Subtítulos:", self)
        self.label_subtitle.setObjectName("Title")
        self.tracks_layout.addWidget(self.label_subtitle)
        
        self.subtitle_layout = QVBoxLayout()
        self.tracks_layout.addLayout(self.subtitle_layout)
        
        # TU LÓGICA DE LECTURA (mkvmerge)
        try:
            mkvmerge_output = subprocess.check_output(["mkvmerge", "-i", "-F", "json", self.selected_file]).decode("utf-8")
            track_info = json.loads(mkvmerge_output)

            for track in track_info["tracks"]:
                if track["type"] == "audio":
                    language = track["properties"].get("language", "Desconocido")
                    track_id = track["id"]
                    
                    checkbox = QCheckBox(f"ID {track_id} | Idioma: {language}", self)
                    checkbox.track_id = track_id  
                    checkbox.setCursor(Qt.PointingHandCursor)
                    
                    self.audio_checkboxes.append(checkbox)
                    self.audio_layout.addWidget(checkbox)
                    
                elif track["type"] == "subtitles":
                    language = track["properties"].get("language", "Desconocido")
                    track_id = track["id"]
                    
                    checkbox = QCheckBox(f"ID {track_id} | Idioma: {language}", self)
                    checkbox.track_id = track_id
                    checkbox.setCursor(Qt.PointingHandCursor)
                    self.subtitle_checkboxes.append(checkbox)
                    
                    extract_button = QPushButton("Extraer", self)
                    extract_button.setObjectName("SmallButton")
                    extract_button.setCursor(Qt.PointingHandCursor)
                    extract_button.setFixedWidth(80)
                    extract_button.clicked.connect(lambda _, tid=track_id: self.extractSubtitle(tid))
                    
                    h_layout = QHBoxLayout()
                    h_layout.addWidget(checkbox)
                    h_layout.addStretch()
                    h_layout.addWidget(extract_button)
                    
                    self.subtitle_layout.addLayout(h_layout)
                    self.subtitle_buttons.append(extract_button)
        except Exception as e:
            self.label_selected_file.setText(f"Error: {str(e)}")

    def extractSubtitle(self, track_id):
        output_file = os.path.splitext(self.selected_file)[0] + f"_subtitle_{track_id}.srt"
        args = ["mkvextract", "tracks", self.selected_file, f"{track_id}:{output_file}"]
        subprocess.run(args)
        print(f"Subtítulo extraído correctamente como '{output_file}'.")

    def clearAudioAndSubtitleSelection(self):
        for checkbox in self.audio_checkboxes:
            checkbox.deleteLater()
        self.audio_checkboxes = []
        for checkbox in self.subtitle_checkboxes:
            checkbox.deleteLater()
        self.subtitle_checkboxes = []
    
    def clearAudioAndSubtitleLabels(self):
        if self.label_audio:
            self.label_audio.deleteLater()
            self.label_audio = None
            self.audio_layout.deleteLater()
            self.audio_layout = None
        if self.label_subtitle:
            self.label_subtitle.deleteLater()
            self.label_subtitle = None
            self.subtitle_layout.deleteLater()
            self.subtitle_layout = None

    def clearSubtitleButtons(self):
        for button in self.subtitle_buttons:
            button.deleteLater()
        self.subtitle_buttons = []
    
    def editFile(self):
        if self.selected_file:
            selected_audio_tracks = [checkbox for checkbox in self.audio_checkboxes if checkbox.isChecked()]
            selected_subtitle_tracks = [checkbox for checkbox in self.subtitle_checkboxes if checkbox.isChecked()]

            audio_ids = [str(checkbox.track_id) for checkbox in selected_audio_tracks]
            audio_args = [f"--audio-tracks", ",".join(audio_ids)]

            if selected_subtitle_tracks:
                subtitle_ids = [str(checkbox.track_id) for checkbox in selected_subtitle_tracks]
                subtitle_args = [f"--subtitle-tracks", ",".join(subtitle_ids)]
            else:
                subtitle_args = ["--no-subtitles"]

            new_filename = self.getNewFilename()
            if new_filename:
                if not new_filename.endswith(".mkv"):
                    new_filename += ".mkv"
                output_file = new_filename
            else:
                output_file = os.path.splitext(self.selected_file)[0] + "_edited.mkv"

            # TU LÓGICA CRÍTICA: resource_path
            mkvmerge_path = resource_path("mkvmerge.exe")
            args = [mkvmerge_path, "-o", output_file] + audio_args + subtitle_args + [self.selected_file]

            print("Argumentos pasados a mkvmerge:", args)
            subprocess.run(args)
            print("Archivo editado correctamente.")
            
            self.output_file = output_file
            
            # Feedback visual
            self.button_edit.setText("✅ Archivo MKV Generado")
            self.button_edit.setDisabled(True)
            self.button_convert_mp4.show()
        else:
            print("Por favor, selecciona un archivo MKV primero.")

    def getNewFilename(self):
        dialog = FilenameInputDialog(os.path.basename(self.selected_file), self)
        return dialog.getFilename()

    def convertToMP4(self):
        if self.output_file:
            output_file = os.path.splitext(self.output_file)[0] + ".mp4"
            original_mkv = self.original_file
            edited_mkv = self.output_file

            # Feedback visual
            self.button_convert_mp4.setText("⏳ Convirtiendo y Limpiando...")
            self.button_convert_mp4.setDisabled(True)
            QApplication.processEvents()

            args = ["ffmpeg", "-i", edited_mkv, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-c:s", "mov_text", "-metadata:s:s:0", "language=spa", "-metadata:s:a:0", "language=spa", output_file]
            subprocess.run(args)
            
            print(f"Convertido a MP4: '{output_file}'")
            self.button_convert_mp4.hide()
            self.playSound()
            
            # TU LÓGICA DE BORRADO DE ARCHIVOS
            try:
                if original_mkv and os.path.exists(original_mkv):
                    os.remove(original_mkv)
                    print(f"Original eliminado: {original_mkv}")
                if edited_mkv and os.path.exists(edited_mkv) and edited_mkv != original_mkv:
                    os.remove(edited_mkv)
                    print(f"Temporal eliminado: {edited_mkv}")
                
                self.button_edit.setText("Proceso Terminado (Reiniciar App)")
                self.label_selected_file.setText(f"✅ FINALIZADO: {os.path.basename(output_file)}")
                
            except Exception as e:
                print(f"Error eliminando archivos: {e}")
        else:
            print("Por favor, edita un archivo MKV primero.")

    def playSound(self):
        # TU LÓGICA: resource_path
        try:
            sound_path = resource_path("finish.wav")
            pygame.mixer.init()
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error de sonido: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    editor = EditorMKV()
    editor.show()
    sys.exit(app.exec_())