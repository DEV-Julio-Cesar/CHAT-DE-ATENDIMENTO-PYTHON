#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo de Conversa - SQLAlchemy para SQL Server
Define a estrutura da tabela conversations e relacionamentos
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, JSON
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
import uuid
import json

from shared.utils.database import Base

class ConversationStatus(enum.Enum):
    """
    Status da conversa no sistema
    """
    AUTOMATION = "automation"    # Atendimento automatizado (bot)
    WAITING = "waiting"          # Aguardando atendimento humano
    IN_SERVICE = "in_service"    # Em atendimento
    CLOSED = "closed"           # Fechada

class ConversationPriority(enum.Enum):
    """
    Prioridade da conversa
    """
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class Conversation(Base):
    """
    Modelo de Conversa do Sistema ISP Chat
    
    Representa uma conversa/atendimento entre cliente e sistema.
    Compatível com migração do sistema Node.js.
    
    Attributes:
        id: Identificador único UUID
        legacy_id: ID do sistema antigo (para migração)
        customer_phone: Telefone do cliente
        customer_name: Nome do cliente
        status: Status atual da conversa
        priority: Prioridade da conversa
        agent_id: ID do agente responsável (FK para users)
        whatsapp_client_id: ID do cliente WhatsApp
        created_at: Data de criação
        updated_at: Data da última atualização
        assigned_at: Data de atribuição ao agente
        closed_at: Data de fechamento
        last_message: Última mensagem (cache)
        last_message_at: Data da última mensagem
        bot_attempts: Tentativas do bot
        bot_escalated: Se foi escalado para humano
        metadata: Dados adicionais em JSON
        status_history: Histórico de mudanças de status
    """
    
    __tablename__ = "conversations"
    __table_args__ = {
        'comment': 'Tabela de conversas - migrada de dados/filas-atendimento.json'
    }
    
    # === CHAVE PRIMÁRIA ===
    id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único UUID da conversa"
    )
    
    # === COMPATIBILIDADE COM SISTEMA ANTIGO ===
    legacy_id = Column(
        String(255),
        nullable=True,
        comment="ID do sistema Node.js antigo (para migração)"
    )
    
    # === DADOS DO CLIENTE ===
    customer_phone = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Telefone do cliente (formato internacional)"
    )
    
    customer_name = Column(
        String(255),
        nullable=True,
        comment="Nome do cliente"
    )
    
    # === STATUS E CONTROLE ===
    status = Column(
        String(20),
        nullable=False,
        default='automation',
        index=True,
        comment="Status atual da conversa"
    )
    
    priority = Column(
        String(20),
        nullable=False,
        default='normal',
        index=True,
        comment="Prioridade da conversa"
    )
    
    # === ATRIBUIÇÃO ===
    agent_id = Column(
        UNIQUEIDENTIFIER,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID do agente responsável"
    )
    
    # === WHATSAPP ===
    whatsapp_client_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="ID do cliente WhatsApp"
    )
    
    # === TIMESTAMPS ===
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.getutcdate(),
        index=True,
        comment="Data e hora de criação"
    )
    
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.getutcdate(),
        comment="Data e hora da última atualização (trigger automático)"
    )
    
    assigned_at = Column(
        DateTime,
        nullable=True,
        comment="Data e hora de atribuição ao agente"
    )
    
    closed_at = Column(
        DateTime,
        nullable=True,
        comment="Data e hora de fechamento"
    )
    
    # === CACHE DE ÚLTIMA MENSAGEM ===
    last_message = Column(
        Text,
        nullable=True,
        comment="Última mensagem (cache para performance)"
    )
    
    last_message_at = Column(
        DateTime,
        nullable=True,
        comment="Data da última mensagem"
    )
    
    # === CONTROLE DO BOT ===
    bot_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Número de tentativas do bot"
    )
    
    bot_escalated = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Se foi escalado para atendimento humano"
    )
    
    # === DADOS ADICIONAIS ===
    metadata_json = Column(
        'metadata',  # Nome real da coluna no banco
        Text,
        nullable=False,
        default='{}',
        comment="Metadados adicionais em formato JSON"
    )
    
    status_history = Column(
        Text,
        nullable=False,
        default='[]',
        comment="Histórico de mudanças de status em JSON"
    )
    
    # === RELACIONAMENTOS ===
    # Relacionamento com usuário (agente)
    agent = relationship(
        "User", 
        back_populates="conversations",
        foreign_keys=[agent_id],
        lazy="select"
    )
    
    # Relacionamento com mensagens
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
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
    def status_history_list(self) -> list:
        """
        Retorna histórico de status como lista Python
        """
        try:
            return json.loads(self.status_history) if self.status_history else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    @status_history_list.setter
    def status_history_list(self, value: list):
        """
        Define histórico de status a partir de lista Python
        """
        self.status_history = json.dumps(value, ensure_ascii=False)
    
    @property
    def is_active(self) -> bool:
        """
        Verifica se a conversa está ativa
        """
        return self.status in ['automation', 'waiting', 'in_service']
    
    @property
    def is_waiting(self) -> bool:
        """
        Verifica se está aguardando atendimento
        """
        return self.status == 'waiting'
    
    @property
    def is_in_service(self) -> bool:
        """
        Verifica se está em atendimento
        """
        return self.status == 'in_service'
    
    @property
    def is_closed(self) -> bool:
        """
        Verifica se está fechada
        """
        return self.status == 'closed'
    
    @property
    def has_agent(self) -> bool:
        """
        Verifica se tem agente atribuído
        """
        return self.agent_id is not None
    
    @property
    def duration_minutes(self) -> int:
        """
        Duração da conversa em minutos
        """
        if not self.closed_at:
            end_time = datetime.utcnow()
        else:
            end_time = self.closed_at
        
        duration = end_time - self.created_at
        return int(duration.total_seconds() / 60)
    
    # === MÉTODOS DE INSTÂNCIA ===
    
    def add_status_change(self, old_status: str, new_status: str, user_id: str = None):
        """
        Adiciona mudança de status ao histórico
        
        Args:
            old_status: Status anterior
            new_status: Novo status
            user_id: ID do usuário que fez a mudança
        """
        history = self.status_history_list
        history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'old_status': old_status,
            'new_status': new_status,
            'user_id': str(user_id) if user_id else None
        })
        self.status_history_list = history
    
    def update_last_message(self, message_content: str):
        """
        Atualiza cache da última mensagem
        
        Args:
            message_content: Conteúdo da mensagem
        """
        self.last_message = message_content[:500]  # Limitar tamanho
        self.last_message_at = datetime.utcnow()
    
    def assign_to_agent(self, agent_id: str):
        """
        Atribui conversa a um agente
        
        Args:
            agent_id: ID do agente
        """
        old_status = self.status
        self.agent_id = agent_id
        self.status = 'in_service'
        self.assigned_at = datetime.utcnow()
        self.add_status_change(old_status, 'in_service', agent_id)
    
    def escalate_to_human(self):
        """
        Escala conversa para atendimento humano
        """
        old_status = self.status
        self.status = 'waiting'
        self.bot_escalated = True
        self.add_status_change(old_status, 'waiting')
    
    def close_conversation(self, user_id: str = None):
        """
        Fecha a conversa
        
        Args:
            user_id: ID do usuário que fechou
        """
        old_status = self.status
        self.status = 'closed'
        self.closed_at = datetime.utcnow()
        self.add_status_change(old_status, 'closed', user_id)
    
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
    
    def to_dict(self) -> dict:
        """
        Converte a conversa para dicionário
        
        Returns:
            Dicionário com dados da conversa
        """
        return {
            'id': str(self.id),
            'legacy_id': self.legacy_id,
            'customer_phone': self.customer_phone,
            'customer_name': self.customer_name,
            'status': self.status,
            'priority': self.priority,
            'agent_id': str(self.agent_id) if self.agent_id else None,
            'whatsapp_client_id': self.whatsapp_client_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'last_message': self.last_message,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'bot_attempts': self.bot_attempts,
            'bot_escalated': self.bot_escalated,
            'metadata': self.metadata_dict,
            'status_history': self.status_history_list,
            'computed': {
                'is_active': self.is_active,
                'is_waiting': self.is_waiting,
                'is_in_service': self.is_in_service,
                'is_closed': self.is_closed,
                'has_agent': self.has_agent,
                'duration_minutes': self.duration_minutes
            }
        }
    
    # === MÉTODOS ESPECIAIS ===
    
    def __repr__(self) -> str:
        """
        Representação string da conversa
        """
        return f"<Conversation(id={self.id}, customer='{self.customer_phone}', status='{self.status}')>"
    
    def __str__(self) -> str:
        """
        String amigável da conversa
        """
        customer = self.customer_name or self.customer_phone
        return f"Conversa com {customer} ({self.status})"
    
    def __eq__(self, other) -> bool:
        """
        Comparação de igualdade entre conversas
        """
        if not isinstance(other, Conversation):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """
        Hash da conversa baseado no ID
        """
        return hash(self.id)