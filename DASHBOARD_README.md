# Dashboard RRHH - Sistema de Ausencias

## 🚀 Implementación Completada

Se implementó un **dashboard web completo para RRHH** que permite visualizar y gestionar todas las ausencias registradas en el sistema.

## 📋 Funcionalidades Implementadas

### ✅ Panel Principal
- **Vista unificada** de todas las ausencias con información completa
- **Estadísticas resumidas** en tiempo real:
  - Total de ausencias activas
  - Casos que requieren validación de RRHH
  - Certificados médicos pendientes
  - Ausencias completadas
  - Casos de prioridad alta

### ✅ Información Detallada por Ausencia
- **ID de aviso** único
- **Datos del empleado**: Legajo, nombre, área, puesto
- **Detalles de la ausencia**: Motivo, fecha inicio, duración estimada
- **Estado del certificado**: Presentado, validado, pendiente, en revisión
- **Validación RRHH**: Indica si requiere intervención
- **Prioridad**: Alta, media, baja (calculada automáticamente)
- **Acción requerida**: Qué debe hacer RRHH

### ✅ Filtros y Controles
- **Filtro por estado**: Completo, incompleto, requiere validación, rechazado
- **Filtro por motivo**: Todos los tipos de ausencias soportados
- **Actualización automática** cada 30 segundos
- **Botón de refresh manual**

### ✅ Interfaz Moderna
- **Diseño responsivo** (funciona en móvil/tablet)
- **Estados visuales claros** con colores y badges
- **Indicadores de prioridad** 
- **Loading states** y manejo de errores

## 🏃‍♂️ Cómo Ejecutar

### 1. Instalar dependencias (si no están)
```bash
cd D:\proyecto_EZE\experto-ausencias
pip install -r requirements.txt
```

### 2. Generar datos de prueba (si no existen)
```bash
python -m src.persistence.seed_synthetic
```

### 3. Iniciar el dashboard
```bash
python dashboard_server.py
```

### 4. Acceder al dashboard
- **Dashboard principal**: http://127.0.0.1:8090/dashboard
- **API de datos**: http://127.0.0.1:8090/api/ausencias
- **Health check**: http://127.0.0.1:8090/health

## 📊 APIs Disponibles

### GET /api/ausencias
Devuelve todas las ausencias con filtros opcionales:
- `?estado=completo|incompleto|pendiente_validacion|rechazado`
- `?motivo=enfermedad_inculpable|art|...`
- `?limit=50` (por defecto)

### GET /api/stats
Estadísticas resumidas del sistema.

### GET /health
Verificación del estado del servidor y BD.

## 🎯 Casos de Uso Principales para RRHH

### 1. **Revisión Diaria**
- Abrir dashboard para ver ausencias nuevas
- Identificar casos que requieren validación (badges rojos)
- Priorizar por columna "Prioridad" y "Acción Requerida"

### 2. **Validación de Empleados**
- Filtrar por "Requiere Validación" 
- Revisar legajos no encontrados en el sistema
- Verificar datos de empleados nuevos

### 3. **Seguimiento de Certificados**
- Ver columna "Certificado" para estado actual
- Identificar documentos "En revisión" 
- Hacer seguimiento de documentos pendientes

### 4. **Gestión por Motivo**
- Filtrar por tipo específico (ej: "ART", "Enfermedad")
- Ver patrones por área o empleado
- Identificar casos recurrentes

### 5. **Reportes Ejecutivos**
- Usar estadísticas del panel superior
- Monitorear tendencias y volúmenes
- Identificar carga de trabajo de RRHH

## 🔧 Arquitectura Técnica

### Backend
- **aiohttp**: Servidor web asíncrono 
- **SQLAlchemy**: ORM para base de datos
- **SQLite**: Base de datos (configurable)

### Frontend  
- **HTML5 + CSS3 + JavaScript vanilla**
- **Responsive design** con Grid/Flexbox
- **Fetch API** para consumo de datos
- **Auto-refresh** y estado de loading

### Integración
- **API REST** con JSON
- **CORS habilitado** para desarrollo
- **Error handling** robusto
- **Logging** estructurado

## 📈 Datos de Ejemplo

El sistema incluye **147 ausencias sintéticas** con datos realistas:
- 200 empleados en 5 áreas diferentes
- Distribución realista de motivos (50% enfermedad, etc.)
- Estados variados (completo, pendiente, en revisión)
- Certificados con diferentes estados de validación

## 🚀 Para Producción

### Mejoras Recomendadas:
1. **Autenticación**: Login/JWT para acceso seguro
2. **Paginación**: Para grandes volúmenes de datos  
3. **Export**: CSV/Excel de reportes
4. **Notificaciones**: Email/SMS automáticas
5. **Audit**: Log de acciones de RRHH
6. **Métricas**: Dashboard de KPIs avanzados

### Configuración:
- Cambiar `HOST/PORT` en `dashboard_server.py`
- Configurar `DATABASE_URL` en `.env` para PostgreSQL
- Ajustar `LOG_LEVEL` para producción

## ✨ Estado del Proyecto

**✅ COMPLETO PARA ENTREGA** - Viernes listo

El dashboard está **100% funcional** e integrado con el sistema existente. Proporciona todas las funcionalidades solicitadas para RRHH y más.