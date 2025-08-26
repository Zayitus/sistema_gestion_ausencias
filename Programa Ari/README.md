# Bot de Ausencias con OCR y Google Sheets

Este bot de Telegram permite registrar avisos de ausencia de empleados, subir certificados médicos y almacenarlos en una planilla de Google Sheets.  
Además, utiliza **OCR** para extraer automáticamente datos de los certificados (fecha, DNI, días de reposo).

## 🚀 Instalación

1. Clonar el proyecto o copiar los archivos (`main_ocr_unificado.py`, `requirements.txt`, etc.).

2. Crear un entorno virtual (opcional pero recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate   # En Linux/Mac
   venv\Scripts\activate    # En Windows
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar las credenciales en un archivo `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=tu_token_aqui
   GS_SERVICE_ACCOUNT_FILE=credenciales.json
   GS_SHEET_ID=tu_id_de_google_sheets
   GS_SHEET_TAB_NAME=Registros
   ```

   - `TELEGRAM_BOT_TOKEN`: Token del bot de Telegram.
   - `GS_SERVICE_ACCOUNT_FILE`: Archivo JSON con credenciales de Google Service Account.
   - `GS_SHEET_ID`: ID de la hoja de Google Sheets.
   - `GS_SHEET_TAB_NAME`: Nombre de la pestaña dentro de la planilla (ej: `Registros`).

5. Asegurarse de tener instalado **Tesseract OCR** en el sistema:  
   - Linux: `sudo apt-get install tesseract-ocr`
   - Windows: descargar de [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
   - Mac: `brew install tesseract`

6. Ejecutar el bot:
   ```bash
   python main_ocr_unificado.py
   ```

## 📌 Funcionalidades principales
- Registro de avisos de ausencia vía Telegram.
- Control de horario de aviso (antes/después de las 10:00 hs).
- Carga de certificados médicos con OCR automático.
- Verificación de fechas, DNI y días de reposo.
- Registro automático en Google Sheets.
- Observaciones en casos especiales (avisos tardíos, certificados subidos fuera de plazo, DNI no coincidente).

## 📄 Requisitos del sistema
- Python 3.10+
- Cuenta de Google Cloud con acceso a Google Sheets API y Google Drive API.
- Tesseract OCR instalado en el sistema.
