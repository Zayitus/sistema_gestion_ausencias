from __future__ import annotations

import logging
from typing import Optional

try:
	from aiogram import Bot, Dispatcher, F
	from aiogram.filters import Command
	from aiogram.types import Message, CallbackQuery
	exists_aiogram = True
except Exception:  # aiogram no instalado aún
	exists_aiogram = False
	Bot = Dispatcher = Message = object  # type: ignore

from ..dialogue.manager import DialogueManager
from ..session_store import set_legajo
from ..persistence.seed import ensure_schema
from ..persistence.dao import session_scope
from ..persistence.models import Employee
from ..config import settings

logging.basicConfig(level=logging.INFO)


_dm = DialogueManager()


async def start_bot(token: str) -> None:
	"""Inicia el bot de Telegram (aiogram 3.x)."""
	if not exists_aiogram:
		print("aiogram no está disponible. Instálalo con requirements.txt")
		return
	
	print(f"Inicializando DialogueManager...")
	try:
		_dm_test = DialogueManager()
		print("DialogueManager inicializado correctamente")
	except Exception as e:
		print(f"Error inicializando DialogueManager: {e}")
		return
	
	bot = Bot(token)
	dp = Dispatcher()
	print(f"Bot configurado, registrando handlers...")

	# Comando /id <legajo>
	@dp.message(Command("id"))
	async def handle_id(msg: Message) -> None:
		try:
			parts = (msg.text or "").split()
			if len(parts) < 2:
				await msg.reply("Usá: /id <legajo> (por ejemplo /id 1001)")
				return
			from ..utils.normalize import parse_legajo
			legajo_digits = parse_legajo(parts[1].strip()) or ""
			if not legajo_digits:
				await msg.reply("Formato inválido. Usá /id 1234 (4 dígitos)")
				return
			# Validar en BD mínima
			ensure_schema()
			with session_scope() as s:
				emp = s.query(Employee).filter(Employee.legajo == legajo_digits).first()
			if not emp:
				await msg.reply("No encontré ese legajo en el sistema. Revisá y volvé a intentar.")
				return
			set_legajo(str(msg.chat.id), legajo_digits)
			_dm.set_legajo_validado(str(msg.chat.id), legajo_digits)
			# Incluir nombre si está disponible
			nombre = getattr(emp, "nombre", None)
			if nombre:
				await msg.reply(f"Listo, {nombre} (legajo {legajo_digits}) verificado")
			else:
				await msg.reply(f"Listo, legajo {legajo_digits} verificado")
		except Exception as e:
			await msg.reply(f"No pude guardar el legajo: {e}")

	# Comando /export_csv (solo demo)
	@dp.message(Command("export_csv"))
	async def handle_export(msg: Message) -> None:
		try:
			if not settings.DEMO_EXPORT:
				await msg.reply("Comando no disponible en este entorno.")
				return
			ensure_schema()
			from ..persistence.export_powerbi import export_all_csv
			export_all_csv(out_dir="./exports")
			await msg.reply("Export listo en /exports (employees.csv, avisos.csv, certificados.csv, notificaciones.csv, auditoria.csv)")
		except Exception as e:
			await msg.reply(f"Error en export: {e}")

	# Handler simplificado para testing
	@dp.message()
	async def handle_message(msg: Message) -> None:
		print(f"MENSAJE RECIBIDO de {msg.chat.id}: {msg.text}")
		logging.info(f"Mensaje recibido de {msg.chat.id}: {msg.text}")
		
		try:
			# Respuesta simple primero para confirmar que funciona
			if msg.text and msg.text.startswith('/start'):
				await msg.reply("Bot funcionando! Soy el sistema de ausencias.")
			elif msg.text and msg.text.startswith('/help'):
				await msg.reply("Puedo ayudarte con avisos de ausencias. Enviá tu legajo y motivo.")
			elif msg.text:
				print(f"Procesando con DialogueManager: {msg.text}")
				session_id = str(msg.chat.id)
				result = _dm.process_message(session_id, msg.text)
				# No imprimir el resultado completo para evitar emojis
				# Limpiar preview de respuesta
				reply_preview = str(result.get('reply_text', ''))[:50]
				import re
				reply_preview = re.sub(r'[\U0001F600-\U0001F6FF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', '', reply_preview)
				print(f"Respuesta generada: {reply_preview}...")
				
				reply_text = result.get("reply_text", "Sistema procesado")
				# Limpiar emojis problemáticos
				if reply_text:
					import re
					reply_text = re.sub(r'[\U0001F600-\U0001F6FF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', '', reply_text)
				
				reply_markup = result.get("reply_markup")
				# Adjuntar teclados reales solo si aiogram está disponible y el objeto parece un markup
				if exists_aiogram and reply_markup is not None and not isinstance(reply_markup, str):
					await msg.reply(reply_text, reply_markup=reply_markup)
				else:
					await msg.reply(reply_text)
				# Mensajes adicionales (ej.: pedir adjuntar documento)
				for extra in (result.get("messages") or []):
					text2 = extra.get("reply_text") or extra.get("text") or ""
					# Limpiar emojis de mensajes adicionales
					if text2:
						import re
						text2 = re.sub(r'[\U0001F600-\U0001F6FF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', '', text2)
					
					mk2 = extra.get("reply_markup") or extra.get("markup")
					if exists_aiogram and mk2 is not None and not isinstance(mk2, str):
						await msg.reply(text2, reply_markup=mk2)
					else:
						await msg.reply(text2)
			else:
				# Manejo básico de documentos/imagenes
				try:
					f = msg.document or msg.photo[-1] if hasattr(msg, "photo") and msg.photo else msg.document  # type: ignore[attr-defined]
					if f is None:
						await msg.reply("Documento o tipo de mensaje no soportado aún")
						return
					# Descargar archivo a uploads/ y además subirlo a Google Drive.
					# Estructura local: uploads/<chat_id>/[<id_aviso>/]<file_id>.<ext>
					path_dir = "uploads"
					import os
					from datetime import date
					os.makedirs(path_dir, exist_ok=True)
					file = await bot.get_file(f.file_id)  # type: ignore[attr-defined]
					# Extensión: si es Document usamos su nombre; si es Photo, forzamos .jpg
					file_ext = ""
					if getattr(f, "file_name", None):
						file_ext = os.path.splitext(f.file_name)[1]
					elif getattr(msg, "photo", None):
						file_ext = ".jpg"
					local_name = f"{f.file_id}{file_ext}"  # type: ignore[attr-defined]
					# Carpeta por chat siempre
					chat_dir = os.path.join(path_dir, str(msg.chat.id))
					os.makedirs(chat_dir, exist_ok=True)
					local_path = os.path.join(chat_dir, local_name)
					await bot.download_file(file.file_path, destination=local_path)

					# Subir a Google Drive y obtener enlace (opcional)
					drive_link = ""
					try:
						from ..utils.drive_upload import upload_file  # import aquí para evitar carga lenta inicial
						drive_link = upload_file(local_path, filename=os.path.basename(local_path), mime_type="image/jpeg" if file_ext.lower() in {".jpg", ".jpeg", ".png"} else "application/octet-stream")
						logging.info(f"Archivo subido a Drive: {drive_link}")
					except Exception as exc:
						logging.warning(f"Google Drive no configurado o error: {exc}")
						drive_link = ""  # Continuar sin Drive

					# Intentar vincular a último aviso del usuario (simple: por legajo en sesión si existe id_aviso en facts)
					session_id = str(msg.chat.id)
					state = _dm.sessions.get(session_id, {})
					facts = state.get("facts", {})
					id_aviso = facts.get("id_aviso")
					if not id_aviso:
						# Nuevo flujo: guardar certificado en facts para usar al crear aviso
						facts["certificado_archivo_nombre"] = os.path.basename(local_path)
						facts["certificado_archivo_path"] = drive_link or local_path
						facts["certificado_documento_legible"] = True
						facts["certificado_fecha_recepcion"] = date.today().isoformat()
						facts["certificado_recibido"] = True
						
						# Actualizar sesión
						state["facts"] = facts
						_dm.sessions[session_id] = state
						
						await msg.reply("Certificado recibido y guardado.")
						
						# Continuar automáticamente con el flujo (simular "adjuntar ahora")
						result = _dm.process_message(session_id, "adjuntar ahora")
						if result and result.get("reply_text"):
							reply_text = result["reply_text"]
							# Limpiar emojis
							import re
							reply_text = re.sub(r'[\U0001F600-\U0001F6FF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', '', reply_text)
							await msg.reply(reply_text)
							# Si hay mensajes adicionales
							for extra in (result.get("messages") or []):
								text2 = extra.get("reply_text") or extra.get("text") or ""
								if text2:
									text2 = re.sub(r'[\U0001F600-\U0001F6FF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', '', text2)
									await msg.reply(text2)
					else:
						from ..persistence.dao import update_certificado
						# Mover a carpeta por id_aviso
						id_dir = os.path.join(path_dir, str(msg.chat.id), id_aviso)
						os.makedirs(id_dir, exist_ok=True)
						new_path = os.path.join(id_dir, os.path.basename(local_path))
						try:
							os.replace(local_path, new_path)
						except Exception:
							new_path = local_path
						res = update_certificado(id_aviso, {
							"archivo_nombre": os.path.basename(local_path),
							"archivo_path": drive_link or new_path,
							"documento_tipo": facts.get("documento_tipo"),
							"documento_legible": True,
							"fecha_recepcion": facts.get("fecha_recepcion") or facts.get("fecha_inicio") or date.today().isoformat(),
						})
						await msg.reply(f"Documento recibido. Estado certificado: {res.get('estado_certificado')}")
				except Exception as e:
					await msg.reply(f"No pude procesar el archivo: {e}")
				
		except Exception as e:
			print(f"ERROR: {e}")
			logging.error(f"Error procesando mensaje: {e}", exc_info=True)
			await msg.reply(f"Error: {str(e)}")

	# Callbacks para inline keyboard de adjuntar certificado
	@dp.callback_query()
	async def handle_callbacks(cb: CallbackQuery) -> None:
		try:
			if not cb.data:
				return
			data = cb.data.lower()
			session_id = str(cb.message.chat.id) if getattr(cb, "message", None) else str(cb.from_user.id)
			if data in {"adjuntar_ahora", "adjuntar_despues"}:
				text = "adjuntar ahora" if data == "adjuntar_ahora" else "enviar más tarde"
				result = _dm.process_message(session_id, text)
				reply_text = result.get("reply_text", "OK")
				# Limpiar emojis
				import re
				reply_text = re.sub(r'[\U0001F600-\U0001F6FF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', '', reply_text)
				reply_markup = result.get("reply_markup")
				await cb.answer()
				if exists_aiogram and reply_markup is not None and not isinstance(reply_markup, str):
					await cb.message.reply(reply_text, reply_markup=reply_markup)
				else:
					await cb.message.reply(reply_text)
				for extra in (result.get("messages") or []):
					text2 = extra.get("reply_text") or extra.get("text") or ""
					# Limpiar emojis de mensajes adicionales
					if text2:
						text2 = re.sub(r'[\U0001F600-\U0001F6FF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', '', text2)
					mk2 = extra.get("reply_markup") or extra.get("markup")
					if exists_aiogram and mk2 is not None and not isinstance(mk2, str):
						await cb.message.reply(text2, reply_markup=mk2)
					else:
						await cb.message.reply(text2)
		except Exception:
			try:
				await cb.answer("Error", show_alert=False)
			except Exception:
				pass

	print(f"Handlers registrados, iniciando polling...")
	
	try:
		# Verificar que el bot funciona antes de polling
		me = await bot.get_me()
		print(f"Bot verificado: @{me.username} (ID: {me.id})")
		
		# Configuración más robusta para el polling
		await dp.start_polling(
			bot,
			polling_timeout=30,
			handle_signals=False,
			close_bot_session=True,
			allowed_updates=None  # Recibir todos los tipos de updates
		)
	except KeyboardInterrupt:
		print("Bot detenido por usuario")
	except Exception as e:
		print(f"Error durante polling: {e}")
		logging.error(f"Error durante polling: {e}", exc_info=True)
