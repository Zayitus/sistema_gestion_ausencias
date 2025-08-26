def notify_hr(message: str) -> None:
	"""PLACEHOLDER: Enviar notificación a HR (email, webhook, etc.)."""
	print(f"[NOTIFY HR] {message}")


def schedule_10pm_reminder(id_aviso: str, needs_doc: bool) -> None:
	"""Programación placeholder para recordatorio 22:00 si falta documento.

	En producción, integrar con un scheduler (APScheduler/Celery) o cron.
	"""
	if not needs_doc:
		return
	print(f"[SCHEDULE] Recordatorio 22:00 para {id_aviso}: enviar certificado pendiente")