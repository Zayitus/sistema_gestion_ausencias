# Sistema de Recordatorios Automáticos 🔔

## Funcionalidad Implementada ✅

El sistema ahora envía **recordatorios automáticos** a empleados que no han adjuntado certificados médicos requeridos.

### ¿Cuándo se envían los recordatorios?

**⏰ Horario**: Automáticamente a las **22:00 horas**

**📋 Condiciones**:
- Ausencia registrada **HOY** (mismo día)
- Motivo: `enfermedad_inculpable` o `enfermedad_familiar` 
- Estado certificado: `pendiente` (no adjuntado)
- Usuario registró la ausencia via **Telegram bot**
- **NO** se le ha enviado recordatorio previamente

### ⚠️ Mensaje del Recordatorio

```
⚠️ **RECORDATORIO IMPORTANTE**

Tu solicitud de ausencia por **enfermedad inculpable** (código A-20250829-0012) está **pendiente del certificado médico**.

🕙 **Solo te quedan 2 horas** para enviarlo (hasta las 24:00).

⚡ **ACCIÓN REQUERIDA:**
Envía tu certificado médico ahora mismo para completar tu solicitud.

⚠️ **IMPORTANTE:** Si no entregas el certificado dentro del plazo reglamentario, podrías ser sancionado según el reglamento interno.

Para enviar el certificado, responde a este mensaje con la foto o archivo del documento.
```

## Arquitectura Técnica 🔧

### Nuevos Componentes

1. **Sistema Scheduler** (`src/reminders/scheduler.py`)
   - Ejecuta cada 30 minutos
   - Solo actúa entre las 22:00-22:59
   - Envía mensajes via Telegram Bot API

2. **Campos BD nuevos** (tabla `avisos`):
   - `recordatorio_22h_enviado`: Boolean (evita spam)
   - `telegram_user_id`: String (ID del usuario de Telegram)

3. **Registro de notificaciones** (tabla `notificaciones`):
   - Tracking de todos los recordatorios enviados
   - Payload con información adicional

### Integración con Bot Existente

- **Sin cambios** en la experiencia de usuario
- **Automático**: Se activa al registrar ausencias
- **Seguro**: Solo funciona con registros válidos

## Testing 🧪

### Para Probar el Sistema:

1. **Crear ausencia via bot** con certificado requerido:
   ```
   /start
   [ingresar legajo]
   [seleccionar "enfermedad_inculpable"]
   [elegir fecha de hoy]
   [elegir duración]
   [seleccionar "enviar más tarde"]
   [confirmar]
   ```

2. **Verificar en BD**:
   ```bash
   python test_reminders.py
   ```

3. **Simular envío** (testing manual):
   ```bash
   python test_reminder_manual.py
   ```

### Logs del Sistema

El sistema loggea:
- ✅ Avisos encontrados para recordatorio
- ✅ Mensajes enviados exitosamente  
- ❌ Errores en envío
- 📊 Estadísticas de procesamiento

## Estado del Deployment 🚀

### ✅ Completado:
- [x] Modelo de datos actualizado
- [x] Migración de BD ejecutada
- [x] Sistema de scheduler implementado
- [x] Integración con bot existente
- [x] Manejo de errores y logging
- [x] Testing y validación

### 🔄 Activación:
Para activar el sistema:

1. **Iniciar bot con recordatorios**:
   ```bash
   python run_bot.py
   ```

2. **Verificar logs**:
   - "Sistema de recordatorios iniciado" ✅
   - Verificaciones cada 30 minutos a las 22:00

## Configuración 🔧

### Variables de Entorno Requeridas:
- `TELEGRAM_TOKEN`: Token del bot (ya configurado)

### Sin Configuración Adicional:
- **Horario fijo**: 22:00 (hardcoded)
- **Intervalo**: 30 minutos (hardcoded) 
- **Plazo**: 24 horas desde registro (hardcoded)

## Seguridad 🔒

### Medidas Implementadas:
- ✅ **Anti-spam**: Un solo recordatorio por aviso
- ✅ **Validación**: Solo usuarios que usaron el bot
- ✅ **Graceful errors**: Fallos no afectan al bot principal
- ✅ **Logging completo**: Auditoría de todas las acciones

### Limitaciones:
- ⚠️ Solo funciona si el bot está corriendo
- ⚠️ Requiere telegram_user_id (nuevas ausencias únicamente)
- ⚠️ Horario fijo (no configurable por empleado)

---

**Sistema implementado y listo para producción** ✅