#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schemas Pydantic para Chat
Define estruturas de dados para API
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ConversationCreate(BaseModel):
    """Schema para criar conversa"""
    customer_phone: str = Field(..., description="Telefone do cliente")
    customer_name: Optional[str] = Field(None, description="Nome do cliente")
    priority: str = Field("normal", description="Prioridade")
    initial_message: Optional[str] = Field(None, description="Mensagem inicial")
    whatsapp_client_id: Optional[str] = Field(None, description="ID do cliente WhatsApp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados extras")

class ConversationUpdate(BaseModel):
    """Schema para atualizar conversa"""
    status: Optional[str] = None
    agent_id: Optional[str] = None
    priority: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ConversationResponse(BaseModel):
    """Schema de resposta para conversa"""
    id: str
    customer_phone: str
    customer_name: Optional[str] = None
    status: str
    priority: str
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
    message_count: int
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    """Schema para criar mensagem"""
    conversation_id: str = Field(..., description="ID da conversa")
    content: str = Field(..., description="Conteúdo da mensagem")
    message_type: str = Field("text", description="Tipo da mensagem")
    sender_type: str = Field("agent", description="Tipo do remetente")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados")

class MessageResponse(BaseModel):
    """Schema de resposta para mensagem"""
    id: str
    conversation_id: str
    content: str
    message_type: str
    sender_type: str
    sender_id: Optional[str] = None
    is_read: bool
    created_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any]
    
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