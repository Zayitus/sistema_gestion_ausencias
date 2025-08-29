#!/usr/bin/env python3
"""
Script de migración para agregar campos del sistema de recordatorios
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.persistence.dao import session_scope
from src.persistence.models import Base
from sqlalchemy import text

def migrate():
    """Ejecuta la migración para agregar campos de recordatorios"""
    print("Ejecutando migración para sistema de recordatorios...")
    
    try:
        with session_scope() as session:
            # Verificar si las columnas ya existen
            result = session.execute(text("PRAGMA table_info(avisos)")).fetchall()
            columns = [row[1] for row in result]
            
            if 'recordatorio_22h_enviado' not in columns:
                print("Agregando columna recordatorio_22h_enviado...")
                session.execute(text(
                    "ALTER TABLE avisos ADD COLUMN recordatorio_22h_enviado BOOLEAN DEFAULT 0 NOT NULL"
                ))
            
            if 'telegram_user_id' not in columns:
                print("Agregando columna telegram_user_id...")
                session.execute(text(
                    "ALTER TABLE avisos ADD COLUMN telegram_user_id VARCHAR(50) NULL"
                ))
            
            session.commit()
            print("✅ Migración completada exitosamente")
            
    except Exception as e:
        print(f"❌ Error en la migración: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)