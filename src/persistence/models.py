from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Date, Boolean, Text, DateTime, JSON, ForeignKey
from datetime import datetime, date


class Base(DeclarativeBase):
	pass


class Employee(Base):
	__tablename__ = "employees"

	# Usamos legajo como PK textual para compatibilidad con valores tipo "L1000" en tests
	legajo: Mapped[str] = mapped_column(String(10), primary_key=True)
	nombre: Mapped[str] = mapped_column(String(100), nullable=False)
	area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	puesto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	fecha_ingreso: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
	turno: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Aviso(Base):
	__tablename__ = "avisos"

	# id_aviso como PK textual
	id_aviso: Mapped[str] = mapped_column(String(64), primary_key=True)
	# FK a employees.legajo
	legajo: Mapped[str] = mapped_column(String(10), ForeignKey("employees.legajo"), nullable=False)
	motivo: Mapped[str] = mapped_column(String(50), nullable=False)
	fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
	fecha_fin_estimada: Mapped[date] = mapped_column(Date, nullable=False)
	duracion_estimdays: Mapped[int] = mapped_column(Integer, nullable=False)
	estado_aviso: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	estado_certificado: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	documento_tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	fuera_de_termino: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	adjunto: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Certificado(Base):
	__tablename__ = "certificados"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	id_aviso: Mapped[str] = mapped_column(String(64), ForeignKey("avisos.id_aviso"), nullable=False)
	tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	recibido_en: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
	valido: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
	notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	archivo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Notificacion(Base):
	__tablename__ = "notificaciones"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	id_aviso: Mapped[str] = mapped_column(String(64), ForeignKey("avisos.id_aviso"), nullable=False)
	destino: Mapped[str] = mapped_column(String(50), nullable=False)
	enviado_en: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
	canal: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class Auditoria(Base):
	__tablename__ = "auditoria"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	entidad: Mapped[str] = mapped_column(String(50), nullable=False)
	entidad_id: Mapped[str] = mapped_column(String(64), nullable=False)
	accion: Mapped[str] = mapped_column(String(50), nullable=False)
	ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
	actor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	detalle: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
