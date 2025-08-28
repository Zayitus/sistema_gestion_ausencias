# 📊 Guía de Configuración Power BI - Sistema de Ausencias

## 🎯 **RESUMEN EJECUTIVO**

Guía completa para integrar Power BI con el sistema de ausencias laborales. Incluye 3 métodos de conexión y templates listos para usar.

---

## 🚀 **PREPARACIÓN PREVIA** 

### ✅ **Verificar que el Sistema Esté Corriendo**

```bash
cd D:\proyecto_EZE\experto-ausencias
python dashboard_server.py
```

**URLs de verificación:**
- Dashboard: http://127.0.0.1:8090/dashboard
- API Power BI (JSON): http://127.0.0.1:8090/api/powerbi
- API Power BI (CSV): http://127.0.0.1:8090/api/powerbi?format=csv

### ✅ **Generar CSVs Actualizados**
```bash
python -c "from src.persistence.export_powerbi import export_all_csv, export_powerbi_consolidated; export_all_csv(); export_powerbi_consolidated()"
```

---

## 📊 **MÉTODO 1: IMPORTAR CSVs (MÁS SIMPLE)**

### **Paso 1: Abrir Power BI Desktop**
1. Crear nuevo reporte
2. Ir a **Obtener datos** → **Texto/CSV**

### **Paso 2: Importar Vista Consolidada (Recomendado)**
- Archivo: `D:\proyecto_EZE\experto-ausencias\exports\vista_consolidada_powerbi.csv`
- **Ventaja:** Una sola tabla con todo lo necesario
- **Campos incluidos:**
  - Datos empleado: legajo, nombre, área, puesto
  - Datos ausencia: motivo, fechas, duración, estados
  - **Campos calculados:** días_desde_inicio, prioridad, estado_consolidado
  - **Campos Power BI:** año, mes, semana, es_largo_plazo

### **Paso 3: Crear Visualizaciones**

#### **📈 KPIs Principales (Cards)**
- Total Ausencias: `COUNT(id_aviso)`
- Casos Activos: `CALCULATE(COUNT(id_aviso), estado_consolidado = "Activo")`
- Alta Prioridad: `CALCULATE(COUNT(id_aviso), prioridad = "Alta")`
- Requieren Acción: `CALCULATE(COUNT(id_aviso), requiere_accion = TRUE)`

#### **📊 Gráficos Recomendados**
1. **Donut Chart:** Estado consolidado (Activo, Pendiente, Cerrado)
2. **Bar Chart:** Ausencias por área
3. **Column Chart:** Ausencias por motivo
4. **Timeline:** Tendencia mensual (`created_at`)
5. **Table:** Vista detallada con filtros

---

## 🌐 **MÉTODO 2: WEB CONNECTOR (DATOS EN VIVO)**

### **Paso 1: Configurar Web Connector**
1. **Obtener datos** → **Web**
2. **URL:** `http://127.0.0.1:8090/api/powerbi?format=csv`
3. Configurar **Actualización automática**

### **Paso 2: Configurar Refresh**
- En Power BI Service: Configurar actualización cada hora
- **URL con refresh:** `http://127.0.0.1:8090/api/powerbi?format=csv&refresh=true`

---

## 🔄 **MÉTODO 3: MÚLTIPLES TABLAS (AVANZADO)**

Para análisis más profundo, importar tablas separadas:

### **Archivos CSV a Importar:**
1. `employees.csv` - Datos empleados + antigüedad calculada
2. `avisos.csv` - Ausencias + métricas calculadas  
3. `certificados.csv` - Estados certificados
4. `notificaciones.csv` - Historial comunicaciones
5. `auditoria.csv` - Log de cambios

### **Relaciones a Configurar:**
```
employees.legajo → avisos.legajo (1:many)
avisos.id_aviso → certificados.id_aviso (1:many) 
avisos.id_aviso → notificaciones.id_aviso (1:many)
```

---

## 📊 **VISUALIZACIONES RECOMENDADAS**

### **🎯 Dashboard Ejecutivo**
- **Página 1:** KPIs principales y tendencias
- **Cards:** Total, Activos, Pendientes, Alta Prioridad
- **Line Chart:** Evolución temporal
- **Donut:** Distribución por estados

### **🔍 Dashboard Operativo**  
- **Página 2:** Vista detallada para RRHH
- **Table:** Lista completa con filtros
- **Slicers:** Área, Motivo, Estado, Prioridad
- **Bar Charts:** Análisis por categorías

### **📈 Dashboard Analítico**
- **Página 3:** Análisis avanzado
- **Scatter Plot:** Duración vs Días transcurridos
- **Heatmap:** Patrones por mes/área
- **Funnel:** Estados del proceso

---

## 🎨 **MEJORES PRÁCTICAS DE DISEÑO**

### **Colores Recomendados:**
- **🟢 Verde:** Estados completados/OK
- **🟡 Amarillo:** En proceso/Media prioridad  
- **🔴 Rojo:** Problemas/Alta prioridad
- **🔵 Azul:** Información/Neutral

### **Filtros Importantes:**
- **Slicers principales:** Área, Estado, Prioridad
- **Filtro de fecha:** Últimos 30/90 días
- **Filtro acción:** Solo "Requiere acción"

### **KPIs Críticos:**
1. **% Completados:** `Cerrados / Total * 100`
2. **Tiempo Promedio:** `AVERAGE(dias_desde_inicio)`
3. **Casos Críticos:** `COUNT(prioridad = "Alta")`
4. **Pendientes RRHH:** `COUNT(requiere_accion = TRUE)`

---

## ⚡ **MEDIDAS DAX ÚTILES**

```dax
// Total Ausencias
Total Ausencias = COUNT('vista_consolidada_powerbi'[id_aviso])

// Casos Activos
Casos Activos = 
CALCULATE(
    COUNT('vista_consolidada_powerbi'[id_aviso]),
    'vista_consolidada_powerbi'[estado_consolidado] = "Activo"
)

// % Completados
% Completados = 
DIVIDE(
    CALCULATE(COUNT('vista_consolidada_powerbi'[id_aviso]), 
             'vista_consolidada_powerbi'[estado_consolidado] = "Cerrado"),
    COUNT('vista_consolidada_powerbi'[id_aviso]),
    0
) * 100

// Tiempo Promedio Resolución
Días Promedio = AVERAGE('vista_consolidada_powerbi'[dias_desde_inicio])

// Casos Urgentes (>30 días)
Casos Largos = 
CALCULATE(
    COUNT('vista_consolidada_powerbi'[id_aviso]),
    'vista_consolidada_powerbi'[es_largo_plazo] = TRUE
)
```

---

## 🔧 **TROUBLESHOOTING**

### **❌ Error: No se puede conectar**
- ✅ Verificar que `dashboard_server.py` esté corriendo
- ✅ Probar URL en navegador: http://127.0.0.1:8090/api/powerbi

### **❌ Error: Datos vacíos**  
- ✅ Regenerar CSVs: `python -c "from src.persistence.export_powerbi import export_powerbi_consolidated; export_powerbi_consolidated()"`
- ✅ Verificar base de datos con datos: `curl http://127.0.0.1:8090/api/stats`

### **❌ Error: Formato incorrecto**
- ✅ Usar URL CSV: `http://127.0.0.1:8090/api/powerbi?format=csv`
- ✅ Verificar encoding UTF-8 en Power BI

---

## 📋 **CHECKLIST FINAL**

- [ ] ✅ Dashboard server corriendo (puerto 8090)
- [ ] ✅ CSVs generados en /exports
- [ ] ✅ API Power BI responde correctamente
- [ ] ✅ Power BI conectado (CSV o Web)
- [ ] ✅ Visualizaciones creadas
- [ ] ✅ KPIs configurados
- [ ] ✅ Filtros funcionando
- [ ] ✅ Actualización automática configurada

---

## 🎯 **DEMO SCRIPT**

### **Para Presentación:**
1. **Abrir dashboard web:** http://127.0.0.1:8090/dashboard
2. **Mostrar datos en tiempo real**
3. **Abrir Power BI** con vista consolidada
4. **Demostrar KPIs y filtros**
5. **Mostrar análisis temporal**
6. **Explicar refresh automático**

### **URLs Útiles para Demo:**
- Dashboard: http://127.0.0.1:8090/dashboard
- API JSON: http://127.0.0.1:8090/api/powerbi
- API CSV: http://127.0.0.1:8090/api/powerbi?format=csv
- Stats: http://127.0.0.1:8090/api/stats

---

## 🚀 **RESULTADO ESPERADO**

**✅ Power BI Dashboard Completo con:**
- KPIs ejecutivos actualizados en tiempo real
- Análisis detallado por área/motivo/estado  
- Visualizaciones interactivas y filtros
- Datos consolidados listos para presentación
- Conexión directa al sistema de ausencias

**🎯 LISTO PARA ENTREGA VIERNES**