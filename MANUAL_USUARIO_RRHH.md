# Manual de Usuario RRHH - Sistema de Gestión de Ausencias

## 🎯 **Introducción**

Este manual está dirigido al personal de Recursos Humanos para el uso del **Dashboard Web** del Sistema de Gestión de Ausencias. El sistema permite supervisar, validar y gestionar todas las solicitudes de ausencia de los empleados de manera centralizada y eficiente.

---

## 🌐 **Acceso al Sistema**

### **URL de Acceso**
```
http://127.0.0.1:8090
```

### **Inicio del Sistema**
1. Abrir terminal/línea de comandos
2. Navegar al directorio del sistema
3. Ejecutar: `python dashboard_server.py`
4. Acceder desde navegador web

### **Navegadores Compatibles**
- Chrome 90+
- Firefox 88+
- Edge 90+
- Safari 14+

---

## 📊 **Pantalla Principal - Dashboard**

### **Estadísticas Resumidas**

Al ingresar verás 6 tarjetas con métricas principales:

#### **Total Ausencias**
- Número total de solicitudes registradas en el sistema
- Incluye todas las solicitudes históricas

#### **Activas**
- Ausencias que están en proceso
- Estados: incompleto, pendiente, en_revision

#### **Requieren Validación**
- Casos donde RRHH debe intervenir
- Empleados no encontrados en sistema
- Legajos provisionales sin validar

#### **Certificados Pendientes**
- Ausencias que requieren certificado médico
- Estados: pendiente, en_revision

#### **Completadas**
- Ausencias totalmente procesadas
- Estado: completo

#### **Alta Prioridad**
- Casos urgentes que requieren atención inmediata
- Combinación de validación + certificado pendiente

### **Auto-actualización**
- Los datos se actualizan automáticamente cada 30 segundos
- Botón "🔄 Actualizar" para refresh manual

---

## 🔍 **Sistema de Filtros**

### **Filtros Disponibles**

#### **1. Estado**
- **Todos los estados**: Muestra todas las solicitudes
- **Completo**: Ausencias finalizadas correctamente
- **Incompleto**: Faltan documentos o validaciones
- **Requiere Validación**: Necesita intervención RRHH
- **Rechazado**: Solicitudes rechazadas

#### **2. Motivo**
- **Todos los motivos**: Sin filtro
- **Enfermedad Inculpable**: Certificado médico requerido
- **Enfermedad Familiar**: Certificado médico requerido
- **ART**: Accidente de trabajo
- **Fallecimiento**: Familiar directo
- **Nacimiento**: Hijo/a
- **Matrimonio**: Propio o familiar
- **Paternidad**: Licencia por paternidad
- **Permiso Gremial**: Actividades sindicales

#### **3. Fecha**
- **Todos**: Sin filtro temporal
- **Hoy**: Solicitudes de hoy únicamente
- **Últimos 3 días**: 3 días hacia atrás desde hoy
- **Última semana**: 7 días hacia atrás
- **Último mes**: 30 días hacia atrás

#### **4. Sector**
- Filtros por área de trabajo:
  - Producción, Logística, Administración
  - Ventas, Sistemas, Recursos Humanos
  - Sin asignar, No disponible

### **Uso de Filtros**
1. Seleccionar criterios en cada dropdown
2. Los filtros se aplican automáticamente al cambiar
3. Se pueden combinar múltiples filtros
4. Para limpiar: seleccionar "Todos" en cada filtro

---

## 📋 **Tabla de Ausencias**

### **Columnas de Información**

#### **ID Aviso**
- Código único: `A-YYYYMMDD-NNNN`
- Formato: A-AñoMesDía-Número secuencial
- Ejemplo: `A-20250829-0001`

#### **Empleado**
- Nombre completo del empleado
- Número de legajo debajo

#### **Área**
- Departamento de trabajo
- "N/A" si no está asignado

#### **Motivo**
- Tipo de ausencia solicitada
- Formato legible

#### **Fecha Inicio**
- Cuándo comienza la ausencia
- Formato: DD/MM/YYYY

#### **Duración**
- Cantidad de días de ausencia
- Formato: "X días"

#### **Estado**
- Estado actual de la solicitud
- Código de colores:
  - 🟢 Verde: Completo
  - 🟡 Amarillo: Pendiente
  - 🔴 Rojo: Rechazado

#### **Certificado**
- Estado del certificado médico
- Mismos colores que Estado

#### **Ver Certificado**
- **📄 Ver**: Certificado disponible (click para abrir)
- **Sin certificado**: Requerido pero no recibido
- **No requerido**: No aplica para este motivo

#### **Validación RRHH**
- **Requerida** (rojo): Necesita validación
- **OK** (verde): Ya validado

#### **Prioridad**
- **ALTA** (rojo): Atención urgente
- **MEDIA** (amarillo): Seguimiento normal
- **BAJA** (verde): Completo

#### **Acción Requerida**
- Texto descriptivo de qué hacer:
  - "Validar empleado"
  - "Revisar certificado" 
  - "Seguimiento"
  - "Sin acción"

---

## 📄 **Gestión de Certificados**

### **Visualización de Certificados**

#### **Tipos de Archivos Soportados**
- **Imágenes**: JPEG, JPG, PNG → Se abren en navegador
- **PDFs**: Se abren en navegador para visualización
- **Word**: DOCX, DOC → Se descargan automáticamente

#### **Cómo Ver un Certificado**
1. Localizar la columna "Ver Certificado"
2. Click en botón "📄 Ver" (azul)
3. El archivo se abre en nueva pestaña/se descarga

#### **Estados de Certificados**
- **Botón azul "📄 Ver"**: Certificado disponible
- **Botón gris "Sin certificado"**: Faltante
- **Texto gris "No requerido"**: No aplica

### **Problemas Comunes**
- **Error 404**: El archivo no existe físicamente
- **No se abre**: Verificar bloqueador de popups
- **Descarga lenta**: Depende del tamaño del archivo

---

## ⚡ **Casos Especiales - Validación RRHH**

### **Legajos Provisionales**

#### **Identificación**
- Columna "Validación RRHH" muestra "Requerida"
- Prioridad aparece como "ALTA"
- Observaciones incluyen "PROVISIONAL"

#### **Información Disponible**
- Nombre proporcionado por el empleado
- Legajo declarado (sin validar)
- Datos de contacto (Telegram ID)

#### **Proceso de Validación**
1. **Verificar identidad** con nombre y legajo declarado
2. **Consultar sistema de empleados** para confirmar datos
3. **Actualizar base de datos** con información correcta
4. **Notificar al empleado** si es necesario

### **Certificados Médicos**

#### **Revisión Requerida**
- Acción: "Revisar certificado"
- Estado: "en_revision" o "pendiente"
- Prioridad: Media o Alta

#### **Proceso de Revisión**
1. **Abrir certificado** usando botón "📄 Ver"
2. **Verificar autenticidad**:
   - Membrete médico oficial
   - Firma y sello del profesional
   - Fechas coherentes con solicitud
   - Diagnóstico apropiado
3. **Determinar validez**
4. **Actualizar estado** en sistema

---

## 🕒 **Sistema de Recordatorios Automáticos**

### **Funcionamiento**
- **Hora**: Todos los días a las 22:00
- **Destinatarios**: Empleados con certificados pendientes
- **Condición**: Solo ausencias registradas el mismo día

### **Contenido del Recordatorio**
```
** RECORDATORIO IMPORTANTE **

Tu solicitud de ausencia por **enfermedad inculpable** 
(código A-20250829-0012) está **pendiente del certificado médico**.

** Solo te quedan 2 horas ** para enviarlo (hasta las 24:00).

[...resto del mensaje...]
```

### **Seguimiento**
- Los recordatorios se registran en tabla "notificaciones"
- Flag anti-spam previene múltiples envíos
- Visible en logs del sistema

---

## 🔧 **Modificaciones en Base de Datos**

### ⚠️ **IMPORTANTE: Backup Antes de Modificar**
```bash
# Crear respaldo
copy sistema_ausencias.db sistema_ausencias_backup.db
```

### **Herramientas Recomendadas**

#### **1. DB Browser for SQLite** (Recomendado para RRHH)
- **Descarga**: https://sqlitebrowser.org/
- **Ventajas**: Interfaz gráfica, fácil de usar
- **Instalación**: Descarga e instala normalmente

#### **2. Acceso por Línea de Comandos**
```bash
sqlite3 sistema_ausencias.db
```

### **Operaciones Comunes**

#### **Ver Todas las Ausencias**
```sql
SELECT id_aviso, legajo, motivo, fecha_inicio, estado_aviso 
FROM avisos 
ORDER BY created_at DESC 
LIMIT 20;
```

#### **Buscar por Legajo**
```sql
SELECT * FROM avisos WHERE legajo = '1234';
```

#### **Actualizar Estado de Aviso**
```sql
UPDATE avisos 
SET estado_aviso = 'completo' 
WHERE id_aviso = 'A-20250829-0001';
```

#### **Validar Legajo Provisional**
```sql
-- 1. Verificar datos actuales
SELECT * FROM avisos WHERE legajo = '9999' AND observaciones LIKE '%PROVISIONAL%';

-- 2. Actualizar información (ejemplo)
UPDATE avisos 
SET observaciones = 'Legajo verificado', 
    legajo = '1234' 
WHERE id_aviso = 'A-20250829-0001';
```

#### **Ver Certificados Pendientes**
```sql
SELECT a.id_aviso, a.legajo, e.nombre, a.motivo, a.estado_certificado
FROM avisos a
LEFT JOIN employees e ON a.legajo = e.legajo
WHERE a.estado_certificado = 'pendiente'
ORDER BY a.created_at;
```

#### **Estadísticas por Área**
```sql
SELECT e.area, COUNT(*) as total_ausencias
FROM avisos a
JOIN employees e ON a.legajo = e.legajo
GROUP BY e.area
ORDER BY total_ausencias DESC;
```

### **Modificaciones Seguras**

#### ✅ **Operaciones Permitidas**
- Actualizar `estado_aviso` y `estado_certificado`
- Modificar `observaciones`
- Corregir datos de empleados en tabla `employees`
- Actualizar campos de validación

#### ❌ **Operaciones NO Recomendadas**
- Eliminar registros de `avisos` (histórico)
- Modificar `id_aviso` (clave primaria)
- Cambiar `created_at` (auditoría)
- Alterar estructura de tablas

### **Ejemplo Completo: Validar Empleado**

```sql
-- 1. Identificar caso
SELECT id_aviso, legajo, observaciones 
FROM avisos 
WHERE observaciones LIKE '%PROVISIONAL%';

-- 2. Verificar empleado existe
SELECT * FROM employees WHERE legajo = '1234';

-- 3. Si no existe, agregar empleado
INSERT INTO employees (legajo, nombre, area, activo) 
VALUES ('1234', 'Juan Pérez', 'Producción', 1);

-- 4. Actualizar aviso
UPDATE avisos 
SET observaciones = 'Legajo verificado'
WHERE id_aviso = 'A-20250829-0001';

-- 5. Verificar cambio
SELECT * FROM avisos WHERE id_aviso = 'A-20250829-0001';
```

---

## 🚨 **Procedimientos de Emergencia**

### **Sistema No Responde**
1. **Verificar conexión**: Ping a servidor
2. **Reiniciar dashboard**: `python dashboard_server.py`
3. **Verificar puerto**: Cambiar a 8091 si 8090 ocupado
4. **Revisar logs**: Buscar errores en salida de consola

### **Datos Incorrectos**
1. **Backup inmediato**: Copiar base de datos
2. **Identificar origen**: ¿Error manual o del sistema?
3. **Corregir con SQL**: Usar comandos seguros
4. **Verificar en dashboard**: Confirmar corrección

### **Certificado No Disponible**
1. **Verificar ruta**: Carpeta `uploads/`
2. **Confirmar permisos**: Lectura de archivos
3. **Buscar manualmente**: Por código de aviso
4. **Contactar empleado**: Si archivo perdido

---

## 📊 **Reportes y Análisis**

### **Datos Disponibles para Exportar**

#### **API Endpoints**
```
GET /api/ausencias?limit=1000    # Todas las ausencias
GET /api/stats                   # Estadísticas resumidas
```

#### **Uso con Excel/Google Sheets**
1. **Acceder a URL**: http://127.0.0.1:8090/api/ausencias
2. **Copiar JSON**: Datos en formato estructurado
3. **Convertir a tabla**: Power Query (Excel) o similar
4. **Generar reportes**: Gráficos y análisis

### **KPIs Sugeridos**
- **Tasa de cumplimiento**: % ausencias completas vs incompletas
- **Tiempo de resolución**: Días promedio para completar
- **Certificados por área**: Distribución de ausencias médicas
- **Legajos provisionales**: % que requieren validación
- **Efectividad recordatorios**: % respuesta post-recordatorio

---

## 💡 **Tips y Mejores Prácticas**

### **Gestión Diaria**
1. **Revisar alta prioridad** al inicio del día
2. **Filtrar por "Hoy"** para casos urgentes  
3. **Validar legajos provisionales** prioritariamente
4. **Revisar certificados** en orden de llegada

### **Gestión Semanal**
1. **Análisis de tendencias** por área/motivo
2. **Seguimiento de pendientes** antiguos
3. **Backup de base de datos**
4. **Limpieza de archivos** temporales

### **Gestión Mensual**
1. **Reportes estadísticos** completos
2. **Análisis de cumplimiento** de plazos
3. **Evaluación del sistema** de recordatorios
4. **Planificación de mejoras**

---

## ❓ **Preguntas Frecuentes**

### **¿Cómo sé si un empleado recibió el recordatorio?**
- Revisar tabla "notificaciones" en BD
- Buscar por `id_aviso` específico
- Campo `enviado_en` muestra timestamp

### **¿Puedo cambiar el horario de recordatorios?**
- Actualmente fijo a las 22:00
- Modificación requiere cambio en código
- Contactar soporte técnico

### **¿Qué hago si el sistema está lento?**
- Verificar cantidad de registros en BD
- Usar filtros para reducir datos mostrados
- Considerar limpiar registros antiguos

### **¿Cómo agrego un nuevo empleado?**
```sql
INSERT INTO employees (legajo, nombre, area, puesto, activo) 
VALUES ('5678', 'María García', 'Ventas', 'Representante', 1);
```

### **¿Puedo eliminar una ausencia?**
- No recomendado (auditoría)
- Alternativa: marcar como "rechazado"
- Agregar observación explicativa

---

## 📞 **Soporte y Contacto**

### **Documentación Adicional**
- **Documentación Técnica**: `DOCUMENTACION_TECNICA.md`
- **Guía de Funcionamiento**: `GUIA_FUNCIONAMIENTO.md`
- **Presentación del Proyecto**: `PRESENTACION_PROYECTO.md`

### **Archivos de Logs**
- **Bot**: Salida de consola de `run_bot.py`
- **Dashboard**: Salida de consola de `dashboard_server.py`
- **Sistema**: Logs en directorio raíz

### **Backup de Emergencia**
```bash
# Base de datos
copy sistema_ausencias.db backup_YYYYMMDD.db

# Certificados
xcopy uploads backup_uploads\ /E /I
```

---

**© 2025 - Sistema de Gestión de Ausencias v1.0**
**Manual actualizado**: Agosto 2025