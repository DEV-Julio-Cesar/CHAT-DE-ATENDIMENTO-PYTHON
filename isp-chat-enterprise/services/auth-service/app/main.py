#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth Service - Microserviço de Autenticação
API FastAPI para autenticação, autorização e gerenciamento de usuários
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

# Imports locais
from shared.config.settings import settings
from shared.utils.database import get_db, init_db, close_db, get_database_info
from shared.utils.memory_cache import memory_cache
from shared.middleware.auth import (
    get_current_user, get_current_user_optional, require_admin, 
    require_supervisor_or_admin, CurrentUser, RequireAdmin, RequireSupervisorOrAdmin
)
from shared.models.user import User, UserRole

from services import (
    AuthService, AuthenticationError, AuthorizationError, 
    UserNotFoundError, UserAlreadyExistsError
)
from schemas import (
    LoginRequest, UserCreateRequest, UserUpdateRequest, PasswordChangeRequest,
    LoginResponse, UserResponse, TokenValidationResponse, UserListResponse,
    ErrorResponse, AuthConfig
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gerenciamento do ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciar ciclo de vida da aplicação
    """
    # Startup
    logger.info("🚀 Iniciando Auth Service...")
    
    try:
        # Inicializar banco de dados
        await init_db()
        logger.info("✅ Banco de dados inicializado")
        
        # Inicializar cache
        await memory_cache.connect()
        logger.info("✅ Cache inicializado")
        
        # Obter informações do banco
        db_info = await get_database_info()
        if db_info:
            logger.info(f"📊 Banco: {db_info.get('database')} ({db_info.get('size_mb', 0)} MB)")
        
        logger.info("🎉 Auth Service iniciado com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Finalizando Auth Service...")
    
    try:
        await memory_cache.disconnect()
        await close_db()
        logger.info("✅ Auth Service finalizado")
    except Exception as e:
        logger.error(f"❌ Erro na finalização: {e}")

# Criar aplicação FastAPI
app = FastAPI(
    title="ISP Chat - Auth Service",
    description="""
    🔐 **Microserviço de Autenticação e Autorização**
    
    Responsável por:
    - Autenticação de usuários (login/logout)
    - Geração e validação de tokens JWT
    - Gerenciamento de usuários (CRUD)
    - Controle de permissões e papéis
    - Rate limiting e segurança
    
    **Compatível com migração do sistema Node.js**
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    **settings.get_cors_config()
)

# Instanciar serviços
auth_service = AuthService()

# === MIDDLEWARE DE LOGGING ===

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para log de requests"""
    start_time = datetime.utcnow()
    
    # Processar request
    response = await call_next(request)
    
    # Calcular tempo de processamento
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Log da request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s - "
        f"IP: {request.client.host}"
    )
    
    # Adicionar header com tempo de processamento
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# === HANDLERS DE ERRO ===

@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handler para erros de autenticação"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "authentication_error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """Handler para erros de autorização"""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "authorization_error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(UserNotFoundError)
async def user_not_found_error_handler(request: Request, exc: UserNotFoundError):
    """Handler para usuário não encontrado"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "user_not_found",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(UserAlreadyExistsError)
async def user_already_exists_error_handler(request: Request, exc: UserAlreadyExistsError):
    """Handler para usuário já existe"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "user_already_exists",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Dados de entrada inválidos",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# === ENDPOINTS PÚBLICOS ===

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz com informações do serviço"""
    return {
        "service": "ISP Chat - Auth Service",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "login": "POST /auth/login",
            "verify": "POST /auth/verify",
            "users": "GET /users",
            "health": "GET /health"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check detalhado"""
    try:
        # Verificar banco de dados
        db_info = await get_database_info()
        db_healthy = bool(db_info)
        
        # Verificar cache
        cache_healthy = await memory_cache.ping() == "PONG"
        
        # Status geral
        overall_healthy = db_healthy and cache_healthy
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "service": "auth-service",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "info": db_info
                },
                "cache": {
                    "status": "healthy" if cache_healthy else "unhealthy",
                    "type": "memory"
                }
            },
            "uptime": "running"
        }
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "auth-service",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# === ENDPOINTS DE AUTENTICAÇÃO ===

@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    **Realizar login no sistema**
    
    Autentica o usuário e retorna token JWT para acesso às APIs.
    
    - **username**: Nome de usuário ou email
    - **password**: Senha do usuário
    - **remember_me**: Manter login por mais tempo (opcional)
    
    **Compatível com sistema Node.js atual**
    """
    try:
        client_ip = request.client.host
        result = await auth_service.login(db, login_data, client_ip)
        
        logger.info(f"Login realizado: {login_data.username} de {client_ip}")
        return result
        
    except AuthenticationError as e:
        logger.warning(f"Falha no login: {login_data.username} de {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@app.post("/auth/verify", response_model=TokenValidationResponse, tags=["Authentication"])
async def verify_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    **Verificar validade do token JWT**
    
    Valida se o token fornecido no header Authorization é válido.
    
    **Headers necessários:**
    - Authorization: Bearer {token}
    """
    try:
        # Extrair token do header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return TokenValidationResponse(valid=False)
        
        token = auth_header.split(" ")[1]
        result = await auth_service.validate_token(db, token)
        
        return result
        
    except Exception as e:
        logger.error(f"Erro na verificação de token: {e}")
        return TokenValidationResponse(valid=False)

@app.post("/auth/logout", tags=["Authentication"])
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    **Realizar logout do sistema**
    
    Invalida o token atual (implementação futura com blacklist).
    """
    # TODO: Implementar blacklist de tokens
    logger.info(f"Logout realizado: {current_user.username}")
    
    return {
        "message": "Logout realizado com sucesso",
        "timestamp": datetime.utcnow().isoformat()
    }

# === ENDPOINTS DE USUÁRIO ===

@app.get("/users/me", response_model=UserResponse, tags=["Users"])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    **Obter informações do usuário atual**
    
    Retorna dados completos do usuário logado.
    """
    return auth_service._user_to_response(current_user)

@app.put("/users/me", response_model=UserResponse, tags=["Users"])
async def update_current_user(
    user_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **Atualizar dados do usuário atual**
    
    Permite ao usuário atualizar seus próprios dados.
    Campos sensíveis como role requerem permissões especiais.
    """
    # Usuários normais não podem alterar role
    if user_data.role is not None and not current_user.is_admin:
        user_data.role = None
    
    updated_user = await auth_service.update_user(
        db, str(current_user.id), user_data, current_user
    )
    
    return auth_service._user_to_response(updated_user)

@app.post("/users/me/change-password", tags=["Users"])
async def change_current_user_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **Alterar senha do usuário atual**
    
    Permite ao usuário alterar sua própria senha.
    """
    await auth_service.change_password(db, current_user, password_data)
    
    return {
        "message": "Senha alterada com sucesso",
        "timestamp": datetime.utcnow().isoformat()
    }

# === ENDPOINTS DE GERENCIAMENTO DE USUÁRIOS (ADMIN/SUPERVISOR) ===

@app.get("/users", response_model=UserListResponse, tags=["User Management"])
async def list_users(
    page: int = 1,
    per_page: int = 50,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = RequireSupervisorOrAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Listar usuários do sistema**
    
    Lista usuários com paginação e filtros.
    Requer papel de supervisor ou administrador.
    
    - **page**: Página atual (padrão: 1)
    - **per_page**: Usuários por página (padrão: 50, máximo: 100)
    - **role**: Filtrar por papel
    - **is_active**: Filtrar por status ativo
    - **search**: Buscar por username ou email
    """
    # Limitar per_page
    per_page = min(per_page, 100)
    
    result = await auth_service.list_users(
        db, page, per_page, role, is_active, search
    )
    
    return UserListResponse(**result)

@app.post("/users", response_model=UserResponse, tags=["User Management"])
async def create_user(
    user_data: UserCreateRequest,
    current_user: User = RequireSupervisorOrAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Criar novo usuário**
    
    Cria um novo usuário no sistema.
    Requer papel de supervisor ou administrador.
    
    **Regras:**
    - Supervisores podem criar apenas agentes e viewers
    - Administradores podem criar qualquer papel
    """
    # Supervisores não podem criar admins ou supervisores
    if (current_user.role == UserRole.SUPERVISOR and 
        user_data.role in [UserRole.ADMIN, UserRole.SUPERVISOR]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisores não podem criar administradores ou supervisores"
        )
    
    new_user = await auth_service.create_user(db, user_data, current_user)
    
    return auth_service._user_to_response(new_user)

@app.get("/users/{user_id}", response_model=UserResponse, tags=["User Management"])
async def get_user(
    user_id: str,
    current_user: User = RequireSupervisorOrAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Obter usuário por ID**
    
    Retorna dados de um usuário específico.
    Requer papel de supervisor ou administrador.
    """
    user = await auth_service.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return auth_service._user_to_response(user)

@app.put("/users/{user_id}", response_model=UserResponse, tags=["User Management"])
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    current_user: User = RequireSupervisorOrAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Atualizar usuário**
    
    Atualiza dados de um usuário específico.
    Requer papel de supervisor ou administrador.
    
    **Regras:**
    - Supervisores não podem alterar admins ou supervisores
    - Apenas admins podem alterar papéis para admin/supervisor
    """
    # Verificar se usuário existe
    target_user = await auth_service.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Supervisores não podem alterar admins ou supervisores
    if (current_user.role == UserRole.SUPERVISOR and 
        target_user.role in [UserRole.ADMIN, UserRole.SUPERVISOR]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisores não podem alterar administradores ou supervisores"
        )
    
    # Apenas admins podem definir papéis de admin/supervisor
    if (user_data.role in [UserRole.ADMIN, UserRole.SUPERVISOR] and 
        current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem definir papéis de admin/supervisor"
        )
    
    updated_user = await auth_service.update_user(db, user_id, user_data, current_user)
    
    return auth_service._user_to_response(updated_user)

@app.delete("/users/{user_id}", tags=["User Management"])
async def delete_user(
    user_id: str,
    current_user: User = RequireAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Desativar usuário**
    
    Desativa um usuário (não remove do banco).
    Requer papel de administrador.
    """
    # Verificar se usuário existe
    target_user = await auth_service.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permitir desativar a si mesmo
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível desativar sua própria conta"
        )
    
    # Desativar usuário
    update_data = UserUpdateRequest(is_active=False)
    await auth_service.update_user(db, user_id, update_data, current_user)
    
    return {
        "message": f"Usuário {target_user.username} desativado com sucesso",
        "timestamp": datetime.utcnow().isoformat()
    }

# === ENDPOINTS DE CONFIGURAÇÃO ===

@app.get("/auth/config", response_model=AuthConfig, tags=["Configuration"])
async def get_auth_config():
    """
    **Obter configurações de autenticação**
    
    Retorna configurações públicas do sistema de autenticação.
    """
    return AuthConfig(
        jwt_expire_hours=settings.JWT_EXPIRE_HOURS,
        max_login_attempts=settings.MAX_LOGIN_ATTEMPTS,
        lockout_duration_minutes=settings.LOCKOUT_DURATION_MINUTES,
        password_min_length=8,
        require_email_verification=False
    )

# === ENDPOINTS DE ESTATÍSTICAS (ADMIN) ===

@app.get("/stats", tags=["Statistics"])
async def get_auth_stats(
    current_user: User = RequireAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Obter estatísticas do sistema**
    
    Retorna estatísticas de usuários e autenticação.
    Requer papel de administrador.
    """
    try:
        # Estatísticas de usuários por papel
        from sqlalchemy import select, func
        
        # Contar usuários por papel
        result = await db.execute(
            select(User.role, func.count(User.id))
            .group_by(User.role)
        )
        users_by_role = dict(result.fetchall())
        
        # Contar usuários ativos
        result = await db.execute(
            select(func.count(User.id))
            .where(User.is_active == True)
        )
        active_users = result.scalar()
        
        # Contar total de usuários
        result = await db.execute(select(func.count(User.id)))
        total_users = result.scalar()
        
        # Informações do banco
        db_info = await get_database_info()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "by_role": {
                    role.value: count for role, count in users_by_role.items()
                }
            },
            "database": db_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter estatísticas"
        )

# === EXECUTAR APLICAÇÃO ===

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=8001,  # Porta específica do Auth Service
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )