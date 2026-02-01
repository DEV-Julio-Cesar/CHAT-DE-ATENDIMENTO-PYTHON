#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelos de dados do Chat Service
Define estruturas para conversas, mensagens, filas e atendimentos
Compatível com SQL Server e sistema migrado
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship
import uuid
import json

# Importar modelos do shared
from shared.models import Conversation, Message
from shared.utils.database import Base

class ConversationStatus(str, Enum):
    """Status da conversa"""
    AUTOMATION = "automation"    # Atendimento automatizado (bot)
    WAITING = "waiting"          # Aguardando atendimento
    IN_SERVICE = "in_service"    # Em atendimento
    CLOSED = "closed"           # Fechada

class MessageType(str, Enum):
    """Tipo de mensagem"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    SYSTEM = "system"

class QueuePriority(str, Enum):
    """Prioridade na fila"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# === MODELOS ADICIONAIS (NÃO CONFLITANTES) ===

class Queue(Base):
    """
    Modelo de fila de atendimento (placeholder)
    """
    __tablename__ = "queues"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class QueueAgent(Base):
    """
    Relacionamento entre filas e agentes (placeholder)
    """
    __tablename__ = "queue_agents"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    queue_id = Column(UNIQUEIDENTIFIER, ForeignKey("queues.id"), nullable=False)
    agent_id = Column(UNIQUEIDENTIFIER, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

# === SCHEMAS PYDANTIC ===

class ConversationBase(BaseModel):
    """Schema base para conversa"""
    customer_phone: str = Field(..., description="Telefone do cliente")
    customer_name: Optional[str] = Field(None, description="Nome do cliente")
    priority: QueuePriority = Field(QueuePriority.NORMAL, description="Prioridade")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados extras")

class ConversationCreate(ConversationBase):
    """Schema para criar conversa"""
    initial_message: Optional[str] = Field(None, description="Mensagem inicial")
    whatsapp_client_id: Optional[str] = Field(None, description="ID do cliente WhatsApp")

class ConversationUpdate(BaseModel):
    """Schema para atualizar conversa"""
    status: Optional[ConversationStatus] = None
    agent_id: Optional[str] = None
    priority: Optional[QueuePriority] = None
    metadata: Optional[Dict[str, Any]] = None

class ConversationResponse(ConversationBase):
    """Schema de resposta para conversa"""
    id: str
    status: ConversationStatus
    agent_id: Optional[str] = None
    whatsapp_client_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    assigned_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    bot_attempts: int
    bot_escalated: bool
    
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    """Schema base para mensagem"""
    content: str = Field(..., description="Conteúdo da mensagem")
    message_type: MessageType = Field(MessageType.TEXT, description="Tipo da mensagem")

class MessageCreate(MessageBase):
    """Schema para criar mensagem"""
    conversation_id: str = Field(..., description="ID da conversa")
    sender_type: str = Field("agent", description="Tipo do remetente")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados")

class MessageResponse(MessageBase):
    """Schema de resposta para mensagem"""
    id: str
    conversation_id: str
    sender_type: str
    sender_id: Optional[str] = None
    is_read: bool
    created_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    """Schema para lista de conversas"""
    conversations: List[ConversationResponse]
    total: int
    page: int
    per_page: int
    pages: int

class MessageListResponse(BaseModel):
    """Schema para lista de mensagens"""
    messages: List[MessageResponse]
    total: int
    page: int
    per_page: int
    pages: int

class ChatStats(BaseModel):
    """Schema para estatísticas do chat"""
    total_conversations: int
    active_conversations: int
    waiting_conversations: int
    resolved_today: int
    avg_response_time: float
    avg_resolution_time: float
    agent_utilization: Dict[str, float]
    queue_stats: Dict[str, Dict[str, Any]]