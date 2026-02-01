#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schemas Pydantic para Auth Service
Define estruturas de dados para validação de entrada e saída da API
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import re

class UserRole(str, Enum):
    """
    Enumeração dos papéis de usuário
    Compatível com o modelo SQLAlchemy
    """
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AGENT = "agent"
    VIEWER = "viewer"

# === SCHEMAS DE REQUEST (ENTRADA) ===

class LoginRequest(BaseModel):
    """
    Schema para requisição de login
    
    Attributes:
        username: Nome de usuário ou email
        password: Senha em texto plano
        remember_me: Se deve manter login por mais tempo
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Nome de usuário ou email"
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Senha do usuário"
    )
    remember_me: bool = Field(
        default=False,
        description="Manter login por mais tempo"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validar formato do username"""
        v = v.strip().lower()
        if not v:
            raise ValueError('Username não pode estar vazio')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validar senha"""
        if not v or len(v.strip()) < 6:
            raise ValueError('Senha deve ter pelo menos 6 caracteres')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "admin123",
                "remember_me": False
            }
        }

class UserCreateRequest(BaseModel):
    """
    Schema para criação de usuário
    
    Attributes:
        username: Nome de usuário único
        email: Email único
        password: Senha em texto plano
        role: Papel do usuário
        is_active: Se o usuário está ativo
        metadata: Metadados adicionais
        settings: Configurações do usuário
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_.-]+$',
        description="Nome de usuário único (3-50 caracteres, apenas letras, números, _, ., -)"
    )
    email: EmailStr = Field(
        ...,
        description="Email único do usuário"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Senha (mínimo 8 caracteres)"
    )
    role: UserRole = Field(
        default=UserRole.AGENT,
        description="Papel do usuário no sistema"
    )
    is_active: bool = Field(
        default=True,
        description="Se o usuário está ativo"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadados adicionais do usuário"
    )
    settings: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "notifications": True,
            "theme": "light",
            "language": "pt-BR"
        },
        description="Configurações do usuário"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validar username"""
        v = v.strip().lower()
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username deve conter apenas letras, números, _, . ou -')
        if v in ['admin', 'root', 'system', 'null', 'undefined']:
            raise ValueError('Username reservado')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validar força da senha"""
        if len(v) < 8:
            raise ValueError('Senha deve ter pelo menos 8 caracteres')
        
        # Verificar se tem pelo menos uma letra e um número
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not (has_letter and has_number):
            raise ValueError('Senha deve conter pelo menos uma letra e um número')
        
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v):
        """Validar domínio do email"""
        email_str = str(v).lower()
        
        # Lista de domínios temporários/descartáveis (básica)
        temp_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com'
        ]
        
        domain = email_str.split('@')[1] if '@' in email_str else ''
        if domain in temp_domains:
            raise ValueError('Email temporário não é permitido')
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "joao.silva",
                "email": "joao.silva@empresa.com",
                "password": "senha123",
                "role": "agent",
                "is_active": True,
                "metadata": {
                    "department": "Atendimento",
                    "phone": "+5511999999999"
                },
                "settings": {
                    "notifications": True,
                    "theme": "dark",
                    "language": "pt-BR"
                }
            }
        }

class UserUpdateRequest(BaseModel):
    """
    Schema para atualização de usuário
    Todos os campos são opcionais
    """
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_.-]+$',
        description="Nome de usuário único"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email do usuário"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="Nova senha"
    )
    role: Optional[UserRole] = Field(
        None,
        description="Papel do usuário"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Se o usuário está ativo"
    )
    is_verified: Optional[bool] = Field(
        None,
        description="Se o email foi verificado"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadados do usuário"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None,
        description="Configurações do usuário"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validar username se fornecido"""
        if v is not None:
            v = v.strip().lower()
            if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
                raise ValueError('Username deve conter apenas letras, números, _, . ou -')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validar senha se fornecida"""
        if v is not None:
            if len(v) < 8:
                raise ValueError('Senha deve ter pelo menos 8 caracteres')
            
            has_letter = any(c.isalpha() for c in v)
            has_number = any(c.isdigit() for c in v)
            
            if not (has_letter and has_number):
                raise ValueError('Senha deve conter pelo menos uma letra e um número')
        
        return v

class PasswordChangeRequest(BaseModel):
    """
    Schema para alteração de senha
    """
    current_password: str = Field(
        ...,
        description="Senha atual"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Nova senha"
    )
    confirm_password: str = Field(
        ...,
        description="Confirmação da nova senha"
    )
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Validar se as senhas coincidem"""
        if self.new_password != self.confirm_password:
            raise ValueError('Nova senha e confirmação não coincidem')
        return self
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validar força da nova senha"""
        if len(v) < 8:
            raise ValueError('Senha deve ter pelo menos 8 caracteres')
        
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not (has_letter and has_number):
            raise ValueError('Senha deve conter pelo menos uma letra e um número')
        
        return v

# === SCHEMAS DE RESPONSE (SAÍDA) ===

class UserPermissions(BaseModel):
    """
    Schema para permissões do usuário
    """
    is_admin: bool = Field(description="Se é administrador")
    is_supervisor: bool = Field(description="Se é supervisor")
    is_agent: bool = Field(description="Se é agente")
    can_manage_users: bool = Field(description="Pode gerenciar usuários")
    can_handle_conversations: bool = Field(description="Pode atender conversas")

class UserResponse(BaseModel):
    """
    Schema para resposta com dados do usuário
    Não inclui dados sensíveis como password_hash
    """
    id: str = Field(description="ID único do usuário")
    username: str = Field(description="Nome de usuário")
    email: str = Field(description="Email do usuário")
    role: UserRole = Field(description="Papel do usuário")
    is_active: bool = Field(description="Se o usuário está ativo")
    is_verified: bool = Field(description="Se o email foi verificado")
    created_at: datetime = Field(description="Data de criação")
    updated_at: datetime = Field(description="Data da última atualização")
    last_login: Optional[datetime] = Field(description="Data do último login")
    display_name: str = Field(description="Nome para exibição")
    metadata: Dict[str, Any] = Field(description="Metadados do usuário")
    settings: Dict[str, Any] = Field(description="Configurações do usuário")
    permissions: UserPermissions = Field(description="Permissões do usuário")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "admin",
                "email": "admin@sistema.com",
                "role": "admin",
                "is_active": True,
                "is_verified": True,
                "created_at": "2026-01-11T07:14:39.060000",
                "updated_at": "2026-01-18T12:34:19.229000",
                "last_login": "2026-01-18T12:45:27.102000",
                "display_name": "admin",
                "metadata": {},
                "settings": {
                    "notifications": True,
                    "theme": "light",
                    "language": "pt-BR"
                },
                "permissions": {
                    "is_admin": True,
                    "is_supervisor": True,
                    "is_agent": True,
                    "can_manage_users": True,
                    "can_handle_conversations": True
                }
            }
        }

class LoginResponse(BaseModel):
    """
    Schema para resposta de login bem-sucedido
    """
    access_token: str = Field(description="Token JWT de acesso")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(description="Tempo de expiração em segundos")
    expires_at: datetime = Field(description="Data/hora de expiração")
    user: UserResponse = Field(description="Dados do usuário logado")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "expires_at": "2026-01-30T12:45:27.102000",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "admin",
                    "email": "admin@sistema.com",
                    "role": "admin",
                    "is_active": True
                }
            }
        }

class TokenValidationResponse(BaseModel):
    """
    Schema para resposta de validação de token
    """
    valid: bool = Field(description="Se o token é válido")
    user: Optional[UserResponse] = Field(description="Dados do usuário se token válido")
    expires_at: Optional[datetime] = Field(description="Data de expiração do token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "admin",
                    "role": "admin"
                },
                "expires_at": "2026-01-30T12:45:27.102000"
            }
        }

class UserListResponse(BaseModel):
    """
    Schema para resposta de listagem de usuários
    """
    users: List[UserResponse] = Field(description="Lista de usuários")
    total: int = Field(description="Total de usuários")
    page: int = Field(description="Página atual")
    per_page: int = Field(description="Usuários por página")
    pages: int = Field(description="Total de páginas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "username": "admin",
                        "email": "admin@sistema.com",
                        "role": "admin",
                        "is_active": True
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 50,
                "pages": 1
            }
        }

# === SCHEMAS DE ERRO ===

class ErrorDetail(BaseModel):
    """
    Schema para detalhes de erro
    """
    field: Optional[str] = Field(description="Campo que causou o erro")
    message: str = Field(description="Mensagem de erro")
    code: Optional[str] = Field(description="Código do erro")

class ErrorResponse(BaseModel):
    """
    Schema para resposta de erro
    """
    error: str = Field(description="Tipo do erro")
    message: str = Field(description="Mensagem de erro")
    details: Optional[List[ErrorDetail]] = Field(description="Detalhes específicos")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp do erro")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Dados de entrada inválidos",
                "details": [
                    {
                        "field": "password",
                        "message": "Senha deve ter pelo menos 8 caracteres",
                        "code": "min_length"
                    }
                ],
                "timestamp": "2026-01-29T12:45:27.102000"
            }
        }

# === SCHEMAS DE CONFIGURAÇÃO ===

class AuthConfig(BaseModel):
    """
    Schema para configurações de autenticação
    """
    jwt_expire_hours: int = Field(description="Horas de expiração do JWT")
    max_login_attempts: int = Field(description="Máximo de tentativas de login")
    lockout_duration_minutes: int = Field(description="Duração do bloqueio em minutos")
    password_min_length: int = Field(description="Tamanho mínimo da senha")
    require_email_verification: bool = Field(description="Requer verificação de email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "jwt_expire_hours": 24,
                "max_login_attempts": 5,
                "lockout_duration_minutes": 15,
                "password_min_length": 8,
                "require_email_verification": False
            }
        }