"""
Schemas para autenticação
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime
from app.models.database import UserRole


class UserLogin(BaseModel):
    """Schema para login do usuário"""
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário")
    password: str = Field(..., min_length=8, description="Senha do usuário")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "admin",
                "password": "password123"
            }
        }


class Token(BaseModel):
    """Schema para token de acesso"""
    access_token: str = Field(..., description="Token de acesso JWT")
    refresh_token: str = Field(..., description="Token de renovação")
    token_type: str = Field("bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }


class RefreshTokenRequest(BaseModel):
    """Schema para renovação de token"""
    refresh_token: str = Field(..., description="Token de renovação")
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class UserResponse(BaseModel):
    """Schema para resposta de usuário"""
    id: str = Field(..., description="ID único do usuário")
    username: str = Field(..., description="Nome de usuário")
    email: str = Field(..., description="Email do usuário")
    role: UserRole = Field(..., description="Role do usuário")
    ativo: bool = Field(..., description="Se o usuário está ativo")
    ultimo_login: Optional[str] = Field(None, description="Data do último login")
    created_at: Optional[datetime] = Field(None, description="Data de criação")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "admin",
                "email": "admin@empresa.com",
                "role": "admin",
                "ativo": True,
                "ultimo_login": "2024-01-01T10:00:00Z",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class UserCreate(BaseModel):
    """Schema para criação de usuário"""
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário")
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=8, description="Senha do usuário")
    role: UserRole = Field(UserRole.ATENDENTE, description="Role do usuário")
    ativo: bool = Field(True, description="Se o usuário está ativo")
    
    @validator('username')
    def validate_username(cls, v):
        """Validar nome de usuário"""
        if not v.isalnum():
            raise ValueError('Username must contain only alphanumeric characters')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Validar senha"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Verificar se tem pelo menos uma letra e um número
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not (has_letter and has_number):
            raise ValueError('Password must contain at least one letter and one number')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "username": "joao_silva",
                "email": "joao.silva@empresa.com",
                "password": "senha123",
                "role": "atendente",
                "ativo": True
            }
        }


class UserUpdate(BaseModel):
    """Schema para atualização de usuário"""
    email: Optional[EmailStr] = Field(None, description="Email do usuário")
    role: Optional[UserRole] = Field(None, description="Role do usuário")
    ativo: Optional[bool] = Field(None, description="Se o usuário está ativo")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "novo.email@empresa.com",
                "role": "supervisor",
                "ativo": True
            }
        }


class PasswordChangeRequest(BaseModel):
    """Schema para alteração de senha"""
    current_password: str = Field(..., description="Senha atual")
    new_password: str = Field(..., min_length=8, description="Nova senha")
    confirm_password: str = Field(..., description="Confirmação da nova senha")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Verificar se as senhas coincidem"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validar nova senha"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Verificar se tem pelo menos uma letra e um número
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not (has_letter and has_number):
            raise ValueError('Password must contain at least one letter and one number')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "current_password": "senha_atual",
                "new_password": "nova_senha123",
                "confirm_password": "nova_senha123"
            }
        }


class PasswordResetRequest(BaseModel):
    """Schema para solicitação de reset de senha"""
    email: EmailStr = Field(..., description="Email do usuário")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "usuario@empresa.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Schema para confirmação de reset de senha"""
    token: str = Field(..., description="Token de reset")
    new_password: str = Field(..., min_length=8, description="Nova senha")
    confirm_password: str = Field(..., description="Confirmação da nova senha")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Verificar se as senhas coincidem"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validar nova senha"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Verificar se tem pelo menos uma letra e um número
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not (has_letter and has_number):
            raise ValueError('Password must contain at least one letter and one number')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "token": "reset_token_here",
                "new_password": "nova_senha123",
                "confirm_password": "nova_senha123"
            }
        }


class LoginHistory(BaseModel):
    """Schema para histórico de login"""
    id: str = Field(..., description="ID do registro")
    user_id: str = Field(..., description="ID do usuário")
    ip_address: Optional[str] = Field(None, description="Endereço IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    success: bool = Field(..., description="Se o login foi bem-sucedido")
    timestamp: datetime = Field(..., description="Data e hora do login")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "success": True,
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }


class SessionInfo(BaseModel):
    """Schema para informações de sessão"""
    user_id: str = Field(..., description="ID do usuário")
    username: str = Field(..., description="Nome de usuário")
    role: UserRole = Field(..., description="Role do usuário")
    login_time: datetime = Field(..., description="Hora do login")
    last_activity: datetime = Field(..., description="Última atividade")
    ip_address: Optional[str] = Field(None, description="Endereço IP")
    expires_at: datetime = Field(..., description="Expiração da sessão")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "admin",
                "role": "admin",
                "login_time": "2024-01-01T10:00:00Z",
                "last_activity": "2024-01-01T10:30:00Z",
                "ip_address": "192.168.1.100",
                "expires_at": "2024-01-02T10:00:00Z"
            }
        }