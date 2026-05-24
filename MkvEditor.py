import sys
import os
import re
import subprocess
import json
import glob
import shutil
import tempfile
import pygame
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QFileDialog, 
                             QLabel, QVBoxLayout, QCheckBox, QHBoxLayout, 
                             QLineEdit, QDialog, QDialogButtonBox, QFrame, QScrollArea)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# --- CONFIGURACIÓN PYINSTALLER (mi LÓGICA dbf) ---
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

def persistent_resource_path(relative_path):
    """Copia recursos de PyInstaller a una ruta estable para usos tardios."""
    source_path = resource_path(relative_path)
    if not getattr(sys, 'frozen', False):
        return source_path

    cache_dir = os.path.join(tempfile.gettempdir(), "mkv_editor_resources")
    os.makedirs(cache_dir, exist_ok=True)
    cached_path = os.path.join(cache_dir, os.path.basename(relative_path))

    if not os.path.exists(cached_path):
        shutil.copy2(source_path, cached_path)

    return cached_path

# --- HOJA DE ESTILO
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

class ConversionWorker(QThread):
    """Worker para ejecutar la conversión a MP4 en un hilo separado"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    message = pyqtSignal(str)
    
    def __init__(self, output_file, original_mkv, edited_mkv):
        super().__init__()
        self.output_file = output_file
        self.original_mkv = original_mkv
        self.edited_mkv = edited_mkv
    
    def run(self):
        try:
            # Detectar si hay PGS en el MKV editado
            has_pgs = False
            pgs_track_id = None
            try:
                mkvmerge_output = subprocess.check_output(["mkvmerge", "-i", "-F", "json", self.edited_mkv]).decode("utf-8")
                track_info = json.loads(mkvmerge_output)
                for track in track_info["tracks"]:
                    if track["type"] == "subtitles":
                        codec = track["properties"].get("codec_id", "")
                        if "hdmv_pgs" in codec.lower() or "pgs" in codec.lower():
                            has_pgs = True
                            pgs_track_id = track["id"]
                            break
            except:
                has_pgs = False

            # Si hay PGS, hacer OCR primero
            if has_pgs:
                self.message.emit("Detectados subtítulos PGS. Haciendo OCR...")
                temp_sup = os.path.splitext(self.edited_mkv)[0] + "_pgs.sup"
                temp_srt = os.path.splitext(self.edited_mkv)[0] + "_pgs.srt"

                try:
                    # Extraer PGS a SUP
                    subprocess.run(["mkvextract", "tracks", self.edited_mkv, f"{pgs_track_id}:{temp_sup}"], check=True)
                    self.message.emit(f"Extraído PGS a SUP: {temp_sup}")

                    # Convertir SUP a SRT con SubtitleEdit
                    ocr_args = ["SubtitleEdit", "/convert", temp_sup, "subrip", "/ocrengine:tesseract", "/overwrite"]
                    subprocess.run(ocr_args, check=True, timeout=120)
                    self.message.emit(f"Convertido a SRT con OCR: {temp_srt}")

                    # FFmpeg con SRT incrustado
                    args = ["ffmpeg", "-y", "-i", self.edited_mkv, "-i", temp_srt, "-map", "0:v", "-map", "0:a", "-map", "1:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-c:s", "mov_text", "-metadata:s:a:0", "language=spa", "-metadata:s:a:0", "title=Spanish", "-metadata:s:s:0", "language=spa", "-metadata:s:s:0", "title=Spanish", self.output_file]
                    subprocess.run(args, check=True)
                    self.message.emit(f"Convertido a MP4 con subtítulos: '{self.output_file}'")

                except Exception as e:
                    self.message.emit(f"Error en OCR, intentando sin subtítulos: {e}")
                    # Fallback: convertir sin subtítulos
                    args = ["ffmpeg", "-y", "-i", self.edited_mkv, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-metadata:s:a:0", "language=spa", "-metadata:s:a:0", "title=Spanish", self.output_file]
                    subprocess.run(args, check=True)
                    self.message.emit(f"Convertido a MP4 sin subtítulos: '{self.output_file}'")
            else:
                # Sin PGS: conversión simple
                args = ["ffmpeg", "-y", "-i", self.edited_mkv, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-c:s", "mov_text", "-metadata:s:a:0", "language=spa", "-metadata:s:a:0", "title=Spanish", "-metadata:s:s:0", "language=spa", "-metadata:s:s:0", "title=Spanish", self.output_file]
                subprocess.run(args, check=True)
                self.message.emit(f"Convertido a MP4: '{self.output_file}'")

            # Limpieza de archivos
            try:
                if self.original_mkv and os.path.exists(self.original_mkv):
                    os.remove(self.original_mkv)
                    self.message.emit(f"Original eliminado: {self.original_mkv}")
                if self.edited_mkv and os.path.exists(self.edited_mkv) and self.edited_mkv != self.original_mkv:
                    os.remove(self.edited_mkv)
                    self.message.emit(f"Temporal eliminado: {self.edited_mkv}")

                # Eliminar archivos temporales _pgs*.srt y _pgs*.sup generados por OCR
                pgs_srt_files = glob.glob(os.path.splitext(self.edited_mkv)[0] + "_pgs*")
                for srt_file in pgs_srt_files:
                    try:
                        if os.path.exists(srt_file):
                            os.remove(srt_file)
                            self.message.emit(f"Temporal eliminado: {srt_file}")
                    except Exception:
                        pass

                self.message.emit(f"✅ FINALIZADO: {os.path.basename(self.output_file)}")
            except Exception as e:
                self.error.emit(f"Error eliminando archivos: {e}")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

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

    # --- MÉTODO DE LIMPIEZA  desde la 1º version q habiaempeezadoensumomento ---
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
        self.conversion_worker = None  # Worker para conversión en background
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

        self.button_play = QPushButton('Reproducir MKV', self)
        self.button_play.setObjectName("ToolButton")
        self.button_play.setCursor(Qt.PointingHandCursor)
        self.button_play.setMinimumHeight(40)
        self.button_play.clicked.connect(self.playSelectedMKV)
        self.button_play.hide()
        self.main_layout.addWidget(self.button_play)

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
        self.scroll_area.setMinimumHeight(300)
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

        # Botones de verificación PGS (solo si hay HDMV PGS)
        self.button_check_tools = QPushButton("Comprobar SubtitleEdit/Tesseract", self)
        self.button_check_tools.setObjectName("ToolButton")
        self.button_check_tools.setCursor(Qt.PointingHandCursor)
        self.button_check_tools.hide()
        self.main_layout.addWidget(self.button_check_tools)

        self.button_add_paths = QPushButton("Añadir rutas necesarias a PATH", self)
        self.button_add_paths.setObjectName("ToolButton")
        self.button_add_paths.setCursor(Qt.PointingHandCursor)
        self.button_add_paths.hide()
        self.main_layout.addWidget(self.button_add_paths)

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

        # Botón para abrir otra instancia (Nueva Ventana)
        self.button_new_instance = QPushButton('➕ Abrir otra ventana', self)
        self.button_new_instance.setObjectName("ToolButton") # Usará el estilo naranja/púrpura
        self.button_new_instance.setStyleSheet("background-color: #cba6f7; color: #1e1e2e;") # Color púrpura premium
        self.button_new_instance.setCursor(Qt.PointingHandCursor)
        self.button_new_instance.clicked.connect(self.openNewInstance)
        self.main_layout.addWidget(self.button_new_instance)
    
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
            self.button_play.show()
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
        has_pgs = False
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
                    codec = track["properties"].get("codec_id", "")

                    # Detectar si hay PGS
                    if "hdmv_pgs" in codec.lower() or "pgs" in codec.lower():
                        has_pgs = True

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

        # Mostrar botones de verificación solo si hay PGS
        if has_pgs:
            self.button_check_tools.show()
            self.button_add_paths.show()
        else:
            self.button_check_tools.hide()
            self.button_add_paths.hide()

    def extractSubtitle(self, track_id):
        output_file = os.path.splitext(self.selected_file)[0] + f"_subtitle_{track_id}.srt"
        args = ["mkvextract", "tracks", self.selected_file, f"{track_id}:{output_file}"]
        subprocess.run(args)
        print(f"Subtítulo extraído correctamente como '{output_file}'.")

    def openNewInstance(self):
        """Lanza una nueva copia desplazada respecto a la ventana actual."""
        try:
            # 1. Obtenemos la posición actual de esta ventana (la que tiene el botón)
            current_x = self.x()
            current_y = self.y()
            
            # 2. Calculamos la nueva posición (desplazada 40px)
            new_x = current_x + 40
            new_y = current_y + 40
            
            # 3. LANZAMIENTO LIMPIO:
            # Usamos sys.argv[0] para coger solo la ruta del programa 
            # y le pasamos solo los nuevos parámetros de posición.
            subprocess.Popen([sys.executable, sys.argv[0], "--pos", str(new_x), str(new_y)])
            
        except Exception as e:
            print(f"No se pudo abrir una nueva instancia: {e}")

    def playSelectedMKV(self):
        if self.selected_file and os.path.exists(self.selected_file):
            try:
                if sys.platform.startswith('win'):
                    os.startfile(self.selected_file)
                else:
                    subprocess.Popen(['xdg-open' if sys.platform.startswith('linux') else 'open', self.selected_file])
            except Exception as e:
                print(f"Error al reproducir el MKV: {e}")
                self.label_selected_file.setText(f"❌ No se pudo reproducir: {e}")
        else:
            self.label_selected_file.setText("❌ Selecciona un archivo MKV primero.")

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

            # Forzar idioma SPA en todas las pistas seleccionadas
            language_args = []
            for track_id in audio_ids:
                language_args.extend(["--language", f"{track_id}:spa"])

            if selected_subtitle_tracks:
                subtitle_ids = [str(checkbox.track_id) for checkbox in selected_subtitle_tracks]
                subtitle_args = [f"--subtitle-tracks", ",".join(subtitle_ids)]
                for track_id in subtitle_ids:
                    language_args.extend(["--language", f"{track_id}:spa"])
            else:
                subtitle_args = ["--no-subtitles"]

            new_filename = self.getNewFilename()
            if not new_filename:
                return

            if not new_filename.endswith(".mkv"):
                new_filename += ".mkv"
            output_file = new_filename

            # TU LÓGICA CRÍTICA: resource_path
            mkvmerge_path = resource_path("mkvmerge.exe")
            args = [mkvmerge_path, "-o", output_file] + audio_args + subtitle_args + language_args + [self.selected_file]

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
            if self.conversion_worker is not None and self.conversion_worker.isRunning():
                print("Ya hay una conversión en curso...")
                return
            
            output_file = os.path.splitext(self.output_file)[0] + ".mp4"
            original_mkv = self.original_file
            edited_mkv = self.output_file

            # Feedback visual
            self.button_convert_mp4.setText("⏳ Convirtiendo y Limpiando...")
            self.button_convert_mp4.setDisabled(True)

            # Crear y configurar el worker
            self.conversion_worker = ConversionWorker(output_file, original_mkv, edited_mkv)
            self.conversion_worker.message.connect(self.on_conversion_message)
            self.conversion_worker.error.connect(self.on_conversion_error)
            self.conversion_worker.finished.connect(self.on_conversion_finished)
            
            # Iniciar el worker en un hilo separado
            self.conversion_worker.start()
        else:
            print("Por favor, edita un archivo MKV primero.")

    def on_conversion_message(self, msg):
        """Actualiza la interfaz con mensajes del worker"""
        print(msg)
        self.label_selected_file.setText(msg)
        QApplication.processEvents()

    def on_conversion_error(self, error_msg):
        """Maneja errores del worker"""
        print(f"Error en conversión: {error_msg}")
        self.label_selected_file.setText(f"❌ Error: {error_msg}")
        self.button_convert_mp4.setText("Convertir a MP4 (Borra originales)")
        self.button_convert_mp4.setDisabled(False)

    def on_conversion_finished(self):
        """Se ejecuta cuando la conversión termina"""
        print("Conversión completada")
        self.button_convert_mp4.hide()
        self.playSound()
        self.button_edit.setText("Proceso Terminado (Reiniciar App)")
        self.button_edit.setDisabled(True)

        # Preguntar si quiere ejecutar srtDIRECTOcompatibleconMKVconargumentos.exe sobre el archivo generado
        from PyQt5.QtWidgets import QMessageBox
        mp4_file = os.path.splitext(self.output_file)[0] + ".mp4"
        if os.path.exists(mp4_file):
            reply = QMessageBox.question(self, "¿Ejecutar srtDIRECTO?",
                f"¿Quieres ejecutar srtDIRECTOcompatibleconMKVconargumentos.exe sobre el archivo generado?\n\n{os.path.basename(mp4_file)}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                # Ejecutar srtDIRECTOcompatibleconMKVconargumentos.exe con el archivo como argumento
                try:
                    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "srtDIRECTOcompatibleconMKVconargumentos.exe")
                    subprocess.Popen([exe_path, mp4_file])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"No se pudo ejecutar srtDIRECTOcompatibleconMKVconargumentos.exe:\n{e}")

    def playSound(self):
        # TU LÓGICA: resource_path
        try:
            sound_path = persistent_resource_path("finish.wav")
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error de sonido: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    try:
        persistent_resource_path("finish.wav")
    except Exception:
        pass
    
    editor = EditorMKV()
    
    # --- LÓGICA DE POSICIONAMIENTO CORREGIDA ---
    args = QApplication.arguments() # Es más fiable que sys.argv en algunos casos
    if "--pos" in args:
        try:
            idx = args.index("--pos")
            nx = int(args[idx + 1])
            ny = int(args[idx + 2])
            editor.move(nx, ny) 
        except (IndexError, ValueError):
            pass 
    # -------------------------------------------

    editor.show()
    sys.exit(app.exec_())
