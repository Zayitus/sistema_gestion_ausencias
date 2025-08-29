# Sistema de Gestión de Ausencias - Documentación Técnica

## 📋 **Resumen Ejecutivo**

Sistema automatizado para la gestión de ausencias laborales que integra un bot de Telegram para empleados con un dashboard web para RRHH. Incluye validación automática de empleados, gestión de certificados médicos, recordatorios automáticos y reportería en tiempo real.

---

## 🏗️ **Arquitectura del Sistema**

### **Componentes Principales**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Bot Telegram  │    │  Dashboard Web   │    │   Base de Datos │
│   (Empleados)   │◄──►│     (RRHH)       │◄──►│    SQLite       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Sistema de      │    │   Gestor de      │    │  Almacenamiento │
│ Recordatorios   │    │  Certificados    │    │  de Archivos    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Stack Tecnológico**

- **Backend**: Python 3.11+
- **Bot Framework**: aiogram 3.x
- **Web Framework**: aiohttp
- **Base de Datos**: SQLite
- **ORM**: SQLAlchemy 2.x
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla)
- **Scheduler**: AsyncIO + Custom Scheduler
- **File Storage**: Sistema de archivos local

---

## 🗄️ **Modelo de Base de Datos**

### **Tablas Principales**

#### **1. employees** - Empleados
```sql
- legajo (PK, VARCHAR(10)): Número de legajo del empleado
- nombre (VARCHAR(100)): Nombre completo del empleado  
- area (VARCHAR(100)): Área/departamento de trabajo
- puesto (VARCHAR(100)): Cargo del empleado
- fecha_ingreso (DATE): Fecha de ingreso a la empresa
- turno (VARCHAR(50)): Turno de trabajo
- activo (BOOLEAN): Estado activo/inactivo
```

#### **2. avisos** - Solicitudes de Ausencia
```sql
- id_aviso (PK, VARCHAR(64)): Código único del aviso (A-YYYYMMDD-NNNN)
- legajo (FK, VARCHAR(10)): Referencia al empleado
- motivo (VARCHAR(50)): Tipo de ausencia
- fecha_inicio (DATE): Fecha de inicio de la ausencia
- fecha_fin_estimada (DATE): Fecha estimada de finalización
- duracion_estimdays (INTEGER): Duración en días
- estado_aviso (VARCHAR(50)): Estado de la solicitud
- estado_certificado (VARCHAR(50)): Estado del certificado médico
- documento_tipo (VARCHAR(50)): Tipo de documento requerido
- fuera_de_termino (BOOLEAN): Si se presentó fuera de plazo
- adjunto (BOOLEAN): Si tiene archivo adjunto
- observaciones (TEXT): Notas adicionales
- created_at (DATETIME): Fecha de creación
- recordatorio_22h_enviado (BOOLEAN): Flag de recordatorio enviado
- telegram_user_id (VARCHAR(50)): ID del usuario de Telegram
```

#### **3. certificados** - Certificados Médicos
```sql
- id (PK, INTEGER): Identificador único
- id_aviso (FK, VARCHAR(64)): Referencia al aviso
- tipo (VARCHAR(50)): Tipo de certificado
- recibido_en (DATETIME): Fecha de recepción
- valido (BOOLEAN): Si el certificado es válido
- notas (TEXT): Observaciones sobre el certificado
- archivo_path (VARCHAR(255)): Ruta del archivo
- created_at (DATETIME): Fecha de creación
```

#### **4. notificaciones** - Log de Notificaciones
```sql
- id (PK, INTEGER): Identificador único
- id_aviso (FK, VARCHAR(64)): Referencia al aviso
- destino (VARCHAR(50)): Destinatario de la notificación
- enviado_en (DATETIME): Fecha de envío
- canal (VARCHAR(50)): Canal usado (telegram)
- payload (JSON): Datos adicionales de la notificación
- created_at (DATETIME): Fecha de creación
```

#### **5. auditoria** - Log de Auditoría
```sql
- id (PK, INTEGER): Identificador único
- entidad (VARCHAR(50)): Tabla afectada
- entidad_id (VARCHAR(64)): ID del registro afectado
- accion (VARCHAR(50)): Acción realizada
- ts (DATETIME): Timestamp de la acción
- actor (VARCHAR(50)): Usuario que ejecutó la acción
- detalle (JSON): Detalles de la operación
```

---

## 🤖 **Bot de Telegram - Flujo de Conversación**

### **Estados del Diálogo**

```
inicio → legajo → [nombre_provisional] → motivo → fecha → dias → [certificado] → confirmacion → completado
```

### **Flujo Detallado**

1. **Inicio** (`/start`)
   - Saludo y explicación del sistema
   - Transición a solicitud de legajo

2. **Validación de Legajo**
   - Búsqueda en base de datos de empleados
   - Si existe: Continúa con datos validados
   - Si no existe: Solicita nombre para legajo provisional

3. **Selección de Motivo**
   - Opciones: enfermedad_inculpable, enfermedad_familiar, fallecimiento, nacimiento, matrimonio, paternidad, permiso_gremial, art
   - Determina automáticamente si requiere certificado

4. **Fecha de Inicio**
   - Opciones rápidas: Hoy, Mañana, Otra fecha
   - Validación de formato DD/MM/YYYY

5. **Duración**
   - Opciones predefinidas: 1, 2, 3, 5, 10 días u "Otro"
   - Validación numérica

6. **Certificado Médico** (si aplica)
   - Opciones: "Adjuntar ahora" o "Enviar más tarde"
   - Procesamiento de archivos (JPEG, PNG, PDF, DOCX)

7. **Confirmación**
   - Resumen completo de la solicitud
   - Opciones: "Confirmar" o "Editar"

8. **Finalización**
   - Mensaje personalizado según motivo
   - Código de seguimiento generado
   - Recordatorios automáticos si aplica

### **Manejo de Archivos**

- **Formatos soportados**: JPEG, JPG, PNG, PDF, DOCX, DOC
- **Almacenamiento**: `uploads/{telegram_user_id}/`
- **Naming**: `certificado_{user_id}_{file_id}.ext`
- **Validación**: Tamaño y formato automático

---

## 🌐 **Dashboard Web RRHH**

### **Funcionalidades**

#### **1. Vista Principal**
- Estadísticas resumidas en tiempo real
- Tabla de ausencias con filtros avanzados
- Auto-refresh cada 30 segundos
- Diseño responsive para desktop y móvil

#### **2. Sistema de Filtros**
- **Estado**: Completo, Incompleto, Rechazado, Requiere Validación
- **Motivo**: Todos los tipos de ausencia disponibles
- **Fecha**: Hoy, Últimos 3 días, Semana, Mes, Todos
- **Sector**: Por área de trabajo del empleado

#### **3. Gestión de Certificados**
- Visualización directa en navegador (PDF, imágenes)
- Descarga automática (documentos Word)
- Validación de existencia de archivos
- Links contextuales según disponibilidad

#### **4. Sistema de Prioridades**
- **Alta**: Requieren validación RRHH o certificados críticos
- **Media**: Ausencias incompletas sin validación
- **Baja**: Ausencias completas y validadas

### **API Endpoints**

```
GET  /api/ausencias     - Lista de ausencias con filtros
GET  /api/stats         - Estadísticas resumidas
GET  /api/certificado/{id} - Descarga de certificado
GET  /health           - Estado del sistema
```

---

## ⏰ **Sistema de Recordatorios**

### **Funcionamiento**

1. **Scheduler Automático**
   - Ejecuta cada 30 minutos
   - Activo solo entre 22:00-22:59
   - Proceso asíncrono independiente

2. **Condiciones de Activación**
   - Ausencia registrada el mismo día
   - Motivo que requiere certificado
   - Estado "pendiente" en certificado
   - Usuario con `telegram_user_id` válido
   - No se ha enviado recordatorio previamente

3. **Contenido del Recordatorio**
   - Mensaje personalizado con código de ausencia
   - Advertencia de plazo (2 horas restantes)
   - Instrucciones claras para envío
   - Menciona consecuencias de no cumplir

4. **Registro y Auditoría**
   - Flag anti-spam en tabla `avisos`
   - Log completo en tabla `notificaciones`
   - Manejo de errores sin afectar bot principal

---

## 🔧 **Configuración e Instalación**

### **Requisitos del Sistema**

- Python 3.11 o superior
- 500 MB de espacio en disco
- Conexión a internet para Telegram
- Token de bot de Telegram

### **Dependencias Python**

```bash
aiogram>=3.0.0
aiohttp>=3.8.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
```

### **Variables de Entorno** (`.env`)

```env
TELEGRAM_TOKEN=tu_token_aqui
DATABASE_URL=sqlite:///sistema_ausencias.db
LOG_LEVEL=INFO
```

### **Estructura de Directorios**

```
Repo-Actualizado/
├── src/
│   ├── config.py              # Configuración global
│   ├── dialogue/              # Lógica del bot
│   │   ├── manager.py         # Gestor de conversación
│   │   └── prompts.py         # Mensajes del bot
│   ├── persistence/           # Base de datos
│   │   ├── dao.py             # Operaciones de datos
│   │   ├── models.py          # Modelos SQLAlchemy
│   │   └── seed.py            # Inicialización de BD
│   ├── reminders/             # Sistema de recordatorios
│   │   └── scheduler.py       # Scheduler automático
│   ├── telegram/              # Bot de Telegram
│   │   └── keyboards.py       # Teclados inline
│   ├── utils/                 # Utilidades
│   │   └── normalize.py       # Validación de datos
│   └── web/                   # Dashboard web
│       ├── api.py             # API REST
│       └── templates/         # HTML templates
├── uploads/                   # Certificados subidos
├── run_bot.py                 # Ejecutor principal del bot
├── dashboard_server.py        # Servidor web
└── sistema_ausencias.db      # Base de datos SQLite
```

---

## 🚀 **Despliegue y Operación**

### **Inicio del Sistema**

```bash
# Bot de Telegram con recordatorios
python run_bot.py

# Dashboard web (puerto 8090)
python dashboard_server.py
```

### **Monitoreo**

- **Logs del sistema**: Salida estándar con nivel INFO
- **Health check**: `GET /health` (dashboard)
- **Métricas**: `GET /api/stats` (dashboard)

### **Backup y Mantenimiento**

1. **Backup de BD**: Copiar `sistema_ausencias.db`
2. **Backup de archivos**: Copiar carpeta `uploads/`
3. **Limpieza**: Scripts de mantenimiento incluidos
4. **Logs**: Rotación manual recomendada

---

## 🔒 **Seguridad**

### **Medidas Implementadas**

- Validación de entrada en todos los endpoints
- Sanitización de nombres de archivo
- Control de acceso por `telegram_user_id`
- Logs de auditoría completos
- Manejo seguro de errores sin exposición de datos

### **Recomendaciones Adicionales**

- Ejecutar en red privada corporativa
- Backup regular de datos
- Monitoreo de logs de error
- Actualización regular de dependencias

---

## 📊 **Métricas y KPIs**

### **Métricas Disponibles**

- Total de ausencias registradas
- Ausencias activas vs completadas
- Certificados pendientes de revisión
- Casos que requieren validación RRHH
- Ausencias de alta prioridad
- Tasa de respuesta a recordatorios

### **Reportes Generados**

- Dashboard en tiempo real
- Filtros por período y departamento
- Exportación de datos (API JSON)
- Historial de notificaciones

---

## 🛠️ **Troubleshooting**

### **Problemas Comunes**

1. **Bot no responde**
   - Verificar token de Telegram
   - Revisar conexión a internet
   - Comprobar que solo una instancia esté corriendo

2. **Dashboard no carga**
   - Verificar puerto disponible (8090)
   - Comprobar permisos de archivo
   - Revisar logs de error

3. **Certificados no se ven**
   - Validar rutas de archivo
   - Comprobar permisos de lectura
   - Verificar formato de archivo

4. **Recordatorios no se envían**
   - Verificar que el scheduler esté activo
   - Comprobar configuración de hora del sistema
   - Revisar logs de recordatorios

### **Logs y Debugging**

```bash
# Ver logs en tiempo real
tail -f logs/sistema.log

# Verificar estado de BD
python -c "from src.persistence.dao import *; print('BD OK')"

# Test de recordatorios
python test_reminder_manual.py
```

---

## 📈 **Roadmap y Mejoras Futuras**

### **Versión Actual: 1.0**
- ✅ Bot de Telegram completo
- ✅ Dashboard web RRHH
- ✅ Sistema de recordatorios
- ✅ Gestión de certificados

### **Propuestas Futuras: 2.0**
- 📧 Notificaciones por email
- 📱 App móvil nativa
- 📊 Reportes avanzados en Excel
- 🔐 Autenticación de usuarios
- ☁️ Integración con sistemas RRHH
- 📅 Calendario de ausencias
- 🤖 IA para validación automática de certificados

---

## 👥 **Contacto y Soporte**

**Sistema desarrollado por**: [Tu nombre]
**Fecha**: Agosto 2025
**Versión**: 1.0.0

Para soporte técnico, consultar logs del sistema y documentación de usuario incluida.