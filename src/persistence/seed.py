from __future__ import annotations
from random import choice, randint

from .models import Base, Employee
from .dao import session_scope, _engine
from sqlalchemy import text

try:
	from faker import Faker
except Exception:  # pragma: no cover - Faker puede no estar instalado antes de tests
	Faker = None  # type: ignore


def ensure_schema() -> None:
	"""Crea tablas si no existen y agrega columnas faltantes para el nuevo esquema.

	Diseñado para SQLite sin migraciones complejas.
	"""
	Base.metadata.create_all(bind=_engine)
	with _engine.begin() as conn:
		def existing_columns(table: str) -> set[str]:
			rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
			# PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
			return {r[1] for r in rows}

		def add_column_if_missing(table: str, column_def: str) -> None:
			name = column_def.split()[0]
			if name not in existing_columns(table):
				conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column_def}")

		# employees: nuevos campos del esquema
		for coldef in (
			"area TEXT",
			"puesto TEXT",
			"fecha_ingreso DATE",
			"turno TEXT",
			"activo BOOLEAN DEFAULT 1",
		):
			add_column_if_missing("employees", coldef)

		# avisos: aseguramos columnas modernas y eliminamos dependencia de fecha_fin_estimada
		for coldef in (
			"fecha_fin DATE",
			"adjunto BOOLEAN DEFAULT 0",
		):
			add_column_if_missing("avisos", coldef)
		# Si existe columna antigua obligatoria, intentar relajarlo creando si falta y dejando NULL permitido.
		# Nota: SQLite no permite DROP COLUMN fácilmente; los tests usan solo columnas modernas.

		# certificados: nuevos campos
		for coldef in (
			"tipo TEXT",
			"recibido_en DATETIME",
			"valido BOOLEAN",
			"notas TEXT",
			"archivo_path TEXT",
		):
			add_column_if_missing("certificados", coldef)

		# notificaciones: nuevos campos
		for coldef in (
			"enviado_en DATETIME",
			"canal TEXT",
			"payload JSON",
		):
			add_column_if_missing("notificaciones", coldef)

		# auditoria: nuevos campos (no migramos los viejos)
		for coldef in (
			"entidad TEXT",
			"entidad_id TEXT",
			"accion TEXT",
			"ts DATETIME",
			"actor TEXT",
			"detalle JSON",
		):
			add_column_if_missing("auditoria", coldef)


def seed_employees() -> None:
	with session_scope() as session:
		# Si ya hay datos, no volver a sembrar
		count = session.query(Employee).count()
		if count >= 10:
			return
		empleados = [
			Employee(legajo=f"L{1000+i}", nombre=f"Empleado {i+1}", area="producción" if i % 2 == 0 else "administración")
			for i in range(10)
		]
		session.add_all(empleados)


def seed_employees_synthetic(n: int = 200) -> int:
	"""Crea empleados sintéticos con Faker.

	Genera legajos "1000".. por defecto hasta cubrir n elementos (1000..1000+n-1).
	Areas/turnos de un conjunto fijo.
	Devuelve la cantidad creada efectivamente (omite existentes).
	"""
	areas = ["producción", "administración", "ventas", "logística"]
	turnos = ["mañana", "tarde", "noche"]
	created = 0
	with session_scope() as session:
		# Obtener existentes para evitar colisiones
		existentes = {row[0] for row in session.query(Employee.legajo).all()}
		start = 1000
		for i in range(n):
			leg = str(start + i)
			if leg in existentes:
				continue
			if Faker is not None:
				fake = Faker("es_AR")
				nombre = fake.name()
				puesto = fake.job()
				# faker.date_between devuelve date
				fecha_ingreso = fake.date_between(start_date="-10y", end_date="-1d")
			else:
				# Fallback sin Faker
				nombre = f"Empleado {leg}"
				puesto = f"Puesto {randint(1, 50)}"
				from datetime import date, timedelta
				fecha_ingreso = date.today() - timedelta(days=randint(30, 3650))
			e = Employee(
				legajo=leg,
				nombre=nombre,
				area=choice(areas),
				puesto=puesto,
				fecha_ingreso=fecha_ingreso,
				turno=choice(turnos),
				activo=True,
			)
			session.add(e)
			created += 1
	return created


def seed_employees_examples() -> int:
	"""Crea un pequeño set de empleados conocidos para pruebas manuales.

	Evita duplicados si ya existen. Incluye el legajo 1111 para Ciro Medina
	y otros legajos numéricos para pruebas.
	"""
	to_create = [
		{"legajo": "1111", "nombre": "Ciro Medina", "area": "administración"},
		{"legajo": "2222", "nombre": "Ana Gómez", "area": "producción"},
		{"legajo": "3333", "nombre": "María López", "area": "ventas"},
		{"legajo": "4444", "nombre": "Juan Pérez", "area": "logística"},
		{"legajo": "5555", "nombre": "Lucía Fernández", "area": "producción"},
	]
	created = 0
	with session_scope() as session:
		existentes = {row[0] for row in session.query(Employee.legajo).all()}
		for e in to_create:
			if e["legajo"] in existentes:
				continue
			session.add(Employee(legajo=e["legajo"], nombre=e["nombre"], area=e["area"]))
			created += 1
	return created


if __name__ == "__main__":
	ensure_schema()
	# Idempotente: si hay menos de 100, sembrar sintético
	with session_scope() as s:
		c = s.query(Employee).count()
	if c < 100:
		seed_employees_synthetic(200)
	else:
		pass
	# Asegurar ejemplos conocidos
	seed_employees_examples()
