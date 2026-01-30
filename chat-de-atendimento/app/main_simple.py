"""
Aplicação FastAPI simplificada para desenvolvimento
"""
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import time
import os

# Importar endpoints WhatsApp
from app.whatsapp_endpoints import router as whatsapp_router

# Configurações simples
app = FastAPI(
    title="ISP Customer Support - Dev",
    version="2.0.0-dev",
    description="Sistema de atendimento ao cliente - Versão de desenvolvimento"
)

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
from fastapi import Form

@app.post("/api/v1/auth/login")
async def login(username: str = Form(), password: str = Form()):
    """Login básico para desenvolvimento"""
    
    # Verificar usuário
    user = users_db.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Verificar senha (simplificado para desenvolvimento)
    if password != "admin123":
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Retornar token fictício
    return {
        "success": True,
        "data": {
            "access_token": "dev-token-123456789",
            "refresh_token": "dev-refresh-123456789",
            "token_type": "bearer",
            "expires_in": 86400
        },
        "message": "Login successful"
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