"""
Roteador principal da API
"""
from fastapi import APIRouter
from app.api.endpoints import auth, users, conversations, campaigns, whatsapp, dashboard
from app.api.endpoints.dashboard_functional import router as dashboard_functional_router

api_router = APIRouter()

# Incluir rotas de autenticação
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Incluir rotas de usuários
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

# Incluir rotas de conversas
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"]
)

# Incluir rotas de campanhas
api_router.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["campaigns"]
)

# Incluir rotas do WhatsApp
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["whatsapp"]
)

# Incluir rotas do dashboard
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)

# Incluir rotas do dashboard funcional
api_router.include_router(
    dashboard_functional_router,
    tags=["dashboard-functional"]
)