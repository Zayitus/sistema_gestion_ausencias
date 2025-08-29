#!/usr/bin/env python3
"""Test funcional del bot sin mostrar emojis problemáticos"""

from src.dialogue.manager import DialogueManager
from src.persistence.seed import ensure_schema
from src.persistence.dao import session_scope
from src.persistence.models import Aviso

def limpiar_texto(texto):
    """Limpia emojis y caracteres problemáticos"""
    if not texto:
        return "Sin respuesta"
    # Reemplazar caracteres problemáticos
    import re
    # Remover emojis Unicode
    emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map
                           u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           u"\U00002600-\U000027BF"  # misc symbols
                           u"\U0001F900-\U0001F9FF"  # supplemental symbols
                           "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', texto).strip()

def main():
    print("=== PRUEBA FUNCIONAL DEL SISTEMA ===")
    
    # Asegurar esquema
    ensure_schema()
    print("✓ Base de datos lista")
    
    # Contar avisos antes
    with session_scope() as session:
        count_antes = len(list(session.query(Aviso).all()))
    print(f"✓ Avisos en BD antes: {count_antes}")
    
    # Crear DialogueManager
    dm = DialogueManager()
    print("✓ DialogueManager inicializado")
    
    # Simular conversación completa
    session_id = "test_funcional_123"
    
    print("\n--- SIMULACIÓN DE CONVERSACIÓN COMPLETA ---")
    
    # Paso 1: Saludo
    print("Usuario dice: 'Hola'")
    result = dm.process_message(session_id, "Hola")
    respuesta = limpiar_texto(result.get('reply_text', ''))
    print(f"Bot responde: {respuesta[:100]}...")
    
    # Paso 2: Legajo
    print("\nUsuario dice: 'Mi legajo es 1001'")
    result = dm.process_message(session_id, "Mi legajo es 1001")
    respuesta = limpiar_texto(result.get('reply_text', ''))
    print(f"Bot responde: {respuesta[:100]}...")
    
    # Paso 3: Motivo
    print("\nUsuario dice: 'enfermedad inculpable'")
    result = dm.process_message(session_id, "enfermedad inculpable")
    respuesta = limpiar_texto(result.get('reply_text', ''))
    print(f"Bot responde: {respuesta[:100]}...")
    
    # Paso 4: Fecha
    print("\nUsuario dice: '2025-08-29'")
    result = dm.process_message(session_id, "2025-08-29")
    respuesta = limpiar_texto(result.get('reply_text', ''))
    print(f"Bot responde: {respuesta[:100]}...")
    
    # Paso 5: Días
    print("\nUsuario dice: '3'")
    result = dm.process_message(session_id, "3")
    respuesta = limpiar_texto(result.get('reply_text', ''))
    print(f"Bot responde: {respuesta[:100]}...")
    
    # Paso 6: Confirmar
    print("\nUsuario dice: 'si'")
    result = dm.process_message(session_id, "si")
    respuesta = limpiar_texto(result.get('reply_text', ''))
    print(f"Bot responde: {respuesta[:100]}...")
    
    # Verificar si se creó un nuevo aviso
    with session_scope() as session:
        count_despues = len(list(session.query(Aviso).all()))
    
    print(f"\n=== RESULTADOS ===")
    print(f"Avisos antes: {count_antes}")
    print(f"Avisos después: {count_despues}")
    
    if count_despues > count_antes:
        print("✓ ¡ÉXITO! Se creó un nuevo aviso de ausencia")
        
        # Mostrar el último aviso creado
        with session_scope() as session:
            ultimo_aviso = session.query(Aviso).order_by(Aviso.created_at.desc()).first()
            if ultimo_aviso:
                print(f"  - ID: {ultimo_aviso.id_aviso}")
                print(f"  - Legajo: {ultimo_aviso.legajo}")
                print(f"  - Motivo: {ultimo_aviso.motivo}")
                print(f"  - Fecha inicio: {ultimo_aviso.fecha_inicio}")
                print(f"  - Días estimados: {ultimo_aviso.duracion_estimdays}")
    else:
        print("⚠ No se detectó creación de nuevo aviso")
    
    print("\n=== PRUEBA COMPLETADA ===")

if __name__ == "__main__":
    main()