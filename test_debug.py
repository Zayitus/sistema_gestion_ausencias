#!/usr/bin/env python3
"""Test específico para debuggear el error"""

from src.dialogue.manager import DialogueManager
from src.persistence.seed import ensure_schema

def test_simple():
    print("=== DEBUGGING SIMPLE FLOW ===")
    
    ensure_schema()
    dm = DialogueManager()
    session_id = "debug_123"
    
    # Flujo simple sin certificado
    steps = [
        "Hola",
        "1001", 
        "nacimiento",  # Motivo que NO requiere certificado
        "hoy",
        "1",
        "confirmar"
    ]
    
    for i, user_input in enumerate(steps):
        print(f"\n--- PASO {i+1} ---")
        print(f"Usuario: {user_input}")
        result = dm.process_message(session_id, user_input)
        print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")
        
        # Si hay error, parar
        if "Error al crear el registro" in result.get('reply_text', ''):
            print(f"\n!!! ERROR DETECTADO EN PASO {i+1} !!!")
            break

if __name__ == "__main__":
    test_simple()