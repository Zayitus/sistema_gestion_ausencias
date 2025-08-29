#!/usr/bin/env python3
"""
Script de prueba para el sistema de recordatorios
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from datetime import datetime, timedelta
from src.persistence.dao import session_scope, crear_aviso_simple
from src.reminders.scheduler import ReminderScheduler

async def test_reminder_system():
    """Prueba el sistema de recordatorios"""
    print("Probando sistema de recordatorios...")
    
    # Crear un aviso de prueba que requiere certificado
    aviso_data = {
        "legajo": "TEST123",
        "motivo": "enfermedad_inculpable", 
        "fecha_inicio": datetime.now().date().isoformat(),
        "duracion_dias": 1,
        "requiere_certificado": True,
        "certificado_path": None,  # Sin certificado para que esté pendiente
        "legajo_provisional": False,
        "nombre_provisional": "",
        "telegram_user_id": "TEST_USER_ID"
    }
    
    try:
        # Crear el aviso
        result = crear_aviso_simple(aviso_data)
        print(f"Aviso creado: {result}")
        
        # Verificar que se guardó con los campos correctos
        with session_scope() as session:
            from src.persistence.models import Aviso
            from sqlalchemy import select
            
            aviso = session.execute(
                select(Aviso).where(Aviso.legajo == "TEST123")
            ).scalars().first()
            
            if aviso:
                print(f"Aviso encontrado: {aviso.id_aviso}")
                print(f"Telegram User ID: {aviso.telegram_user_id}")
                print(f"Recordatorio enviado: {aviso.recordatorio_22h_enviado}")
                print(f"Estado certificado: {aviso.estado_certificado}")
                print(f"Motivo: {aviso.motivo}")
                
                # Limpiar el aviso de prueba
                session.delete(aviso)
                session.commit()
                print("Aviso de prueba eliminado")
            else:
                print("ERROR: No se encontró el aviso")
                
    except Exception as e:
        print(f"Error en la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reminder_system())