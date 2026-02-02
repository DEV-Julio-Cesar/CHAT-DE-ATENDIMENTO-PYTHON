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


# ============================================================================
# ENUMS PARA SEMANA 1 - SEGURANÇA
# ============================================================================

class GDPRRequestType(str, enum.Enum):
    """Tipos de requisição GDPR/LGPD"""
    DELETION = "deletion"  # Direito ao esquecimento
    EXPORT = "export"  # Portabilidade de dados
    CONSENT = "consent"  # Consentimento


class GDPRRequestStatus(str, enum.Enum):
    """Status da requisição GDPR"""
    PENDING = "pending"
    CONFIRMATION_SENT = "confirmation_sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AuditEventType(str, enum.Enum):
    """Tipos de eventos de auditoria"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    DATA_ACCESSED = "data_accessed"
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    SECURITY_ALERT = "security_alert"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    GDPR_REQUEST = "gdpr_request"
    GDPR_DATA_DELETED = "gdpr_data_deleted"


class ConsentType(str, enum.Enum):
    """Tipos de consentimento LGPD"""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    DATA_PROCESSING = "data_processing"
    THIRD_PARTY = "third_party"


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
    client_metadata = Column(JSON, nullable=True)  # Dados adicionais do cliente
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
    conversation_metadata = Column(JSON, nullable=True)  # Dados adicionais da conversa
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    encerrada_em = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    cliente = relationship("ClienteWhatsApp", back_populates="conversas")
    atendente = relationship("Usuario", back_populates="conversas_atendidas")
    mensagens = relationship("Mensagem", back_populates="conversa", cascade="all, delete-orphan")
    
    # Índices otimizados
    __table_args__ = (
        Index('idx_conversa_cliente_estado', 'cliente_id', 'estado'),
        Index('idx_conversa_atendente_ativo', 'atendente_id', 'estado'),
        Index('idx_conversa_chat_id', 'chat_id'),
        Index('idx_conversa_estado_prioridade', 'estado', 'prioridade'),
        Index('idx_conversa_created_at', 'created_at'),
        Index('idx_conversa_updated_at', 'updated_at'),
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
    conteudo = Column(Text, nullable=True)  # Deprecado - usar campos criptografados
    
    # CAMPOS CRIPTOGRAFADOS (SEMANA 1)
    conteudo_criptografado = Column(Text, nullable=True)  # Base64 do conteúdo AES-256
    iv = Column(String(255), nullable=True)  # Base64 do IV
    tipo_criptografia = Column(String(50), default="AES-256-CBC", nullable=True)
    
    tipo_mensagem = Column(Enum(MessageType), default=MessageType.TEXTO, nullable=False)
    arquivo_url = Column(String(500), nullable=True)  # URL do arquivo se for mídia
    message_metadata = Column(JSON, nullable=True)  # Dados adicionais da mensagem
    lida = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relacionamentos
    conversa = relationship("Conversa", back_populates="mensagens")
    
    # Índices otimizados
    __table_args__ = (
        Index('idx_mensagem_conversa_data', 'conversa_id', 'created_at'),
        Index('idx_mensagem_whatsapp_id', 'whatsapp_message_id'),
        Index('idx_mensagem_remetente', 'remetente_tipo', 'remetente_id'),
        Index('idx_mensagem_tipo_data', 'tipo_mensagem', 'created_at'),
        Index('idx_mensagem_lida', 'lida', 'created_at'),
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
    campaign_metadata = Column(JSON, nullable=True)
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


# ============================================================================
# NOVAS TABELAS SEMANA 1 - SEGURANÇA (GDPR/LGPD)
# ============================================================================

class AuditLogEnhanced(Base):
    """
    Log de auditoria com hash chaining para integridade
    
    Implementa blockchain-like integrity verification:
    hash = SHA256(event_id | timestamp | user_id | action | previous_hash)
    """
    __tablename__ = "audit_logs_enhanced"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)  # login_success, data_accessed, etc
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False)  # read, write, delete, export
    resource_type = Column(String(50), nullable=True)  # user, message, conversation, etc
    resource_id = Column(String(255), nullable=True)  # ID do recurso acessado
    status = Column(String(20), default="success")  # success, failed, error
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)  # Dados adicionais do evento
    
    # Hash chaining para integridade (blockchain-like)
    entry_hash = Column(String(64), nullable=False, unique=True)  # SHA256 do evento
    previous_hash = Column(String(64), nullable=True)  # Hash anterior (para chain validation)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relacionamentos
    usuario = relationship("Usuario")
    
    # Índices
    __table_args__ = (
        Index('idx_audit_enhanced_event_type', 'event_type', 'created_at'),
        Index('idx_audit_enhanced_user_action', 'user_id', 'action'),
        Index('idx_audit_enhanced_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_enhanced_hash_chain', 'entry_hash', 'previous_hash'),
    )


class GDPRRequest(Base):
    """
    Requisição GDPR/LGPD do usuário
    
    Rastreia direito ao esquecimento, portabilidade e consentimento
    """
    __tablename__ = "gdpr_requests"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True)
    request_type = Column(Enum(GDPRRequestType), nullable=False)  # deletion, export, consent
    status = Column(Enum(GDPRRequestStatus), default=GDPRRequestStatus.PENDING)
    reason = Column(Text, nullable=True)  # Motivo da requisição
    
    # Confirmação
    confirmation_token = Column(String(255), nullable=True, unique=True)
    confirmation_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Backup para retenção legal
    backup_id = Column(String(255), nullable=True)  # ID do backup isolado
    backup_retention_until = Column(DateTime(timezone=True), nullable=True)  # Até quando guardar backup
    
    # Metadados
    requested_by = Column(String(255), nullable=False)  # user_id ou admin_id
    processed_by = Column(String(255), nullable=True)  # Admin que processou
    details = Column(JSON, nullable=True)  # Dados da requisição
    error_message = Column(Text, nullable=True)  # Se falhou, por quê
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    usuario = relationship("Usuario")
    
    # Índices
    __table_args__ = (
        Index('idx_gdpr_user_status', 'user_id', 'status'),
        Index('idx_gdpr_request_type', 'request_type', 'created_at'),
        Index('idx_gdpr_confirmation_token', 'confirmation_token'),
    )


class UserConsent(Base):
    """
    Rastreamento de consentimento LGPD do usuário
    
    Art. 7 - Consentimento: deve ser informado, específico e dado livremente
    """
    __tablename__ = "user_consents"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True)
    consent_type = Column(Enum(ConsentType), nullable=False)  # marketing, analytics, data_processing, third_party
    
    granted = Column(Boolean, default=False)  # Se foi concedido ou não
    version = Column(Integer, default=1)  # Versão do consentimento
    
    # Rastreamento
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    granted_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    
    # Contexto
    ip_address = Column(String(45), nullable=True)  # IP onde foi consentido
    user_agent = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)  # Descrição do que foi consentido
    
    # Validade
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Data de expiração (se aplicável)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    usuario = relationship("Usuario")
    
    # Índices
    __table_args__ = (
        Index('idx_consent_user_type', 'user_id', 'consent_type'),
        Index('idx_consent_granted', 'granted', 'created_at'),
        Index('idx_consent_expires', 'expires_at'),
    )


class TokenBlacklist(Base):
    """
    Blacklist de tokens JWT revogados
    
    Tokens adicionados aqui não podem ser usados
    """
    __tablename__ = "token_blacklists"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)  # SHA256 do token
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    
    reason = Column(String(100), default="logout")  # logout, password_change, admin_revoke
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Quando o token expira mesmo
    
    # Contexto
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Relacionamentos
    usuario = relationship("Usuario")
    
    # Índices
    __table_args__ = (
        Index('idx_token_blacklist_expires', 'expires_at'),
        Index('idx_token_blacklist_user', 'user_id', 'revoked_at'),
    )