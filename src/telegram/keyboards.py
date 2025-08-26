from __future__ import annotations

from typing import Any, Iterable, Sequence

try:
	from aiogram.types import (
		ReplyKeyboardMarkup,
		KeyboardButton,
		InlineKeyboardMarkup,
		InlineKeyboardButton,
	)
	exists_aiogram = True
except Exception:
	# aiogram no instalado o no disponible: permitir fallback a texto
	exists_aiogram = False
	ReplyKeyboardMarkup = KeyboardButton = InlineKeyboardMarkup = InlineKeyboardButton = object  # type: ignore


def _ensure_sequence(values: Any) -> list[str]:
	"""Convierte entradas posibles a lista de strings.

	- Acepta list/tuple/set de strings.
	- Si viene dict glosario, intenta extraer variables.motivo.values.
	"""
	if values is None:
		return []
	if isinstance(values, dict):
		# Intento estándar del glosario: variables -> motivo -> values
		try:
			motivos = values["variables"]["motivo"]["values"]
			return [str(v) for v in motivos]
		except Exception:
			# A CONFIRMAR: estructura distinta del glosario
			return []
	if isinstance(values, (list, tuple, set)):
		return [str(v) for v in values]
	return [str(values)]


def kb_motivos(glosario: Any, *, as_text: bool = False) -> Any:
	"""Teclado de motivos (2 filas, 4 columnas) con fallback a texto.

	- Preferir pasar el glosario completo o una lista de motivos.
	- Si as_text=True o no hay aiogram, devuelve una cadena de opciones.
	"""
	motivos = _ensure_sequence(glosario) or [
		# Fallback por defecto (docs/glossary.json). A CONFIRMAR si cambia el dominio.
		"art",
		"enfermedad_inculpable",
		"enfermedad_familiar",
		"fallecimiento",
		"matrimonio",
		"nacimiento",
		"paternidad",
		"permiso_gremial",
	]
	if as_text or not exists_aiogram:
		return " / ".join(motivos)
	# 2 filas x 4 columnas
	row1 = [KeyboardButton(text=m) for m in motivos[:4]]
	row2 = [KeyboardButton(text=m) for m in motivos[4:8]]
	keyboard = ReplyKeyboardMarkup(
		keyboard=[row1, row2],
		resize_keyboard=True,
		one_time_keyboard=False,
		input_field_placeholder="Elegí un motivo…",
	)
	return keyboard


def kb_fecha(*, as_text: bool = False) -> Any:
	"""Teclado para fecha: Hoy / Mañana / Otra fecha.

	- Fallback a texto si as_text=True o no hay aiogram.
	"""
	labels = ["Hoy", "Mañana", "Otra fecha"]
	if as_text or not exists_aiogram:
		return " / ".join(labels)
	row = [KeyboardButton(text=lbl) for lbl in labels]
	keyboard = ReplyKeyboardMarkup(
		keyboard=[row],
		resize_keyboard=True,
		one_time_keyboard=True,
		input_field_placeholder="Elegí una opción…",
	)
	return keyboard


def kb_dias(*, as_text: bool = False) -> Any:
	"""Teclado para días estimados: 1, 2, 3, 5, 10, Otro.

	- Fallback a texto si as_text=True o no hay aiogram.
	"""
	labels = ["1", "2", "3", "5", "10", "Otro"]
	if as_text or not exists_aiogram:
		return " / ".join(labels)
	row1 = [KeyboardButton(text=l) for l in labels[:3]]
	row2 = [KeyboardButton(text=l) for l in labels[3:6]]
	keyboard = ReplyKeyboardMarkup(
		keyboard=[row1, row2],
		resize_keyboard=True,
		one_time_keyboard=True,
		input_field_placeholder="Indicá días…",
	)
	return keyboard


def kb_si_no(*, as_text: bool = False) -> Any:
	"""Teclado de confirmación: Confirmar / Editar.

	- Fallback a texto si as_text=True o no hay aiogram.
	"""
	labels = ["Confirmar", "Editar"]
	if as_text or not exists_aiogram:
		return " / ".join(labels)
	row = [KeyboardButton(text=l) for l in labels]
	keyboard = ReplyKeyboardMarkup(
		keyboard=[row],
		resize_keyboard=True,
		one_time_keyboard=True,
	)
	return keyboard


def ik_adjuntar(*, as_text: bool = False) -> Any:
	"""Inline keyboard para adjuntar certificado: Adjuntar ahora / Enviar más tarde.

	- Fallback a texto si as_text=True o no hay aiogram.
	"""
	labels = ("Adjuntar ahora", "Enviar más tarde")
	if as_text or not exists_aiogram:
		return " / ".join(labels)
	row = [
		InlineKeyboardButton(text=labels[0], callback_data="adjuntar_ahora"),
		InlineKeyboardButton(text=labels[1], callback_data="adjuntar_despues"),
	]
	keyboard = InlineKeyboardMarkup(inline_keyboard=[row])
	return keyboard



def kb_vinculo_familiar(*, as_text: bool = False) -> Any:
	"""Teclado para vínculo familiar.

	Opciones: padre, madre, hijo/a, cónyuge, otro.
	"""
	labels = ["padre", "madre", "hijo/a", "cónyuge", "otro"]
	if as_text or not exists_aiogram:
		return " / ".join(labels)
	row1 = [KeyboardButton(text=l) for l in labels[:3]]
	row2 = [KeyboardButton(text=l) for l in labels[3:5]]
	keyboard = ReplyKeyboardMarkup(
		keyboard=[row1, row2],
		resize_keyboard=True,
		one_time_keyboard=True,
		input_field_placeholder="Elegí vínculo…",
	)
	return keyboard
