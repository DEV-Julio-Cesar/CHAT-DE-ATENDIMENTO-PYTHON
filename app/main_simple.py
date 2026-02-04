"""
Aplicação FastAPI simplificada para desenvolvimento
"""
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import time
import os
from pathlib import Path

# Importar endpoints WhatsApp
from app.whatsapp_endpoints import router as whatsapp_router

# Importar dashboard funcional
from app.api.endpoints.dashboard_functional import router as dashboard_functional_router

# Configurações simples
app = FastAPI(
    title="ISP Customer Support - Dev",
    version="2.0.0-dev",
    description="Sistema de atendimento ao cliente - Versão de desenvolvimento"
)

# Configurar templates e arquivos estáticos
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

# Montar arquivos estáticos
if (BASE_DIR / "web" / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")

# CORS para desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas WhatsApp
app.include_router(whatsapp_router)

# Incluir dashboard funcional
app.include_router(dashboard_functional_router, prefix="/api/v1")

# ============= ROTAS DE PÁGINAS WEB =============

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Página do dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Página do chat"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request):
    """Página de clientes"""
    return templates.TemplateResponse("customers.html", {"request": request})

@app.get("/whatsapp-config", response_class=HTMLResponse)
@app.get("/whatsapp", response_class=HTMLResponse)
async def whatsapp_config_page(request: Request):
    """Página de configuração do WhatsApp"""
    return templates.TemplateResponse("whatsapp_config.html", {"request": request})

@app.get("/chatbot-admin", response_class=HTMLResponse)
async def chatbot_admin_page(request: Request):
    """Página de administração do chatbot"""
    return templates.TemplateResponse("chatbot_admin.html", {"request": request})

@app.get("/teste", response_class=HTMLResponse)
async def teste_page(request: Request):
    """Página de teste"""
    return templates.TemplateResponse("teste.html", {"request": request})

# ============= FIM ROTAS DE PÁGINAS WEB =============

# Dados em memória para desenvolvimento
users_db = {
    "admin": {
        "id": "admin-123",
        "username": "admin",
        "email": "admin@sistema.com",
        "role": "admin",
        "ativo": True,
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG."  # admin123
    }
}

# Rotas básicas
@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "ISP Customer Support API - Desenvolvimento",
        "version": "2.0.0-dev",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check simplificado"""
    return {
        "status": "healthy",
        "version": "2.0.0-dev",
        "timestamp": time.time(),
        "environment": "development",
        "checks": {
            "api": True,
            "database": True,  # SQLite sempre disponível
            "redis": True      # Assumindo que está rodando
        }
    }

@app.get("/info")
async def app_info():
    """Informações da aplicação"""
    return {
        "name": "ISP Customer Support",
        "version": "2.0.0-dev",
        "environment": "development",
        "database": "SQLite (local)",
        "features": [
            "Health Check",
            "Basic Authentication",
            "User Management",
            "API Documentation"
        ]
    }

# Rota de autenticação básica
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/v1/auth/login")
async def login(login_data: LoginRequest):
    """Login básico para desenvolvimento"""
    
    # Credenciais de desenvolvimento
    valid_credentials = {
        "admin@empresa.com.br": "Admin@123",
        "admin@sistema.com": "admin123",
        "admin": "admin123"
    }
    
    # Verificar credenciais
    expected_password = valid_credentials.get(login_data.email)
    if not expected_password or login_data.password != expected_password:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    
    # Retornar token e dados do usuário
    return {
        "access_token": "dev-token-123456789",
        "refresh_token": "dev-refresh-123456789",
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {
            "id": "admin-123",
            "nome": "Administrador",
            "email": login_data.email,
            "role": "admin"
        }
    }

@app.get("/api/v1/auth/me")
async def get_current_user():
    """Obter usuário atual (desenvolvimento)"""
    return {
        "success": True,
        "data": {
            "id": "admin-123",
            "username": "admin",
            "email": "admin@sistema.com",
            "role": "admin",
            "ativo": True
        },
        "message": "User information retrieved"
    }

@app.get("/api/v1/users")
async def list_users():
    """Listar usuários"""
    return {
        "success": True,
        "data": list(users_db.values()),
        "message": "Users retrieved successfully"
    }

@app.post("/api/v1/users")
async def create_user(username: str = Form(), email: str = Form(), password: str = Form(), role: str = Form(default="atendente")):
    """Criar usuário"""
    if username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    
    new_user = {
        "id": f"{username}-{int(time.time())}",
        "username": username,
        "email": email,
        "role": role,
        "ativo": True,
        "password_hash": f"hash-{password}"  # Simplificado
    }
    
    users_db[username] = new_user
    
    return {
        "success": True,
        "data": new_user,
        "message": "User created successfully"
    }

@app.get("/metrics")
async def metrics():
    """Métricas básicas"""
    return """# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/"} 1
http_requests_total{method="GET",endpoint="/health"} 1

# HELP app_info Application information
# TYPE app_info gauge
app_info{version="2.0.0-dev",environment="development"} 1
"""

# Rotas de desenvolvimento
@app.get("/dev/status")
async def dev_status():
    """Status de desenvolvimento"""
    return {
        "environment": "development",
        "database_url": os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./isp_support.db"),
        "redis_url": os.getenv("REDIS_URL", "redis://redis:6379/0"),
        "debug": True,
        "features_enabled": [
            "CORS",
            "Auto-reload",
            "SQLite database",
            "In-memory auth"
        ]
    }

@app.get("/dev/test-error")
async def test_error():
    """Testar tratamento de erro"""
    raise HTTPException(status_code=500, detail="This is a test error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)