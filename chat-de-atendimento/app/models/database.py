"""
Modelos de banco de dados SQLAlchemy
"""
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text, 
    ForeignKey, Enum, UUID, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import enum
import uuid
from datetime import datetime
from typing import Optional

Base = declarative_base()


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ATENDENTE = "atendente"
    SUPERVISOR = "supervisor"


class ClientStatus(str, enum.Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    SUSPENSO = "suspenso"


class ConversationState(str, enum.Enum):
    AUTOMACAO = "automacao"
    ESPERA = "espera"
    ATENDIMENTO = "atendimento"
    ENCERRADO = "encerrado"


class MessageType(str, enum.Enum):
    TEXTO = "texto"
    IMAGEM = "imagem"
    DOCUMENTO = "documento"
    AUDIO = "audio"
    VIDEO = "video"


class SenderType(str, enum.Enum):
    CLIENTE = "cliente"
    ATENDENTE = "atendente"
    BOT = "bot"
    SISTEMA = "sistema"


class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.ATENDENTE)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ultimo_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    conversas_atendidas = relationship("Conversa", back_populates="atendente")
    campanhas_criadas = relationship("Campanha", back_populates="criador")
    
    def __repr__(self):
        return f"<Usuario(username='{self.username}', role='{self.role}')>"


class ClienteWhatsApp(Base):
    __tablename__ = "clientes_whatsapp"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(100), unique=True, nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    telefone = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    status = Column(Enum(ClientStatus), default=ClientStatus.ATIVO, nullable=False)
    servidor_id = Column(String(50), nullable=True)  # Para sharding
    metadata = Column(JSON, nullable=True)  # Dados adicionais do cliente
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    conversas = relationship("Conversa", back_populates="cliente")
    
    # Índices
    __table_args__ = (
        Index('idx_cliente_telefone_status', 'telefone', 'status'),
        Index('idx_cliente_servidor', 'servidor_id'),
    )
    
    def __repr__(self):
        return f"<ClienteWhatsApp(nome='{self.nome}', telefone='{self.telefone}')>"


class Conversa(Base):
    __tablename__ = "conversas"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(PG_UUID(as_uuid=True), ForeignKey("clientes_whatsapp.id"), nullable=False)
    chat_id = Column(String(255), nullable=False, index=True)  # WhatsApp chat ID
    estado = Column(Enum(ConversationState), default=ConversationState.AUTOMACAO, nullable=False)
    atendente_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    tentativas_bot = Column(Integer, default=0, nullable=False)
    prioridade = Column(Integer, default=0, nullable=False)  # 0=normal, 1=alta, 2=urgente
    tags = Column(JSON, nullable=True)  # Tags para categorização
    metadata = Column(JSON, nullable=True)  # Dados adicionais da conversa
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    encerrada_em = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    cliente = relationship("ClienteWhatsApp", back_populates="conversas")
    atendente = relationship("Usuario", back_populates="conversas_atendidas")
    mensagens = relationship("Mensagem", back_populates="conversa", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_conversa_cliente_estado', 'cliente_id', 'estado'),
        Index('idx_conversa_atendente', 'atendente_id'),
        Index('idx_conversa_chat_id', 'chat_id'),
        Index('idx_conversa_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Conversa(chat_id='{self.chat_id}', estado='{self.estado}')>"


class Mensagem(Base):
    __tablename__ = "mensagens"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversa_id = Column(PG_UUID(as_uuid=True), ForeignKey("conversas.id"), nullable=False)
    whatsapp_message_id = Column(String(255), nullable=True, index=True)  # ID da mensagem no WhatsApp
    remetente_tipo = Column(Enum(SenderType), nullable=False)
    remetente_id = Column(String(255), nullable=True)  # ID do remetente (telefone, user_id, etc)
    conteudo = Column(Text, nullable=False)
    tipo_mensagem = Column(Enum(MessageType), default=MessageType.TEXTO, nullable=False)
    arquivo_url = Column(String(500), nullable=True)  # URL do arquivo se for mídia
    metadata = Column(JSON, nullable=True)  # Dados adicionais da mensagem
    lida = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    conversa = relationship("Conversa", back_populates="mensagens")
    
    # Índices
    __table_args__ = (
        Index('idx_mensagem_conversa_data', 'conversa_id', 'created_at'),
        Index('idx_mensagem_whatsapp_id', 'whatsapp_message_id'),
        Index('idx_mensagem_remetente', 'remetente_tipo', 'remetente_id'),
    )
    
    def __repr__(self):
        return f"<Mensagem(tipo='{self.tipo_mensagem}', remetente='{self.remetente_tipo}')>"


class Campanha(Base):
    __tablename__ = "campanhas"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    mensagem_template = Column(Text, nullable=False)
    criador_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    status = Column(String(50), default="rascunho", nullable=False)  # rascunho, ativa, pausada, finalizada
    agendada_para = Column(DateTime(timezone=True), nullable=True)
    total_destinatarios = Column(Integer, default=0, nullable=False)
    enviadas = Column(Integer, default=0, nullable=False)
    falharam = Column(Integer, default=0, nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    finalizada_em = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    criador = relationship("Usuario", back_populates="campanhas_criadas")
    envios = relationship("EnvioCampanha", back_populates="campanha", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Campanha(nome='{self.nome}', status='{self.status}')>"


class EnvioCampanha(Base):
    __tablename__ = "envios_campanha"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campanha_id = Column(PG_UUID(as_uuid=True), ForeignKey("campanhas.id"), nullable=False)
    destinatario_telefone = Column(String(20), nullable=False)
    destinatario_nome = Column(String(255), nullable=True)
    mensagem_personalizada = Column(Text, nullable=False)
    status = Column(String(50), default="pendente", nullable=False)  # pendente, enviado, falhou, entregue
    whatsapp_message_id = Column(String(255), nullable=True)
    erro_detalhes = Column(Text, nullable=True)
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    entregue_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    campanha = relationship("Campanha", back_populates="envios")
    
    # Índices
    __table_args__ = (
        Index('idx_envio_campanha_status', 'campanha_id', 'status'),
        Index('idx_envio_telefone', 'destinatario_telefone'),
    )


class ConfiguracaoSistema(Base):
    __tablename__ = "configuracoes_sistema"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chave = Column(String(100), unique=True, nullable=False, index=True)
    valor = Column(JSON, nullable=False)
    descricao = Column(Text, nullable=True)
    categoria = Column(String(50), nullable=False, default="geral")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ConfiguracaoSistema(chave='{self.chave}', categoria='{self.categoria}')>"


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    acao = Column(String(100), nullable=False)
    recurso = Column(String(100), nullable=False)
    recurso_id = Column(String(255), nullable=True)
    detalhes = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    usuario = relationship("Usuario")
    
    # Índices
    __table_args__ = (
        Index('idx_auditoria_usuario_acao', 'usuario_id', 'acao'),
        Index('idx_auditoria_recurso', 'recurso', 'recurso_id'),
        Index('idx_auditoria_created_at', 'created_at'),
    )