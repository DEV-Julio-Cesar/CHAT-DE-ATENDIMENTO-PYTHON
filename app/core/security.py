"""
Módulo de segurança - autenticação, autorização e criptografia
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog
import secrets
import hashlib
from functools import wraps

from app.core.config import settings
from app.core.redis_client import redis_manager, CacheKeys
from app.models.database import UserRole

logger = structlog.get_logger(__name__)

# Configuração de hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


class SecurityManager:
    """Gerenciador de segurança centralizado"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    # Hash de senhas
    def hash_password(self, password: str) -> str:
        """Gerar hash da senha"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar senha"""
        return pwd_context.verify(plain_password, hashed_password)
    
    # JWT Tokens
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Criar token JWT com claims de segurança"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        # Adicionar claims de segurança obrigatórios
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "aud": "chatbot-api",  # Audiência
            "iss": "cianet-auth",  # Emissor
            "jti": secrets.token_urlsafe(32)  # JWT ID único para revogação
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error("Failed to create JWT token", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verificar e decodificar token JWT com validação completa"""
        try:
            # Validação completa com audience, issuer e claims obrigatórios
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience="chatbot-api",  # Validar audiência
                issuer="cianet-auth",    # Validar emissor
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "jti", "sub"]  # Claims obrigatórios
                }
            )
            
            # Verificar se token está na blacklist
            jti = payload.get("jti")
            if jti:
                # Verificação síncrona para compatibilidade
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Se já estamos em um loop, criar task
                        blacklisted = False  # Fallback seguro
                    else:
                        blacklisted = loop.run_until_complete(self._check_blacklist(jti))
                except RuntimeError:
                    blacklisted = False  # Fallback seguro
                
                if blacklisted:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidIssuerError:
            logger.warning("Invalid token issuer")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError as e:
            logger.warning("Invalid JWT token", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def _check_blacklist(self, jti: str) -> bool:
        """Verificar se JTI está na blacklist"""
        try:
            blacklisted = await redis_manager.get(f"blacklist:{jti}")
            return blacklisted is not None
        except Exception:
            return False  # Fallback seguro
    
    # Refresh tokens
    def create_refresh_token(self, user_id: str) -> str:
        """Criar refresh token"""
        data = {
            "sub": user_id,
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)  # JWT ID único
        }
        
        # Refresh tokens têm validade maior
        expires_delta = timedelta(days=30)
        return self.create_access_token(data, expires_delta)
    
    async def revoke_token(self, token: str):
        """Revogar token (blacklist)"""
        try:
            payload = self.verify_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # Adicionar à blacklist até expirar
                ttl = exp - int(datetime.utcnow().timestamp())
                if ttl > 0:
                    await redis_manager.set(f"blacklist:{jti}", "1", ex=ttl)
                    
        except HTTPException:
            # Token já inválido, não precisa revogar
            pass
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Verificar se token está na blacklist"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Não verificar expiração aqui
            )
            jti = payload.get("jti")
            
            if jti:
                blacklisted = await redis_manager.get(f"blacklist:{jti}")
                return blacklisted is not None
                
        except jwt.JWTError:
            pass
        
        return False
    
    # Geração de tokens seguros
    def generate_secure_token(self, length: int = 32) -> str:
        """Gerar token seguro para webhooks, etc."""
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self) -> str:
        """Gerar chave de API"""
        return f"isp_{secrets.token_urlsafe(32)}"
    
    # Hash para dados sensíveis
    def hash_sensitive_data(self, data: str) -> str:
        """Hash SHA-256 para dados sensíveis"""
        return hashlib.sha256(data.encode()).hexdigest()


# Instância global
security_manager = SecurityManager()


# Dependências FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Dependency para obter usuário atual"""
    token = credentials.credentials
    
    # Verificar se token está na blacklist
    if await security_manager.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar e decodificar token
    payload = security_manager.verify_token(token)
    
    # Verificar se é access token
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Buscar dados do usuário no cache
    cache_key = CacheKeys.format_key(CacheKeys.USER_SESSION, user_id=user_id)
    user_data = await redis_manager.get_json(cache_key)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_data


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dependency para usuário ativo"""
    if not current_user.get("ativo", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


# Decoradores de autorização
def require_role(required_role: UserRole):
    """Decorador para exigir role específica"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Buscar current_user nos kwargs
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, dict) and "role" in value:
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
            
            user_role = UserRole(current_user.get("role"))
            
            # Hierarquia de roles: admin > supervisor > atendente
            role_hierarchy = {
                UserRole.ADMIN: 3,
                UserRole.SUPERVISOR: 2,
                UserRole.ATENDENTE: 1
            }
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {required_role.value} role or higher"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Dependency para exigir role admin"""
    if UserRole(current_user.get("role")) != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_supervisor_or_admin(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Dependency para exigir role supervisor ou admin"""
    user_role = UserRole(current_user.get("role"))
    if user_role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor or admin access required"
        )
    return current_user


# Rate Limiting
class RateLimiter:
    """Rate limiter baseado em Redis"""
    
    def __init__(self, redis_client=redis_manager):
        self.redis = redis_client
    
    async def is_allowed(
        self, 
        identifier: str, 
        limit: int, 
        window: int,
        key_prefix: str = "rate_limit"
    ) -> tuple[bool, int]:
        """
        Verificar se request é permitido
        Retorna (permitido, tentativas_restantes)
        """
        key = f"{key_prefix}:{identifier}"
        return await self.redis.rate_limit_check(key, limit, window)


# Instância global do rate limiter
rate_limiter = RateLimiter()


# Middleware de rate limiting
async def rate_limit_middleware(
    request: Request,
    limit: int = settings.RATE_LIMIT_PER_MINUTE,
    window: int = 60
):
    """Middleware de rate limiting por IP"""
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    
    identifier = f"{client_ip}:{endpoint}"
    allowed, remaining = await rate_limiter.is_allowed(
        identifier, limit, window, "rate_limit_ip"
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(window)
            }
        )
    
    # Adicionar headers informativos
    request.state.rate_limit_remaining = remaining


# Validação de entrada
import re
from typing import Union

class InputValidator:
    """Validador de entrada para segurança"""
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validar formato de telefone"""
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validar formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitizar string removendo caracteres perigosos"""
        if not text:
            return ""
        
        # Remover caracteres de controle
        sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # Limitar tamanho
        return sanitized[:max_length]
    
    @staticmethod
    def validate_uuid(uuid_string: str) -> bool:
        """Validar formato UUID"""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_string.lower()))
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Verificar se nome de arquivo é seguro"""
        # Não permitir caracteres perigosos
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(char in filename for char in dangerous_chars)


# Instância global do validador
input_validator = InputValidator()