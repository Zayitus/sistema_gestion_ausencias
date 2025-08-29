#!/usr/bin/env python3
"""Test completo del flujo DialogueManager"""

from src.dialogue.manager import DialogueManager
from src.persistence.seed import ensure_schema

def test_flujo_con_certificado():
    print("=== TEST: FLUJO CON CERTIFICADO ===")
    
    ensure_schema()
    dm = DialogueManager()
    session_id = "test_cert_123"
    
    steps = [
        ("Hola", "Saludo inicial"),
        ("1001", "Legajo válido"),
        ("enfermedad_inculpable", "Motivo que requiere certificado"),
        ("hoy", "Fecha de inicio"),
        ("3", "Días de ausencia"),
        ("enviar mas tarde", "Opción certificado"),
        ("confirmar", "Confirmación final")
    ]
    
    for user_input, descripcion in steps:
        print(f"\n[{descripcion}]")
        print(f"Usuario: {user_input}")
        result = dm.process_message(session_id, user_input)
        print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")

def test_flujo_sin_certificado():
    print("\n\n=== TEST: FLUJO SIN CERTIFICADO ===")
    
    dm = DialogueManager()
    session_id = "test_no_cert_456"
    
    steps = [
        ("Hola", "Saludo inicial"),
        ("1001", "Legajo válido"),
        ("nacimiento", "Motivo sin certificado"),
        ("mañana", "Fecha de inicio"),
        ("1", "Un día"),
        ("confirmar", "Confirmación final")
    ]
    
    for user_input, descripcion in steps:
        print(f"\n[{descripcion}]")
        print(f"Usuario: {user_input}")
        result = dm.process_message(session_id, user_input)
        print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")

def test_legajo_provisional():
    print("\n\n=== TEST: LEGAJO PROVISIONAL ===")
    
    dm = DialogueManager()
    session_id = "test_provisional_789"
    
    steps = [
        ("Hola", "Saludo inicial"),
        ("9999", "Legajo inexistente"),
        ("continuar provisional", "Acepta provisional"),
        ("permiso_gremial", "Motivo"),
        ("otra fecha", "Opción fecha específica"),
        ("01/09/2024", "Fecha específica"),
        ("otro", "Días personalizados"),
        ("5", "5 días específicos"),
        ("confirmar", "Confirmación final")
    ]
    
    for user_input, descripcion in steps:
        print(f"\n[{descripcion}]")
        print(f"Usuario: {user_input}")
        result = dm.process_message(session_id, user_input)
        print(f"Bot: {result.get('reply_text', 'Sin respuesta')}")

if __name__ == "__main__":
    test_flujo_con_certificado()
    test_flujo_sin_certificado() 
    test_legajo_provisional()
    print("\n=== TODAS LAS PRUEBAS COMPLETADAS ===")