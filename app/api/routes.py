"""
Roteador principal da API
CIANET PROVEDOR - Sistema de Atendimento WhatsApp
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.api.endpoints import auth, users, conversations, campaigns, dashboard, chatbot
from app.api.endpoints import gdpr
from app.api.endpoints.dashboard_functional import router as dashboard_functional_router
from app.api.endpoints.chatbot_admin import router as chatbot_admin_router
from app.api.endpoints.whatsapp_python import router as whatsapp_python_router
from app.api.endpoints.mobile_pwa import router as mobile_pwa_router
from app.api.endpoints.backup import router as backup_router
from app.api.endpoints.atendimento import router as atendimento_router
from app.core.security_headers import security_headers_manager

api_router = APIRouter()

# ============================================================================
# ROTAS PRINCIPAIS (MariaDB/MySQL)
# ============================================================================

# Autenticação
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Usuários
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

# GDPR/LGPD
api_router.include_router(
     gdpr.router,
     tags=["gdpr-lgpd"]
)

# Conversas/Atendimentos
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"]
)

# Campanhas
api_router.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["campaigns"]
)

# WhatsApp
api_router.include_router(
    whatsapp_python_router,
    tags=["whatsapp"]
)

# Dashboard
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)

# Dashboard Funcional
api_router.include_router(
    dashboard_functional_router,
    tags=["dashboard-functional"]
)

# Chatbot AI
api_router.include_router(
    chatbot.router,
    tags=["chatbot-ai"]
)

# Chatbot Admin
api_router.include_router(
    chatbot_admin_router,
    tags=["chatbot-admin"]
)

# PWA Mobile
api_router.include_router(
    mobile_pwa_router,
    tags=["mobile-pwa"]
)

# Backup (Admin only)
api_router.include_router(
    backup_router,
    tags=["backup"]
)

# Atendimento Profissional
api_router.include_router(
    atendimento_router,
    tags=["atendimento"]
)

# ============================================================================
# ROTAS LEGADAS (DEPRECADAS - Serão removidas em 12/03/2026)
# ============================================================================
# Versões V2 foram movidas para app/api/endpoints/_legacy/
# Motivo: Consolidação para usar apenas MariaDB/MySQL
# Ver: app/api/endpoints/_legacy/README.md para mais informações
# ============================================================================


# =============================================================================
# ENDPOINT DE RELATÓRIO CSP
# =============================================================================
@api_router.post("/csp-report", include_in_schema=False)
async def csp_report_endpoint(request: Request) -> JSONResponse:
    """
    Endpoint para receber relatórios de violação CSP.
    Browsers enviam automaticamente quando CSP é violado.
    """
    try:
        report = await request.json()
        security_headers_manager.validate_csp_report(report)
        return JSONResponse(content={"status": "received"}, status_code=204)
    except Exception:
        return JSONResponse(content={"error": "Invalid report"}, status_code=400)