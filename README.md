# Sistema Experto de Ausencias

Proyecto de sistema experto basado en reglas para gestionar avisos de ausencias laborales. Incluye motor de inferencia (forward/backward chaining), base de conocimiento externa (glosario + reglas), gestor de diálogo con slot-filling y bot de Telegram.

## Características
- Motor experto con encadenamiento hacia adelante (`forward_chain`) y un backward-chaining básico para completar slots.
- Base de conocimiento editable en archivos JSON: `docs/glossary.json` y `docs/rules.json` (cargados y validados por `src/engine/kb_loader.py`).
- Explicabilidad: trazas con `regla_id`, “por qué” y hechos usados (`src/engine/explain.py`).
- Interfaz conversacional vía Telegram (aiogram 3.x) y demo local sin red.
- Persistencia con SQLAlchemy (SQLite por defecto) y export a CSV para Power BI.

## Requisitos
- Python 3.10+
- (Opcional) Cuenta de bot de Telegram y token

## Estructura del proyecto (resumen)
```
experto-ausencias/
  src/
    app.py                 # entrypoint del bot (polling)
    config.py              # variables de entorno (pydantic + dotenv)
    dialogue/              # gestor de diálogo y prompts
    engine/                # motor de inferencia + KB loader + explicaciones
    notify/                # ruteo de notificaciones (placeholder)
    persistence/           # modelos, DAO y exportaciones
    telegram/              # bot y teclados (aiogram)
    utils/                 # normalización (fechas, motivos, etc.)
  docs/
    glossary.json          # glosario (dominio y tipos de variables)
    rules.json             # reglas de negocio (when/then + certainty)
    Arbol_Dialogo_v1.md    # guía de diálogo/slots
    Reglas_BC_v1.md        # resumen funcional de reglas
  demo_local.py            # demo sin red (motor + diálogo)
  bot_webhook.py           # modo webhook (ngrok)
  bot_resiliente.py        # modo polling con reintentos
  setup_telegram.py        # diagnóstico/conexión a Telegram
  CONECTAR_TELEGRAM.md     # guía rápida de conectividad
```

## Configuración
1) Crear entorno virtual e instalar dependencias
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Variables de entorno (.env)
Copia `env.example` a `.env` y ajusta:
```
TELEGRAM_TOKEN=
DATABASE_URL=sqlite:///./ausencias.db
LOG_LEVEL=INFO
DEMO_EXPORT=true
```
- `TELEGRAM_TOKEN`: requerido para usar Telegram.
- `DATABASE_URL`: por defecto SQLite local.
- `DEMO_EXPORT`: habilita comando demo `/export_csv`.

3) Inicializar base y datos demo
```bash
python -m src.persistence.seed
```

## Ejecución
### A) Modo polling (Telegram)
```bash
python -m src.app
```
Requiere `TELEGRAM_TOKEN` válido y conectividad a Telegram. Handlers básicos: `/start`, `/help`, `/id <legajo>`, `/export_csv` (si `DEMO_EXPORT=true`).

### B) Modo webhook (ngrok)
1. Inicia ngrok en otro terminal (HTTPS → puerto 8080):
```bash
ngrok http 8080
```
2. Ejecuta el bot webhook:
```bash
python bot_webhook.py
```
El script detecta automáticamente la URL pública y configura el webhook.

### C) Demo local (sin red)
```bash
python demo_local.py
```
Simula conversación y muestra ejecución del motor experto sin Telegram.

### D) Bot resiliente (polling con reintentos)
```bash
python bot_resiliente.py
```
Pensado para redes problemáticas; incorpora reintentos y mensajes de ayuda.

### Diagnóstico de conectividad
```bash
python setup_telegram.py
```
Prueba token, verifica ngrok y sugiere alternativas (hotspot, VPN, etc.). Ver `CONECTAR_TELEGRAM.md` para guía rápida.

## Cómo usar (flujo típico)
1. Usuario envía su legajo (`/id 1001` o “legajo: L1001”).
2. Bot pide motivo, fecha de inicio y días estimados (slot-filling).
3. El motor deriva `documento_tipo` y estados (`estado_aviso`, `estado_certificado`).
4. Si corresponde, solicita adjuntar certificado; valida legibilidad y plazos (fuera de término).
5. Confirma y persiste el `aviso` con `id_aviso = A-YYYYMMDD-####`.

## Motor de inferencia (resumen técnico)
- Forward chaining: `src/engine/inference.py::forward_chain(facts)`
  - Aplica reglas `when/then` desde `docs/rules.json` sobre la memoria de trabajo (`facts`).
  - Combina `certainty` simple por variable y genera top-3 conclusiones + trazas.
  - Deriva estados auxiliares: `fecha_fin_estimada`, `estado_certificado`, `fuera_de_termino`, duplicados.
- Backward chaining: `src/engine/inference.py::backward_chain(goal, facts)`
  - Orientado a metas del diálogo: `crear_aviso`, `adjuntar_certificado`, `consultar_estado`.
  - Devuelve slots faltantes (`need_info`) o dispara una pasada de forward si está completo.
- Carga/validación de KB: `src/engine/kb_loader.py` (glosario y reglas con validaciones de tipos, operadores y variables).
- Explicaciones: `src/engine/explain.py` (formato compactado y trazas).

## Base de conocimiento
- Glosario (`docs/glossary.json`): define variables, tipos (`string`, `int`, `date`, `enum`, `boolean`, `list`) y dominios (enums).
- Reglas (`docs/rules.json`): lista de reglas con `id`, `when` (condiciones) y `then` (acciones `set/append`, `certainty`, `explanation`).
- Ejemplos de reglas incluidas:
  - Mapear motivo → documento requerido (p. ej., `enfermedad_inculpable` → `certificado_medico`).
  - Ruteo de notificaciones (RRHH siempre; médico laboral, delegado, jefe de producción según contexto).
  - ART sin documento inicial; estados por certificado.

## Persistencia y exportación
- ORM: SQLAlchemy 2.x con modelos en `src/persistence/models.py`.
- DAO en `src/persistence/dao.py`:
  - `create_aviso(facts)`: valida solapes, genera `id_aviso`, persiste.
  - `update_certificado(id_aviso, meta_doc)`: actualiza certificado y estados.
  - `historial_empleado(legajo, limit)`.
- Export a CSV: `src/persistence/export_powerbi.py` → genera `exports/*.csv` para Power BI/Excel.

## Pruebas
Ejecutar test suite:
```bash
pytest
```
Cubre normalización, motor, diálogo y persistencia.

## Solución de problemas
- Telegram no conecta: usa `python setup_telegram.py` o seguí `CONECTAR_TELEGRAM.md` (hotspot móvil recomendado).
- Falta token: configurar `TELEGRAM_TOKEN` en `.env`.
- DB vacía: correr `python -m src.persistence.seed` para crear esquema y datos demo.
- aiogram no instalado: `pip install -r requirements.txt`.

## Licencia
Uso académico/educativo. Ajustar según necesidad del repositorio.

## Créditos
- Basado en principios de sistemas expertos (Giarratano & Riley) y arquitectura conversacional con aiogram.
- Desarrollo y documentación: equipo del proyecto.
