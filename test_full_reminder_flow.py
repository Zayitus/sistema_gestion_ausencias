#!/usr/bin/env python3
"""
Prueba completa del flujo de recordatorios
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from datetime import datetime, timedelta
from src.persistence.dao import session_scope, crear_aviso_simple
from src.persistence.models import Aviso, Notificacion
from sqlalchemy import select, and_

class MockTelegramBot:
    """Bot simulado para testing"""
    def __init__(self):
        self.messages_sent = []
    
    async def send_message(self, chat_id, text, parse_mode=None):
        print(f"MENSAJE TELEGRAM ENVIADO A: {chat_id}")
        print("CONTENIDO:")
        print("-" * 50)
        print(text)
        print("-" * 50)
        
        self.messages_sent.append({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        })
        return True

async def test_complete_flow():
    """Prueba el flujo completo de recordatorios"""
    print("=== PRUEBA COMPLETA DEL SISTEMA DE RECORDATORIOS ===")
    
    # 1. Crear una ausencia que requiere certificado (simulando el bot)
    print("\n1. Creando ausencia de prueba...")
    
    aviso_data = {
        "legajo": "9999",
        "motivo": "enfermedad_inculpable", 
        "fecha_inicio": datetime.now().date().isoformat(),
        "duracion_dias": 2,
        "requiere_certificado": True,
        "certificado_path": None,  # Sin certificado = pendiente
        "legajo_provisional": False,
        "nombre_provisional": "",
        "telegram_user_id": "987654321"  # ID de prueba
    }
    
    try:
        result = crear_aviso_simple(aviso_data)
        if result.get('success'):
            id_aviso = result['id_aviso']
            print(f"   Ausencia creada: {id_aviso}")
            print(f"   Estado: {result.get('estado_certificado', 'N/A')}")
        else:
            print(f"   ERROR: {result}")
            return
        
        # 2. Verificar que la ausencia se creó correctamente
        print("\n2. Verificando ausencia en BD...")
        
        with session_scope() as session:
            aviso = session.execute(
                select(Aviso).where(Aviso.id_aviso == id_aviso)
            ).scalars().first()
            
            if not aviso:
                print("   ERROR: Ausencia no encontrada")
                return
            
            print(f"   ID: {aviso.id_aviso}")
            print(f"   Legajo: {aviso.legajo}")
            print(f"   Motivo: {aviso.motivo}")
            print(f"   Estado certificado: {aviso.estado_certificado}")
            print(f"   Telegram ID: {aviso.telegram_user_id}")
            print(f"   Recordatorio enviado: {aviso.recordatorio_22h_enviado}")
            print(f"   Fecha creación: {aviso.created_at}")
        
        # 3. Simular el sistema de recordatorios
        print("\n3. Simulando sistema de recordatorios...")
        
        mock_bot = MockTelegramBot()
        
        # Importar el scheduler
        from src.reminders.scheduler import ReminderScheduler
        scheduler = ReminderScheduler()
        scheduler.set_bot_instance(mock_bot)
        
        # Buscar avisos que requieran recordatorio (como lo haría el scheduler)
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
            
            print(f"   Avisos encontrados para recordatorio: {len(avisos_pendientes)}")
            
            # Procesar nuestro aviso de prueba
            test_aviso = None
            for aviso in avisos_pendientes:
                if aviso.id_aviso == id_aviso:
                    test_aviso = aviso
                    break
            
            if not test_aviso:
                print("   ERROR: Aviso de prueba no encontrado en lista de pendientes")
                return
            
            # 4. Enviar recordatorio
            print("\n4. Enviando recordatorio...")
            
            try:
                await scheduler._send_reminder(session, test_aviso)
                print("   Recordatorio enviado exitosamente!")
                
                # Simular que se marca como enviado
                test_aviso.recordatorio_22h_enviado = True
                
                # Crear notificación
                notificacion = Notificacion(
                    id_aviso=test_aviso.id_aviso,
                    destino=test_aviso.telegram_user_id,
                    enviado_en=datetime.now(),
                    canal="telegram",
                    payload={
                        "tipo": "recordatorio_certificado",
                        "hora_limite": "24:00",
                        "motivo": test_aviso.motivo
                    }
                )
                session.add(notificacion)
                session.commit()
                
                print("   Notificación registrada en BD")
                
            except Exception as e:
                print(f"   ERROR enviando recordatorio: {e}")
                import traceback
                traceback.print_exc()
        
        # 5. Verificar resultados
        print("\n5. Verificando resultados finales...")
        
        with session_scope() as session:
            # Verificar aviso actualizado
            aviso_final = session.execute(
                select(Aviso).where(Aviso.id_aviso == id_aviso)
            ).scalars().first()
            
            print(f"   Recordatorio marcado como enviado: {aviso_final.recordatorio_22h_enviado}")
            
            # Verificar notificación creada
            notif = session.execute(
                select(Notificacion).where(Notificacion.id_aviso == id_aviso)
            ).scalars().first()
            
            if notif:
                print(f"   Notificación creada: {notif.canal} -> {notif.destino}")
                print(f"   Enviada en: {notif.enviado_en}")
            
            print(f"\n   Mensajes enviados por el bot: {len(mock_bot.messages_sent)}")
        
        # 6. Cleanup
        print("\n6. Limpieza...")
        with session_scope() as session:
            # Eliminar notificación
            notif = session.execute(
                select(Notificacion).where(Notificacion.id_aviso == id_aviso)
            ).scalars().first()
            if notif:
                session.delete(notif)
            
            # Eliminar aviso
            aviso = session.execute(
                select(Aviso).where(Aviso.id_aviso == id_aviso)
            ).scalars().first()
            if aviso:
                session.delete(aviso)
            
            session.commit()
            print("   Datos de prueba eliminados")
        
        print("\n=== PRUEBA COMPLETADA EXITOSAMENTE ===")
        
    except Exception as e:
        print(f"ERROR en la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_flow())