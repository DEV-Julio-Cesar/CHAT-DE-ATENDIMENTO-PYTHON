"""
Endpoints de autenticação com JWT + auditoria
SEMANA 1 - Integração de segurança
"""
from fastapi import APIRouter, HTTPException, status, Request, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import jwt
import logging

from app.core.config import settings
from app.core.dependencies import revoke_token
from app.core.audit_logger import audit_logger, AuditEventTypes
from app.core.rate_limiter import rate_limiter, RateLimitConfig
from app.core.database import db_manager
from app.models.database import Usuario
from sqlalchemy import select
import bcrypt

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LoginRequest(BaseModel):
    """Credenciais para login"""
    email: EmailStr
    password: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "usuario@empresa.com",
                    "password": "SenhaSegura123!"
                }
            ]
        }
    }


class LoginResponse(BaseModel):
    """Resposta de login bem-sucedido"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 86400,
                    "user": {
                        "id": 1,
                        "email": "usuario@empresa.com",
                        "nome": "João Silva",
                        "role": "atendente"
                    }
                }
            ]
        }
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/login", 
    response_model=LoginResponse,
    summary="Autenticar usuário",
    description="""
Realiza autenticação do usuário e retorna um token JWT.

### Rate Limiting
- **5 tentativas** a cada **15 minutos** por IP
- Após exceder, retorna HTTP 429

### Segurança
- Senhas são verificadas com bcrypt (12 rounds)
- Tokens JWT expiram em 24 horas
- Tentativas falhas são registradas em auditoria

### Exemplo de uso
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@email.com", "password": "senha123"}
)
token = response.json()["access_token"]

# Usar token em requisições
headers = {"Authorization": f"Bearer {token}"}
```
""",
    responses={
        200: {"description": "Login bem-sucedido"},
        401: {"description": "Credenciais inválidas"},
        429: {"description": "Muitas tentativas - rate limit excedido"},
        500: {"description": "Erro interno do servidor"}
    },
    tags=["auth"]
)
async def login(
    request: Request,
    credentials: LoginRequest
):
    """
    Autenticar usuário e obter token JWT.
    
    - **email**: Email do usuário cadastrado
    - **password**: Senha do usuário
    """
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # ===== 1. APLICAR RATE LIMITING =====
        identifier = f"login:{client_ip}"
        allowed, remaining = await rate_limiter.is_allowed(
            identifier=identifier,
            max_requests=RateLimitConfig.LOGIN["max_requests"],
            window_seconds=RateLimitConfig.LOGIN["window_seconds"]
        )
        
        if not allowed:
            logger.warning(f"Login rate limit exceeded for {identifier}")
            
            await audit_logger.log(
                event_type=AuditEventTypes.RATE_LIMIT_EXCEEDED,
                user_id=None,
                action="login",
                ip_address=client_ip,
                details={"email": credentials.email}
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later."
            )
        
        # ===== 2. VALIDAR CREDENCIAIS =====
        # Primeiro verificar se é o usuário demo (funciona sem banco)
        DEMO_USERS = {
            "admin@empresa.com.br": {
                "id": "1",
                "email": "admin@empresa.com.br",
                "password": "Admin@123",
                "nome": "Administrador",
                "role": "admin",
                "is_active": True
            },
            "atendente@empresa.com.br": {
                "id": "2",
                "email": "atendente@empresa.com.br",
                "password": "Atend@123",
                "nome": "Atendente Demo",
                "role": "atendente",
                "is_active": True
            },
            "supervisor@empresa.com.br": {
                "id": "3",
                "email": "supervisor@empresa.com.br",
                "password": "Super@123",
                "nome": "Supervisor Demo",
                "role": "supervisor",
                "is_active": True
            }
        }
        
        user = None
        is_demo_user = False
        
        # Verificar se é usuário demo
        if credentials.email in DEMO_USERS:
            demo = DEMO_USERS[credentials.email]
            if credentials.password == demo["password"]:
                user = demo
                is_demo_user = True
                logger.info(f"Demo user login: {credentials.email}")
        
        # Se não for demo, tentar buscar no banco MariaDB/MySQL
        if not user:
            try:
                db_user = await get_user_by_email(credentials.email)
                if db_user and await verify_password(credentials.password, db_user.password_hash):
                    user = {
                        "id": str(db_user.id),
                        "email": db_user.email,
                        "nome": db_user.username,
                        "role": db_user.role.value,
                        "ativo": db_user.ativo
                    }
                else:
                    user = None  # Senha incorreta ou usuário não existe
            except Exception as db_error:
                logger.warning(f"Banco MariaDB/MySQL não disponível, usando modo demo: {db_error}")
                user = None
        
        if not user:
            logger.warning(f"Failed login attempt for {credentials.email} from {client_ip} - user not found")
            
            await audit_logger.log(
                event_type=AuditEventTypes.LOGIN_FAILED,
                user_id=None,
                action="login",
                resource_type="user",
                ip_address=client_ip,
                status="failed",
                details={"email": credentials.email, "reason": "user_not_found"}
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # ===== 3. CRIAR JWT TOKEN =====
        user_id = user["id"]
        user_role = user["role"]
        user_nome = user["nome"]
        
        exp = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {
            "sub": str(user_id),
            "username": user_nome,
            "email": credentials.email,
            "role": user_role,
            "exp": exp,
            "iat": datetime.now(timezone.utc),
            "aud": "isp-support-users",
            "iss": "isp-support-system"
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Atualizar last_login no banco MariaDB/MySQL (apenas se não for demo user)
        if not is_demo_user and user:
            try:
                async with db_manager.session_factory() as session:
                    db_user = await get_user_by_email(credentials.email)
                    if db_user:
                        db_user.ultimo_login = datetime.now(timezone.utc)
                        await session.commit()
            except Exception as e:
                logger.warning(f"Não foi possível atualizar ultimo_login: {e}")
        
        # ===== 4. REGISTRAR EM AUDITORIA =====
        await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_SUCCESS,
            user_id=user_id,
            action="login",
            resource_type="user",
            resource_id=user_id,
            ip_address=client_ip,
            status="success"
        )
        
        logger.info(f"Successful login for {credentials.email} from {client_ip}")
        
        # ===== 5. RETORNAR TOKEN =====
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": user_id,
                "email": credentials.email,
                "nome": user_nome,
                "role": user_role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        
        await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_FAILED,
            user_id=None,
            action="login",
            ip_address=client_ip,
            status="error",
            details={"error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Logout do usuário com revogação de token
    
    Headers:
        Authorization: Bearer {token}
    
    Returns:
        status: "logged out"
    """
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header"
            )
        
        # Extrair token
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = parts[1]
        
        # Decodificar token para obter user_id
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # ===== 1. REVOGAR TOKEN =====
        await revoke_token(token)
        
        logger.info(f"Token revoked for user {user_id} from {client_ip}")
        
        # ===== 2. REGISTRAR EM AUDITORIA =====
        await audit_logger.log(
            event_type=AuditEventTypes.LOGOUT,
            user_id=user_id,
            action="logout",
            resource_type="user",
            resource_id=user_id,
            ip_address=client_ip,
            status="success"
        )
        
        return {"status": "logged out"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/token/validate")
async def validate_token(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Validar se token é válido (sem expiração ou revogação)
    
    Útil para verificar status de sessão
    """
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = parts[1]
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "expires_at": datetime.fromtimestamp(payload.get("exp")).isoformat()
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Função utilitária para buscar usuário por e-mail
async def get_user_by_email(email: str):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Usuario).where(Usuario.email == email))
        user = result.scalar_one_or_none()
        return user

# Função utilitária para verificar senha
async def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())