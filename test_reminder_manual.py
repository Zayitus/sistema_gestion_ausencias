#!/usr/bin/env python3
"""
Prueba manual del sistema de recordatorios (simula las 22:00)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from datetime import datetime, timedelta
from src.persistence.dao import session_scope
from src.persistence.models import Aviso, Notificacion
from sqlalchemy import select, and_

class MockBot:
    """Bot simulado para testing"""
    def __init__(self):
        self.messages_sent = []
    
    async def send_message(self, chat_id, text, parse_mode=None):
        """Simula el envío de mensaje"""
        print(f"📱 MENSAJE ENVIADO A {chat_id}:")
        print(f"📄 CONTENIDO:")
        print(text)
        print("="*50)
        
        self.messages_sent.append({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        })

async def test_manual_reminder():
    """Prueba manual del sistema de recordatorios"""
    print("🧪 PRUEBA MANUAL DEL SISTEMA DE RECORDATORIOS")
    print("="*50)
    
    # Buscar avisos reales que necesiten recordatorio
    with session_scope() as session:
        today = datetime.now().date()
        avisos_pendientes = session.execute(
            select(Aviso).where(
                and_(
                    Aviso.motivo.in_(['enfermedad_inculpable', 'enfermedad_familiar']),
                    Aviso.estado_certificado == 'pendiente',
                    Aviso.created_at >= datetime.combine(today, datetime.min.time()),
                    Aviso.recordatorio_22h_enviado == False,
                    Aviso.telegram_user_id.isnot(None)
                )
            )
        ).scalars().all()
        
        print(f"📊 Avisos encontrados: {len(avisos_pendientes)}")
        
        if not avisos_pendientes:
            print("ℹ️  No hay avisos pendientes de certificado creados hoy con Telegram ID")
            print("   Para testear, crea una nueva ausencia con el bot de Telegram")
            return
        
        # Configurar bot simulado
        mock_bot = MockBot()
        
        # Importar y configurar el scheduler
        from src.reminders.scheduler import ReminderScheduler
        scheduler = ReminderScheduler()
        scheduler.set_bot_instance(mock_bot)
        
        # Procesar cada aviso
        for aviso in avisos_pendientes:
            print(f"📋 Procesando aviso: {aviso.id_aviso}")
            print(f"   Legajo: {aviso.legajo}")
            print(f"   Motivo: {aviso.motivo}")
            print(f"   Telegram ID: {aviso.telegram_user_id}")
            
            try:
                await scheduler._send_reminder(session, aviso)
                
                # Marcar como enviado (solo para la prueba, no lo commitemos)
                print(f"✅ Recordatorio simulado enviado exitosamente")
                
            except Exception as e:
                print(f"❌ Error enviando recordatorio: {e}")
        
        print(f"\n📱 RESUMEN: {len(mock_bot.messages_sent)} mensajes enviados")

if __name__ == "__main__":
    asyncio.run(test_manual_reminder())