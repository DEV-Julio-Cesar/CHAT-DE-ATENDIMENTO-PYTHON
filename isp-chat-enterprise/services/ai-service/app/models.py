#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelos de dados do AI Service
Define estruturas para IA, análise de sentimento, respostas automáticas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, JSON, ForeignKey
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

class AIProvider(str, Enum):
    """Provedor de IA"""
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    LOCAL = "local"

class AIModelType(str, Enum):
    """Tipo de modelo de IA"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    SENTIMENT = "sentiment"
    CLASSIFICATION = "classification"

class SentimentType(str, Enum):
    """Tipo de sentimento"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class ResponseType(str, Enum):
    """Tipo de resposta automática"""
    GREETING = "greeting"
    FAQ = "faq"
    ESCALATION = "escalation"
    CLOSING = "closing"
    CUSTOM = "custom"

class AIRequestStatus(str, Enum):
    """Status da requisição de IA"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

# === MODELOS SQLALCHEMY ===

class AIModel(Base):
    """
    Modelo de configuração de IA
    Define modelos disponíveis e suas configurações
    """
    __tablename__ = "ai_models"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    
    # Identificação
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuração
    provider = Column(String(20), nullable=False, index=True)
    model_type = Column(String(20), nullable=False, index=True)
    model_id = Column(String(100), nullable=False)  # ID do modelo no provedor
    
    # Parâmetros
    max_tokens = Column(Integer, nullable=False, default=1000)
    temperature = Column(Float, nullable=False, default=0.7)
    top_p = Column(Float, nullable=False, default=1.0)
    frequency_penalty = Column(Float, nullable=False, default=0.0)
    presence_penalty = Column(Float, nullable=False, default=0.0)
    
    # Controle
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=1)
    
    # Custos e limites
    cost_per_token = Column(Float, nullable=True)
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    rate_limit_per_day = Column(Integer, nullable=False, default=1000)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    requests = relationship("AIRequest", back_populates="model")

class AIRequest(Base):
    """
    Histórico de requisições para IA
    Armazena todas as interações com modelos de IA
    """
    __tablename__ = "ai_requests"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    
    # Relacionamentos
    model_id = Column(UNIQUEIDENTIFIER, ForeignKey("ai_models.id"), nullable=False, index=True)
    conversation_id = Column(UNIQUEIDENTIFIER, nullable=True, index=True)  # Referência externa
    user_id = Column(UNIQUEIDENTIFIER, nullable=True, index=True)  # Referência externa
    
    # Request
    prompt = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)  # Contexto adicional
    parameters = Column(JSON, nullable=True)  # Parâmetros específicos
    
    # Response
    response = Column(Text, nullable=True)
    response_metadata = Column(JSON, nullable=True)  # Metadados da resposta
    
    # Controle
    status = Column(String(20), nullable=False, default=AIRequestStatus.PENDING.value, index=True)
    error_message = Column(Text, nullable=True)
    
    # Métricas
    tokens_used = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)  # Em segundos
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relacionamentos
    model = relationship("AIModel", back_populates="requests")

class SentimentAnalysis(Base):
    """
    Análise de sentimento de mensagens
    Armazena resultados de análise de sentimento
    """
    __tablename__ = "sentiment_analysis"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    
    # Referências
    conversation_id = Column(UNIQUEIDENTIFIER, nullable=False, index=True)
    message_id = Column(UNIQUEIDENTIFIER, nullable=True, index=True)
    
    # Análise
    text = Column(Text, nullable=False)
    sentiment = Column(String(20), nullable=False, index=True)
    confidence = Column(Float, nullable=False)  # 0.0 a 1.0
    
    # Detalhes
    positive_score = Column(Float, nullable=False, default=0.0)
    negative_score = Column(Float, nullable=False, default=0.0)
    neutral_score = Column(Float, nullable=False, default=0.0)
    
    # Metadados
    language = Column(String(10), nullable=True)
    keywords = Column(JSON, nullable=True)  # Palavras-chave extraídas
    emotions = Column(JSON, nullable=True)  # Emoções detectadas
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class AutoResponse(Base):
    """
    Respostas automáticas configuradas
    Define respostas automáticas baseadas em contexto
    """
    __tablename__ = "auto_responses"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    
    # Identificação
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    response_type = Column(String(20), nullable=False, index=True)
    
    # Condições
    triggers = Column(JSON, nullable=False)  # Palavras-chave, padrões
    conditions = Column(JSON, nullable=True)  # Condições adicionais
    
    # Resposta
    response_text = Column(Text, nullable=False)
    response_variations = Column(JSON, nullable=True)  # Variações da resposta
    
    # Configuração
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=1)
    use_ai_enhancement = Column(Boolean, nullable=False, default=False)
    
    # Métricas
    usage_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Float, nullable=False, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# === SCHEMAS PYDANTIC ===

class AIModelBase(BaseModel):
    """Schema base para modelo de IA"""
    name: str = Field(..., description="Nome único do modelo")
    display_name: str = Field(..., description="Nome para exibição")
    description: Optional[str] = Field(None, description="Descrição do modelo")
    provider: AIProvider = Field(..., description="Provedor de IA")
    model_type: AIModelType = Field(..., description="Tipo do modelo")
    model_id: str = Field(..., description="ID do modelo no provedor")

class AIModelCreate(AIModelBase):
    """Schema para criar modelo de IA"""
    max_tokens: int = Field(1000, description="Máximo de tokens")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperatura")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Top P")
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="Penalidade de frequência")
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="Penalidade de presença")
    cost_per_token: Optional[float] = Field(None, description="Custo por token")
    rate_limit_per_minute: int = Field(60, description="Limite por minuto")
    rate_limit_per_day: int = Field(1000, description="Limite por dia")

class AIModelResponse(AIModelBase):
    """Schema de resposta para modelo de IA"""
    id: str
    max_tokens: int
    temperature: float
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    is_active: bool
    is_default: bool
    priority: int
    cost_per_token: Optional[float]
    rate_limit_per_minute: int
    rate_limit_per_day: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AIRequestCreate(BaseModel):
    """Schema para criar requisição de IA"""
    model_name: Optional[str] = Field(None, description="Nome do modelo (usa padrão se não especificado)")
    prompt: str = Field(..., description="Prompt para a IA")
    conversation_id: Optional[str] = Field(None, description="ID da conversa")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parâmetros específicos")

class AIRequestResponse(BaseModel):
    """Schema de resposta para requisição de IA"""
    id: str
    model_name: str
    prompt: str
    response: Optional[str]
    status: AIRequestStatus
    error_message: Optional[str]
    tokens_used: Optional[int]
    cost: Optional[float]
    processing_time: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class SentimentAnalysisCreate(BaseModel):
    """Schema para criar análise de sentimento"""
    text: str = Field(..., description="Texto para análise")
    conversation_id: Optional[str] = Field(None, description="ID da conversa")
    message_id: Optional[str] = Field(None, description="ID da mensagem")

class SentimentAnalysisResponse(BaseModel):
    """Schema de resposta para análise de sentimento"""
    id: str
    conversation_id: Optional[str]
    message_id: Optional[str]
    text: str
    sentiment: SentimentType
    confidence: float
    positive_score: float
    negative_score: float
    neutral_score: float
    language: Optional[str]
    keywords: Optional[List[str]]
    emotions: Optional[Dict[str, float]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AutoResponseCreate(BaseModel):
    """Schema para criar resposta automática"""
    name: str = Field(..., description="Nome da resposta")
    description: Optional[str] = Field(None, description="Descrição")
    response_type: ResponseType = Field(..., description="Tipo de resposta")
    triggers: List[str] = Field(..., description="Palavras-chave que ativam a resposta")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Condições adicionais")
    response_text: str = Field(..., description="Texto da resposta")
    response_variations: Optional[List[str]] = Field(None, description="Variações da resposta")
    use_ai_enhancement: bool = Field(False, description="Usar IA para melhorar resposta")

class AutoResponseResponse(BaseModel):
    """Schema de resposta para resposta automática"""
    id: str
    name: str
    description: Optional[str]
    response_type: ResponseType
    triggers: List[str]
    conditions: Optional[Dict[str, Any]]
    response_text: str
    response_variations: Optional[List[str]]
    is_active: bool
    priority: int
    use_ai_enhancement: bool
    usage_count: int
    success_rate: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChatCompletionRequest(BaseModel):
    """Schema para requisição de chat completion"""
    message: str = Field(..., description="Mensagem do usuário")
    conversation_id: Optional[str] = Field(None, description="ID da conversa para contexto")
    model_name: Optional[str] = Field(None, description="Modelo específico")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperatura")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Máximo de tokens")
    system_prompt: Optional[str] = Field(None, description="Prompt do sistema")

class ChatCompletionResponse(BaseModel):
    """Schema de resposta para chat completion"""
    response: str = Field(..., description="Resposta da IA")
    model_used: str = Field(..., description="Modelo utilizado")
    tokens_used: int = Field(..., description="Tokens utilizados")
    processing_time: float = Field(..., description="Tempo de processamento")
    cost: Optional[float] = Field(None, description="Custo da requisição")
    request_id: str = Field(..., description="ID da requisição")

class AIStats(BaseModel):
    """Schema para estatísticas de IA"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_processing_time: float
    total_tokens_used: int
    total_cost: float
    requests_by_model: Dict[str, int]
    sentiment_distribution: Dict[str, int]
    auto_responses_triggered: int
    success_rate: float

class SuggestedResponse(BaseModel):
    """Schema para resposta sugerida"""
    text: str = Field(..., description="Texto da resposta sugerida")
    confidence: float = Field(..., description="Confiança na sugestão")
    type: ResponseType = Field(..., description="Tipo da resposta")
    reasoning: Optional[str] = Field(None, description="Explicação da sugestão")
    alternatives: Optional[List[str]] = Field(None, description="Alternativas")