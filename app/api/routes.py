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
from app.api.endpoints.users_v2 import router as users_v2_router
from app.api.endpoints.conversations_v2 import router as conversations_v2_router
from app.api.endpoints.dashboard_v2 import router as dashboard_v2_router
from app.api.endpoints.chatbot_admin_v2 import router as chatbot_admin_v2_router
from app.api.endpoints.reports_v2 import router as reports_v2_router
from app.api.endpoints.mobile_pwa import router as mobile_pwa_router
from app.core.security_headers import security_headers_manager

api_router = APIRouter()

# Incluir rotas de autenticação (com suporte a usuários demo)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Incluir rotas de autenticação V2 (requer SQL Server - desabilitado)
# api_router.include_router(
#     auth_v2_router,
#     tags=["authentication-v2"]
# )

# Incluir rotas de usuários V2 (CRUD completo com SQL Server)
api_router.include_router(
    users_v2_router,
    tags=["users-v2"]
)

# Incluir rotas de conversas V2 (Atendimentos com SQL Server)
api_router.include_router(
    conversations_v2_router,
    tags=["conversations-v2"]
)

# Incluir rotas de dashboard V2 (Métricas reais SQL Server)
api_router.include_router(
    dashboard_v2_router,
    tags=["dashboard-v2"]
)

# Rotas WhatsApp V2 removidas (dependiam de WhatsApp Business API)

# Incluir rotas Chatbot Admin V2 (Treinamento e métricas)
api_router.include_router(
    chatbot_admin_v2_router,
    tags=["chatbot-v2"]
)

# Incluir rotas de Relatórios PDF V2
api_router.include_router(
    reports_v2_router,
    tags=["reports-v2"]
)

# Incluir rotas PWA Mobile
api_router.include_router(
    mobile_pwa_router,
    tags=["mobile-pwa"]
)

# Rotas legadas removidas (agora usando auth.py como principal)

# Incluir rotas de usuários (legado)
api_router.include_router(
    users.router,
    prefix="/users-legacy",
    tags=["users-legacy"]
)

# Incluir rotas GDPR/LGPD
api_router.include_router(
     gdpr.router,
     tags=["gdpr-lgpd"]
)

# Incluir rotas de conversas (legado)
api_router.include_router(
    conversations.router,
    prefix="/conversations-legacy",
    tags=["conversations-legacy"]
)

# Incluir rotas de campanhas
api_router.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["campaigns"]
)

# Incluir rotas do WhatsApp Python (novo)
api_router.include_router(
    whatsapp_python_router,
    tags=["whatsapp"]
)

# Incluir rotas do Chatbot AI
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)

# Incluir rotas do Chatbot AI
api_router.include_router(
    chatbot.router,
    tags=["chatbot-ai"]
)

# Incluir rotas do dashboard funcional
api_router.include_router(
    dashboard_functional_router,
    tags=["dashboard-functional"]
)

# Incluir rotas de administração do Chatbot Treinável
api_router.include_router(
    chatbot_admin_router,
    tags=["chatbot-admin"]
)

# Rotas WhatsApp V2 removidas (dependiam de SQL Server e WhatsApp Business API)


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