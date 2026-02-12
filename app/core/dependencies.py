"""
Dependências compartilhadas da aplicação
- Autenticação JWT
- Autorização por role
- Validação de usuário
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    DecodeError,
    InvalidTokenError
)
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.redis_client import redis_manager
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Extrair e validar JWT do Bearer token
    
    Verifica:
    1. Se token está revogado (blacklist)
    2. Se token é válido (assinatura)
    3. Se token não expirou
    
    Retorna payload do JWT
    """
    try:
        token = credentials.credentials
        
        # 1. Verificar se está na blacklist (revogado)
        is_revoked = await redis_manager.get(f"revoked_token:{token}")
        if is_revoked:
            logger.warning(f"Tentativa de uso de token revogado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token was revoked"
            )
        
        # 2. Decodificar JWT com validações
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience="isp-support-users",
            issuer="isp-support-system"
        )
        
        # 3. Extrair sub (user_id)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        logger.debug(f"User {user_id} authenticated successfully")
        return payload
        
    except ExpiredSignatureError:
        logger.warning(f"Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except InvalidAudienceError:
        logger.warning(f"Invalid token audience")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience"
        )
    except InvalidIssuerError:
        logger.warning(f"Invalid token issuer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer"
        )
    except (DecodeError, InvalidTokenError) as e:
        logger.warning(f"JWT validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Alias para compatibilidade
get_current_active_user = get_current_user


async def require_admin(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validar se usuário tem role 'admin'
    
    Uso:
        @router.post("/admin-only")
        async def admin_endpoint(user = Depends(require_admin)):
            ...
    """
    role = user.get("role")
    
    if role != "admin":
        logger.warning(f"User {user.get('sub')} attempted admin action without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user


async def require_role(*allowed_roles: str):
    """
    Factory para criar dependency que verifica múltiplas roles
    
    Uso:
        @router.post("/moderators-only")
        async def mod_endpoint(user = Depends(require_role("admin", "moderator"))):
            ...
    """
    async def check_role(
        user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_role = user.get("role")
        
        if user_role not in allowed_roles:
            logger.warning(
                f"User {user.get('sub')} role '{user_role}' not in {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role must be one of: {', '.join(allowed_roles)}"
            )
        
        return user
    
    return check_role


async def revoke_token(token: str, expiry_seconds: Optional[int] = None) -> bool:
    """
    Adicionar token à blacklist (revogação)
    
    Usa Redis com TTL = tempo até expiração do token
    
    Args:
        token: JWT token a revogar
        expiry_seconds: Segundos até expiração (default: usar exp do token)
    """
    try:
        if not expiry_seconds:
            # Se não informado, calcular do token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_signature": False}
            )
            exp = payload.get("exp")
            import time
            expiry_seconds = max(0, int(exp - time.time()))
        
        # Adicionar à blacklist com TTL
        await redis_manager.set(
            f"revoked_token:{token}",
            "1",
            ex=expiry_seconds
        )
        
        logger.info(f"Token revoked successfully (expires in {expiry_seconds}s)")
        return True
        
    except Exception as e:
        logger.error(f"Error revoking token: {str(e)}")
        return False


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security) if False else None
) -> Optional[Dict[str, Any]]:
    """
    Opcionalmente validar JWT (para endpoints públicos com autenticação opcional)
    
    Se token não informado: retorna None
    Se token informado mas inválido: lança erro 401
    Se token válido: retorna payload
    
    Uso:
        @router.get("/public-endpoint")
        async def public_endpoint(user = Depends(get_optional_user)):
            if user:
                return f"Olá, {user['sub']}"
            return "Olá, anônimo"
    """
    if credentials is None:
        return None
    
    # Se credentials informado, validar com get_current_user
    return await get_current_user(credentials)



async def get_db():
    """
    Dependency para obter sessão do banco de dados
    
    Uso:
        @router.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Usuario))
            return result.scalars().all()
    """
    from app.core.database import db_manager
    
    async with db_manager.get_session() as session:
        yield session
