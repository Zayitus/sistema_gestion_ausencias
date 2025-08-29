# Guía de Funcionamiento - Sistema de Gestión de Ausencias

## 🎯 **Visión General del Sistema**

El Sistema de Gestión de Ausencias es una solución integral que automatiza el proceso de solicitud, seguimiento y validación de ausencias laborales mediante dos interfaces principales:

- **Bot de Telegram**: Para empleados (solicitud y seguimiento)
- **Dashboard Web**: Para RRHH (gestión y supervisión)

---

## 🔄 **Flujo General del Proceso**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EMPLEADO      │    │      SISTEMA     │    │      RRHH       │
│  (Telegram)     │    │   (Automático)   │    │   (Dashboard)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
    1. Solicita ausencia         │                       │
         │──────────────────────►│                       │
         │                  2. Valida datos              │
         │                       │                       │
    3. Recibe confirmación       │                       │
         │◄──────────────────────│                       │
         │                       │                       │
    4. [Si requiere] Envía       │                       │
       certificado               │                       │
         │──────────────────────►│                       │
         │                       │                       │
         │                  5. Procesa y                 │
         │                     almacena                  │
         │                       │                       │
         │                       │  6. Notifica caso     │
         │                       │      especial         │
         │                       │──────────────────────►│
         │                       │                       │
         │                       │              7. Revisa y valida
         │                       │                       │
         │                  8. [22:00] Envía             │
         │                     recordatorio              │
         │◄──────────────────────│                       │
         │                       │                       │
    9. Responde con              │                       │
       certificado               │                       │
         │──────────────────────►│                       │
         │                       │                       │
         │                       │  10. Actualiza estado │
         │                       │──────────────────────►│
         │                       │                       │
```

---

## 🤖 **Funcionamiento Detallado del Bot de Telegram**

### **Inicialización y Configuración**

#### **Startup Sequence**
1. **Carga de configuración** desde `.env`
2. **Inicialización de BD** (crear tablas si no existen)  
3. **Setup del DialogueManager** (estado de conversaciones)
4. **Configuración de handlers** (comandos y mensajes)
5. **Inicio del sistema de recordatorios** en background
6. **Conexión con API de Telegram** (polling)

#### **Componentes Clave**
- **DialogueManager**: Controla el estado de cada conversación
- **Session Store**: Almacena datos temporales por usuario
- **File Handler**: Procesa uploads de certificados
- **Reminder Scheduler**: Envía notificaciones automáticas

### **Estados de Conversación**

#### **Estado: `inicio`**
- **Trigger**: `/start`, "hola", o mensaje inicial
- **Acción**: Muestra saludo y explica el sistema
- **Transición**: → `legajo`

#### **Estado: `legajo`**
- **Input esperado**: Número de legajo (4 dígitos)
- **Validación**: 
  - Formato numérico
  - Longitud correcta
  - Búsqueda en tabla `employees`
- **Resultado exitoso**: → `motivo`
- **Resultado fallido**: → `pedir_nombre_provisional`

#### **Estado: `pedir_nombre_provisional`**
- **Input esperado**: Nombre y apellido completo
- **Validación**: Mínimo 5 caracteres
- **Acción**: Almacena nombre para validación RRHH
- **Transición**: → `confirmar_legajo_provisional`

#### **Estado: `confirmar_legajo_provisional`**
- **Opciones**: "Continuar provisional" o "Reingresar legajo"
- **Continuar**: → `motivo` (con flag provisional = true)
- **Reingresar**: → `legajo`

#### **Estado: `motivo`**
- **Input**: Selección de motivo de ausencia
- **Opciones disponibles**:
  - `enfermedad_inculpable` → Requiere certificado
  - `enfermedad_familiar` → Requiere certificado
  - `fallecimiento` → No requiere certificado
  - `nacimiento` → No requiere certificado
  - `matrimonio` → No requiere certificado
  - `paternidad` → No requiere certificado
  - `permiso_gremial` → No requiere certificado
  - `art` → No requiere certificado
- **Validación**: Debe estar en lista válida
- **Transición**: → `fecha`

#### **Estado: `fecha`**
- **Opciones rápidas**: "Hoy", "Mañana", "Otra fecha"
- **Fecha específica**: Formato DD/MM/YYYY
- **Validación**: 
  - Formato de fecha válido
  - Fecha no anterior a hoy
  - Conversión a formato ISO
- **Transición**: → `dias`

#### **Estado: `dias`**
- **Opciones predefinidas**: 1, 2, 3, 5, 10, "Otro"
- **Valor específico**: Número entero positivo
- **Validación**: 
  - Número válido entre 1-365
  - Coherencia con tipo de ausencia
- **Cálculo automático**: `fecha_fin_estimada`
- **Transición**: 
  - Si requiere certificado → `certificado`
  - Si no requiere → `confirmacion`

#### **Estado: `certificado`**
- **Solo si motivo requiere certificado médico**
- **Opciones**: "Adjuntar ahora" o "Enviar más tarde"
- **Adjuntar ahora**: → `esperando_certificado`
- **Más tarde**: → `confirmacion` (con flag pendiente)

#### **Estado: `esperando_certificado`**
- **Input esperado**: Archivo (foto, PDF, documento)
- **Formatos soportados**: JPG, PNG, PDF, DOCX, DOC
- **Proceso**:
  1. Download desde API de Telegram
  2. Almacenamiento en `uploads/{user_id}/`
  3. Generación de nombre único
  4. Registro de ruta en sesión
- **Transición**: → `confirmacion`

#### **Estado: `confirmacion`**
- **Presenta resumen completo** de la solicitud:
  - Legajo (validado/provisional)
  - Motivo de ausencia
  - Fechas y duración
  - Estado del certificado
- **Opciones**: "Confirmar" o "Editar"
- **Confirmar**: → `completado` + creación en BD
- **Editar**: → `motivo` (reinicio parcial)

#### **Estado: `completado`**
- **Mensaje personalizado** según motivo:
  - Fallecimiento → Condolencias
  - Nacimiento → Felicitaciones
  - Otros → Mensaje estándar
- **Información proporcionada**:
  - Código de seguimiento único
  - Tipo de registro (confirmado/provisional)
  - Recordatorios si aplica
- **Fin de conversación**

### **Manejo de Archivos**

#### **Proceso de Upload**
```python
# 1. Detección de tipo de archivo
if message.photo:
    file_info = await bot.get_file(message.photo[-1].file_id)
    file_name = f"certificado_{session_id}_{message.photo[-1].file_id}.jpg"
elif message.document:
    file_info = await bot.get_file(message.document.file_id)
    file_name = message.document.file_name or f"certificado_{session_id}_{message.document.file_id}"

# 2. Creación de directorio
upload_dir = f"uploads/{session_id}"
os.makedirs(upload_dir, exist_ok=True)

# 3. Download del archivo
file_path = os.path.join(upload_dir, file_name)
await bot.download_file(file_info.file_path, file_path)

# 4. Registro en sesión
session["certificado_path"] = file_path
```

#### **Estructura de Almacenamiento**
```
uploads/
├── 123456789/                    # Telegram User ID
│   ├── certificado_123_file1.jpg
│   ├── certificado_123_file2.pdf
│   └── ...
├── 987654321/
│   ├── certificado_987_file1.docx
│   └── ...
```

---

## 🌐 **Funcionamiento del Dashboard Web**

### **Arquitectura Backend**

#### **Servidor aiohttp**
```python
# Configuración del servidor
app = web.Application()
app.router.add_get('/', serve_dashboard)       # Página principal
app.router.add_get('/api/ausencias', get_ausencias)    # API datos
app.router.add_get('/api/stats', get_stats)            # API estadísticas  
app.router.add_get('/api/certificado/{id}', get_certificate)  # API certificados
```

#### **API Endpoints Detallados**

##### **GET /api/ausencias**
```python
# Parámetros de query soportados:
- estado: 'completo', 'incompleto', 'rechazado'
- motivo: cualquier motivo válido
- fecha_desde: fecha ISO (YYYY-MM-DD) 
- fecha_hasta: fecha ISO (YYYY-MM-DD)
- filtro_fecha: 'hoy', '3dias', 'semana', 'mes', 'todos'
- area: área de trabajo del empleado
- limit: número máximo de resultados (default: 100)

# Query SQL generado:
SELECT Aviso.*, Employee.nombre, Employee.area, Employee.puesto
FROM avisos 
LEFT JOIN employees ON avisos.legajo = employees.legajo
WHERE [condiciones aplicadas]
ORDER BY created_at DESC
LIMIT [limit]
```

##### **GET /api/stats**
```python
# Estadísticas calculadas:
{
    "total_ausencias": COUNT(*) FROM avisos,
    "ausencias_activas": COUNT(*) WHERE estado_aviso != 'completo',
    "requieren_validacion": COUNT(*) WHERE employee.legajo IS NULL,
    "certificados_pendientes": COUNT(*) WHERE estado_certificado IN ('pendiente', 'en_revision'),
    "completadas": COUNT(*) WHERE estado_aviso = 'completo',
    "alta_prioridad": COUNT(*) WHERE requieren_validacion AND certificados_pendientes
}
```

##### **GET /api/certificado/{id_aviso}**
```python
# Proceso de servir certificado:
1. Buscar certificado en BD por id_aviso
2. Validar existencia del archivo físico  
3. Determinar content-type por extensión
4. Configurar headers apropiados:
   - Images/PDF: disposition="inline" (ver en browser)
   - Word docs: disposition="attachment" (descargar)
5. Servir archivo con aiohttp.FileResponse
```

### **Frontend - Interfaz de Usuario**

#### **Componentes JavaScript**

##### **Auto-refresh System**
```javascript
// Actualización automática cada 30 segundos
setInterval(() => {
    loadData();
}, 30000);

// Pausa cuando pestaña no visible
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh(); 
    }
});
```

##### **Sistema de Filtros**
```javascript
function applyFilters() {
    const filters = {
        estado: document.getElementById('filtroEstado').value,
        motivo: document.getElementById('filtroMotivo').value,
        filtro_fecha: document.getElementById('filtroFecha').value,
        area: document.getElementById('filtroSector').value
    };
    
    // Construcción de query string
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
    });
    
    // Llamada a API
    fetch(`/api/ausencias?${params}`)
        .then(response => response.json())
        .then(data => renderTable(data.data));
}
```

##### **Renderizado de Tabla**
```javascript
function renderTable(data) {
    const tbody = document.getElementById('ausenciasTableBody');
    tbody.innerHTML = '';
    
    data.forEach(ausencia => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ausencia.id_aviso}</td>
            <td>${ausencia.nombre_empleado}<br>Leg: ${ausencia.legajo}</td>
            <td>${ausencia.area}</td>
            <td>${formatMotivo(ausencia.motivo)}</td>
            <td>${formatDate(ausencia.fecha_inicio)}</td>
            <td>${ausencia.dias_estimados} días</td>
            <td><span class="badge badge-${ausencia.estado_aviso}">${formatEstado(ausencia.estado_aviso)}</span></td>
            <td><span class="badge badge-${ausencia.estado_certificado}">${formatEstado(ausencia.estado_certificado)}</span></td>
            <td>${renderCertificateButton(ausencia)}</td>
            <td><span class="${ausencia.requiere_validacion_rrhh ? 'validation-required' : 'validation-ok'}">${ausencia.requiere_validacion_rrhh ? 'Requerida' : 'OK'}</span></td>
            <td><span class="badge priority-${ausencia.prioridad}">${ausencia.prioridad.toUpperCase()}</span></td>
            <td>${ausencia.accion_requerida}</td>
        `;
        tbody.appendChild(row);
    });
}
```

#### **Lógica de Negocio Frontend**

##### **Cálculo de Prioridades**
```javascript
// Lógica replicada del backend
function calculatePriority(ausencia) {
    const requiereValidacion = !ausencia.nombre_empleado || ausencia.nombre_empleado === "No encontrado";
    
    if (requiereValidacion) {
        return "alta";  // Validación RRHH siempre es alta prioridad
    } else if (ausencia.estado_aviso === "completo") {
        return "baja";
    } else {
        return "media";
    }
}
```

##### **Renderizado Contextual de Certificados**
```javascript
function renderCertificateButton(ausencia) {
    const needsCertificate = ['enfermedad_inculpable', 'enfermedad_familiar'].includes(ausencia.motivo);
    const hasCertificate = ausencia.estado_certificado && 
                          ausencia.estado_certificado !== 'N/A' && 
                          ausencia.estado_certificado !== 'pendiente';
    
    if (needsCertificate && hasCertificate) {
        return `<a href="/api/certificado/${ausencia.id_aviso}" target="_blank" class="cert-btn cert-btn-view">📄 Ver</a>`;
    } else if (needsCertificate) {
        return `<span class="cert-btn cert-btn-unavailable">Sin certificado</span>`;
    } else {
        return `<span style="font-size: 0.8rem; color: #666;">No requerido</span>`;
    }
}
```

---

## ⏰ **Sistema de Recordatorios Automáticos**

### **Arquitectura del Scheduler**

#### **Componente ReminderScheduler**
```python
class ReminderScheduler:
    def __init__(self):
        self.bot_instance = None
        self.running = False
    
    async def start(self):
        """Loop principal del scheduler"""
        while self.running:
            try:
                await self._check_and_send_reminders()
                await asyncio.sleep(30 * 60)  # 30 minutos
            except Exception as e:
                logger.error(f"Error en scheduler: {e}")
                await asyncio.sleep(60)  # Reintentar en 1 minuto
```

#### **Lógica de Detección**
```python
async def _check_and_send_reminders(self):
    now = datetime.now()
    
    # Solo ejecutar entre 22:00-22:59
    if now.hour != 22:
        return
        
    today = now.date()
    
    # Query para encontrar candidatos
    avisos_pendientes = session.execute(
        select(Aviso).where(
            and_(
                Aviso.motivo.in_(['enfermedad_inculpable', 'enfermedad_familiar']),
                Aviso.estado_certificado == 'pendiente',
                Aviso.created_at >= datetime.combine(today, datetime.min.time()),
                Aviso.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                Aviso.recordatorio_22h_enviado == False,
                Aviso.telegram_user_id.isnot(None)
            )
        )
    ).scalars().all()
```

#### **Proceso de Envío**
```python
async def _send_reminder(self, session, aviso):
    # 1. Generar mensaje personalizado
    mensaje = f"""
** RECORDATORIO IMPORTANTE **
Tu solicitud de ausencia por **{motivo_text}** (código {aviso.id_aviso}) 
está **pendiente del certificado médico**.
[...resto del mensaje...]
"""
    
    # 2. Enviar via Telegram Bot API
    await self.bot_instance.send_message(
        chat_id=aviso.telegram_user_id,
        text=mensaje,
        parse_mode='Markdown'
    )
    
    # 3. Marcar como enviado (anti-spam)
    aviso.recordatorio_22h_enviado = True
    
    # 4. Registrar en log de notificaciones
    notificacion = Notificacion(
        id_aviso=aviso.id_aviso,
        destino=aviso.telegram_user_id,
        enviado_en=datetime.now(),
        canal="telegram",
        payload={
            "tipo": "recordatorio_certificado",
            "hora_limite": "24:00",
            "motivo": aviso.motivo
        }
    )
    session.add(notificacion)
```

### **Integración con Bot Principal**

#### **Inicialización Concurrente**
```python
async def main():
    # Configurar bot instance para recordatorios
    reminder_scheduler.set_bot_instance(bot)
    
    # Iniciar ambos procesos en paralelo
    reminder_task = asyncio.create_task(reminder_scheduler.start())
    
    try:
        # Bot principal (polling)
        await dp.start_polling(bot, skip_updates=True)
    finally:
        # Cleanup al terminar
        reminder_scheduler.stop()
        reminder_task.cancel()
```

---

## 💾 **Gestión de Base de Datos**

### **Modelo de Datos Detallado**

#### **Tabla: avisos**
```sql
CREATE TABLE avisos (
    id_aviso VARCHAR(64) PRIMARY KEY,           -- A-YYYYMMDD-NNNN
    legajo VARCHAR(10) NOT NULL,                -- FK a employees.legajo
    motivo VARCHAR(50) NOT NULL,                -- Tipo de ausencia
    fecha_inicio DATE NOT NULL,                 -- Inicio de ausencia
    fecha_fin_estimada DATE NOT NULL,           -- Fin estimado
    duracion_estimdays INTEGER NOT NULL,        -- Duración en días
    estado_aviso VARCHAR(50),                   -- completo, incompleto, pendiente, rechazado
    estado_certificado VARCHAR(50),             -- pendiente, en_revision, validado, N/A
    documento_tipo VARCHAR(50),                 -- certificado_medico, etc.
    fuera_de_termino BOOLEAN DEFAULT 0,         -- Presentado tarde
    adjunto BOOLEAN DEFAULT 0,                  -- Tiene archivo
    observaciones TEXT,                         -- Notas adicionales
    created_at DATETIME DEFAULT (datetime('now')), -- Timestamp creación
    recordatorio_22h_enviado BOOLEAN DEFAULT 0, -- Flag anti-spam
    telegram_user_id VARCHAR(50)                -- ID Telegram del usuario
);
```

#### **Relaciones y Constraints**
- **FK avisos.legajo → employees.legajo**: Referencia a empleado
- **FK certificados.id_aviso → avisos.id_aviso**: Un certificado por aviso
- **FK notificaciones.id_aviso → avisos.id_aviso**: Múltiples notificaciones por aviso

### **Operaciones de Datos Críticas**

#### **Creación de Aviso**
```python
def crear_aviso_simple(aviso_data):
    with session_scope() as session:
        # 1. Validar y normalizar datos
        legajo = str(aviso_data["legajo"])
        motivo = str(aviso_data["motivo"])
        fecha_inicio = _to_date_iso(aviso_data["fecha_inicio"])
        
        # 2. Generar ID único
        id_aviso = _gen_id_aviso(session, fecha_inicio)
        
        # 3. Determinar requerimientos de certificado
        documento_tipo = None
        if aviso_data.get("requiere_certificado"):
            if motivo in ["enfermedad_inculpable", "enfermedad_familiar"]:
                documento_tipo = "certificado_medico"
        
        # 4. Crear registro
        aviso = Aviso(
            id_aviso=id_aviso,
            legajo=legajo,
            motivo=motivo,
            fecha_inicio=fecha_inicio,
            # ... resto de campos
            telegram_user_id=aviso_data.get("telegram_user_id")
        )
        
        session.add(aviso)
        session.flush()
        
        # 5. Crear certificado si aplica
        if certificado_path and requiere_certificado:
            certificado = Certificado(
                id_aviso=id_aviso,
                tipo=documento_tipo,
                archivo_path=str(certificado_path),
                valido=True,
                recibido_en=datetime.now()
            )
            session.add(certificado)
```

#### **Queries de Dashboard**
```python
def get_ausencias_with_filters(filters):
    query = select(Aviso, Employee).outerjoin(Employee, Aviso.legajo == Employee.legajo)
    
    # Aplicar filtros dinámicamente
    if filters.get('estado'):
        if filters['estado'] == 'completo':
            query = query.where(Aviso.estado_aviso == 'completo')
        elif filters['estado'] == 'incompleto':
            query = query.where(Aviso.estado_aviso != 'completo')
    
    if filters.get('motivo'):
        query = query.where(Aviso.motivo == filters['motivo'])
    
    if filters.get('filtro_fecha'):
        today = datetime.now().date()
        if filters['filtro_fecha'] == 'hoy':
            query = query.where(Aviso.fecha_inicio == today)
        elif filters['filtro_fecha'] == '3dias':
            query = query.where(Aviso.fecha_inicio >= today - timedelta(days=2))
    
    # Ordenar y ejecutar
    query = query.order_by(Aviso.created_at.desc()).limit(filters.get('limit', 100))
    return session.execute(query).all()
```

---

## 🔧 **Configuración y Variables de Entorno**

### **Archivo .env**
```env
# Telegram Bot Configuration
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Database Configuration  
DATABASE_URL=sqlite:///sistema_ausencias.db
DATABASE_ECHO=false

# Server Configuration
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8090
DEBUG_MODE=false

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=sistema_ausencias.log

# File Upload Configuration
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf,docx,doc

# Reminder Configuration
REMINDER_HOUR=22
REMINDER_MESSAGE_TEMPLATE=recordatorio_certificado.txt
```

### **Configuración Centralizada**
```python
# src/config.py
class Settings:
    def __init__(self):
        load_dotenv()
        
        # Telegram
        self.TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN is required")
        
        # Database
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///sistema_ausencias.db')
        
        # Server
        self.DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '127.0.0.1')
        self.DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '8090'))
        
        # Upload
        self.UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', 'uploads'))
        self.MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))

settings = Settings()
```

---

## 🚀 **Procesos de Startup y Shutdown**

### **Secuencia de Inicio del Bot**
```python
async def main():
    print("Bot iniciando...")
    
    # 1. Verificar configuración
    if not settings.TELEGRAM_TOKEN:
        raise ValueError("Token de Telegram requerido")
    
    # 2. Inicializar base de datos
    ensure_schema()
    print("Base de datos inicializada")
    
    # 3. Crear instancias
    dm = DialogueManager()
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()
    
    # 4. Registrar handlers
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_document, lambda msg: msg.document or msg.photo)
    dp.callback_query.register(handle_callback)
    dp.message.register(handle_message)
    
    # 5. Configurar recordatorios
    reminder_scheduler.set_bot_instance(bot)
    reminder_task = asyncio.create_task(reminder_scheduler.start())
    
    try:
        # 6. Iniciar polling
        print("Iniciando polling...")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        # 7. Cleanup
        reminder_scheduler.stop()
        reminder_task.cancel()
        await bot.session.close()
```

### **Secuencia de Inicio del Dashboard**
```python
async def init_app():
    # 1. Verificar base de datos
    ensure_schema()
    
    # 2. Crear aplicación aiohttp
    app = web.Application()
    
    # 3. Configurar rutas
    app.router.add_get('/', serve_dashboard)
    app.router.add_get('/api/ausencias', get_ausencias)
    app.router.add_get('/api/stats', get_stats)
    app.router.add_get('/api/certificado/{id_aviso}', get_certificate)
    
    # 4. Configurar middleware
    app.middlewares.append(cors_middleware)
    
    return app

async def main():
    # 5. Inicializar
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    # 6. Iniciar servidor
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    
    print(f"Dashboard iniciado en: http://{HOST}:{PORT}")
    
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
```

---

## 📊 **Monitoreo y Logs**

### **Sistema de Logging**
```python
import logging

# Configuración global
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Consola
        logging.FileHandler('sistema_ausencias.log')  # Archivo
    ]
)

# Loggers específicos
bot_logger = logging.getLogger('bot')
dashboard_logger = logging.getLogger('dashboard')
reminder_logger = logging.getLogger('reminders')
```

### **Eventos Críticos Loggeados**
- **Bot**: Mensajes recibidos, errores de procesamiento, uploads
- **Dashboard**: Requests API, errores de servidor, acceso a certificados
- **Recordatorios**: Ejecución de scheduler, mensajes enviados, errores
- **Base de Datos**: Operaciones críticas, errores de integridad

### **Health Checks**
```python
async def health_check():
    try:
        # 1. Test de base de datos
        with session_scope() as session:
            count = session.execute(select(func.count()).select_from(Employee)).scalar()
        
        # 2. Test de archivos
        upload_dir = Path('uploads')
        if not upload_dir.exists():
            upload_dir.mkdir()
        
        # 3. Response
        return {
            "status": "ok",
            "database": "connected", 
            "employees_count": count,
            "upload_directory": "accessible",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

---

## 🔒 **Seguridad y Validaciones**

### **Validación de Entrada**
```python
def parse_legajo(text: str) -> str:
    """Valida y normaliza número de legajo"""
    if not text:
        return ""
    
    # Extraer solo dígitos
    digits = re.sub(r'\D', '', text)
    
    # Validar longitud
    if len(digits) != 4:
        return ""
    
    return digits

def sanitize_filename(filename: str) -> str:
    """Sanitiza nombre de archivo para seguridad"""
    # Remover caracteres peligrosos
    clean = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Limitar longitud
    return clean[:100]

def validate_date_input(date_str: str) -> Optional[date]:
    """Valida formato de fecha DD/MM/YYYY"""
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        return None
```

### **Control de Acceso**
- **Bot**: Solo usuarios con Telegram ID válido
- **Dashboard**: Acceso por red local (127.0.0.1)
- **API**: Sin autenticación (red confiable)
- **Archivos**: Path validation para prevenir directory traversal

### **Manejo de Errores**
```python
try:
    result = process_user_input(user_message)
except ValidationError as e:
    logger.warning(f"Validation error: {e}")
    return {"reply_text": "Formato inválido. Intenta nuevamente."}
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    return {"reply_text": "Error del sistema. Contacta soporte."}
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return {"reply_text": "Error inesperado. Por favor intenta más tarde."}
```

---

## 🔧 **Mantenimiento y Operaciones**

### **Tareas de Mantenimiento Regulares**

#### **Diario**
- Verificar logs de errores
- Monitorear uso de disco (uploads)
- Revisar casos de alta prioridad en dashboard

#### **Semanal**
- Backup de base de datos
- Limpieza de logs antiguos
- Análisis de métricas de uso

#### **Mensual**
- Backup completo del sistema
- Revisión de certificados pendientes antiguos
- Análisis de performance y optimizaciones

### **Scripts de Utilidad**
```bash
# Backup de base de datos
cp sistema_ausencias.db backup/sistema_$(date +%Y%m%d).db

# Limpiar logs antiguos (más de 30 días)
find . -name "*.log" -mtime +30 -delete

# Verificar integridad de uploads
python -c "
from pathlib import Path
upload_dir = Path('uploads')
total_files = sum(1 for _ in upload_dir.rglob('*') if _.is_file())
total_size = sum(_.stat().st_size for _ in upload_dir.rglob('*') if _.is_file())
print(f'Archivos: {total_files}, Tamaño: {total_size/1024/1024:.2f}MB')
"
```

### **Recuperación ante Fallos**
1. **Bot no responde**: Reiniciar proceso, verificar token
2. **Dashboard error 500**: Revisar logs, verificar BD
3. **Certificados no accesibles**: Verificar permisos, rutas
4. **BD corrupta**: Restaurar desde backup más reciente
5. **Disco lleno**: Limpiar uploads antiguos, logs

---

**© 2025 - Sistema de Gestión de Ausencias**  
**Documentación actualizada**: Agosto 2025