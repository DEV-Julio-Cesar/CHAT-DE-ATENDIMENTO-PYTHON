#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo de Mensagem - SQLAlchemy para SQL Server
Define a estrutura da tabela messages e relacionamentos
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
import uuid
import json

from shared.utils.database import Base

class MessageSenderType(enum.Enum):
    """
    Tipo de remetente da mensagem
    """
    CUSTOMER = "customer"  # Cliente
    AGENT = "agent"       # Agente humano
    BOT = "bot"          # Bot/sistema automatizado
    SYSTEM = "system"    # Sistema (notificações)

class MessageType(enum.Enum):
    """
    Tipo de mensagem
    """
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    SYSTEM = "system"

class Message(Base):
    """
    Modelo de Mensagem do Sistema ISP Chat
    
    Representa uma mensagem individual dentro de uma conversa.
    Compatível com migração do sistema Node.js.
    
    Attributes:
        id: Identificador único UUID
        conversation_id: ID da conversa (FK)
        sender_type: Tipo do remetente (customer, agent, bot, system)
        sender_id: ID do remetente (se aplicável)
        content: Conteúdo da mensagem
        message_type: Tipo da mensagem (text, image, etc.)
        created_at: Data de criação
        is_read: Se foi lida
        delivered_at: Data de entrega
        read_at: Data de leitura
        metadata: Dados adicionais em JSON
    """
    
    __tablename__ = "messages"
    __table_args__ = {
        'comment': 'Tabela de mensagens do sistema'
    }
    
    # === CHAVE PRIMÁRIA ===
    id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID da mensagem"
    )
    
    # === REFERÊNCIA À CONVERSA ===
    conversation_id = Column(
        UNIQUEIDENTIFIER,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID da conversa"
    )
    
    # === DADOS DO REMETENTE ===
    sender_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Tipo do remetente (customer, agent, bot, system)"
    )
    
    sender_id = Column(
        UNIQUEIDENTIFIER,
        nullable=True,
        index=True,
        comment="ID do remetente (pode ser NULL para mensagens de sistema)"
    )
    
    # === CONTEÚDO DA MENSAGEM ===
    content = Column(
        Text,
        nullable=False,
        comment="Conteúdo da mensagem"
    )
    
    message_type = Column(
        String(20),
        nullable=False,
        default='text',
        comment="Tipo da mensagem (text, image, audio, etc.)"
    )
    
    # === TIMESTAMPS ===
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.getutcdate(),
        index=True,
        comment="Data e hora de criação"
    )
    
    # === STATUS DA MENSAGEM ===
    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Se a mensagem foi lida"
    )
    
    delivered_at = Column(
        DateTime,
        nullable=True,
        comment="Data e hora de entrega"
    )
    
    read_at = Column(
        DateTime,
        nullable=True,
        comment="Data e hora de leitura"
    )
    
    # === METADADOS ===
    metadata_json = Column(
        'metadata',  # Nome real da coluna no banco
        Text,
        nullable=False,
        default='{}',
        comment="Metadados adicionais em formato JSON (anexos, localização, etc.)"
    )
    
    # === RELACIONAMENTOS ===
    # Relacionamento com conversa
    conversation = relationship(
        "Conversation",
        back_populates="messages",
        lazy="select"
    )
    
    # Relacionamento com usuário (remetente)
    # sender = relationship(
    #     "User",
    #     back_populates="messages",
    #     foreign_keys=[sender_id],
    #     lazy="select"
    # )
    
    # === PROPRIEDADES CALCULADAS ===
    
    @property
    def metadata_dict(self) -> dict:
        """
        Retorna metadata como dicionário Python
        """
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: dict):
        """
        Define metadata a partir de dicionário Python
        """
        self.metadata_json = json.dumps(value, ensure_ascii=False)
    
    @property
    def is_from_customer(self) -> bool:
        """
        Verifica se a mensagem é do cliente
        """
        return self.sender_type == 'customer'
    
    @property
    def is_from_agent(self) -> bool:
        """
        Verifica se a mensagem é de um agente
        """
        return self.sender_type == 'agent'
    
    @property
    def is_from_bot(self) -> bool:
        """
        Verifica se a mensagem é do bot
        """
        return self.sender_type == 'bot'
    
    @property
    def is_system_message(self) -> bool:
        """
        Verifica se é uma mensagem do sistema
        """
        return self.sender_type == 'system'
    
    @property
    def is_media_message(self) -> bool:
        """
        Verifica se é uma mensagem de mídia
        """
        return self.message_type in ['image', 'audio', 'video', 'document']
    
    @property
    def age_minutes(self) -> int:
        """
        Idade da mensagem em minutos
        """
        now = datetime.utcnow()
        age = now - self.created_at
        return int(age.total_seconds() / 60)
    
    @property
    def is_recent(self) -> bool:
        """
        Verifica se a mensagem é recente (menos de 5 minutos)
        """
        return self.age_minutes < 5
    
    # === MÉTODOS DE INSTÂNCIA ===
    
    def mark_as_read(self):
        """
        Marca a mensagem como lida
        """
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def mark_as_delivered(self):
        """
        Marca a mensagem como entregue
        """
        if not self.delivered_at:
            self.delivered_at = datetime.utcnow()
    
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
    
    def add_attachment(self, url: str, type: str, size: int = None):
        """
        Adiciona anexo à mensagem
        
        Args:
            url: URL do anexo
            type: Tipo do anexo
            size: Tamanho em bytes
        """
        self.update_metadata('attachment', {
            'url': url,
            'type': type,
            'size': size,
            'uploaded_at': datetime.utcnow().isoformat()
        })
    
    def add_location(self, latitude: float, longitude: float, address: str = None):
        """
        Adiciona localização à mensagem
        
        Args:
            latitude: Latitude
            longitude: Longitude
            address: Endereço (opcional)
        """
        self.update_metadata('location', {
            'latitude': latitude,
            'longitude': longitude,
            'address': address
        })
    
    def add_contact(self, name: str, phone: str, email: str = None):
        """
        Adiciona contato à mensagem
        
        Args:
            name: Nome do contato
            phone: Telefone do contato
            email: Email do contato (opcional)
        """
        self.update_metadata('contact', {
            'name': name,
            'phone': phone,
            'email': email
        })
    
    def to_dict(self) -> dict:
        """
        Converte a mensagem para dicionário
        
        Returns:
            Dicionário com dados da mensagem
        """
        return {
            'id': str(self.id),
            'conversation_id': str(self.conversation_id),
            'sender_type': self.sender_type,
            'sender_id': str(self.sender_id) if self.sender_id else None,
            'content': self.content,
            'message_type': self.message_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_read': self.is_read,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'metadata': self.metadata_dict,
            'computed': {
                'is_from_customer': self.is_from_customer,
                'is_from_agent': self.is_from_agent,
                'is_from_bot': self.is_from_bot,
                'is_system_message': self.is_system_message,
                'is_media_message': self.is_media_message,
                'age_minutes': self.age_minutes,
                'is_recent': self.is_recent
            }
        }
    
    # === MÉTODOS ESPECIAIS ===
    
    def __repr__(self) -> str:
        """
        Representação string da mensagem
        """
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, sender_type='{self.sender_type}', content='{content_preview}')>"
    
    def __str__(self) -> str:
        """
        String amigável da mensagem
        """
        return f"{self.sender_type}: {self.content[:100]}"
    
    def __eq__(self, other) -> bool:
        """
        Comparação de igualdade entre mensagens
        """
        if not isinstance(other, Message):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """
        Hash da mensagem baseado no ID
        """
        return hash(self.id)