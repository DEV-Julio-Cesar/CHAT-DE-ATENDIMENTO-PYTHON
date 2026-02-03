"""
Endpoints PWA Mobile - CIANET Atendente
Versão: 3.0

Serve:
- Página mobile HTML
- Service Worker
- Manifest
- Assets estáticos
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Mobile PWA"])

# Templates
templates_path = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Static path
static_path = Path(__file__).parent.parent.parent / "static"


@router.get("/mobile", response_class=HTMLResponse, summary="Página PWA Mobile")
async def mobile_page(request: Request):
    """
    Página principal do PWA Mobile.
    
    Retorna o HTML que carrega o app mobile para atendentes.
    Suporta instalação como PWA (Add to Home Screen).
    """
    return templates.TemplateResponse(
        "mobile.html",
        {"request": request}
    )


@router.get("/mobile/chat", response_class=HTMLResponse, summary="Chat Mobile")
async def mobile_chat(request: Request):
    """Redireciona para a página mobile principal"""
    return templates.TemplateResponse(
        "mobile.html",
        {"request": request}
    )


@router.get("/offline.html", response_class=HTMLResponse, summary="Página Offline")
async def offline_page(request: Request):
    """Página exibida quando o usuário está offline"""
    return templates.TemplateResponse(
        "offline.html",
        {"request": request}
    )


@router.get("/static/sw.js", summary="Service Worker")
async def service_worker():
    """
    Service Worker para PWA.
    
    Responsável por:
    - Cache de assets
    - Suporte offline
    - Push notifications
    - Background sync
    """
    sw_path = static_path / "sw.js"
    
    return FileResponse(
        sw_path,
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache"
        }
    )


@router.get("/static/manifest.json", summary="PWA Manifest")
async def manifest():
    """
    Web App Manifest para PWA.
    
    Define:
    - Nome do app
    - Ícones
    - Cores
    - Display mode
    """
    manifest_path = static_path / "manifest.json"
    
    return FileResponse(
        manifest_path,
        media_type="application/manifest+json"
    )


@router.get("/static/css/{filename}", summary="CSS Files")
async def css_files(filename: str):
    """Servir arquivos CSS"""
    file_path = static_path / "css" / filename
    
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path, media_type="text/css")
    
    return FileResponse(status_code=404)


@router.get("/static/js/{filename}", summary="JavaScript Files")
async def js_files(filename: str):
    """Servir arquivos JavaScript"""
    file_path = static_path / "js" / filename
    
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path, media_type="application/javascript")
    
    return FileResponse(status_code=404)


@router.get("/static/icons/{filename}", summary="Icon Files")
async def icon_files(filename: str):
    """Servir ícones do PWA"""
    file_path = static_path / "icons" / filename
    
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path, media_type="image/png")
    
    # Retornar placeholder se ícone não existir
    return FileResponse(status_code=404)


@router.get("/static/sounds/{filename}", summary="Sound Files")
async def sound_files(filename: str):
    """Servir arquivos de som"""
    file_path = static_path / "sounds" / filename
    
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path, media_type="audio/mpeg")
    
    return FileResponse(status_code=404)


# ============================================================================
# PWA INFO
# ============================================================================

@router.get("/pwa/info", summary="Informações do PWA")
async def pwa_info():
    """Retorna informações sobre o PWA"""
    return {
        "name": "CIANET Atendente",
        "version": "3.0.0",
        "features": [
            "offline_support",
            "push_notifications",
            "background_sync",
            "installable"
        ],
        "install_prompt": {
            "ios": "Toque em 'Compartilhar' e depois 'Adicionar à Tela de Início'",
            "android": "Toque no menu ⋮ e depois 'Instalar app' ou 'Adicionar à tela inicial'"
        },
        "requirements": {
            "browser": "Chrome 67+, Safari 11.3+, Firefox 79+, Edge 79+",
            "connection": "Required for first load, optional after"
        }
    }
