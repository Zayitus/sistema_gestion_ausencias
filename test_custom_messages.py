#!/usr/bin/env python3
"""
Prueba de mensajes personalizados para diferentes motivos
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.dialogue.manager import DialogueManager
from datetime import datetime

def test_custom_messages():
    """Prueba los mensajes personalizados para fallecimiento y nacimiento"""
    print("=== PRUEBA DE MENSAJES PERSONALIZADOS ===")
    
    dm = DialogueManager()
    
    # Casos de prueba
    test_cases = [
        {
            'motivo': 'fallecimiento',
            'descripcion': 'Fallecimiento (debería mostrar condolencias)'
        },
        {
            'motivo': 'nacimiento', 
            'descripcion': 'Nacimiento (debería mostrar felicidades)'
        },
        {
            'motivo': 'enfermedad_inculpable',
            'descripcion': 'Enfermedad (mensaje normal)'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. PROBANDO: {test_case['descripcion']}")
        print("-" * 50)
        
        session_id = f"TEST_USER_{i}"
        motivo = test_case['motivo']
        
        # Simular todo el flujo hasta la confirmación
        try:
            # Crear sesión completa
            sess = dm._ensure_session(session_id)
            sess.update({
                "legajo": "1234",
                "legajo_validado": True,
                "legajo_provisional": False,
                "motivo": motivo,
                "fecha_inicio": datetime.now().date().isoformat(),
                "duracion_dias": 1,
                "requiere_certificado": motivo in ['enfermedad_inculpable', 'enfermedad_familiar'],
                "certificado_recibido": False,
                "step": "confirmacion"
            })
            
            # Simular confirmación
            response = dm.process_message(session_id, "confirmar")
            
            print("MENSAJE GENERADO:")
            print(response['reply_text'])
            
            # Verificar contenido esperado
            reply_text = response['reply_text']
            
            if motivo == 'fallecimiento':
                if "Lamentamos mucho tu pérdida" in reply_text and "condolencias" in reply_text:
                    print("✅ CORRECTO: Mensaje de condolencias presente")
                else:
                    print("❌ ERROR: Mensaje de condolencias faltante")
            
            elif motivo == 'nacimiento':
                if "Felicidades" in reply_text:
                    print("✅ CORRECTO: Mensaje de felicitaciones presente")
                else:
                    print("❌ ERROR: Mensaje de felicitaciones faltante")
            
            else:
                if "Lamentamos" not in reply_text and "Felicidades" not in reply_text:
                    print("✅ CORRECTO: Mensaje normal sin texto especial")
                else:
                    print("❌ ERROR: Mensaje especial no debería estar presente")
                    
        except Exception as e:
            print(f"❌ ERROR en la prueba: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== PRUEBA COMPLETADA ===")

if __name__ == "__main__":
    test_custom_messages()