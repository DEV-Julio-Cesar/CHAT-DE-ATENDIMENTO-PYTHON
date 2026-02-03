"""
Sistema de Autenticação JWT Completo
CIANET PROVEDOR - v3.0

Features:
- JWT Access Tokens (curta duração)
- Refresh Tokens (longa duração)
- Sessões com rastreamento de dispositivos
- Blacklist de tokens
- Permissões granulares por role
- Rate limiting por IP
- Auditoria completa
"""
import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from functools import wraps

import jwt
import bcrypt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.redis_client import redis_manager

logger = logging.getLogger(__name__)

# Security bearer
security = HTTPBearer(auto_error=False)


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class TokenPayload(BaseModel):
    """Payload do JWT Token"""
    sub: str  # user_id
    email: str
    role: str
    permissions: List[str] = []
    session_id: Optional[str] = None
    jti: str  # JWT ID único
    type: str = "access"  # access ou refresh
    exp: datetime
    iat: datetime


class UserSession(BaseModel):
    """Sessão do usuário"""
    session_id: str
    user_id: int
    email: str
    nome: str
    role: str
    permissions: List[str]
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    expires_at: datetime


class AuthTokens(BaseModel):
    """Par de tokens retornado no login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos
    session_id: str


# ============================================================================
# GERENCIADOR DE AUTENTICAÇÃO
# ============================================================================

class AuthManager:
    """
    Gerenciador central de autenticação JWT
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Prefixos de cache Redis
        self.CACHE_PREFIX = "auth:"
        self.SESSION_PREFIX = f"{self.CACHE_PREFIX}session:"
        self.BLACKLIST_PREFIX = f"{self.CACHE_PREFIX}blacklist:"
        self.REFRESH_PREFIX = f"{self.CACHE_PREFIX}refresh:"
        self.USER_SESSIONS_PREFIX = f"{self.CACHE_PREFIX}user_sessions:"
    
    # =========================================================================
    # HASH DE SENHAS
    # =========================================================================
    
    def hash_password(self, password: str) -> str:
        """Gerar hash bcrypt da senha"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar senha contra hash"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    # =========================================================================
    # GERAÇÃO DE TOKENS
    # =========================================================================
    
    def _generate_jti(self) -> str:
        """Gerar ID único para JWT"""
        return secrets.token_urlsafe(32)
    
    def _generate_session_id(self) -> str:
        """Gerar ID de sessão"""
        return f"sess_{secrets.token_urlsafe(24)}"
    
    def create_access_token(
        self,
        user_id: int,
        email: str,
        role: str,
        permissions: List[str],
        session_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, str]:
        """
        Criar access token JWT
        
        Returns:
            Tuple[token, jti]
        """
        jti = self._generate_jti()
        expire = datetime.now(timezone.utc) + (expires_delta or self.access_token_expire)
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "permissions": permissions,
            "session_id": session_id,
            "jti": jti,
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": "cianet-auth",
            "aud": "cianet-api"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti
    
    def create_refresh_token(
        self,
        user_id: int,
        session_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, str]:
        """
        Criar refresh token JWT
        
        Returns:
            Tuple[token, jti]
        """
        jti = self._generate_jti()
        expire = datetime.now(timezone.utc) + (expires_delta or self.refresh_token_expire)
        
        payload = {
            "sub": str(user_id),
            "session_id": session_id,
            "jti": jti,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": "cianet-auth"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti
    
    async def create_auth_tokens(
        self,
        user_id: int,
        email: str,
        nome: str,
        role: str,
        permissions: List[str],
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuthTokens:
        """
        Criar par completo de tokens (access + refresh) e sessão
        """
        session_id = self._generate_session_id()
        
        # Criar tokens
        access_token, access_jti = self.create_access_token(
            user_id=user_id,
            email=email,
            role=role,
            permissions=permissions,
            session_id=session_id
        )
        
        refresh_token, refresh_jti = self.create_refresh_token(
            user_id=user_id,
            session_id=session_id
        )
        
        # Criar sessão no Redis
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "email": email,
            "nome": nome,
            "role": role,
            "permissions": permissions,
            "access_jti": access_jti,
            "refresh_jti": refresh_jti,
            "device_info": device_info,
            "ip_address": ip_address,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + self.refresh_token_expire).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        
        # Salvar sessão
        session_ttl = int(self.refresh_token_expire.total_seconds())
        await redis_manager.set_json(
            f"{self.SESSION_PREFIX}{session_id}",
            session_data,
            ex=session_ttl
        )
        
        # Adicionar à lista de sessões do usuário
        await redis_manager.sadd(
            f"{self.USER_SESSIONS_PREFIX}{user_id}",
            session_id
        )
        await redis_manager.expire(
            f"{self.USER_SESSIONS_PREFIX}{user_id}",
            session_ttl
        )
        
        # Salvar refresh token hash
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        await redis_manager.set(
            f"{self.REFRESH_PREFIX}{refresh_hash}",
            session_id,
            ex=session_ttl
        )
        
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(self.access_token_expire.total_seconds()),
            session_id=session_id
        )
    
    # =========================================================================
    # VALIDAÇÃO DE TOKENS
    # =========================================================================
    
    def decode_token(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        """Decodificar e validar token JWT"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": verify_exp},
                audience="cianet-api" if verify_exp else None
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    async def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verificar access token completo"""
        # Decodificar
        payload = self.decode_token(token)
        
        # Verificar tipo
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tipo de token inválido",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verificar blacklist
        jti = payload.get("jti")
        if jti and await self.is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revogado",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verificar sessão
        session_id = payload.get("session_id")
        if session_id:
            session = await self.get_session(session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sessão inválida ou expirada",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Atualizar última atividade
            await self.update_session_activity(session_id)
        
        return payload
    
    async def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Verificar refresh token"""
        # Decodificar
        payload = self.decode_token(token)
        
        # Verificar tipo
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tipo de token inválido"
            )
        
        # Verificar se refresh token existe no Redis
        refresh_hash = hashlib.sha256(token.encode()).hexdigest()
        session_id = await redis_manager.get(f"{self.REFRESH_PREFIX}{refresh_hash}")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou revogado"
            )
        
        # Verificar sessão
        session = await self.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão expirada"
            )
        
        return {**payload, "session_data": session}
    
    # =========================================================================
    # GERENCIAMENTO DE SESSÕES
    # =========================================================================
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obter dados da sessão"""
        return await redis_manager.get_json(f"{self.SESSION_PREFIX}{session_id}")
    
    async def update_session_activity(self, session_id: str) -> None:
        """Atualizar última atividade da sessão"""
        session = await self.get_session(session_id)
        if session:
            session["last_activity"] = datetime.now(timezone.utc).isoformat()
            ttl = await redis_manager.ttl(f"{self.SESSION_PREFIX}{session_id}")
            if ttl > 0:
                await redis_manager.set_json(
                    f"{self.SESSION_PREFIX}{session_id}",
                    session,
                    ex=ttl
                )
    
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Obter todas as sessões ativas do usuário"""
        session_ids = await redis_manager.smembers(f"{self.USER_SESSIONS_PREFIX}{user_id}")
        sessions = []
        
        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)
            else:
                # Limpar sessão expirada da lista
                await redis_manager.srem(f"{self.USER_SESSIONS_PREFIX}{user_id}", session_id)
        
        return sessions
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revogar uma sessão específica"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Blacklist do access token
        access_jti = session.get("access_jti")
        if access_jti:
            await self.blacklist_token(access_jti, int(self.access_token_expire.total_seconds()))
        
        # Remover refresh token
        refresh_jti = session.get("refresh_jti")
        if refresh_jti:
            await redis_manager.delete(f"{self.REFRESH_PREFIX}{refresh_jti}")
        
        # Remover sessão
        user_id = session.get("user_id")
        await redis_manager.delete(f"{self.SESSION_PREFIX}{session_id}")
        
        if user_id:
            await redis_manager.srem(f"{self.USER_SESSIONS_PREFIX}{user_id}", session_id)
        
        logger.info(f"Session revoked: {session_id}")
        return True
    
    async def revoke_all_user_sessions(self, user_id: int, except_session: Optional[str] = None) -> int:
        """Revogar todas as sessões do usuário"""
        sessions = await self.get_user_sessions(user_id)
        count = 0
        
        for session in sessions:
            session_id = session.get("session_id")
            if session_id and session_id != except_session:
                await self.revoke_session(session_id)
                count += 1
        
        return count
    
    # =========================================================================
    # BLACKLIST DE TOKENS
    # =========================================================================
    
    async def blacklist_token(self, jti: str, ttl: int) -> None:
        """Adicionar token à blacklist"""
        await redis_manager.set(f"{self.BLACKLIST_PREFIX}{jti}", "1", ex=ttl)
    
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Verificar se token está na blacklist"""
        return await redis_manager.exists(f"{self.BLACKLIST_PREFIX}{jti}")
    
    # =========================================================================
    # REFRESH TOKEN ROTATION
    # =========================================================================
    
    async def refresh_tokens(self, refresh_token: str) -> AuthTokens:
        """
        Rotacionar tokens usando refresh token
        Implementa refresh token rotation para segurança
        """
        # Validar refresh token
        payload = await self.verify_refresh_token(refresh_token)
        session_data = payload.get("session_data", {})
        
        user_id = int(payload.get("sub"))
        session_id = payload.get("session_id")
        
        # Invalidar refresh token antigo
        old_refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        await redis_manager.delete(f"{self.REFRESH_PREFIX}{old_refresh_hash}")
        
        # Criar novos tokens
        access_token, access_jti = self.create_access_token(
            user_id=user_id,
            email=session_data.get("email", ""),
            role=session_data.get("role", "atendente"),
            permissions=session_data.get("permissions", []),
            session_id=session_id
        )
        
        new_refresh_token, refresh_jti = self.create_refresh_token(
            user_id=user_id,
            session_id=session_id
        )
        
        # Atualizar sessão
        session_data["access_jti"] = access_jti
        session_data["refresh_jti"] = refresh_jti
        session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        ttl = await redis_manager.ttl(f"{self.SESSION_PREFIX}{session_id}")
        if ttl > 0:
            await redis_manager.set_json(
                f"{self.SESSION_PREFIX}{session_id}",
                session_data,
                ex=ttl
            )
        
        # Salvar novo refresh token
        new_refresh_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        await redis_manager.set(
            f"{self.REFRESH_PREFIX}{new_refresh_hash}",
            session_id,
            ex=ttl
        )
        
        return AuthTokens(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=int(self.access_token_expire.total_seconds()),
            session_id=session_id
        )


# Instância global
auth_manager = AuthManager()


# ============================================================================
# DEPENDENCIES FASTAPI
# ============================================================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency para obter usuário atual a partir do token JWT
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    payload = await auth_manager.verify_access_token(token)
    
    return {
        "id": int(payload.get("sub")),
        "email": payload.get("email"),
        "role": payload.get("role"),
        "permissions": payload.get("permissions", []),
        "session_id": payload.get("session_id")
    }


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dependency para usuário ativo"""
    return current_user


def require_permissions(*required_permissions: str):
    """
    Decorator/Dependency para exigir permissões específicas
    
    Uso:
        @router.get("/admin")
        async def admin_route(user: dict = Depends(require_permissions("admin.view"))):
            ...
    """
    async def permission_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_permissions = set(current_user.get("permissions", []))
        required = set(required_permissions)
        
        if not required.issubset(user_permissions):
            missing = required - user_permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissões insuficientes. Necessário: {', '.join(missing)}"
            )
        
        return current_user
    
    return permission_checker


def require_role(minimum_role: str):
    """
    Dependency para exigir role mínima
    
    Hierarquia: admin > supervisor > atendente
    """
    role_hierarchy = {
        "atendente": 1,
        "supervisor": 2,
        "admin": 3
    }
    
    async def role_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_role = current_user.get("role", "atendente")
        
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(minimum_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role insuficiente. Necessário: {minimum_role} ou superior"
            )
        
        return current_user
    
    return role_checker


# Aliases convenientes
require_admin = require_role("admin")
require_supervisor = require_role("supervisor")
require_atendente = require_role("atendente")
