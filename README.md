# MKV-Editor

Editor MKV con GUI (PyQt5) para seleccionar pistas de audio/subtitulos, extraer subtitulos y convertir a MP4. El log del proceso se muestra dentro de la aplicacion y la exportacion a EXE puede hacerse sin consola.

## Lo que se hizo

- Se agrego un log en la interfaz para ver el progreso de conversiones y procesos.
- Las ejecuciones de mkvmerge/mkvextract/ffmpeg se enrutan al log del GUI.
- Se preparo el empaquetado con PyInstaller en modo sin consola.

## Requisitos

- Python 3.x
- PyQt5
- pygame-ce
- MKVToolNix (mkvmerge/mkvextract) en PATH o junto al ejecutable
- FFmpeg en PATH o junto al ejecutable

Instala dependencias:

```bash
pip install -r requirements.txt
```

## Ejecutar en desarrollo

Si quieres evitar que se abra la consola en Windows durante el desarrollo:

```bash
pythonw.exe "prueba febrero aun SIN PROBAR.py"
```

## Exportar a EXE sin consola

```bash
pyinstaller --onefile --noconsole "prueba febrero aun SIN PROBAR.py"
```

El EXE final se genera en:

```
./dist/prueba febrero aun SIN PROBAR.exe
```

## Notas

- Si no ves herramientas como mkvmerge/mkvextract/ffmpeg, agrega sus rutas al PATH o coloca los binarios junto al EXE.
- El log del GUI muestra los mensajes de conversion y estado del proceso.
