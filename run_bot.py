#!/usr/bin/env python3
"""Bot simple para probar el DialogueManager"""

import asyncio
import logging
import os
from pathlib import Path

# Configurar encoding para Windows
if os.name == 'nt':
    import codecs
    import locale
    
    # Intentar usar UTF-8 para la consola
    try:
        codecs.lookup('cp1252')
        # Si estamos en Windows, usar print sin emojis
        WINDOWS_MODE = True
    except:
        WINDOWS_MODE = False

# Agregar directorio actual al path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.dialogue.manager import DialogueManager
from src.persistence.seed import ensure_schema
from src.reminders import reminder_scheduler

try:
    from aiogram import Bot, Dispatcher
    from aiogram.types import Message, ContentType, CallbackQuery
    from aiogram.filters import Command
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    import os
except ImportError:
    print("ERROR: aiogram no instalado. Ejecuta: pip install aiogram")
    exit(1)

# Configurar logging sin emojis para Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar componentes
ensure_schema()
dm = DialogueManager()

# Crear bot
bot = Bot(
    token=settings.TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Comando /start"""
    session_id = str(message.from_user.id)
    response = dm.process_message(session_id, "/start")
    reply_markup = response.get("reply_markup")
    await message.answer(response["reply_text"], reply_markup=reply_markup)

@dp.message(lambda message: message.document or message.photo)
async def handle_document(message: Message):
    """Manejar documentos y fotos (certificados)"""
    session_id = str(message.from_user.id)
    
    try:
        # Determinar si es foto o documento
        if message.photo:
            file_info = await bot.get_file(message.photo[-1].file_id)
            file_name = f"certificado_{session_id}_{message.photo[-1].file_id}.jpg"
        elif message.document:
            file_info = await bot.get_file(message.document.file_id)
            file_name = message.document.file_name or f"certificado_{session_id}_{message.document.file_id}"
        else:
            return
        
        # Crear directorio si no existe
        upload_dir = f"uploads/{session_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Descargar archivo
        file_path = os.path.join(upload_dir, file_name)
        await bot.download_file(file_info.file_path, file_path)
        
        # Procesar con DialogueManager
        response = dm.handle_certificate_upload(session_id, file_path)
        reply_markup = response.get("reply_markup")
        await message.answer(response["reply_text"], reply_markup=reply_markup)
        
        logger.info(f"Certificado recibido de usuario {session_id}: {file_name}")
        
    except Exception as e:
        logger.error(f"Error procesando certificado: {e}")
        await message.answer("Error al procesar el certificado. Por favor intentá nuevamente.")

@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    """Manejar callbacks de inline keyboards"""
    session_id = str(callback.from_user.id)
    
    # Mapear callback_data a texto que entiende el DialogueManager
    callback_map = {
        "adjuntar_ahora": "adjuntar ahora",
        "adjuntar_despues": "enviar mas tarde"
    }
    
    user_text = callback_map.get(callback.data, callback.data)
    logger.info(f"Callback usuario {session_id}: {callback.data} -> {user_text}")
    
    # Procesar como mensaje normal
    response = dm.process_message(session_id, user_text)
    
    # Responder al callback
    await callback.answer()
    
    # Enviar respuesta
    reply_markup = response.get("reply_markup")
    await callback.message.answer(response["reply_text"], reply_markup=reply_markup)

@dp.message()
async def handle_message(message: Message):
    """Procesar todos los mensajes"""
    session_id = str(message.from_user.id)
    user_text = message.text or ""
    
    logger.info(f"Usuario {session_id}: {user_text}")
    
    # Procesar mensaje
    response = dm.process_message(session_id, user_text)
    
    # Enviar respuesta con keyboard si existe
    reply_markup = response.get("reply_markup")
    await message.answer(response["reply_text"], reply_markup=reply_markup)
    
    logger.info(f"Bot responde: {response['reply_text'][:50]}...")

async def main():
    """Función principal"""
    print("Bot iniciando...")
    print(f"Token configurado: {settings.TELEGRAM_TOKEN[:10]}...")
    
    try:
        # Configurar el bot instance para recordatorios
        reminder_scheduler.set_bot_instance(bot)
        
        # Iniciar sistema de recordatorios en background
        reminder_task = asyncio.create_task(reminder_scheduler.start())
        print("Sistema de recordatorios iniciado")
        
        # Iniciar polling
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Error en el bot: {e}")
    finally:
        # Detener recordatorios
        reminder_scheduler.stop()
        if 'reminder_task' in locals():
            reminder_task.cancel()
        
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido por usuario")
    except Exception as e:
        print(f"Error fatal: {e}")