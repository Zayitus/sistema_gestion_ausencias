#!/usr/bin/env python3
"""Test simple del DialogueManager sin emojis problemáticos"""

from src.dialogue.manager import DialogueManager
from src.persistence.seed import ensure_schema

def main():
    print("=== INICIANDO PRUEBA DEL BOT ===")
    
    # Asegurar esquema de BD
    ensure_schema()
    print("BD inicializada")
    
    # Crear DialogueManager
    dm = DialogueManager()
    print("DialogueManager creado")
    
    # Simular conversación
    session_id = "test_user_123"
    
    print("\n--- SIMULANDO CONVERSACIÓN ---")
    
    # 1. Saludo inicial
    print("\nUsuario: Hola")
    result = dm.process_message(session_id, "Hola")
    print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")
    
    # 2. Enviar legajo
    print("\nUsuario: Mi legajo es 1001")
    result = dm.process_message(session_id, "Mi legajo es 1001")
    print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")
    
    # 3. Motivo de ausencia
    print("\nUsuario: enfermedad")
    result = dm.process_message(session_id, "enfermedad")
    print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")
    
    # 4. Fecha
    print("\nUsuario: hoy")
    result = dm.process_message(session_id, "hoy")
    print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")
    
    # 5. Días estimados
    print("\nUsuario: 3 dias")
    result = dm.process_message(session_id, "3 dias")
    print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")
    
    # 6. Confirmación
    print("\nUsuario: si, confirmar")
    result = dm.process_message(session_id, "si, confirmar")
    print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")
    
    print("\n=== PRUEBA COMPLETADA ===")

if __name__ == "__main__":
    main()