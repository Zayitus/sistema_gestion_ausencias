#!/usr/bin/env python3
"""
API routes para el dashboard RRHH
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

logger = logging.getLogger(__name__)


async def get_ausencias(request: Request) -> Response:
    """Endpoint que devuelve todas las ausencias con filtros opcionales"""
    try:
        from ..persistence.dao import session_scope
        from ..persistence.models import Aviso, Employee
        from sqlalchemy import select, func, and_
        
        # Parámetros de query
        estado = request.query.get('estado', '').lower().strip()
        motivo = request.query.get('motivo', '').strip()
        fecha_desde = request.query.get('fecha_desde', '').strip()
        fecha_hasta = request.query.get('fecha_hasta', '').strip()
        filtro_fecha = request.query.get('filtro_fecha', '').strip()  # hoy, 3dias, semana, mes, todos
        area = request.query.get('area', '').strip()  # filtro por sector/área
        limit = int(request.query.get('limit', '100'))
        
        with session_scope() as session:
            # Query base - LEFT JOIN para mostrar avisos sin empleado
            query = select(Aviso, Employee).outerjoin(Employee, Aviso.legajo == Employee.legajo)
            
            # Aplicar filtros
            if estado:
                if estado == 'completo':
                    query = query.where(Aviso.estado_aviso == 'completo')
                elif estado == 'incompleto':
                    query = query.where(Aviso.estado_aviso != 'completo')
                elif estado == 'rechazado':
                    query = query.where(Aviso.estado_aviso == 'rechazado')
            
            if motivo:
                query = query.where(Aviso.motivo == motivo)
            
            if area:
                if area == "N/A":
                    query = query.where(Employee.area.is_(None))
                else:
                    query = query.where(Employee.area == area)
            
            # Filtros de fecha - predefinidos tienen prioridad
            from datetime import datetime, timedelta
            if filtro_fecha:
                today = datetime.now().date()
                if filtro_fecha == "hoy":
                    query = query.where(Aviso.fecha_inicio == today)
                elif filtro_fecha == "3dias":
                    fecha_desde_obj = today - timedelta(days=2)
                    query = query.where(Aviso.fecha_inicio >= fecha_desde_obj)
                elif filtro_fecha == "semana":
                    fecha_desde_obj = today - timedelta(days=6)
                    query = query.where(Aviso.fecha_inicio >= fecha_desde_obj)
                elif filtro_fecha == "mes":
                    fecha_desde_obj = today - timedelta(days=29)
                    query = query.where(Aviso.fecha_inicio >= fecha_desde_obj)
                # "todos" no aplica filtro
            else:
                # Filtros de fecha personalizados
                if fecha_desde:
                    try:
                        fecha_desde_obj = datetime.fromisoformat(fecha_desde).date()
                        query = query.where(Aviso.fecha_inicio >= fecha_desde_obj)
                    except:
                        pass  # Ignorar fecha inválida
                
                if fecha_hasta:
                    try:
                        fecha_hasta_obj = datetime.fromisoformat(fecha_hasta).date()
                        query = query.where(Aviso.fecha_inicio <= fecha_hasta_obj)
                    except:
                        pass  # Ignorar fecha inválida
            
            # Ordenar por fecha más reciente primero
            query = query.order_by(Aviso.created_at.desc()).limit(limit)
            
            # Ejecutar query con LEFT JOIN
            result_tuples = session.execute(query).all()
            
            # Formatear respuesta
            results = []
            for row in result_tuples:
                aviso = row[0]  # Aviso object
                empleado = row[1] if len(row) > 1 else None  # Employee object or None
                
                # Calcular si requiere validación RRHH (empleado no encontrado o datos faltantes)
                requiere_validacion = not empleado or not empleado.nombre or not empleado.area
                
                # Calcular prioridad
                if requiere_validacion:
                    prioridad = "alta"  # Validación RRHH siempre es alta prioridad
                elif aviso.estado_aviso == "completo":
                    prioridad = "baja"
                else:
                    prioridad = "media"
                
                # Determinar acción requerida
                accion = "Sin acción"
                if requiere_validacion:
                    accion = "Validar empleado"
                elif aviso.estado_certificado in ["pendiente", "en_revision"]:
                    accion = "Revisar certificado"
                elif aviso.estado_aviso == "pendiente":
                    accion = "Seguimiento"
                
                # Extraer nombre provisional de observaciones si existe
                nombre_provisional = None
                if hasattr(aviso, 'observaciones') and aviso.observaciones:
                    # Formato: "Legajo PROVISIONAL - juan carlos pérez - validar con RRHH"
                    if "PROVISIONAL -" in aviso.observaciones:
                        parts = aviso.observaciones.split(" - ")
                        if len(parts) >= 2:
                            nombre_provisional = parts[1].title()  # Capitalize
                
                result = {
                    "id_aviso": aviso.id_aviso,
                    "legajo": aviso.legajo,
                    "nombre_empleado": (
                        empleado.nombre if empleado 
                        else nombre_provisional if nombre_provisional 
                        else "No encontrado"
                    ),
                    "area": empleado.area if empleado else "N/A",
                    "puesto": empleado.puesto if empleado else "N/A",
                    "motivo": aviso.motivo,
                    "fecha_inicio": aviso.fecha_inicio.isoformat() if aviso.fecha_inicio else None,
                    "dias_estimados": aviso.duracion_estimdays,
                    "fecha_fin_estimada": aviso.fecha_fin_estimada.isoformat() if aviso.fecha_fin_estimada else None,
                    "estado_aviso": aviso.estado_aviso or "pendiente",
                    "estado_certificado": aviso.estado_certificado or "N/A",
                    "requiere_validacion_rrhh": requiere_validacion,
                    "prioridad": prioridad,
                    "accion_requerida": accion,
                    "fecha_creacion": aviso.created_at.isoformat() if aviso.created_at else None,
                    "observaciones": getattr(aviso, 'observaciones', '') or ""
                }
                results.append(result)
        
        return web.json_response({
            "success": True,
            "count": len(results),
            "data": results
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo ausencias: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_stats(request: Request) -> Response:
    """Endpoint que devuelve estadísticas resumidas"""
    try:
        from ..persistence.dao import session_scope
        from ..persistence.models import Aviso, Employee
        from sqlalchemy import select, func, and_
        
        with session_scope() as session:
            # Contar totales
            total_ausencias = session.execute(
                select(func.count()).select_from(Aviso)
            ).scalar()
            
            ausencias_activas = session.execute(
                select(func.count()).select_from(Aviso).where(
                    Aviso.estado_aviso != 'completo'
                )
            ).scalar()
            
            # Para requieren_validacion necesitamos hacer un join y evaluar la lógica
            from sqlalchemy import or_
            requieren_validacion = session.execute(
                select(func.count()).select_from(Aviso).join(Employee, Aviso.legajo == Employee.legajo, isouter=True).where(
                    or_(Employee.legajo.is_(None), Employee.nombre.is_(None), Employee.area.is_(None))
                )
            ).scalar()
            
            certificados_pendientes = session.execute(
                select(func.count()).select_from(Aviso).where(
                    Aviso.estado_certificado.in_(['pendiente', 'en_revision'])
                )
            ).scalar()
            
            completadas = session.execute(
                select(func.count()).select_from(Aviso).where(
                    Aviso.estado_aviso == 'completo'
                )
            ).scalar()
            
            # Casos de alta prioridad (requieren validación + certificados en revisión)
            alta_prioridad = session.execute(
                select(func.count()).select_from(Aviso).join(Employee, Aviso.legajo == Employee.legajo, isouter=True).where(
                    and_(
                        or_(Employee.legajo.is_(None), Employee.nombre.is_(None), Employee.area.is_(None)),
                        Aviso.estado_certificado.in_(['pendiente', 'en_revision'])
                    )
                )
            ).scalar()
        
        stats = {
            "total_ausencias": total_ausencias,
            "ausencias_activas": ausencias_activas,
            "requieren_validacion": requieren_validacion,
            "certificados_pendientes": certificados_pendientes,
            "completadas": completadas,
            "alta_prioridad": alta_prioridad
        }
        
        return web.json_response({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_certificate(request: Request) -> Response:
    """Endpoint para descargar certificados"""
    try:
        id_aviso = request.match_info['id_aviso']
        
        from ..persistence.dao import session_scope
        from ..persistence.models import Certificado
        from sqlalchemy import select
        
        with session_scope() as session:
            # Buscar el certificado
            certificado = session.execute(
                select(Certificado).where(Certificado.id_aviso == id_aviso)
            ).scalars().first()
            
            if not certificado or not certificado.archivo_path:
                return web.json_response({
                    "success": False,
                    "error": "Certificado no encontrado"
                }, status=404)
            
            # Construir ruta del archivo
            base_dir = Path(__file__).parent.parent.parent  # Ir al directorio raíz
            file_path = base_dir / certificado.archivo_path.replace('\\', '/')
            
            if not file_path.exists():
                return web.json_response({
                    "success": False,
                    "error": "Archivo no encontrado en disco"
                }, status=404)
            
            # Determinar content type
            content_type = "image/jpeg"
            if file_path.suffix.lower() == ".pdf":
                content_type = "application/pdf"
            elif file_path.suffix.lower() == ".png":
                content_type = "image/png"
            elif file_path.suffix.lower() == ".docx":
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif file_path.suffix.lower() == ".doc":
                content_type = "application/msword"
            
            # Determinar disposition (inline para imágenes/PDF, attachment para documentos)
            disposition = "inline"
            if file_path.suffix.lower() in [".docx", ".doc"]:
                disposition = "attachment"
            
            # Devolver el archivo
            return web.FileResponse(
                path=file_path,
                headers={
                    "Content-Disposition": f'{disposition}; filename="certificado_{id_aviso}{file_path.suffix}"',
                    "Content-Type": content_type
                }
            )
            
    except Exception as e:
        logger.error(f"Error sirviendo certificado: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


def setup_api_routes(app: web.Application) -> None:
    """Configura las rutas de API"""
    app.router.add_get('/api/ausencias', get_ausencias)
    app.router.add_get('/api/stats', get_stats)
    app.router.add_get('/api/certificado/{id_aviso}', get_certificate)
    
    logger.info("Rutas de API configuradas")