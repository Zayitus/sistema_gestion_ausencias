# 🤖 Sistema de Gestión de Ausencias Laborales

Sistema integral de gestión de ausencias laborales que automatiza y digitaliza el proceso completo de solicitud, validación y seguimiento de ausencias de empleados, integrando un **Bot de Telegram** para empleados con un **Dashboard Web** para supervisión de RRHH.

## 🚀 **Características Principales**

- ✅ **Bot de Telegram Conversacional** - Interfaz intuitiva para empleados
- ✅ **Dashboard Web RRHH** - Supervisión centralizada y filtros avanzados
- ✅ **Gestión de Certificados** - Subida y visualización de documentos médicos
- ✅ **Recordatorios Automáticos** - Notificaciones inteligentes a las 22:00
- ✅ **Validación de Empleados** - Manejo de legajos provisionales
- ✅ **Sistema de Prioridades** - Identificación automática de casos urgentes
- ✅ **Estadísticas en Tiempo Real** - Métricas actualizadas automáticamente

## 🏗️ **Arquitectura**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EMPLEADOS     │    │      RRHH        │    │   BASE DE       │
│  (Telegram Bot) │◄──►│  (Dashboard Web) │◄──►│    DATOS        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Recordatorios   │    │   Certificados   │    │  Almacenamiento │
│  Automáticos    │    │     Médicos      │    │  de Archivos    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🛠️ **Stack Tecnológico**

- **Backend**: Python 3.11+
- **Bot Framework**: aiogram 3.x
- **Web Framework**: aiohttp
- **Base de Datos**: SQLite + SQLAlchemy 2.x
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla)
- **Scheduler**: AsyncIO + Custom Tasks

## 📦 **Instalación**

### **Requisitos**
- Python 3.11 o superior
- Token de Bot de Telegram (obtener de [@BotFather](https://t.me/BotFather))

### **Pasos de Instalación**

1. **Clonar el repositorio**
```bash
git clone [URL_DEL_REPO]
cd Repo-Actualizado
```

2. **Crear entorno virtual**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac  
source .venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus valores reales
```

5. **Inicializar base de datos**
```bash
python src/persistence/seed.py
```

## 🚀 **Ejecución**

### **Iniciar el Sistema Completo**

1. **Bot de Telegram + Recordatorios**
```bash
python run_bot.py
```

2. **Dashboard Web** (puerto 8090)
```bash
python dashboard_server.py
```

### **Acceso al Dashboard**
- URL: http://127.0.0.1:8090
- Sin autenticación requerida (red interna)

## 📱 **Uso del Sistema**

### **Para Empleados (Telegram)**
1. Buscar el bot en Telegram
2. Enviar `/start` para comenzar
3. Seguir el flujo conversacional:
   - Ingresar legajo
   - Seleccionar motivo de ausencia
   - Especificar fecha y duración
   - Adjuntar certificado (si es requerido)
   - Confirmar solicitud

### **Para RRHH (Dashboard Web)**
- **Vista Principal**: Estadísticas resumidas y tabla de ausencias
- **Filtros**: Por estado, motivo, fecha y sector
- **Certificados**: Acceso directo a documentos adjuntos
- **Prioridades**: Identificación visual de casos urgentes
- **Validaciones**: Gestión de empleados provisionales

## 📋 **Tipos de Ausencia Soportados**

- **Enfermedad Inculpable** *(requiere certificado)*
- **Enfermedad Familiar** *(requiere certificado)*
- **ART** - Accidente de Trabajo
- **Fallecimiento** - Familiar directo
- **Nacimiento** - Hijo/a
- **Matrimonio** - Propio o familiar
- **Paternidad** - Licencia por paternidad
- **Permiso Gremial** - Actividades sindicales

## 🔄 **Sistema de Recordatorios**

- **Horario**: Todos los días a las 22:00
- **Objetivo**: Recordar certificados médicos pendientes
- **Condición**: Solo ausencias registradas el mismo día
- **Anti-spam**: Un recordatorio por solicitud

## 📊 **Documentación Completa**

- **[Documentación Técnica](DOCUMENTACION_TECNICA.md)** - Arquitectura y detalles técnicos
- **[Manual de Usuario RRHH](MANUAL_USUARIO_RRHH.md)** - Guía completa para RRHH
- **[Guía de Funcionamiento](GUIA_FUNCIONAMIENTO.md)** - Explicación detallada del sistema
- **[Presentación del Proyecto](PRESENTACION_PROYECTO.md)** - Resumen para presentaciones

## 🗂️ **Estructura del Proyecto**

```
Repo-Actualizado/
├── src/
│   ├── dialogue/         # Lógica del bot conversacional
│   ├── persistence/      # Base de datos y modelos
│   ├── reminders/        # Sistema de recordatorios
│   ├── telegram/         # Bot de Telegram
│   ├── utils/           # Utilidades y validaciones
│   └── web/             # Dashboard web y API
├── uploads/             # Certificados médicos
├── run_bot.py          # Ejecutor principal del bot
├── dashboard_server.py  # Servidor web
└── docs/               # Documentación adicional
```

## ⚡ **API Endpoints**

```
GET  /api/ausencias     # Lista de ausencias con filtros
GET  /api/stats         # Estadísticas resumidas
GET  /api/certificado/{id} # Descarga de certificado
GET  /health           # Estado del sistema
```

## 🔒 **Seguridad**

- ✅ Validación de entrada en todos los endpoints
- ✅ Sanitización de nombres de archivo
- ✅ Control de acceso por telegram_user_id
- ✅ Logs de auditoría completos
- ✅ Exclusión de secretos del repositorio

## 🚨 **Troubleshooting**

### **Bot no responde**
- Verificar token de Telegram en .env
- Comprobar conexión a internet
- Revisar logs de error

### **Dashboard no carga**
- Verificar puerto disponible (8090)
- Comprobar permisos de archivo
- Revisar logs del servidor

### **Certificados no se ven**
- Validar rutas de archivo en uploads/
- Comprobar permisos de lectura
- Verificar formato de archivo soportado

## 📈 **Contribución**

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 **Licencia**

Este proyecto está desarrollado para uso académico y empresarial interno.

## 🎯 **Autor**

**Sistema desarrollado por**: [Tu Nombre]  
**Fecha**: Agosto 2025  
**Versión**: 1.0.0  

---

**© 2025 - Sistema de Gestión de Ausencias v1.0**