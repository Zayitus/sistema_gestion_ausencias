from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional, Any, List

from datetime import date, datetime, timedelta

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from ..config import settings
from .models import Base, Employee, Aviso, Certificado


_engine = create_engine(settings.DATABASE_URL, echo=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
	session = Session(bind=_engine, future=True, expire_on_commit=False)
	try:
		yield session
		session.commit()
	except Exception:
		session.rollback()
		raise
	finally:
		session.close()


def _gen_id_aviso(session: Session, fecha: date) -> str:
	"""Genera id_aviso con formato A-YYYYMMDD-#### (#### secuencial por día)."""
	prefix = fecha.strftime("A-%Y%m%d-")
	q = select(func.count()).select_from(Aviso).where(Aviso.id_aviso.like(f"{prefix}%"))
	n = session.execute(q).scalar_one()
	seq = n + 1
	return f"{prefix}{seq:04d}"


def _to_date_iso(d: Any) -> date:
	if isinstance(d, date) and not isinstance(d, datetime):
		return d
	if isinstance(d, str):
		return date.fromisoformat(d)
	raise ValueError("fecha inválida")


def find_solape(session: Session, legajo: str, fecha_inicio: date, fecha_fin: date) -> Optional[Aviso]:
	"""Busca un aviso que se solape para el mismo legajo y rango."""
	q = (
		select(Aviso)
		.where(Aviso.legajo == legajo)
		.where(~(Aviso.fecha_fin_estimada < fecha_inicio))
		.where(~(Aviso.fecha_inicio > fecha_fin))
	)
	return session.execute(q).scalars().first()


def create_aviso(facts: dict[str, Any]) -> dict[str, Any]:
	"""Crea aviso desde facts. Valida solape y genera id_aviso.

	Usa EXACTAMENTE nombres del glosario. Si falta algún dato esencial → ValueError.
	"""
	required = {"legajo", "motivo", "fecha_inicio", "duracion_estimdays"}
	missing = [k for k in required if not facts.get(k)]
	if missing:
		raise ValueError(f"Faltan campos: {missing}")
	fi = _to_date_iso(facts["fecha_inicio"])
	ff = fi + timedelta(days=int(facts["duracion_estimdays"]))
	with session_scope() as session:
		# Validar solape
		dup = find_solape(session, facts["legajo"], fi, ff)
		if dup is not None:
			raise ValueError("Solape detectado")
		# Generar id
		id_aviso = _gen_id_aviso(session, fi)
		av = Aviso(
			id_aviso=id_aviso,
			legajo=str(facts["legajo"]),
			motivo=str(facts["motivo"]),
			fecha_inicio=fi,
			fecha_fin_estimada=ff,
			duracion_estimdays=int(facts["duracion_estimdays"]),
			documento_tipo=facts.get("documento_tipo"),
			estado_aviso=facts.get("estado_aviso"),
			estado_certificado=facts.get("estado_certificado"),
			fuera_de_termino=bool(facts.get("fuera_de_termino", False)),
			adjunto=bool(facts.get("adjunto", False)),
		)
		session.add(av)
		return {"id_aviso": id_aviso}


def update_certificado(id_aviso: str, meta_doc: dict[str, Any]) -> dict[str, Any]:
	"""Actualiza certificado vinculado y estados en Aviso.

	- meta_doc: {archivo_nombre?, documento_legible?, fecha_recepcion? (ISO), documento_tipo?}
	- Ajusta estado_certificado a: pendiente_revision si ilegible, validado si legible, sino pendiente
	- Marca fuera_de_termino si corresponde según plazo (A CONFIRMAR: plazo exacto)
	"""
	with session_scope() as session:
		av = session.execute(select(Aviso).where(Aviso.id_aviso == id_aviso)).scalars().first()
		if not av:
			raise ValueError("id_aviso inexistente")
		# Upsert de certificado
		cert = session.execute(select(Certificado).where(Certificado.id_aviso == id_aviso)).scalars().first()
		if not cert:
			cert = Certificado(id_aviso=id_aviso)
			session.add(cert)
		# Actualizar campos
		adjunto_nombre = meta_doc.get("archivo_nombre")
		if adjunto_nombre is not None:
			av.adjunto = bool(adjunto_nombre)
		if "documento_tipo" in meta_doc:
			cert.tipo = meta_doc["documento_tipo"]
		if "documento_legible" in meta_doc:
			cert.valido = bool(meta_doc["documento_legible"])
		if "fecha_recepcion" in meta_doc and meta_doc["fecha_recepcion"]:
			fr = _to_date_iso(meta_doc["fecha_recepcion"])
			cert.recibido_en = datetime.combine(fr, datetime.min.time())
		if "archivo_path" in meta_doc and meta_doc["archivo_path"]:
			cert.archivo_path = str(meta_doc["archivo_path"])[:255]
		# Derivar estado del certificado y reflejar en Aviso
		if av.adjunto:
			if cert.valido is False:
				estado_cert = "pendiente_revision"
			else:
				estado_cert = "validado"
		else:
			estado_cert = "pendiente"
		av.estado_certificado = estado_cert
		# Plazos y fuera de término: cálculo no persistente
		fuera_de_termino = False
		if cert.recibido_en and av.fecha_inicio:
			delta = cert.recibido_en - datetime.combine(av.fecha_inicio, datetime.min.time())
			fuera_de_termino = delta > timedelta(hours=int(meta_doc.get("plazo_cert_horas", 48)))
		# Estado aviso según requerimiento documental
		requiere_doc = bool(av.documento_tipo)
		if not requiere_doc:
			av.estado_aviso = "completo"
		elif av.estado_certificado == "validado":
			av.estado_aviso = "completo"
		else:
			av.estado_aviso = "incompleto"
		return {
			"estado_aviso": av.estado_aviso,
			"estado_certificado": av.estado_certificado,
			"fuera_de_termino": fuera_de_termino,
			"archivo_path": getattr(cert, "archivo_path", None),
		}


def historial_empleado(legajo: str, limit: int = 10) -> list[dict[str, Any]]:
	"""Devuelve últimos avisos de un legajo (máx. limit)."""
	with session_scope() as session:
		q = (
			select(Aviso)
			.where(Aviso.legajo == str(legajo))
			.order_by(Aviso.created_at.desc())
			.limit(limit)
		)
		rows = session.execute(q).scalars().all()
		return [
			{
				"id_aviso": r.id_aviso,
				"motivo": r.motivo,
				"fecha_inicio": r.fecha_inicio.isoformat(),
				"duracion_estimdays": r.duracion_estimdays,
				"estado_aviso": r.estado_aviso,
				"estado_certificado": r.estado_certificado,
			}
			for r in rows
		]


def get_aviso_status(id_aviso: str) -> Optional[dict[str, Any]]:
	"""Obtiene estado de aviso/certificado por id."""
	with session_scope() as session:
		row = session.execute(select(Aviso).where(Aviso.id_aviso == id_aviso)).scalars().first()
		if not row:
			return None
		return {
			"id_aviso": row.id_aviso,
			"legajo": row.legajo,
			"estado_aviso": row.estado_aviso,
			"estado_certificado": row.estado_certificado,
			"documento_tipo": row.documento_tipo,
		}

