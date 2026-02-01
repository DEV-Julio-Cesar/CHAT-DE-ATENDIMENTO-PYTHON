#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurações Centralizadas do Sistema ISP Chat
Gerencia todas as configurações de ambiente, banco de dados, segurança e integrações
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os
from pathlib import Path

class Settings(BaseSettings):
    """
    Classe de configurações centralizadas usando Pydantic
    Carrega automaticamente variáveis de ambiente e fornece valores padrão
    """
    
    # === CONFIGURAÇÕES DA APLICAÇÃO ===
    APP_NAME: str = Field(
        default="ISP Chat System",
        description="Nome da aplicação"
    )
    
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Versão da aplicação"
    )
    
    DEBUG: bool = Field(
        default=True,
        description="Modo debug (True para desenvolvimento)"
    )
    
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Nível de log (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # === CONFIGURAÇÕES DO SERVIDOR ===
    HOST: str = Field(
        default="0.0.0.0",
        description="Host do servidor"
    )
    
    PORT: int = Field(
        default=8000,
        description="Porta do servidor principal"
    )
    
    # === CONFIGURAÇÕES DO BANCO DE DADOS ===
    DATABASE_URL: str = Field(
        default="mssql+aioodbc:///?odbc_connect=DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=ISPChat;Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=yes;",
        description="URL de conexão com SQL Server"
    )
    
    DATABASE_POOL_SIZE: int = Field(
        default=20,
        description="Tamanho do pool de conexões"
    )
    
    DATABASE_MAX_OVERFLOW: int = Field(
        default=30,
        description="Máximo de conexões extras"
    )
    
    # === CONFIGURAÇÕES DO REDIS ===
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="URL de conexão com Redis"
    )
    
    REDIS_DB: int = Field(
        default=0,
        description="Número do banco Redis"
    )
    
    REDIS_MAX_CONNECTIONS: int = Field(
        default=50,
        description="Máximo de conexões Redis"
    )
    
    # === CONFIGURAÇÕES DE SEGURANÇA ===
    JWT_SECRET: str = Field(
        default="your-super-secret-jwt-key-change-in-production-2026",
        description="Chave secreta para JWT (MUDE EM PRODUÇÃO!)"
    )
    
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algoritmo de criptografia JWT"
    )
    
    JWT_EXPIRE_HOURS: int = Field(
        default=24,
        description="Tempo de expiração do token em horas"
    )
    
    # === CONFIGURAÇÕES DE RATE LIMITING ===
    MAX_LOGIN_ATTEMPTS: int = Field(
        default=5,
        description="Máximo de tentativas de login"
    )
    
    LOCKOUT_DURATION_MINUTES: int = Field(
        default=15,
        description="Duração do bloqueio em minutos"
    )
    
    # === CONFIGURAÇÕES DO WHATSAPP ===
    WHATSAPP_ACCESS_TOKEN: Optional[str] = Field(
        default="EAAYour_Access_Token_Here",
        description="Token de acesso da API do WhatsApp Business"
    )
    
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = Field(
        default="123456789012345",
        description="ID do número de telefone WhatsApp"
    )
    
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = Field(
        default="webhook_verify_token_2026_secure",
        description="Token de verificação do webhook"
    )
    
    WHATSAPP_API_VERSION: str = Field(
        default="v18.0",
        description="Versão da API do WhatsApp"
    )
    
    WHATSAPP_WEBHOOK_URL: Optional[str] = Field(
        default="https://your-domain.com/webhook/whatsapp",
        description="URL do webhook configurada no WhatsApp"
    )
    
    # === CONFIGURAÇÕES DE IA ===
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="Chave da API OpenAI"
    )
    
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Chave da API Google Gemini"
    )
    
    AI_MODEL_DEFAULT: str = Field(
        default="gpt-3.5-turbo",
        description="Modelo de IA padrão"
    )
    
    AI_MAX_TOKENS: int = Field(
        default=1000,
        description="Máximo de tokens por resposta"
    )
    
    # === CONFIGURAÇÕES DE CORS ===
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="Origens permitidas para CORS"
    )
    
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Permitir credenciais CORS"
    )
    
    # === CONFIGURAÇÕES DE MONITORAMENTO ===
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Habilitar coleta de métricas"
    )
    
    METRICS_PORT: int = Field(
        default=9090,
        description="Porta para métricas Prometheus"
    )
    
    # === CONFIGURAÇÕES DE AMBIENTE ===
    ENVIRONMENT: str = Field(
        default="development",
        description="Ambiente (development, staging, production)"
    )
    
    # === CONFIGURAÇÕES DE UPLOAD ===
    MAX_FILE_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Tamanho máximo de arquivo em bytes"
    )
    
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Diretório para uploads"
    )
    
    class Config:
        """
        Configurações do Pydantic
        """
        env_file = ".env"  # Carrega automaticamente do arquivo .env
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    def get_database_url(self) -> str:
        """
        Retorna a URL do banco de dados formatada
        """
        return self.DATABASE_URL
    
    def get_redis_url(self) -> str:
        """
        Retorna a URL do Redis formatada
        """
        return f"{self.REDIS_URL}/{self.REDIS_DB}"
    
    def is_production(self) -> bool:
        """
        Verifica se está em ambiente de produção
        """
        return self.ENVIRONMENT.lower() == "production"
    
    def is_development(self) -> bool:
        """
        Verifica se está em ambiente de desenvolvimento
        """
        return self.ENVIRONMENT.lower() == "development"
    
    def get_cors_config(self) -> dict:
        """
        Retorna configuração CORS formatada
        """
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_credentials": self.CORS_ALLOW_CREDENTIALS,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

# Instância global das configurações
# Carrega automaticamente variáveis de ambiente
settings = Settings()

# Função para validar configurações críticas
def validate_settings():
    """
    Valida configurações críticas do sistema
    Levanta exceções se configurações obrigatórias estão faltando
    """
    errors = []
    
    # Validar configurações de produção
    if settings.is_production():
        if settings.JWT_SECRET == "your-super-secret-jwt-key-change-in-production-2026":
            errors.append("JWT_SECRET deve ser alterado em produção!")
        
        if not settings.WHATSAPP_ACCESS_TOKEN:
            errors.append("WHATSAPP_ACCESS_TOKEN é obrigatório em produção!")
        
        if not settings.OPENAI_API_KEY and not settings.GEMINI_API_KEY:
            errors.append("Pelo menos uma chave de IA deve ser configurada!")
    
    # Validar URLs de conexão
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL é obrigatória!")
    
    if not settings.REDIS_URL:
        errors.append("REDIS_URL é obrigatória!")
    
    if errors:
        raise ValueError(f"Erros de configuração: {'; '.join(errors)}")
    
    return True

# Validar configurações na importação (apenas em produção)
if settings.is_production():
    validate_settings()