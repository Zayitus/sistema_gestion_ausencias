from __future__ import annotations

from typing import Any, Dict
from datetime import date, datetime, timedelta

from ..utils.normalize import parse_legajo, normalize_motivo, parse_date, sanitize_number_of_days
from .prompts import (
    msg_saludo, msg_pedir_legajo, msg_pedir_motivo, msg_pedir_fecha, msg_pedir_dias, 
    msg_pedir_certificado, msg_resumen, msg_confirmar, msg_ok_creado
)
from ..telegram.keyboards import kb_motivos, kb_fecha, kb_dias, ik_adjuntar, kb_si_no, kb_legajo_provisional
from ..session_store import get_legajo, set_legajo


class DialogueManager:
    def __init__(self) -> None:
        self.sessions: Dict[str, dict[str, Any]] = {}
    
    def set_legajo_validado(self, session_id: str, legajo: str) -> None:
        """Marca el legajo como validado desde el comando /id"""
        sess = self._ensure_session(session_id)
        sess["legajo"] = str(legajo)
        sess["legajo_validado"] = True
        sess["step"] = "motivo"
    
    def _ensure_session(self, session_id: str) -> dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "step": "inicio",
                "legajo": None,
                "legajo_validado": False,
                "legajo_provisional": False,
                "motivo": None,
                "fecha_inicio": None,
                "duracion_dias": None,
                "requiere_certificado": False,
                "certificado_recibido": False,
                "certificado_path": None,
                "nombre_provisional": None,
            }
        return self.sessions[session_id]
    
    def _validate_legajo_in_db(self, legajo_digits: str) -> tuple[bool, str]:
        """Retorna (existe, nombre_empleado)"""
        try:
            from ..persistence.seed import ensure_schema
            from ..persistence.dao import session_scope
            from ..persistence.models import Employee
            ensure_schema()
            with session_scope() as s:
                emp = s.query(Employee).filter(Employee.legajo == legajo_digits).first()
                if emp:
                    nombre = getattr(emp, "nombre", None) or "Empleado"
                    return True, nombre
                return False, ""
        except Exception:
            return False, ""
    
    def _requires_certificate(self, motivo: str) -> bool:
        """Determina si el motivo requiere certificado médico"""
        motivos_con_certificado = {"enfermedad_inculpable", "enfermedad_familiar"}
        return motivo in motivos_con_certificado
    
    def _get_motivos_list(self) -> list[str]:
        """Retorna lista de motivos disponibles"""
        return [
            "enfermedad_inculpable",
            "enfermedad_familiar", 
            "fallecimiento",
            "nacimiento",
            "matrimonio",
            "paternidad",
            "permiso_gremial",
            "art"
        ]
    
    def process_message(self, session_id: str, incoming: str) -> dict[str, Any]:
        sess = self._ensure_session(session_id)
        text = (incoming or "").strip().lower()
        step = sess["step"]
        
        # PASO 1: INICIO - Presentación
        if step == "inicio":
            if text.startswith("/start") or text.startswith("hola") or text == "":
                sess["step"] = "legajo"
                return {
                    "reply_text": msg_saludo()
                }
            else:
                # Si no es start, asumir que quiere empezar el proceso
                sess["step"] = "legajo"
                return {
                    "reply_text": msg_saludo()
                }
        
        # PASO 2: LEGAJO - Validación
        elif step == "legajo":
            legajo_digits = parse_legajo(text)
            if not legajo_digits:
                return {
                    "reply_text": "Formato inválido. Por favor ingresá tu legajo (4 dígitos). Ejemplo: 1234"
                }
            
            exists, nombre = self._validate_legajo_in_db(legajo_digits)
            sess["legajo"] = legajo_digits
            
            if exists:
                sess["legajo_validado"] = True
                sess["legajo_provisional"] = False
                sess["step"] = "motivo"
                motivos = self._get_motivos_list()
                return {
                    "reply_text": f"Perfecto, {nombre} (legajo {legajo_digits}) verificado.\n\n" + msg_pedir_motivo(motivos),
                    "reply_markup": kb_motivos(motivos)
                }
            else:
                sess["step"] = "pedir_nombre_provisional"
                return {
                    "reply_text": f"No encontré el legajo {legajo_digits} en el sistema.\n\nPara continuar necesito tu nombre y apellido completo para que RRHH pueda identificarte:"
                }
        
        # PASO 2.5: PEDIR NOMBRE PARA LEGAJO PROVISIONAL
        elif step == "pedir_nombre_provisional":
            nombre_completo = (text or "").strip()
            if len(nombre_completo) < 5:  # Mínimo validación
                return {
                    "reply_text": "Por favor ingresá tu nombre y apellido completo (ej: Juan Pérez):"
                }
            
            # Guardar el nombre y continuar con confirmación
            sess["nombre_provisional"] = nombre_completo
            sess["step"] = "confirmar_legajo_provisional"
            return {
                "reply_text": f"Nombre: {nombre_completo}\nLegajo: {sess['legajo']} (provisional)\n\n¿Querés continuar? Tu registro será validado por RRHH.",
                "reply_markup": kb_legajo_provisional()
            }
        
        # PASO 2.6: CONFIRMAR LEGAJO PROVISIONAL
        elif step == "confirmar_legajo_provisional":
            if "continuar" in text or "provisional" in text:
                sess["legajo_provisional"] = True
                sess["step"] = "motivo"
                motivos = self._get_motivos_list()
                return {
                    "reply_text": f"OK, continuamos con legajo {sess['legajo']} de forma provisional.\n\n" + msg_pedir_motivo(motivos),
                    "reply_markup": kb_motivos(motivos)
                }
            elif "reingresar" in text or "nuevo" in text:
                sess["step"] = "legajo"
                return {
                    "reply_text": msg_pedir_legajo()
                }
            else:
                return {
                    "reply_text": "Por favor responde: 'continuar provisional' o 'reingresar legajo'"
                }
        
        # PASO 3: MOTIVO
        elif step == "motivo":
            motivo = normalize_motivo(text)
            motivos_validos = self._get_motivos_list()
            
            if motivo not in motivos_validos:
                return {
                    "reply_text": f"Motivo no reconocido. Por favor elegí uno de: {', '.join(motivos_validos)}",
                    "reply_markup": kb_motivos(motivos_validos)
                }
            
            sess["motivo"] = motivo
            sess["requiere_certificado"] = self._requires_certificate(motivo)
            sess["step"] = "fecha"
            
            return {
                "reply_text": f"Motivo registrado: {motivo}\n\n" + msg_pedir_fecha(),
                "reply_markup": kb_fecha()
            }
        
        # PASO 4: FECHA
        elif step == "fecha":
            if text == "hoy":
                fecha = date.today()
            elif text == "mañana":
                fecha = date.today() + timedelta(days=1)
            elif text == "otra fecha":
                sess["step"] = "fecha_especifica"
                return {
                    "reply_text": "Ingresá la fecha en formato DD/MM/AAAA (ejemplo: 15/12/2024):"
                }
            else:
                # Intentar parsear fecha directamente
                fecha_str = parse_date(text)
                if not fecha_str:
                    return {
                        "reply_text": "Fecha no reconocida. Elegí: Hoy, Mañana, o Otra fecha",
                        "reply_markup": kb_fecha()
                    }
                fecha = datetime.fromisoformat(fecha_str).date()
            
            sess["fecha_inicio"] = fecha.isoformat()
            sess["step"] = "dias"
            return {
                "reply_text": f"Fecha registrada: {fecha.strftime('%d/%m/%Y')}\n\n" + msg_pedir_dias(),
                "reply_markup": kb_dias()
            }
        
        # PASO 4.5: FECHA ESPECÍFICA
        elif step == "fecha_especifica":
            fecha_str = parse_date(text)
            if not fecha_str:
                return {
                    "reply_text": "Formato incorrecto. Ingresá la fecha como DD/MM/AAAA (ejemplo: 15/12/2024):"
                }
            
            fecha = datetime.fromisoformat(fecha_str).date()
            sess["fecha_inicio"] = fecha.isoformat()
            sess["step"] = "dias"
            return {
                "reply_text": f"Fecha registrada: {fecha.strftime('%d/%m/%Y')}\n\n" + msg_pedir_dias(),
                "reply_markup": kb_dias()
            }
        
        # PASO 5: DÍAS
        elif step == "dias":
            if text == "otro":
                sess["step"] = "dias_especifico"
                return {
                    "reply_text": "¿Cuántos días de ausencia? Ingresá un número:"
                }
            
            dias = sanitize_number_of_days(text)
            if not dias or dias <= 0:
                return {
                    "reply_text": "Número de días inválido. Elegí: 1, 2, 3, 5, 10, o Otro",
                    "reply_markup": kb_dias()
                }
            
            sess["duracion_dias"] = dias
            
            # Decidir siguiente paso
            if sess["requiere_certificado"]:
                sess["step"] = "certificado"
                return {
                    "reply_text": f"Duración: {dias} día(s)\n\n" + msg_pedir_certificado(sess["motivo"]),
                    "reply_markup": ik_adjuntar()
                }
            else:
                sess["step"] = "confirmacion"
                return self._generate_summary(sess)
        
        # PASO 5.5: DÍAS ESPECÍFICO
        elif step == "dias_especifico":
            dias = sanitize_number_of_days(text)
            if not dias or dias <= 0:
                return {
                    "reply_text": "Número inválido. Ingresá la cantidad de días (ejemplo: 7):"
                }
            
            sess["duracion_dias"] = dias
            
            # Decidir siguiente paso
            if sess["requiere_certificado"]:
                sess["step"] = "certificado"
                return {
                    "reply_text": f"Duración: {dias} día(s)\n\n" + msg_pedir_certificado(sess["motivo"]),
                    "reply_markup": ik_adjuntar()
                }
            else:
                sess["step"] = "confirmacion"
                return self._generate_summary(sess)
        
        # PASO 6: CERTIFICADO
        elif step == "certificado":
            if "adjuntar ahora" in text or "adjuntar" in text:
                sess["step"] = "esperando_certificado"
                return {
                    "reply_text": "Por favor adjuntá el certificado enviando la imagen o PDF:"
                }
            elif "enviar mas tarde" in text or "enviar más tarde" in text or "despues" in text:
                sess["certificado_recibido"] = False
                sess["step"] = "confirmacion"
                return self._generate_summary(sess, certificado_pendiente=True)
            else:
                return {
                    "reply_text": "Por favor elegí una opción:",
                    "reply_markup": ik_adjuntar()
                }
        
        # PASO 6.5: ESPERANDO CERTIFICADO
        elif step == "esperando_certificado":
            return {
                "reply_text": "Estoy esperando que adjuntes el certificado. Por favor envía la imagen o PDF del certificado médico."
            }
        
        # PASO 7: CONFIRMACIÓN
        elif step == "confirmacion":
            if "confirmar" in text or "si" in text or text == "sí":
                return self._create_absence_record(session_id, sess)
            elif "editar" in text or "cambiar" in text:
                sess["step"] = "motivo"
                motivos = self._get_motivos_list()
                return {
                    "reply_text": "OK, editemos el registro.\n\n" + msg_pedir_motivo(motivos),
                    "reply_markup": kb_motivos(motivos)
                }
            else:
                return {
                    "reply_text": "Por favor responde: 'Confirmar' o 'Editar'"
                }
        
        # Si llegamos acá, estado desconocido - reiniciar
        else:
            sess["step"] = "legajo"
            return {
                "reply_text": msg_saludo()
            }
    
    def handle_certificate_upload(self, session_id: str, file_path: str) -> dict[str, Any]:
        """Maneja la subida de certificado"""
        sess = self._ensure_session(session_id)
        
        if sess["step"] in ["certificado", "esperando_certificado"] or (sess["step"] == "confirmacion" and sess["requiere_certificado"]):
            sess["certificado_recibido"] = True
            sess["certificado_path"] = file_path
            sess["step"] = "confirmacion"
            
            return self._generate_summary(sess, certificado_recibido=True)
        else:
            return {
                "reply_text": "No estaba esperando un certificado en este momento."
            }
    
    def _generate_summary(self, sess: dict[str, Any], certificado_pendiente: bool = False, certificado_recibido: bool = False) -> dict[str, Any]:
        """Genera el resumen para confirmación"""
        fecha_obj = datetime.fromisoformat(sess["fecha_inicio"]).date()
        
        resumen = f"""
RESUMEN DE TU SOLICITUD:

• Legajo: {sess['legajo']} {'(PROVISIONAL - validar con RRHH)' if sess['legajo_provisional'] else '(verificado)'}
• Motivo: {sess['motivo']}
• Fecha inicio: {fecha_obj.strftime('%d/%m/%Y')}
• Duración: {sess['duracion_dias']} día(s)
"""
        
        if sess["requiere_certificado"]:
            if certificado_recibido:
                resumen += "• Certificado: RECIBIDO\n"
            elif certificado_pendiente:
                resumen += "• Certificado: PENDIENTE (recordá enviarlo)\n"
            else:
                resumen += "• Certificado: REQUERIDO\n"
        
        resumen += "\n¿Confirmas la solicitud?"
        
        return {
            "reply_text": resumen,
            "reply_markup": kb_si_no()
        }
    
    def _create_absence_record(self, session_id: str, sess: dict[str, Any]) -> dict[str, Any]:
        """Crea el registro de ausencia en la base de datos"""
        try:
            from ..persistence.dao import crear_aviso_simple
            
            # Crear el aviso
            aviso_data = {
                "legajo": sess["legajo"],
                "motivo": sess["motivo"],
                "fecha_inicio": sess["fecha_inicio"],
                "duracion_dias": sess["duracion_dias"],
                "requiere_certificado": sess["requiere_certificado"],
                "certificado_path": sess.get("certificado_path"),
                "legajo_provisional": sess["legajo_provisional"],
                "nombre_provisional": sess.get("nombre_provisional", ""),
                "telegram_user_id": session_id
            }
            
            result = crear_aviso_simple(aviso_data)
            
            if result and result.get("success") and result.get("id_aviso"):
                codigo = result["id_aviso"]
                tipo_registro = "PROVISIONAL" if sess["legajo_provisional"] else "CONFIRMADO"
                
                # Limpiar sesión
                sess["step"] = "completado"
                
                # Mensaje personalizado según motivo
                motivo_display = {
                    'fallecimiento': 'Fallecimiento',
                    'nacimiento': 'Nacimiento',
                    'enfermedad_inculpable': 'Enfermedad Inculpable',
                    'enfermedad_familiar': 'Enfermedad Familiar',
                    'matrimonio': 'Matrimonio',
                    'paternidad': 'Paternidad',
                    'permiso_gremial': 'Permiso Gremial',
                    'art': 'ART'
                }.get(sess['motivo'], sess['motivo'])
                
                mensaje = f"""
¡SOLICITUD REGISTRADA!

Código: {codigo}
Tipo: {tipo_registro}
Legajo: {sess['legajo']}
Motivo: {motivo_display}

"""
                
                # Mensajes especiales según motivo
                if sess['motivo'] == 'fallecimiento':
                    mensaje += "Lamentamos mucho tu pérdida. Mis más sinceras condolencias.\n\n"
                elif sess['motivo'] == 'nacimiento':
                    mensaje += "¡¡¡¡Felicidades!!!!\n\n"
                if sess["legajo_provisional"]:
                    mensaje += "IMPORTANTE: Tu legajo será validado por RRHH.\n"
                
                if sess["requiere_certificado"] and not sess["certificado_recibido"]:
                    mensaje += "RECORDATORIO: Debes enviar el certificado médico antes de las 24 hs.\n"
                
                mensaje += "\nGracias por usar el sistema de ausencias."
                
                return {
                    "reply_text": mensaje
                }
            else:
                error_msg = result.get("error", "Error desconocido") if result else "Sin respuesta del sistema"
                return {
                    "reply_text": f"Error al crear el registro: {error_msg}\n\nPor favor intentá nuevamente o contactá a sistemas."
                }
        
        except Exception as e:
            return {
                "reply_text": f"Error al procesar la solicitud: {str(e)}"
            }