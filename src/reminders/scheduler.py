#!/usr/bin/env python3
"""
Sistema de recordatorios automáticos para certificados pendientes
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..persistence.dao import session_scope
from ..persistence.models import Aviso, Notificacion
from ..config import settings
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self):
        self.bot_instance = None
        self.running = False
    
    def set_bot_instance(self, bot):
        """Configura la instancia del bot de Telegram para enviar mensajes"""
        self.bot_instance = bot
    
    async def start(self):
        """Inicia el scheduler de recordatorios"""
        self.running = True
        logger.info("Sistema de recordatorios iniciado")
        
        while self.running:
            try:
                await self._check_and_send_reminders()
                # Verificar cada 30 minutos
                await asyncio.sleep(30 * 60)
            except Exception as e:
                logger.error(f"Error en scheduler de recordatorios: {e}", exc_info=True)
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    def stop(self):
        """Detiene el scheduler"""
        self.running = False
        logger.info("Sistema de recordatorios detenido")
    
    async def _check_and_send_reminders(self):
        """Verifica y envía recordatorios a las 22:00"""
        now = datetime.now()
        
        # Solo procesar entre las 22:00 y 22:59
        if now.hour != 22:
            return
        
        try:
            with session_scope() as session:
                # Buscar avisos que:
                # 1. Requieren certificado (enfermedad_inculpable o enfermedad_familiar)
                # 2. Tienen estado_certificado pendiente 
                # 3. Fueron creados hoy
                # 4. No se les ha enviado recordatorio
                # 5. Tienen telegram_user_id
                
                today = now.date()
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
                
                logger.info(f"Encontrados {len(avisos_pendientes)} avisos para recordatorio")
                
                for aviso in avisos_pendientes:
                    try:
                        await self._send_reminder(session, aviso)
                        # Marcar como enviado
                        aviso.recordatorio_22h_enviado = True
                        
                        # Crear registro de notificación
                        notificacion = Notificacion(
                            id_aviso=aviso.id_aviso,
                            destino=aviso.telegram_user_id,
                            enviado_en=now,
                            canal="telegram",
                            payload={
                                "tipo": "recordatorio_certificado",
                                "hora_limite": "24:00",
                                "motivo": aviso.motivo
                            }
                        )
                        session.add(notificacion)
                        
                        logger.info(f"Recordatorio enviado para aviso {aviso.id_aviso}")
                        
                    except Exception as e:
                        logger.error(f"Error enviando recordatorio para aviso {aviso.id_aviso}: {e}")
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Error en verificación de recordatorios: {e}", exc_info=True)
    
    async def _send_reminder(self, session, aviso: Aviso):
        """Envía un recordatorio específico via Telegram"""
        if not self.bot_instance:
            logger.warning("Bot instance not configured, cannot send reminder")
            return
        
        # Determinar el nombre del motivo para el mensaje
        motivo_text = {
            'enfermedad_inculpable': 'enfermedad inculpable',
            'enfermedad_familiar': 'enfermedad familiar'
        }.get(aviso.motivo, aviso.motivo)
        
        mensaje = f"""
** RECORDATORIO IMPORTANTE **

Tu solicitud de ausencia por **{motivo_text}** (código {aviso.id_aviso}) está **pendiente del certificado médico**.

** Solo te quedan 2 horas ** para enviarlo (hasta las 24:00).

** ACCIÓN REQUERIDA: **
Envía tu certificado médico ahora mismo para completar tu solicitud.

** IMPORTANTE: ** Si no entregas el certificado dentro del plazo reglamentario, podrías ser sancionado según el reglamento interno.

Para enviar el certificado, responde a este mensaje con la foto o archivo del documento.
"""
        
        try:
            await self.bot_instance.send_message(
                chat_id=aviso.telegram_user_id,
                text=mensaje,
                parse_mode='Markdown'
            )
            logger.info(f"Mensaje de recordatorio enviado a {aviso.telegram_user_id}")
            
        except Exception as e:
            logger.error(f"Error enviando mensaje de Telegram: {e}")
            raise


# Instancia global del scheduler
reminder_scheduler = ReminderScheduler()