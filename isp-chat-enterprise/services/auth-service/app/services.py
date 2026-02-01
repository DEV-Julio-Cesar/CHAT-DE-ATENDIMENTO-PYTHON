#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviços de Autenticação
Lógica de negócio para autenticação, autorização e gerenciamento de usuários
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import JWTError, jwt

from shared.config.settings import settings
from shared.models.user import User, UserRole
from shared.utils.memory_cache import get_cache
from schemas import (
    LoginRequest, UserCreateRequest, UserUpdateRequest, PasswordChangeRequest,
    UserResponse, LoginResponse, TokenValidationResponse, UserPermissions
)

# Configurar logging
logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Erro de autenticação"""
    pass

class AuthorizationError(Exception):
    """Erro de autorização"""
    pass

class UserNotFoundError(Exception):
    """Usuário não encontrado"""
    pass

class UserAlreadyExistsError(Exception):
    """Usuário já existe"""
    pass

class AuthService:
    """
    Serviço de Autenticação e Autorização
    
    Responsável por:
    - Autenticação de usuários (login/logout)
    - Geração e validação de tokens JWT
    - Gerenciamento de usuários (CRUD)
    - Controle de permissões
    - Rate limiting de login
    - Cache de sessões
    """
    
    def __init__(self):
        # Configurar criptografia de senhas (compatível com Node.js)
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=10  # Mesmo padrão do Node.js
        )
        
        # Configurações JWT
        self.jwt_secret = settings.JWT_SECRET
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.jwt_expire_hours = settings.JWT_EXPIRE_HOURS
        
        # Configurações de rate limiting
        self.max_login_attempts = settings.MAX_LOGIN_ATTEMPTS
        self.lockout_duration = settings.LOCKOUT_DURATION_MINUTES
        
        # Cache para sessões e rate limiting
        self.cache = None
    
    async def _get_cache(self):
        """Obter instância do cache"""
        if self.cache is None:
            self.cache = await get_cache()
        return self.cache
    
    # === MÉTODOS DE CRIPTOGRAFIA ===
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verificar senha usando bcrypt (compatível com Node.js)
        
        Args:
            plain_password: Senha em texto plano
            hashed_password: Hash da senha
            
        Returns:
            True se a senha está correta
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Erro ao verificar senha: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """
        Gerar hash da senha usando bcrypt
        
        Args:
            password: Senha em texto plano
            
        Returns:
            Hash da senha
        """
        return self.pwd_context.hash(password)
    
    # === MÉTODOS JWT ===
    
    def create_access_token(self, user: User, remember_me: bool = False) -> Dict[str, Any]:
        """
        Criar token JWT de acesso
        
        Args:
            user: Usuário para o qual criar o token
            remember_me: Se deve criar token de longa duração
            
        Returns:
            Dicionário com token e informações
        """
        # Definir tempo de expiração
        expire_hours = self.jwt_expire_hours
        if remember_me:
            expire_hours = expire_hours * 7  # 7x mais tempo se "lembrar"
        
        expire_time = datetime.utcnow() + timedelta(hours=expire_hours)
        
        # Dados do token
        token_data = {
            "sub": user.username,  # Subject (identificador principal)
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "iat": datetime.utcnow(),  # Issued at
            "exp": expire_time,  # Expiration
            "jti": str(uuid.uuid4()),  # JWT ID (único)
            "type": "access_token"
        }
        
        # Gerar token
        token = jwt.encode(token_data, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expire_hours * 3600,  # Em segundos
            "expires_at": expire_time,
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decodificar e validar token JWT
        
        Args:
            token: Token JWT
            
        Returns:
            Dados do token decodificado
            
        Raises:
            JWTError: Se o token é inválido
        """
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            
            # Verificar se é token de acesso
            if payload.get("type") != "access_token":
                raise JWTError("Tipo de token inválido")
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Token inválido: {e}")
            raise
    
    # === MÉTODOS DE RATE LIMITING ===
    
    async def check_login_attempts(self, identifier: str) -> bool:
        """
        Verificar se o usuário não excedeu tentativas de login
        
        Args:
            identifier: Username, email ou IP
            
        Returns:
            True se pode tentar login
        """
        cache = await self._get_cache()
        key = f"login_attempts:{identifier}"
        
        attempts = await cache.get(key)
        if attempts is None:
            return True
        
        return int(attempts) < self.max_login_attempts
    
    async def record_login_attempt(self, identifier: str, success: bool):
        """
        Registrar tentativa de login
        
        Args:
            identifier: Username, email ou IP
            success: Se o login foi bem-sucedido
        """
        cache = await self._get_cache()
        key = f"login_attempts:{identifier}"
        
        if success:
            # Limpar tentativas em caso de sucesso
            await cache.delete(key)
        else:
            # Incrementar tentativas falhadas
            current = await cache.get(key)
            attempts = int(current) + 1 if current else 1
            
            # Definir TTL baseado na duração do lockout
            ttl = self.lockout_duration * 60  # Converter para segundos
            await cache.set(key, str(attempts), ex=ttl)
            
            logger.warning(f"Tentativa de login falhada para {identifier}: {attempts}/{self.max_login_attempts}")
    
    async def get_remaining_lockout_time(self, identifier: str) -> int:
        """
        Obter tempo restante de bloqueio em segundos
        
        Args:
            identifier: Username, email ou IP
            
        Returns:
            Segundos restantes de bloqueio (0 se não bloqueado)
        """
        cache = await self._get_cache()
        key = f"login_attempts:{identifier}"
        
        ttl = await cache.ttl(key)
        return max(0, ttl) if ttl > 0 else 0
    
    # === MÉTODOS DE USUÁRIO ===
    
    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """
        Buscar usuário por username
        
        Args:
            db: Sessão do banco de dados
            username: Nome de usuário
            
        Returns:
            Usuário encontrado ou None
        """
        try:
            result = await db.execute(
                select(User).where(User.username == username.lower())
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por username {username}: {e}")
            return None
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        Buscar usuário por email
        
        Args:
            db: Sessão do banco de dados
            email: Email do usuário
            
        Returns:
            Usuário encontrado ou None
        """
        try:
            result = await db.execute(
                select(User).where(User.email == email.lower())
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por email {email}: {e}")
            return None
    
    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """
        Buscar usuário por ID
        
        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário
            
        Returns:
            Usuário encontrado ou None
        """
        try:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por ID {user_id}: {e}")
            return None
    
    async def get_user_by_login(self, db: AsyncSession, login: str) -> Optional[User]:
        """
        Buscar usuário por username ou email
        
        Args:
            db: Sessão do banco de dados
            login: Username ou email
            
        Returns:
            Usuário encontrado ou None
        """
        try:
            # Tentar buscar por username ou email
            result = await db.execute(
                select(User).where(
                    or_(
                        User.username == login.lower(),
                        User.email == login.lower()
                    )
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por login {login}: {e}")
            return None
    
    # === MÉTODOS DE AUTENTICAÇÃO ===
    
    async def authenticate_user(
        self, 
        db: AsyncSession, 
        login_data: LoginRequest,
        client_ip: str = None
    ) -> User:
        """
        Autenticar usuário
        
        Args:
            db: Sessão do banco de dados
            login_data: Dados de login
            client_ip: IP do cliente (para rate limiting)
            
        Returns:
            Usuário autenticado
            
        Raises:
            AuthenticationError: Se a autenticação falhar
        """
        identifier = login_data.username.lower()
        
        # Verificar rate limiting
        if not await self.check_login_attempts(identifier):
            remaining_time = await self.get_remaining_lockout_time(identifier)
            raise AuthenticationError(
                f"Muitas tentativas de login. Tente novamente em {remaining_time // 60} minutos."
            )
        
        # Buscar usuário
        user = await self.get_user_by_login(db, login_data.username)
        
        if not user:
            await self.record_login_attempt(identifier, False)
            raise AuthenticationError("Credenciais inválidas")
        
        # Verificar se usuário está ativo
        if not user.is_active:
            await self.record_login_attempt(identifier, False)
            raise AuthenticationError("Usuário inativo")
        
        # Verificar senha
        if not self.verify_password(login_data.password, user.password_hash):
            await self.record_login_attempt(identifier, False)
            raise AuthenticationError("Credenciais inválidas")
        
        # Sucesso - limpar tentativas e atualizar último login
        await self.record_login_attempt(identifier, True)
        
        user.update_last_login()
        await db.commit()
        
        logger.info(f"Login bem-sucedido para usuário: {user.username}")
        return user
    
    async def login(
        self, 
        db: AsyncSession, 
        login_data: LoginRequest,
        client_ip: str = None
    ) -> LoginResponse:
        """
        Realizar login completo
        
        Args:
            db: Sessão do banco de dados
            login_data: Dados de login
            client_ip: IP do cliente
            
        Returns:
            Resposta de login com token
        """
        # Autenticar usuário
        user = await self.authenticate_user(db, login_data, client_ip)
        
        # Criar token
        token_info = self.create_access_token(user, login_data.remember_me)
        
        # Converter usuário para response
        user_response = self._user_to_response(user)
        
        # Criar resposta
        return LoginResponse(
            access_token=token_info["access_token"],
            token_type=token_info["token_type"],
            expires_in=token_info["expires_in"],
            expires_at=token_info["expires_at"],
            user=user_response
        )
    
    async def validate_token(self, db: AsyncSession, token: str) -> TokenValidationResponse:
        """
        Validar token JWT
        
        Args:
            db: Sessão do banco de dados
            token: Token JWT
            
        Returns:
            Resposta de validação
        """
        try:
            # Decodificar token
            payload = self.decode_token(token)
            
            # Buscar usuário
            user_id = payload.get("user_id")
            user = await self.get_user_by_id(db, user_id)
            
            if not user or not user.is_active:
                return TokenValidationResponse(valid=False)
            
            # Token válido
            return TokenValidationResponse(
                valid=True,
                user=self._user_to_response(user),
                expires_at=datetime.fromtimestamp(payload["exp"])
            )
            
        except JWTError:
            return TokenValidationResponse(valid=False)
    
    async def get_current_user(self, db: AsyncSession, token: str) -> User:
        """
        Obter usuário atual a partir do token
        
        Args:
            db: Sessão do banco de dados
            token: Token JWT
            
        Returns:
            Usuário atual
            
        Raises:
            AuthenticationError: Se o token é inválido
        """
        try:
            payload = self.decode_token(token)
            user_id = payload.get("user_id")
            
            user = await self.get_user_by_id(db, user_id)
            
            if not user or not user.is_active:
                raise AuthenticationError("Token inválido ou usuário inativo")
            
            return user
            
        except JWTError as e:
            raise AuthenticationError(f"Token inválido: {e}")
    
    # === MÉTODOS DE GERENCIAMENTO DE USUÁRIOS ===
    
    async def create_user(
        self, 
        db: AsyncSession, 
        user_data: UserCreateRequest,
        created_by: User = None
    ) -> User:
        """
        Criar novo usuário
        
        Args:
            db: Sessão do banco de dados
            user_data: Dados do usuário
            created_by: Usuário que está criando (para auditoria)
            
        Returns:
            Usuário criado
            
        Raises:
            UserAlreadyExistsError: Se usuário já existe
        """
        try:
            # Verificar se username já existe
            existing_user = await self.get_user_by_username(db, user_data.username)
            if existing_user:
                raise UserAlreadyExistsError(f"Username '{user_data.username}' já existe")
            
            # Verificar se email já existe
            existing_email = await self.get_user_by_email(db, user_data.email)
            if existing_email:
                raise UserAlreadyExistsError(f"Email '{user_data.email}' já está em uso")
            
            # Criar hash da senha
            password_hash = self.hash_password(user_data.password)
            
            # Criar usuário
            user = User(
                username=user_data.username.lower(),
                email=user_data.email.lower(),
                password_hash=password_hash,
                role=UserRole(user_data.role.value),
                is_active=user_data.is_active,
                metadata=user_data.metadata or {},
                settings=user_data.settings or {
                    "notifications": True,
                    "theme": "light",
                    "language": "pt-BR"
                }
            )
            
            # Definir metadados JSON
            user.metadata_dict = user_data.metadata or {}
            user.settings_dict = user_data.settings or {
                "notifications": True,
                "theme": "light",
                "language": "pt-BR"
            }
            
            # Adicionar informações de auditoria
            if created_by:
                user.update_metadata("created_by", str(created_by.id))
                user.update_metadata("created_by_username", created_by.username)
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Usuário criado: {user.username} por {created_by.username if created_by else 'sistema'}")
            return user
            
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Erro de integridade ao criar usuário: {e}")
            raise UserAlreadyExistsError("Usuário já existe")
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao criar usuário: {e}")
            raise
    
    async def update_user(
        self,
        db: AsyncSession,
        user_id: str,
        user_data: UserUpdateRequest,
        updated_by: User = None
    ) -> User:
        """
        Atualizar usuário existente
        
        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário
            user_data: Dados para atualização
            updated_by: Usuário que está atualizando
            
        Returns:
            Usuário atualizado
            
        Raises:
            UserNotFoundError: Se usuário não existe
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundError(f"Usuário com ID {user_id} não encontrado")
        
        try:
            # Atualizar campos fornecidos
            if user_data.username is not None:
                # Verificar se novo username já existe
                existing = await self.get_user_by_username(db, user_data.username)
                if existing and existing.id != user.id:
                    raise UserAlreadyExistsError(f"Username '{user_data.username}' já existe")
                user.username = user_data.username.lower()
            
            if user_data.email is not None:
                # Verificar se novo email já existe
                existing = await self.get_user_by_email(db, user_data.email)
                if existing and existing.id != user.id:
                    raise UserAlreadyExistsError(f"Email '{user_data.email}' já está em uso")
                user.email = user_data.email.lower()
            
            if user_data.password is not None:
                user.password_hash = self.hash_password(user_data.password)
            
            if user_data.role is not None:
                user.role = UserRole(user_data.role.value)
            
            if user_data.is_active is not None:
                user.is_active = user_data.is_active
            
            if user_data.is_verified is not None:
                user.is_verified = user_data.is_verified
            
            if user_data.metadata is not None:
                user.metadata_dict = user_data.metadata
            
            if user_data.settings is not None:
                user.settings_dict = user_data.settings
            
            # Adicionar informações de auditoria
            if updated_by:
                user.update_metadata("updated_by", str(updated_by.id))
                user.update_metadata("updated_by_username", updated_by.username)
                user.update_metadata("updated_at", datetime.utcnow().isoformat())
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Usuário atualizado: {user.username} por {updated_by.username if updated_by else 'sistema'}")
            return user
            
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Erro de integridade ao atualizar usuário: {e}")
            raise UserAlreadyExistsError("Dados já existem")
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao atualizar usuário: {e}")
            raise
    
    async def change_password(
        self,
        db: AsyncSession,
        user: User,
        password_data: PasswordChangeRequest
    ) -> bool:
        """
        Alterar senha do usuário
        
        Args:
            db: Sessão do banco de dados
            user: Usuário
            password_data: Dados da alteração de senha
            
        Returns:
            True se alteração foi bem-sucedida
            
        Raises:
            AuthenticationError: Se senha atual está incorreta
        """
        # Verificar senha atual
        if not self.verify_password(password_data.current_password, user.password_hash):
            raise AuthenticationError("Senha atual incorreta")
        
        try:
            # Definir nova senha
            user.password_hash = self.hash_password(password_data.new_password)
            
            # Adicionar metadados
            user.update_metadata("password_changed_at", datetime.utcnow().isoformat())
            
            await db.commit()
            
            logger.info(f"Senha alterada para usuário: {user.username}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao alterar senha: {e}")
            raise
    
    async def list_users(
        self,
        db: AsyncSession,
        page: int = 1,
        per_page: int = 50,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Listar usuários com paginação e filtros
        
        Args:
            db: Sessão do banco de dados
            page: Página atual
            per_page: Usuários por página
            role: Filtrar por papel
            is_active: Filtrar por status ativo
            search: Buscar por username ou email
            
        Returns:
            Dicionário com usuários e informações de paginação
        """
        try:
            # Construir query base
            query = select(User)
            
            # Aplicar filtros
            conditions = []
            
            if role is not None:
                conditions.append(User.role == role)
            
            if is_active is not None:
                conditions.append(User.is_active == is_active)
            
            if search:
                search_term = f"%{search.lower()}%"
                conditions.append(
                    or_(
                        User.username.like(search_term),
                        User.email.like(search_term)
                    )
                )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Contar total
            count_query = select(func.count(User.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Aplicar paginação
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            query = query.order_by(User.created_at.desc())
            
            # Executar query
            result = await db.execute(query)
            users = result.scalars().all()
            
            # Calcular páginas
            pages = (total + per_page - 1) // per_page
            
            return {
                "users": [self._user_to_response(user) for user in users],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages
            }
            
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}")
            raise
    
    # === MÉTODOS DE AUTORIZAÇÃO ===
    
    def require_role(self, required_role: UserRole):
        """
        Decorator para exigir papel específico
        
        Args:
            required_role: Papel necessário
            
        Returns:
            Decorator function
        """
        def decorator(func):
            async def wrapper(current_user: User, *args, **kwargs):
                if not self.has_role(current_user, required_role):
                    raise AuthorizationError(f"Papel '{required_role.value}' necessário")
                return await func(current_user, *args, **kwargs)
            return wrapper
        return decorator
    
    def has_role(self, user: User, role: UserRole) -> bool:
        """
        Verificar se usuário tem papel específico
        
        Args:
            user: Usuário
            role: Papel a verificar
            
        Returns:
            True se usuário tem o papel
        """
        # Admin tem todos os papéis
        if user.role == UserRole.ADMIN:
            return True
        
        # Supervisor tem papéis de agent e viewer
        if user.role == UserRole.SUPERVISOR and role in [UserRole.AGENT, UserRole.VIEWER]:
            return True
        
        # Agent tem papel de viewer
        if user.role == UserRole.AGENT and role == UserRole.VIEWER:
            return True
        
        # Verificar papel exato
        return user.role == role
    
    def has_permission(self, user: User, permission: str) -> bool:
        """
        Verificar se usuário tem permissão específica
        
        Args:
            user: Usuário
            permission: Permissão a verificar
            
        Returns:
            True se usuário tem a permissão
        """
        permissions_map = {
            "manage_users": [UserRole.ADMIN, UserRole.SUPERVISOR],
            "handle_conversations": [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.AGENT],
            "view_reports": [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.AGENT, UserRole.VIEWER],
            "manage_system": [UserRole.ADMIN],
            "manage_campaigns": [UserRole.ADMIN, UserRole.SUPERVISOR]
        }
        
        allowed_roles = permissions_map.get(permission, [])
        return user.role in allowed_roles
    
    # === MÉTODOS AUXILIARES ===
    
    def _user_to_response(self, user: User) -> UserResponse:
        """
        Converter modelo User para UserResponse
        
        Args:
            user: Modelo do usuário
            
        Returns:
            Schema de resposta do usuário
        """
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            display_name=user.display_name,
            metadata=user.metadata_dict,
            settings=user.settings_dict,
            permissions=UserPermissions(
                is_admin=user.is_admin,
                is_supervisor=user.is_supervisor,
                is_agent=user.is_agent,
                can_manage_users=user.can_manage_users,
                can_handle_conversations=user.can_handle_conversations
            )
        )