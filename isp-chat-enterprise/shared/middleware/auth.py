#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Middleware de Autenticação
Middleware para validação de tokens JWT e controle de acesso
"""

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging
import jwt
from datetime import datetime

from shared.utils.database import get_db
from shared.models.user import User, UserRole
from shared.config.settings import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Configurar esquema de segurança HTTP Bearer
security = HTTPBearer(auto_error=False)

class AuthMiddleware:
    """
    Middleware de Autenticação
    
    Responsável por:
    - Validar tokens JWT
    - Extrair usuário do token
    - Controlar acesso baseado em papéis
    - Rate limiting por usuário
    """
    
    async def decode_jwt_token(self, token: str) -> Optional[dict]:
        """
        Decodificar token JWT
        
        Args:
            token: Token JWT
            
        Returns:
            Payload do token ou None se inválido
        """
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Verificar expiração
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                return None
                
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token JWT inválido: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao decodificar token: {e}")
            return None
    
    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """
        Buscar usuário por ID
        
        Args:
            db: Sessão do banco
            user_id: ID do usuário
            
        Returns:
            Usuário ou None se não encontrado
        """
        try:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário {user_id}: {e}")
            return None
    
    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """
        Buscar usuário por username
        
        Args:
            db: Sessão do banco
            username: Nome de usuário
            
        Returns:
            Usuário ou None se não encontrado
        """
        try:
            result = await db.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por username {username}: {e}")
            return None
    
    async def get_current_user_optional(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> Optional[User]:
        """
        Obter usuário atual (opcional - não falha se não autenticado)
        
        Args:
            credentials: Credenciais HTTP Bearer
            db: Sessão do banco de dados
            
        Returns:
            Usuário atual ou None se não autenticado
        """
        if not credentials:
            return None
        
        try:
            # Decodificar token
            payload = await self.decode_jwt_token(credentials.credentials)
            if not payload:
                return None
            
            # Extrair identificador do usuário
            user_identifier = payload.get("sub")
            if not user_identifier:
                return None
            
            # Buscar usuário - primeiro tentar por ID, depois por username
            user = None
            
            # Se o identificador parece ser um UUID, buscar por ID
            if len(user_identifier) == 36 and user_identifier.count('-') == 4:
                user = await self.get_user_by_id(db, user_identifier)
            
            # Se não encontrou por ID ou não é UUID, buscar por username
            if not user:
                user = await self.get_user_by_username(db, user_identifier)
            
            return user
            
        except Exception as e:
            logger.warning(f"Token inválido (opcional): {e}")
            return None
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """
        Obter usuário atual (obrigatório - falha se não autenticado)
        
        Args:
            credentials: Credenciais HTTP Bearer
            db: Sessão do banco de dados
            
        Returns:
            Usuário atual
            
        Raises:
            HTTPException: Se não autenticado ou token inválido
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de acesso necessário",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            # Decodificar token
            payload = await self.decode_jwt_token(credentials.credentials)
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Extrair identificador do usuário
            user_identifier = payload.get("sub")
            if not user_identifier:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token malformado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Buscar usuário - primeiro tentar por ID, depois por username
            user = None
            
            logger.info(f"🔍 Buscando usuário: {user_identifier}")
            logger.info(f"🔍 Token payload completo: {payload}")
            
            # Se o identificador parece ser um UUID, buscar por ID
            if len(user_identifier) == 36 and user_identifier.count('-') == 4:
                logger.info(f"🆔 Tentando buscar por ID: {user_identifier}")
                user = await self.get_user_by_id(db, user_identifier)
                if user:
                    logger.info(f"✅ Usuário encontrado por ID: {user.username}")
            
            # Se não encontrou por ID ou não é UUID, buscar por username
            if not user:
                logger.info(f"👤 Tentando buscar por username: {user_identifier}")
                user = await self.get_user_by_username(db, user_identifier)
                if user:
                    logger.info(f"✅ Usuário encontrado por username: {user.username}")
                else:
                    logger.warning(f"❌ Usuário não encontrado: {user_identifier}")
                    logger.warning(f"❌ Tentou buscar por ID: {len(user_identifier) == 36 and user_identifier.count('-') == 4}")
                    logger.warning(f"❌ Payload: {payload}")
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário não encontrado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário inativo",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Erro na autenticação",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def get_current_active_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """
        Obter usuário atual ativo
        
        Args:
            credentials: Credenciais HTTP Bearer
            db: Sessão do banco de dados
            
        Returns:
            Usuário ativo
            
        Raises:
            HTTPException: Se usuário não está ativo
        """
        current_user = await self.get_current_user(credentials, db)
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário inativo"
            )
        return current_user
    
    def has_role(self, user: User, required_role: UserRole) -> bool:
        """
        Verificar se usuário tem papel específico
        
        Args:
            user: Usuário
            required_role: Papel necessário
            
        Returns:
            True se tem o papel
        """
        # Hierarquia de papéis: ADMIN > SUPERVISOR > AGENT > VIEWER
        role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.AGENT: 1,
            UserRole.SUPERVISOR: 2,
            UserRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def has_permission(self, user: User, permission: str) -> bool:
        """
        Verificar se usuário tem permissão específica
        
        Args:
            user: Usuário
            permission: Permissão necessária
            
        Returns:
            True se tem a permissão
        """
        # Implementação básica baseada em papéis
        role_permissions = {
            UserRole.ADMIN: ["*"],  # Todas as permissões
            UserRole.SUPERVISOR: [
                "chat.read", "chat.write", "chat.assign", 
                "stats.read", "users.read"
            ],
            UserRole.AGENT: [
                "chat.read", "chat.write", "chat.own"
            ],
            UserRole.VIEWER: [
                "chat.read_own"
            ]
        }
        
        user_permissions = role_permissions.get(user.role, [])
        
        # Admin tem todas as permissões
        if "*" in user_permissions:
            return True
        
        return permission in user_permissions
    
    def require_role(self, required_role: UserRole):
        """
        Dependency para exigir papel específico
        
        Args:
            required_role: Papel necessário
            
        Returns:
            Dependency function
        """
        async def role_dependency(
            credentials: HTTPAuthorizationCredentials = Depends(security),
            db: AsyncSession = Depends(get_db)
        ) -> User:
            current_user = await self.get_current_user(credentials, db)
            if not self.has_role(current_user, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Papel '{required_role.value}' necessário"
                )
            
            return current_user
        
        return role_dependency
    
    def require_roles(self, required_roles: List[UserRole]):
        """
        Dependency para exigir um dos papéis especificados
        
        Args:
            required_roles: Lista de papéis aceitos
            
        Returns:
            Dependency function
        """
        async def roles_dependency(
            credentials: HTTPAuthorizationCredentials = Depends(security),
            db: AsyncSession = Depends(get_db)
        ) -> User:
            current_user = await self.get_current_user(credentials, db)
            has_any_role = any(
                self.has_role(current_user, role) 
                for role in required_roles
            )
            
            if not has_any_role:
                roles_str = ", ".join([role.value for role in required_roles])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Um dos seguintes papéis é necessário: {roles_str}"
                )
            
            return current_user
        
        return roles_dependency
        
        return roles_dependency
    
    def require_permission(self, permission: str):
        """
        Dependency para exigir permissão específica
        
        Args:
            permission: Permissão necessária
            
        Returns:
            Dependency function
        """
        async def permission_dependency(
            credentials: HTTPAuthorizationCredentials = Depends(security),
            db: AsyncSession = Depends(get_db)
        ) -> User:
            current_user = await self.get_current_user(credentials, db)
            if not self.has_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permissão '{permission}' necessária"
                )
            
            return current_user
        
        return permission_dependency
    
    def require_admin(self):
        """
        Dependency para exigir papel de administrador
        
        Returns:
            Dependency function
        """
        return self.require_role(UserRole.ADMIN)
    
    def require_supervisor_or_admin(self):
        """
        Dependency para exigir papel de supervisor ou admin
        
        Returns:
            Dependency function
        """
        return self.require_roles([UserRole.ADMIN, UserRole.SUPERVISOR])
    
    def require_agent_or_above(self):
        """
        Dependency para exigir papel de agente ou superior
        
        Returns:
            Dependency function
        """
        return self.require_roles([UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.AGENT])

# Instância global do middleware
auth_middleware = AuthMiddleware()

# Aliases para facilitar importação
get_current_user = auth_middleware.get_current_user
get_current_user_optional = auth_middleware.get_current_user_optional
get_current_active_user = auth_middleware.get_current_active_user
require_role = auth_middleware.require_role
require_roles = auth_middleware.require_roles
require_permission = auth_middleware.require_permission
require_admin = auth_middleware.require_admin
require_supervisor_or_admin = auth_middleware.require_supervisor_or_admin
require_agent_or_above = auth_middleware.require_agent_or_above

# Dependency shortcuts mais comuns
RequireAdmin = Depends(auth_middleware.require_admin())
RequireSupervisorOrAdmin = Depends(auth_middleware.require_supervisor_or_admin())
RequireAgentOrAbove = Depends(auth_middleware.require_agent_or_above())
CurrentUser = Depends(get_current_user)
CurrentUserOptional = Depends(get_current_user_optional)
CurrentActiveUser = Depends(get_current_active_user)