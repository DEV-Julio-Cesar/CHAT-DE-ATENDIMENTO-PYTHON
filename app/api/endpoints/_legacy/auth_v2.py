"""
Endpoints de Autenticação JWT Completo
CIANET PROVEDOR - v3.0

Endpoints:
- POST /auth/login - Login com email/senha
- POST /auth/logout - Logout (revoga sessão atual)
- POST /auth/logout-all - Logout de todas as sessões
- POST /auth/refresh - Renovar tokens
- GET /auth/me - Dados do usuário atual
- GET /auth/sessions - Listar sessões ativas
- DELETE /auth/sessions/{session_id} - Revogar sessão específica
- POST /auth/change-password - Alterar senha
- GET /auth/permissions - Listar permissões do usuário
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Request, Depends, Header
from pydantic import BaseModel, EmailStr, Field, validator

from app.core.config import settings
from app.core.auth_manager import auth_manager, get_current_user, require_role
from app.core.database import db_manager
from app.models.database import Usuario
from app.core.rate_limiter import rate_limiter, RateLimitConfig
from app.core.audit_logger import audit_logger, AuditEventTypes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticação"])


# ============================================================================
# SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    """Credenciais de login"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    remember_me: bool = False  # Se true, refresh token dura mais
    device_name: Optional[str] = None  # Ex: "Chrome no Windows"


class LoginResponse(BaseModel):
    """Resposta de login bem-sucedido"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    session_id: str
    user: Dict[str, Any]


class RefreshRequest(BaseModel):
    """Request para renovar tokens"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Resposta com novos tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """Request para alterar senha"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    logout_other_sessions: bool = True  # Deslogar outras sessões
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validar força da senha"""
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve ter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in v):
            raise ValueError('Senha deve ter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve ter pelo menos um número')
        return v


class SessionInfo(BaseModel):
    """Informações de uma sessão"""
    session_id: str
    device_info: Optional[str]
    ip_address: Optional[str]
    created_at: str
    last_activity: str
    is_current: bool = False


class UserProfile(BaseModel):
    """Perfil do usuário"""
    id: int
    email: str
    nome: str
    role: str
    permissions: List[str]
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None


# ============================================================================
# HELPERS
# ============================================================================

def get_client_info(request: Request) -> Dict[str, str]:
    """Extrair informações do cliente da request"""
    user_agent = request.headers.get("user-agent", "")
    
    # Parse simples do user agent
    device_info = "Dispositivo desconhecido"
    if "Windows" in user_agent:
        device_info = "Windows"
    elif "Mac" in user_agent:
        device_info = "Mac"
    elif "Linux" in user_agent:
        device_info = "Linux"
    elif "Android" in user_agent:
        device_info = "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        device_info = "iOS"
    
    # Navegador
    browser = ""
    if "Chrome" in user_agent and "Edg" not in user_agent:
        browser = "Chrome"
    elif "Firefox" in user_agent:
        browser = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser = "Safari"
    elif "Edg" in user_agent:
        browser = "Edge"
    
    if browser:
        device_info = f"{browser} no {device_info}"
    
    return {
        "device_info": device_info,
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": user_agent
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login com email e senha",
    responses={
        200: {"description": "Login bem-sucedido"},
        401: {"description": "Credenciais inválidas"},
        423: {"description": "Conta bloqueada"},
        429: {"description": "Muitas tentativas"}
    }
)
async def login(request: Request, credentials: LoginRequest):
    """
    Autenticar usuário e retornar tokens JWT.
    
    - **email**: Email cadastrado
    - **password**: Senha do usuário
    - **remember_me**: Se true, sessão dura 30 dias (padrão: 7 dias)
    - **device_name**: Nome do dispositivo (opcional)
    
    **Rate Limit**: 5 tentativas a cada 15 minutos por IP
    """
    client_info = get_client_info(request)
    
    # Rate limiting
    identifier = f"login:{client_info['ip_address']}"
    allowed, remaining = await rate_limiter.is_allowed(
        identifier=identifier,
        max_requests=5,
        window_seconds=900  # 15 minutos
    )
    
    if not allowed:
        await audit_logger.log(
            event_type=AuditEventTypes.RATE_LIMIT_EXCEEDED,
            user_id=None,
            action="login",
            ip_address=client_info['ip_address'],
            details={"email": credentials.email}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde 15 minutos."
        )
    
    # Buscar usuário
    user = sqlserver_manager.get_user_by_email(credentials.email)
    
    if not user:
        await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_FAILED,
            user_id=None,
            action="login",
            ip_address=client_info['ip_address'],
            status="failed",
            details={"email": credentials.email, "reason": "user_not_found"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )
    
    # Verificar se conta está bloqueada
    if user.get("locked_until"):
        locked_until = user["locked_until"]
        if isinstance(locked_until, datetime) and locked_until > datetime.now():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Conta bloqueada até {locked_until.strftime('%H:%M:%S')}"
            )
    
    # Verificar senha
    if not sqlserver_manager.verify_password(credentials.password, user["password_hash"]):
        await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_FAILED,
            user_id=user["id"],
            action="login",
            ip_address=client_info['ip_address'],
            status="failed",
            details={"email": credentials.email, "reason": "invalid_password"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )
    
    # Obter permissões do usuário
    permissions = sqlserver_manager.get_user_permissions(int(user["id"]))
    permission_codes = [p["code"] for p in permissions] if permissions else []
    
    # Criar tokens
    device_info = credentials.device_name or client_info["device_info"]
    
    tokens = await auth_manager.create_auth_tokens(
        user_id=int(user["id"]),
        email=user["email"],
        nome=user["nome"],
        role=user["role"],
        permissions=permission_codes,
        device_info=device_info,
        ip_address=client_info["ip_address"]
    )
    
    # Atualizar último login
    sqlserver_manager.update_last_login(int(user["id"]))
    
    # Registrar em auditoria
    await audit_logger.log(
        event_type=AuditEventTypes.LOGIN_SUCCESS,
        user_id=user["id"],
        action="login",
        ip_address=client_info["ip_address"],
        status="success",
        details={"device": device_info, "session_id": tokens.session_id}
    )
    
    logger.info(f"Login successful: {credentials.email} from {client_info['ip_address']}")
    
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        session_id=tokens.session_id,
        user={
            "id": int(user["id"]),
            "email": user["email"],
            "nome": user["nome"],
            "role": user["role"],
            "permissions": permission_codes
        }
    )


@router.post(
    "/logout",
    summary="Logout da sessão atual",
    responses={
        200: {"description": "Logout realizado"},
        401: {"description": "Não autenticado"}
    }
)
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Encerrar sessão atual e revogar tokens.
    """
    session_id = current_user.get("session_id")
    
    if session_id:
        await auth_manager.revoke_session(session_id)
    
    await audit_logger.log(
        event_type=AuditEventTypes.LOGOUT,
        user_id=current_user["id"],
        action="logout",
        ip_address=request.client.host if request.client else "unknown",
        status="success"
    )
    
    return {"message": "Logout realizado com sucesso"}


@router.post(
    "/logout-all",
    summary="Logout de todas as sessões",
    responses={
        200: {"description": "Todas as sessões encerradas"}
    }
)
async def logout_all(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Encerrar todas as sessões do usuário (exceto a atual).
    Útil quando suspeita de acesso não autorizado.
    """
    current_session = current_user.get("session_id")
    count = await auth_manager.revoke_all_user_sessions(
        user_id=current_user["id"],
        except_session=current_session
    )
    
    await audit_logger.log(
        event_type=AuditEventTypes.LOGOUT,
        user_id=current_user["id"],
        action="logout_all",
        ip_address=request.client.host if request.client else "unknown",
        status="success",
        details={"sessions_revoked": count}
    )
    
    return {
        "message": f"{count} sessões encerradas",
        "sessions_revoked": count
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar tokens",
    responses={
        200: {"description": "Tokens renovados"},
        401: {"description": "Refresh token inválido"}
    }
)
async def refresh_tokens(data: RefreshRequest):
    """
    Renovar access token usando refresh token.
    
    O refresh token antigo é invalidado (rotation) e um novo par é gerado.
    """
    tokens = await auth_manager.refresh_tokens(data.refresh_token)
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in
    )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Dados do usuário atual",
    responses={
        200: {"description": "Dados do usuário"},
        401: {"description": "Não autenticado"}
    }
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Retorna dados completos do usuário autenticado.
    """
    # Buscar dados completos do usuário
    user = sqlserver_manager.get_user_by_id(int(current_user["id"]))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return UserProfile(
        id=int(user["id"]),
        email=user["email"],
        nome=user["nome"],
        role=user["role"],
        permissions=current_user.get("permissions", []),
        avatar_url=user.get("avatar_url"),
        phone=user.get("phone"),
        department=user.get("department"),
        created_at=str(user.get("created_at")) if user.get("created_at") else None,
        last_login=str(user.get("last_login")) if user.get("last_login") else None
    )


@router.get(
    "/sessions",
    response_model=List[SessionInfo],
    summary="Listar sessões ativas",
    responses={
        200: {"description": "Lista de sessões"}
    }
)
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """
    Lista todas as sessões ativas do usuário.
    Útil para ver dispositivos conectados.
    """
    sessions = await auth_manager.get_user_sessions(current_user["id"])
    current_session_id = current_user.get("session_id")
    
    return [
        SessionInfo(
            session_id=s["session_id"],
            device_info=s.get("device_info"),
            ip_address=s.get("ip_address"),
            created_at=s.get("created_at", ""),
            last_activity=s.get("last_activity", ""),
            is_current=s["session_id"] == current_session_id
        )
        for s in sessions
    ]


@router.delete(
    "/sessions/{session_id}",
    summary="Revogar sessão específica",
    responses={
        200: {"description": "Sessão revogada"},
        404: {"description": "Sessão não encontrada"}
    }
)
async def revoke_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Revogar uma sessão específica do usuário.
    Não é possível revogar a sessão atual (use /logout).
    """
    if session_id == current_user.get("session_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /logout para encerrar a sessão atual"
        )
    
    # Verificar se sessão pertence ao usuário
    session = await auth_manager.get_session(session_id)
    if not session or session.get("user_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada"
        )
    
    await auth_manager.revoke_session(session_id)
    
    await audit_logger.log(
        event_type=AuditEventTypes.LOGOUT,
        user_id=current_user["id"],
        action="revoke_session",
        ip_address=request.client.host if request.client else "unknown",
        status="success",
        details={"revoked_session": session_id}
    )
    
    return {"message": "Sessão revogada com sucesso"}


@router.post(
    "/change-password",
    summary="Alterar senha",
    responses={
        200: {"description": "Senha alterada"},
        400: {"description": "Senha atual incorreta"}
    }
)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Alterar senha do usuário.
    
    - **current_password**: Senha atual
    - **new_password**: Nova senha (mín 8 chars, 1 maiúscula, 1 minúscula, 1 número)
    - **logout_other_sessions**: Se true, encerra outras sessões
    """
    # Buscar usuário com hash da senha
    user = sqlserver_manager.get_user_by_email(current_user["email"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verificar senha atual
    if not sqlserver_manager.verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta"
        )
    
    # Atualizar senha
    new_hash = auth_manager.hash_password(data.new_password)
    sqlserver_manager.update_user_password(int(user["id"]), new_hash)
    
    # Logout de outras sessões se solicitado
    sessions_revoked = 0
    if data.logout_other_sessions:
        sessions_revoked = await auth_manager.revoke_all_user_sessions(
            user_id=current_user["id"],
            except_session=current_user.get("session_id")
        )
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_UPDATED,
        user_id=current_user["id"],
        action="change_password",
        resource_type="user",
        resource_id=str(current_user["id"]),
        ip_address=request.client.host if request.client else "unknown",
        status="success"
    )
    
    return {
        "message": "Senha alterada com sucesso",
        "sessions_revoked": sessions_revoked
    }


@router.get(
    "/permissions",
    summary="Listar permissões do usuário",
    responses={
        200: {"description": "Lista de permissões"}
    }
)
async def get_permissions(current_user: dict = Depends(get_current_user)):
    """
    Retorna todas as permissões do usuário atual.
    """
    permissions = sqlserver_manager.get_user_permissions(current_user["id"])
    
    # Agrupar por categoria
    by_category = {}
    for perm in permissions or []:
        cat = perm.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "code": perm["code"],
            "name": perm["name"]
        })
    
    return {
        "role": current_user["role"],
        "permissions": current_user.get("permissions", []),
        "by_category": by_category
    }


@router.get(
    "/validate",
    summary="Validar token atual",
    responses={
        200: {"description": "Token válido"},
        401: {"description": "Token inválido"}
    }
)
async def validate_token(current_user: dict = Depends(get_current_user)):
    """
    Verificar se o token atual é válido.
    Útil para o frontend verificar status da autenticação.
    """
    return {
        "valid": True,
        "user_id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "session_id": current_user.get("session_id")
    }
