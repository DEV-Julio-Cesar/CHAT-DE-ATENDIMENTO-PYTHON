#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo de Usuário - SQLAlchemy para SQL Server
Define a estrutura da tabela users e relacionamentos
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
import uuid
import json

from shared.utils.database import Base

class UserRole(enum.Enum):
    """
    Enumeração dos papéis de usuário no sistema
    Compatível com o sistema Node.js atual
    """
    ADMIN = "admin"           # Administrador do sistema
    SUPERVISOR = "supervisor" # Supervisor de atendimento  
    AGENT = "agent"          # Agente de atendimento
    VIEWER = "viewer"        # Visualizador (apenas leitura)

class User(Base):
    """
    Modelo de Usuário do Sistema ISP Chat
    
    Representa um usuário do sistema com suas credenciais,
    perfil e configurações. Compatível com migração do Node.js.
    
    Attributes:
        id: Identificador único UUID
        username: Nome de usuário único
        email: Email único do usuário
        password_hash: Hash bcrypt da senha (compatível com Node.js)
        role: Papel do usuário no sistema
        is_active: Se o usuário está ativo
        is_verified: Se o email foi verificado
        created_at: Data de criação
        updated_at: Data da última atualização (trigger automático)
        last_login: Data do último login
        metadata: Dados adicionais em JSON
        settings: Configurações do usuário em JSON
    """
    
    __tablename__ = "users"
    __table_args__ = {
        'comment': 'Tabela de usuários do sistema - migrada de dados/usuarios.json'
    }
    
    # === CHAVE PRIMÁRIA ===
    id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID do usuário"
    )
    
    # === DADOS BÁSICOS ===
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Nome de usuário único (3-50 caracteres)"
    )
    
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Email único do usuário"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Hash bcrypt da senha (compatível com Node.js)"
    )
    
    # === PERFIL E PERMISSÕES ===
    role = Column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.AGENT,
        index=True,
        comment="Papel do usuário no sistema"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Se o usuário está ativo no sistema"
    )
    
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Se o email do usuário foi verificado"
    )
    
    # === TIMESTAMPS ===
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.getutcdate(),
        comment="Data e hora de criação do usuário"
    )
    
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.getutcdate(),
        comment="Data e hora da última atualização (trigger automático)"
    )
    
    last_login = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="Data e hora do último login"
    )
    
    # === DADOS ADICIONAIS ===
    user_metadata = Column(
        'metadata',  # Nome real da coluna no banco
        Text,
        nullable=False,
        default='{}',
        comment="Metadados adicionais do usuário em formato JSON"
    )
    
    settings = Column(
        Text,
        nullable=False,
        default='{"notifications": true, "theme": "light", "language": "pt-BR"}',
        comment="Configurações personalizadas do usuário em JSON"
    )
    
    # === RELACIONAMENTOS ===
    # Relacionamentos serão definidos quando todos os modelos estiverem criados
    conversations = relationship("Conversation", back_populates="agent", foreign_keys="Conversation.agent_id", lazy="select")
    # messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id", lazy="select")
    
    # === PROPRIEDADES CALCULADAS ===
    
    @property
    def metadata_dict(self) -> dict:
        """
        Retorna metadata como dicionário Python
        """
        try:
            return json.loads(self.user_metadata) if self.user_metadata else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: dict):
        """
        Define metadata a partir de dicionário Python
        """
        self.user_metadata = json.dumps(value, ensure_ascii=False)
    
    @property
    def settings_dict(self) -> dict:
        """
        Retorna settings como dicionário Python
        """
        try:
            return json.loads(self.settings) if self.settings else {}
        except (json.JSONDecodeError, TypeError):
            return {
                "notifications": True,
                "theme": "light", 
                "language": "pt-BR"
            }
    
    @settings_dict.setter
    def settings_dict(self, value: dict):
        """
        Define settings a partir de dicionário Python
        """
        self.settings = json.dumps(value, ensure_ascii=False)
    
    @property
    def is_admin(self) -> bool:
        """
        Verifica se o usuário é administrador
        """
        return self.role == UserRole.ADMIN
    
    @property
    def is_supervisor(self) -> bool:
        """
        Verifica se o usuário é supervisor
        """
        return self.role == UserRole.SUPERVISOR
    
    @property
    def is_agent(self) -> bool:
        """
        Verifica se o usuário é agente
        """
        return self.role == UserRole.AGENT
    
    @property
    def can_manage_users(self) -> bool:
        """
        Verifica se o usuário pode gerenciar outros usuários
        """
        return self.role in [UserRole.ADMIN, UserRole.SUPERVISOR]
    
    @property
    def can_handle_conversations(self) -> bool:
        """
        Verifica se o usuário pode atender conversas
        """
        return self.role in [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.AGENT]
    
    @property
    def display_name(self) -> str:
        """
        Nome para exibição (username ou email)
        """
        return self.username or self.email.split('@')[0]
    
    # === MÉTODOS DE INSTÂNCIA ===
    
    def update_last_login(self):
        """
        Atualiza o timestamp do último login
        """
        self.last_login = datetime.utcnow()
    
    def update_metadata(self, key: str, value):
        """
        Atualiza um campo específico nos metadados
        
        Args:
            key: Chave do metadado
            value: Valor a ser definido
        """
        metadata = self.metadata_dict
        metadata[key] = value
        self.metadata_dict = metadata
    
    def get_metadata(self, key: str, default=None):
        """
        Obtém um valor específico dos metadados
        
        Args:
            key: Chave do metadado
            default: Valor padrão se não encontrado
            
        Returns:
            Valor do metadado ou default
        """
        return self.metadata_dict.get(key, default)
    
    def update_setting(self, key: str, value):
        """
        Atualiza uma configuração específica
        
        Args:
            key: Chave da configuração
            value: Valor a ser definido
        """
        settings = self.settings_dict
        settings[key] = value
        self.settings_dict = settings
    
    def get_setting(self, key: str, default=None):
        """
        Obtém uma configuração específica
        
        Args:
            key: Chave da configuração
            default: Valor padrão se não encontrado
            
        Returns:
            Valor da configuração ou default
        """
        return self.settings_dict.get(key, default)
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Converte o usuário para dicionário
        
        Args:
            include_sensitive: Se deve incluir dados sensíveis (password_hash)
            
        Returns:
            Dicionário com dados do usuário
        """
        data = {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'metadata': self.metadata_dict,
            'settings': self.settings_dict,
            'display_name': self.display_name,
            'permissions': {
                'is_admin': self.is_admin,
                'is_supervisor': self.is_supervisor,
                'is_agent': self.is_agent,
                'can_manage_users': self.can_manage_users,
                'can_handle_conversations': self.can_handle_conversations
            }
        }
        
        if include_sensitive:
            data['password_hash'] = self.password_hash
        
        return data
    
    # === MÉTODOS ESPECIAIS ===
    
    def __repr__(self) -> str:
        """
        Representação string do usuário
        """
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}', active={self.is_active})>"
    
    def __str__(self) -> str:
        """
        String amigável do usuário
        """
        return f"{self.display_name} ({self.role.value})"
    
    def __eq__(self, other) -> bool:
        """
        Comparação de igualdade entre usuários
        """
        if not isinstance(other, User):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """
        Hash do usuário baseado no ID
        """
        return hash(self.id)