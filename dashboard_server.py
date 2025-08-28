#!/usr/bin/env python3
"""
Dashboard Web para RRHH - Sistema de Ausencias
Servidor web independiente que sirve el panel de control para RRHH
"""

import asyncio
import logging
import os
from pathlib import Path
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from src.config import settings
from src.web.api import setup_api_routes
from src.persistence.seed import ensure_schema

# Configuración
HOST = "127.0.0.1"
PORT = 8090  # Puerto diferente al webhook
BASE_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def serve_dashboard(request: Request) -> Response:
    """Sirve la página principal del dashboard"""
    try:
        dashboard_path = BASE_DIR / "src" / "web" / "templates" / "dashboard.html"
        
        if not dashboard_path.exists():
            return web.Response(
                text="Dashboard no encontrado", 
                status=404
            )
        
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return web.Response(
            text=html_content, 
            content_type='text/html',
            charset='utf-8'
        )
        
    except Exception as e:
        logger.error(f"Error sirviendo dashboard: {e}")
        return web.Response(
            text=f"Error interno: {str(e)}", 
            status=500
        )


async def health_check(request: Request) -> Response:
    """Endpoint de salud del servidor"""
    try:
        # Verificar conexión a BD
        from src.persistence.dao import session_scope
        from src.persistence.models import Employee
        
        with session_scope() as session:
            # Test query simple
            from sqlalchemy import select, func
            count = session.execute(select(func.count()).select_from(Employee)).scalar()
            
        return web.json_response({
            "status": "ok",
            "database": "connected",
            "employees_count": count,
            "message": "Dashboard server running"
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response({
            "status": "error",
            "message": str(e)
        }, status=500)


async def init_app() -> web.Application:
    """Inicializa la aplicación web"""
    app = web.Application()
    
    # Configurar rutas
    app.router.add_get('/', serve_dashboard)
    app.router.add_get('/dashboard', serve_dashboard)
    app.router.add_get('/health', health_check)
    
    # Configurar rutas de API
    setup_api_routes(app)
    
    # Middleware para CORS si fuera necesario
    async def cors_middleware(app, handler):
        async def cors_handler(request):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        return cors_handler
    
    app.middlewares.append(cors_middleware)
    
    return app


async def main():
    """Función principal del servidor"""
    print("Dashboard RRHH - Sistema de Ausencias")
    print("=" * 50)
    
    try:
        # Inicializar esquema de BD si es necesario
        print("Verificando base de datos...")
        ensure_schema()
        print("Base de datos lista")
        
        # Crear aplicación
        app = await init_app()
        
        # Configurar runner
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Crear site
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        
        print(f"Dashboard iniciado en: http://{HOST}:{PORT}")
        print(f"Panel RRHH: http://{HOST}:{PORT}/dashboard")
        print(f"API Status: http://{HOST}:{PORT}/api/ausencias")
        print(f"Health Check: http://{HOST}:{PORT}/health")
        print("=" * 50)
        print("Servidor listo - Presiona Ctrl+C para detener")
        
        # Verificar datos de prueba
        try:
            from src.persistence.dao import session_scope
            from src.persistence.models import Aviso
            from sqlalchemy import select, func
            
            with session_scope() as session:
                count = session.execute(select(func.count()).select_from(Aviso)).scalar()
                print(f"Ausencias en BD: {count}")
                
                if count == 0:
                    print("No hay datos de prueba. Para generar datos:")
                    print("   python -m src.persistence.seed_synthetic")
                    
        except Exception as e:
            print(f"No se pudo verificar datos: {e}")
        
        print("=" * 50)
        
        # Mantener servidor activo
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nDeteniendo servidor...")
            
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
        print(f"Error: {e}")
    
    finally:
        if 'runner' in locals():
            await runner.cleanup()


if __name__ == "__main__":
    # Configurar logging para desarrollo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())