START_PROMPT = "¡Hola! Soy el asistente de ausencias. ¿En qué te puedo dar una mano hoy? 🙂"

PROMPTS = {
	"crear_aviso": {
		"legajo": "¿Me pasás tu legajo? (solo números/letras) 🆔",
		"motivo": (
			"""Elegí el motivo:
	- art
	- enfermedad_inculpable
	- enfermedad_familiar
	- fallecimiento
	- matrimonio
	- nacimiento
	- paternidad
	- permiso_gremial"""
		),
		"fecha_inicio": "¿Desde qué fecha querés iniciar el aviso? Podés decir 'hoy', 'mañana' o pasar la fecha (YYYY-MM-DD / DD/MM/AAAA) 📅",
		"duracion_estimdays": "¿Por cuántos días estimás la ausencia? (número entero) 📏",
		"vinculo_familiar": "Si es por enfermedad_familiar, indicá el vínculo: padre, madre, hijo/a, cónyuge u otro 👪",
	},
	"adjuntar_certificado": {
		"id_aviso": "Decime el ID del aviso o, si no lo tenés, tu legajo y la fecha de inicio 🔎",
		"adjunto_certificado": "Si lo tenés a mano, adjuntá el documento (PDF/JPG/PNG). También podés decir 'adjunto' para enviarlo luego 📎",
	},
	"consultar_estado": {
		"id_aviso": "¿Me compartís el ID del aviso o tu legajo para buscarlo? 🗂️",
	},
	"modificar_aviso": {
		"duracion_estimdays": "¿A cuántos días querés cambiar la duración estimada? ✏️",
	},
	"cancelar_aviso": {
		"confirm": "¿Confirmás que querés cancelar el aviso? Escribí CONFIRMAR para avanzar ❌",
	},
}

def resumen_corto(facts: dict) -> str:
	mot = facts.get("motivo")
	ini = facts.get("fecha_inicio")
	dur = facts.get("duracion_estimdays")
	est = facts.get("estado_aviso")
	flag = " · fuera_de_termino" if facts.get("fuera_de_termino") else ""
	ida = facts.get("id_aviso")
	if ida:
		return f"ID: {ida} · Motivo: {mot} · Inicio: {ini} · Días: {dur} · Estado: {est}{flag}"
	return f"Motivo: {mot} · Inicio: {ini} · Días: {dur} · Estado: {est}{flag}"


# --- Helpers de UX (tono es-AR, emojis sutiles) ---

def msg_saludo() -> str:
	"""Saludo inicial amable en es-AR.

	No altera la lógica; solo texto de presentación.
	"""
	return "¡Hola! 👋 Soy el asistente de ausencias. Te acompaño para crear avisos, adjuntar certificados o consultar estados."


def msg_pedir_legajo() -> str:
	return "¿Me pasás tu legajo? (solo números/letras) 🆔"


def msg_pedir_motivo(opciones: list[str] | tuple[str, ...]) -> str:
	"""Pide motivo mostrando lista cerrada.

	Se espera que 'opciones' use los valores del dominio (glosario). Si se desea mostrar
	etiquetas más amigables, mantener compatibilidad con el normalizador.
	"""
	if not opciones:
		# A CONFIRMAR: si no hay opciones provistas desde docs/glosario
		opciones = [
			"art",
			"enfermedad_inculpable",
			"enfermedad_familiar",
			"fallecimiento",
			"matrimonio",
			"nacimiento",
			"paternidad",
			"permiso_gremial",
		]
	items = "\n".join(f"- {o}" for o in opciones)
	return f"Elegí el motivo:\n{items}"


def msg_pedir_fecha() -> str:
	return "¿Desde qué fecha querés iniciar el aviso? Decime 'hoy', 'mañana' o una fecha (YYYY-MM-DD / DD/MM/AAAA) 📅"


def msg_pedir_dias() -> str:
	return "¿Cuántos días estimás de ausencia? Indicá un número entero (p. ej., 1, 3, 10) 📏"


def msg_pedir_certificado(tipo: str | None) -> str:
	"""Pide adjuntar certificado del tipo indicado.

	'tipo' debería provenir del dominio (p. ej., 'certificado_medico', 'acta_defuncion').
	"""
	t = tipo or "certificado"
	return (
		f"Si tenés el {t} a mano, podés adjuntarlo ahora (PDF/JPG/PNG). "
		"Si preferís, podés enviarlo más tarde. 📎"
	)


def msg_resumen(facts: dict, traza: str | None = None) -> str:
	"""Resumen amigable del aviso a partir de hechos + una breve explicación opcional.

	No modifica los hechos ni la lógica; solo formatea el mensaje.
	"""
	mot = facts.get("motivo") or "—"
	ini = facts.get("fecha_inicio") or "—"
	dur = facts.get("duracion_estimdays") or "—"
	est = facts.get("estado_aviso") or "—"
	ida = facts.get("id_aviso")
	flag = " ⏰ fuera de término" if facts.get("fuera_de_termino") else ""
	lineas: list[str] = []
	if ida:
		lineas.append(f"ID aviso: {ida}")
	lineas.append(f"Motivo: {mot}")
	lineas.append(f"Inicio: {ini}")
	lineas.append(f"Días (estimado): {dur}")
	lineas.append(f"Estado: {est}{flag}")
	if traza:
		lineas.append(f"ℹ️ {traza}")
	return "\n".join(lineas)


def msg_confirmar(resumen: str) -> str:
	return (
		"¿Confirmamos estos datos? ✅\n"
		f"{resumen}\n"
		"Elegí 'Confirmar' o 'Editar'."
	)


def msg_ok_creado(id_aviso: str | int | None) -> str:
	if id_aviso is None:
		return "¡Listo! Tu aviso quedó creado 🎉"
	return f"¡Listo! Tu aviso #{id_aviso} quedó creado 🎉"


def msg_cierre_con_contexto(facts: dict) -> str:
	"""Mensaje de cierre con tono contextual según motivo.

	- nacimiento: felicitaciones
	- fallecimiento: condolencias
	- otros: cierre estándar
	"""
	mot = (facts.get("motivo") or "").lower()
	if mot == "fallecimiento":
		# Mensaje sobrio, sin emoji
		return (
			"Tu aviso fue registrado.\n"
			"Lamentamos tu pérdida. RRHH se pondrá en contacto para acompañarte con el trámite."
		)
	base = msg_ok_creado(facts.get("id_aviso"))
	if mot == "nacimiento":
		return base + "\n¡Felicitaciones! RRHH se pondrá en contacto para explicar el trámite."
	return base + "\nRRHH se pondrá en contacto para confirmarlo."


def msg_error(message: str) -> str:
	return f"Uy… hubo un problema: {message} ⚠️ Intentá nuevamente o pedime ayuda."
