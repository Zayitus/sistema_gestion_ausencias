from __future__ import annotations

from typing import Any, Dict
import re

from ..utils.normalize import (
	extract_pairs,
	normalize_motivo,
	parse_date,
	sanitize_number_of_days,
	parse_legajo,
)
from ..engine.inference import backward_chain, forward_chain
from ..engine.kb_loader import load_knowledge_base
from .prompts import (
	PROMPTS,
	resumen_corto,
	msg_saludo,
	msg_pedir_legajo,
	msg_pedir_motivo,
	msg_pedir_fecha,
	msg_pedir_dias,
	msg_pedir_certificado,
	msg_resumen,
	msg_confirmar,
	msg_ok_creado,
	msg_error,
    msg_cierre_con_contexto,
)
from ..telegram.keyboards import kb_motivos, kb_fecha, kb_dias, kb_si_no, ik_adjuntar, kb_vinculo_familiar
from ..session_store import get_legajo, set_legajo


class DialogueManager:
	def __init__(self) -> None:
		self.sessions: Dict[str, dict[str, Any]] = {}
		self._glossary = load_knowledge_base().glossary

	def set_legajo_validado(self, session_id: str, legajo: str) -> None:
		sess = self._ensure_session(session_id)
		sess["legajo_validado"] = str(legajo)

	def _validate_legajo_in_db(self, legajo_digits: str) -> bool:
		try:
			from ..persistence.seed import ensure_schema
			from ..persistence.dao import session_scope
			from ..persistence.models import Employee
			ensure_schema()
			with session_scope() as s:
				emp = s.query(Employee).filter(Employee.legajo == legajo_digits).first()
				return bool(emp)
		except Exception:
			return False

	def _maybe_gate_by_legajo(self, session_id: str, facts: dict[str, Any], incoming: str) -> dict[str, Any] | None:
		"""Enforces legajo gate: must have a validated 4-digit legajo existing in DB.

		If validated, ensure facts["legajo"] is set and return confirmation on first validation.
		If not validated and cannot extract candidate → ask for legajo and stop.
		"""
		sess = self._ensure_session(session_id)
		ui = sess.get("ui", {})
		if sess.get("legajo_validado"):
			facts.setdefault("legajo", sess.get("legajo_validado"))
			# Completar datos del empleado si faltan (nombre/area) usando la BD
			if not facts.get("empleado_nombre"):
				try:
					from ..persistence.dao import session_scope
					from ..persistence.models import Employee
					with session_scope() as s:
						emp = s.query(Employee).filter(Employee.legajo == sess.get("legajo_validado")).first()
						if emp:
							facts["empleado_nombre"] = emp.nombre
							if getattr(emp, "area", None):
								facts.setdefault("area", emp.area)
				except Exception:
					pass
			return None
		# Intentar extraer candidato del mensaje o facts
		cand = parse_legajo(incoming)
		if not cand:
			# buscar en facts (puede venir como "L1001" o similar)
			raw = facts.get("legajo") or ""
			m = re.search(r"(\d{4})", str(raw))
			cand = m.group(1) if m else None
		# También aceptar patrón "/id 1234"
		if not cand:
			m = re.search(r"/id\s+(\d{4})\b", incoming.lower() if incoming else "")
			cand = m.group(1) if m else None
		if not cand:
			from .prompts import msg_pedir_legajo
			ui["awaiting"] = "waiting_legajo"
			sess["ui"] = ui
			return {"reply_text": msg_pedir_legajo(), "ask": ["legajo"]}
		# Validar en BD
		if self._validate_legajo_in_db(cand):
			sess["legajo_validado"] = cand
			facts["legajo"] = cand
			ui["awaiting"] = None
			sess["ui"] = ui
			# Guardar también en store por usuario/chat
			try:
				set_legajo(session_id, cand)
			except Exception:
				pass
			# Si no hay meta definida, iniciar crear_aviso y pedir motivo
			# Saludo con nombre si está disponible
			try:
				from ..persistence.dao import session_scope
				from ..persistence.models import Employee
				with session_scope() as s:
					emp = s.query(Employee).filter(Employee.legajo == cand).first()
				nombre = emp.nombre if emp else None
				# Persistir en facts datos del empleado verificado
				if emp:
					facts.setdefault("empleado_nombre", emp.nombre)
					if getattr(emp, "area", None):
						facts.setdefault("area", emp.area)
			except Exception:
				nombre = None
			reply = f"{('Hola ' + nombre + '! ' if nombre else '')}Legajo {cand} verificado ✅"
			if not sess.get("goal"):
				sess["goal"] = "crear_aviso"
				motivos = self._glossary.get("variables", {}).get("motivo", {}).get("values", [])
				ui["awaiting"] = "motivo"
				sess["ui"] = ui
				return {
					"reply_text": reply + "\n" + msg_pedir_motivo(motivos) + "\n" + kb_motivos(motivos, as_text=True),
					"reply_markup": kb_motivos(motivos),
				}
			return {"reply_text": reply}
		else:
			ui["awaiting"] = "waiting_legajo"
			sess["ui"] = ui
			return {"reply_text": "Legajo inválido, intente de nuevo", "ask": ["legajo"]}

	def _ensure_session(self, session_id: str) -> dict[str, Any]:
		if session_id not in self.sessions:
			self.sessions[session_id] = {"facts": {}, "goal": None, "ui": {"awaiting": "waiting_legajo"}}
		return self.sessions[session_id]

	# ------------------------------------------------------------------
	# NUEVAS UTILIDADES PARA MEJORAR FLUJO (puntos 1-5 del roadmap)
	# ------------------------------------------------------------------
	def _next_pending_question(
		self,
		session_id: str,
		facts: dict[str, Any],
		ui: dict[str, Any],
	) -> dict[str, Any] | None:
		"""Analiza qué información falta y arma el siguiente mensaje en el *mismo* paso.

		Si no falta nada, devuelve None y el flujo continuará normalmente.
		"""
		bw = backward_chain("crear_aviso", facts)
		if bw["status"] != "need_info":
			return None
		asks = bw["ask"]
		# MOTIVO
		if "motivo" in asks:
			motivos = self._glossary.get("variables", {}).get("motivo", {}).get("values", [])
			ui["awaiting"] = "motivo"
			self.sessions[session_id]["ui"] = ui
			return {
				"reply_text": f"{msg_pedir_motivo(motivos)}\n{kb_motivos(motivos, as_text=True)}",
				"reply_markup": kb_motivos(motivos),
			}
		# FECHA
		if "fecha_inicio" in asks:
			ui["awaiting"] = "fecha_opciones"
			self.sessions[session_id]["ui"] = ui
			return {
				"reply_text": f"{msg_pedir_fecha()}\n{kb_fecha(as_text=True)}",
				"reply_markup": kb_fecha(),
			}
		# DIAS
		if "duracion_estimdays" in asks:
			ui["awaiting"] = "dias_opciones"
			self.sessions[session_id]["ui"] = ui
			return {
				"reply_text": f"{msg_pedir_dias()}\n{kb_dias(as_text=True)}",
				"reply_markup": kb_dias(),
			}
		# VINCULO FAMILIAR
		if "vinculo_familiar" in asks:
			ui["awaiting"] = "vinculo_familiar"
			self.sessions[session_id]["ui"] = ui
			return {
				"reply_text": f"{PROMPTS['crear_aviso']['vinculo_familiar']}\n{kb_vinculo_familiar(as_text=True)}",
				"reply_markup": kb_vinculo_familiar(),
			}
		return None

	def process_message(self, session_id: str, incoming: str) -> dict[str, Any]:
		sess = self._ensure_session(session_id)
		facts = sess["facts"]
		ui = sess.get("ui", {"awaiting": None})

		# Extraer hechos del texto
		delta = extract_pairs(incoming)
		facts.update(delta)

		text_l = (incoming or "").strip()
		text_norm = text_l.lower()

		# Precargar legajo desde store antes del gate
		if not facts.get("legajo"):
			stored = get_legajo(session_id)
			if stored:
				facts["legajo"] = stored
				sess["legajo_guardado"] = stored

		# Gate por legajo: obligatorio antes de continuar con cualquier flujo
		gate = self._maybe_gate_by_legajo(session_id, facts, incoming or "")
		if gate is not None:
			return gate

		# Detección simple de meta (A CONFIRMAR si se requiere NLU adicional)
		goal = sess.get("goal")
		if goal is None:
			if any(w in text_l for w in ["avisar", "licencia", "enfermedad", "crear aviso"]):
				goal = "crear_aviso"
			elif any(w in text_l for w in ["adjunto", "certificado", "mando", "enviar doc"]):
				goal = "adjuntar_certificado"
			elif any(w in text_l for w in ["estado", "como va", "mi aviso"]):
				goal = "consultar_estado"
			elif any(w in text_l for w in ["cambiar", "extender", "modificar"]):
				goal = "modificar_aviso"
			elif any(w in text_l for w in ["cancelar", "anular"]):
				goal = "cancelar_aviso"
			sess["goal"] = goal

		# Guardar legajo si ya vino para no volver a pedirlo
		if facts.get("legajo") and sess.get("legajo_guardado") != facts.get("legajo"):
			sess["legajo_guardado"] = facts.get("legajo")

		# Flujo asistido: crear_aviso
		if goal == "crear_aviso":
			awaiting = ui.get("awaiting")
			# Estados transitorios de UI
			if awaiting == "motivo":
				mot = normalize_motivo(text_l)
				if mot:
					facts["motivo"] = mot
					ui["awaiting"] = None
					# Preguntar lo siguiente inmediatamente
					next_q = self._next_pending_question(session_id, facts, ui)
					if next_q:
						# Anteponer confirmación + salto de línea
						confirm = f"✅ Motivo '{mot}' confirmado"
						next_q.setdefault("reply_text", "")
						next_q["reply_text"] = confirm + "\n" + next_q["reply_text"]
						return next_q
					return {"reply_text": f"✅ Motivo '{mot}' confirmado"}
				else:
					motivos = self._glossary.get("variables", {}).get("motivo", {}).get("values", [])
					return {
						"reply_text": f"{msg_pedir_motivo(motivos)}\n{kb_motivos(motivos, as_text=True)}",
						"reply_markup": kb_motivos(motivos),
					}
			elif awaiting == "fecha_opciones":
				# Acepta botones Hoy / Mañana / Otra fecha
				if text_norm in {"hoy", "mañana", "manana"}:
					fd = parse_date(text_l)
					if fd:
						facts["fecha_inicio"] = fd
						ui["awaiting"] = None
						next_q = self._next_pending_question(session_id, facts, ui)
						if next_q:
							confirm = f"✅ Fecha {fd} confirmada"
							next_q.setdefault("reply_text", "")
							next_q["reply_text"] = confirm + "\n" + next_q["reply_text"]
							return next_q
						return {"reply_text": f"✅ Fecha {fd} confirmada"}
					else:
						return {"reply_text": f"{msg_pedir_fecha()}\n{kb_fecha(as_text=True)}", "reply_markup": kb_fecha()}
				elif text_norm == "otra fecha":
					ui["awaiting"] = "otra_fecha_text"
					return {"reply_text": msg_pedir_fecha()}
				else:
					return {"reply_text": f"{msg_pedir_fecha()}\n{kb_fecha(as_text=True)}", "reply_markup": kb_fecha()}
			elif awaiting == "dias_opciones":
				# Botones 1 / 2 / 3 / 5 / 10 / Otro
				if text_norm in {"1", "2", "3", "5", "10"}:
					facts["duracion_estimdays"] = int(text_norm)
					ui["awaiting"] = None
					next_q = self._next_pending_question(session_id, facts, ui)
					if next_q:
						confirm = f"✅ {text_norm} días confirmados"
						next_q.setdefault("reply_text", "")
						next_q["reply_text"] = confirm + "\n" + next_q["reply_text"]
						return next_q
					return {"reply_text": f"✅ {text_norm} días confirmados"}
				elif text_norm.startswith("otro"):
					ui["awaiting"] = "dias_otro_numero"
					return {"reply_text": msg_pedir_dias()}
				else:
					d = sanitize_number_of_days(text_l)
					if d is not None:
						facts["duracion_estimdays"] = d
						ui["awaiting"] = None
						next_q = self._next_pending_question(session_id, facts, ui)
						if next_q:
							confirm = f"✅ {d} días confirmados"
							next_q.setdefault("reply_text", "")
							next_q["reply_text"] = confirm + "\n" + next_q["reply_text"]
							return next_q
						return {"reply_text": f"✅ {d} días confirmados"}
			if awaiting == "otra_fecha_text":
				fd = parse_date(text_l)
				if fd:
					facts["fecha_inicio"] = fd
					ui["awaiting"] = None
					next_q = self._next_pending_question(session_id, facts, ui)
					if next_q:
						confirm = f"✅ Fecha {fd} confirmada"
						next_q.setdefault("reply_text", "")
						next_q["reply_text"] = confirm + "\n" + next_q["reply_text"]
						return next_q
					return {"reply_text": f"✅ Fecha {fd} confirmada"}
			elif awaiting == "dias_otro_numero":
				d = sanitize_number_of_days(text_l)
				if d is not None:
					facts["duracion_estimdays"] = d
					ui["awaiting"] = None
					next_q = self._next_pending_question(session_id, facts, ui)
					if next_q:
						confirm = f"✅ {d} días confirmados"
						next_q.setdefault("reply_text", "")
						next_q["reply_text"] = confirm + "\n" + next_q["reply_text"]
						return next_q
					return {"reply_text": f"✅ {d} días confirmados"}
			elif awaiting == "vinculo_familiar":
				# Aceptar botones exactos y normalizar
				options = {"padre", "madre", "hijo/a", "conyuge", "cónyuge", "otro"}
				val = text_norm.replace("cónyuge", "conyuge")
				if val in {"padre", "madre", "hijo/a", "conyuge", "otro"}:
					facts["vinculo_familiar"] = "cónyuge" if val == "conyuge" else val
					ui["awaiting"] = None
					next_q = self._next_pending_question(session_id, facts, ui)
					if next_q:
						confirm = f"✅ Vínculo '{facts['vinculo_familiar']}' confirmado"
						next_q.setdefault("reply_text", "")
						next_q["reply_text"] = confirm + "\n" + next_q["reply_text"]
						return next_q
					return {"reply_text": f"✅ Vínculo '{facts['vinculo_familiar']}' confirmado"}
				else:
					return {
						"reply_text": f"{PROMPTS['crear_aviso']['vinculo_familiar']}\n{kb_vinculo_familiar(as_text=True)}",
						"reply_markup": kb_vinculo_familiar(),
					}
			elif awaiting == "doc_choice":
				# Maneja texto directo (adjuntar ahora / enviar más tarde) además de callbacks
				if text_norm.startswith("adjuntar ahora") or text_norm.startswith("adjuntar"):
					facts["adjunto_certificado"] = True
				elif text_norm.startswith("enviar mas tarde") or text_norm.startswith("enviar más tarde") or text_norm.startswith("despues") or text_norm.startswith("después"):
					facts["adjunto_certificado"] = False
				else:
					return {"reply_text": f"{msg_pedir_certificado(facts.get('documento_tipo'))}\n{ik_adjuntar(as_text=True)}", "reply_markup": ik_adjuntar()}
				# Luego de decidir doc, pedir confirmación final
				resumen = msg_resumen(facts)
				ui["awaiting"] = "confirm_final"
				self.sessions[session_id]["ui"] = ui
				return {
					"reply_text": msg_confirmar(resumen) + f"\n{kb_si_no(as_text=True)}",
					"reply_markup": kb_si_no(),
				}
			elif awaiting == "confirm_final":
				if text_norm.startswith("confirmar") or text_norm in {"si", "sí", "si!", "sí!"}:
					try:
						fw = forward_chain(facts)
						facts.update(fw["facts"])
						# Intentar crear el aviso en la base de datos
						from ..persistence.dao import create_aviso
						res = create_aviso(facts)
						facts["id_aviso"] = res.get("id_aviso")
						
						# Si había documento pendiente en sesión, asociarlo ahora
						pending = self._ensure_session(session_id).get("pending_doc")
						if pending:
							try:
								from ..persistence.dao import update_certificado
								# Intentar mover a uploads/<chat_id>/<id_aviso>/ si tenemos ruta previa
								import os
								old_path = pending.get("archivo_path")
								if old_path and os.path.exists(old_path):
									chat_dir = os.path.dirname(old_path)
									id_dir = os.path.join(chat_dir, facts["id_aviso"]) if chat_dir else None
									if id_dir:
										os.makedirs(id_dir, exist_ok=True)
										new_path = os.path.join(id_dir, os.path.basename(old_path))
										try:
											os.replace(old_path, new_path)
										except Exception as ex:
											import logging
											logging.warning(f"No se pudo mover archivo: {ex}")
											new_path = old_path
										pending["archivo_path"] = new_path
								update_certificado(facts["id_aviso"], pending)
							except Exception as ex:
								import logging
								logging.warning(f"Error actualizando certificado: {ex}")
							# limpiar
							self.sessions.get(session_id, {}).pop("pending_doc", None)
						ui["awaiting"] = None
						# Mensaje de cierre amable con contexto
						closing = msg_cierre_con_contexto(facts)
						# Recordatorio de 24h solo si hay documento requerido y no validado, salvo motivos especiales (nacimiento/fallecimiento no piden doc)
						if facts.get("documento_tipo") and facts.get("estado_certificado") != "validado" and facts.get("motivo") not in {"nacimiento", "fallecimiento"}:
							closing += "\nTenés 24h para enviar el documento requerido."
						# Programar recordatorio 22:00 si falta doc (placeholder)
						try:
							from ..notify.router import schedule_10pm_reminder
							schedule_10pm_reminder(facts.get("id_aviso"), bool(facts.get("documento_tipo")) and (facts.get("estado_certificado") != "validado"))
						except Exception:
							pass
						return {"reply_text": closing}
					except Exception as e:
						ui["awaiting"] = None
						return {"reply_text": msg_error(str(e))}
				elif text_norm.startswith("editar"):
					ui["awaiting"] = "editar_campo"
					return {"reply_text": "¿Qué querés editar? Escribí 'motivo', 'fecha' o 'días'."}
				else:
					# Re-mostrar confirmación si texto no reconocido
					resumen = msg_resumen(facts)
					return {
						"reply_text": msg_confirmar(resumen) + f"\n{kb_si_no(as_text=True)}",
						"reply_markup": kb_si_no(),
					}
			elif awaiting == "editar_campo":
				edited = False
				if "motivo" in text_norm:
					facts.pop("motivo", None)
					edited = True
				if "fecha" in text_norm:
					facts.pop("fecha_inicio", None)
					edited = True
				if "dia" in text_norm:
					facts.pop("duracion_estimdays", None)
					edited = True
				ui["awaiting"] = None
				if not edited:
					return {"reply_text": "No entendí qué editar. Decime 'motivo', 'fecha' o 'días'."}

			# Interpretación directa desde texto (atajos/botones simulados)
			if not facts.get("motivo"):
				mot = normalize_motivo(text_l)
				if mot:
					facts["motivo"] = mot
			if not facts.get("fecha_inicio"):
				fd = parse_date(text_l)
				if not fd:
					if "mañana" in text_norm or "manana" in text_norm:
						fd = parse_date("mañana")
					elif "hoy" in text_norm:
						fd = parse_date("hoy")
					elif "ayer" in text_norm:
						fd = parse_date("ayer")
				if fd:
					facts["fecha_inicio"] = fd
			elif text_norm == "otra fecha":
				ui["awaiting"] = "otra_fecha_text"
				return {"reply_text": msg_pedir_fecha()}
			if not facts.get("duracion_estimdays"):
				if text_norm.startswith("otro"):
					ui["awaiting"] = "dias_otro_numero"
					return {"reply_text": msg_pedir_dias()}
				else:
					d = sanitize_number_of_days(text_l)
					if d is not None:
						facts["duracion_estimdays"] = d

			# Detectar faltantes y usar teclados/mensajes
			bw = backward_chain("crear_aviso", facts)
			if bw["status"] == "need_info":
				tasks = bw["ask"]
				if "motivo" in tasks:
					motivos = self._glossary.get("variables", {}).get("motivo", {}).get("values", [])
					kb_txt = kb_motivos(motivos, as_text=True)
					ui["awaiting"] = "motivo"
					sess["ui"] = ui
					return {
						"reply_text": f"{msg_pedir_motivo(motivos)}\n{kb_txt}",
						"ask": tasks,
						"reply_markup": kb_motivos(motivos),
					}
				if "vinculo_familiar" in tasks:
					ui["awaiting"] = "vinculo_familiar"
					sess["ui"] = ui
					return {
						"reply_text": f"{PROMPTS['crear_aviso']['vinculo_familiar']}\n{kb_vinculo_familiar(as_text=True)}",
						"ask": tasks,
						"reply_markup": kb_vinculo_familiar(),
					}
				if "fecha_inicio" in tasks:
					ui["awaiting"] = "fecha_opciones"
					sess["ui"] = ui
					return {
						"reply_text": f"{msg_pedir_fecha()}\n{kb_fecha(as_text=True)}",
						"ask": tasks,
						"reply_markup": kb_fecha(),
					}
				if "duracion_estimdays" in tasks:
					ui["awaiting"] = "dias_opciones"
					sess["ui"] = ui
					return {
						"reply_text": f"{msg_pedir_dias()}\n{kb_dias(as_text=True)}",
						"ask": tasks,
						"reply_markup": kb_dias(),
					}
				if "legajo" in tasks and not sess.get("legajo_guardado"):
					return {"reply_text": msg_pedir_legajo(), "ask": tasks}
				# Otros slots (fallback compatibilidad)
				prompt_set = PROMPTS.get("crear_aviso", {})
				msgs = [prompt_set.get(a) for a in tasks if prompt_set.get(a)]
				return {"reply_text": "\n".join(msgs) or "A CONFIRMAR", "ask": tasks}

			# Completo: resumen + confirmación + doc si corresponde
			fw = forward_chain(facts)
			facts.update(fw["facts"])
			traces = fw.get("traces", [])
			traza = ""
			if traces:
				main = traces[0]
				traza = f"[{main.get('regla_id')}] {main.get('porque')}" if main.get("regla_id") or main.get("porque") else ""
			resumen = msg_resumen(facts, traza)
			doc_tipo = facts.get("documento_tipo")
			motivo = facts.get("motivo")
			pending_doc = self.sessions.get(session_id, {}).get("pending_doc")
			needs_doc = (
				doc_tipo
				and facts.get("estado_certificado") != "no_requerido"
				and not pending_doc
				and motivo not in {"fallecimiento", "nacimiento"}
			)
			if needs_doc:
				# Primero preguntar por el documento
				ui["awaiting"] = "doc_choice"
				self.sessions[session_id]["ui"] = ui
				return {
					"reply_text": f"{msg_pedir_certificado(doc_tipo)}\n{ik_adjuntar(as_text=True)}",
					"reply_markup": ik_adjuntar(),
				}
			# Si no se necesita doc (o ya se resolvió), pedir confirmación final
			ui["awaiting"] = "confirm_final"
			self.sessions[session_id]["ui"] = ui
			return {
				"reply_text": msg_confirmar(resumen) + f"\n{kb_si_no(as_text=True)}",
				"reply_markup": kb_si_no(),
				"resumen": resumen,
			}

		# Backward para pedir slots faltantes (otros flujos)
		if goal in {"adjuntar_certificado", "consultar_estado"}:
			bw = backward_chain(goal, facts)
			if bw["status"] == "need_info":
				tasks = bw["ask"]
				prompt_set = PROMPTS.get(goal, {})
				msgs = [prompt_set.get(a) for a in tasks if prompt_set.get(a)]
				return {"reply_text": "\n".join(msgs) or "A CONFIRMAR", "ask": tasks}
			elif bw["status"] == "no_match":
				return {"reply_text": "A CONFIRMAR", "ask": ["A CONFIRMAR"]}

		# Forward cuando hay suficiente info (flujo general)
		fw = forward_chain(facts)
		facts.update(fw["facts"])
		summary = resumen_corto(facts)
		traces = fw.get("traces", [])
		explic = ""
		if traces:
			main = traces[0]
			explic = f"[{main.get('regla_id')}] {main.get('porque')}" if main.get("regla_id") or main.get("porque") else ""
		return {"reply_text": summary or "A CONFIRMAR", "facts_delta": delta, "resumen": summary, "next_action": None, "traza_principal": explic}

