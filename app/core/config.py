"""
Configurações centralizadas da aplicação
Suporta carregamento de secrets via Secrets Manager
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


def get_secret_or_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Buscar secret do Secrets Manager ou variável de ambiente
    
    Ordem de prioridade:
    1. Secrets Manager (se SECRETS_PROVIDER != 'local')
    2. Variável de ambiente
    3. Valor default
    """
    # Verificar se deve usar Secrets Manager
    provider = os.getenv('SECRETS_PROVIDER', 'local').lower()
    
    if provider != 'local':
        try:
            from app.core.secrets_manager import get_secret
            value = get_secret(key)
            if value is not None:
                return value
        except Exception:
            pass  # Fallback para env
    
    # Fallback para variável de ambiente
    return os.getenv(key, default)


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ISP Customer Support"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Database MariaDB/MySQL (único banco de dados usado)
    # Exemplo: mysql+aiomysql://usuario:senha@localhost:3306/cianet_provedor
    DATABASE_URL: str = "mysql+aiomysql://root:suasenha@localhost:3306/cianet_provedor"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Security Settings - Password Policy
    PASSWORD_MIN_LENGTH: int = 12  # Aumentado de 8 para 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_HISTORY_COUNT: int = 5  # Não reutilizar últimas 5 senhas
    PASSWORD_EXPIRY_DAYS: int = 90  # Expirar senha após 90 dias
    
    # Security Settings - Authentication
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    SESSION_ABSOLUTE_TIMEOUT_HOURS: int = 1  # Reduzido de 24 para 1 hora
    SESSION_IDLE_TIMEOUT_MINUTES: int = 30  # Timeout por inatividade
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Security Settings - Encryption
    MASTER_ENCRYPTION_KEY: Optional[str] = None  # Para criptografia de dados sensíveis
    ENCRYPTION_SALT: str = "default-salt-change-in-production"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CLUSTER_NODES: Optional[List[str]] = None
    
    # JWT
    # IMPORTANTE: Em produção, armazene no Secrets Manager
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # WhatsApp Business API
    # IMPORTANTE: Em produção, armazene no Secrets Manager
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_APP_SECRET: Optional[str] = None
    WHATSAPP_API_VERSION: str = "v18.0"
    
    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Chatbot Settings
    CHATBOT_COMPANY_NAME: str = "TelecomISP"
    CHATBOT_MAX_CONTEXT_MESSAGES: int = 10
    CHATBOT_RESPONSE_MAX_TOKENS: int = 1024
    CHATBOT_TEMPERATURE: float = 0.7
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 200
    
    # Monitoring
    PROMETHEUS_METRICS_PATH: str = "/metrics"
    LOG_LEVEL: str = "INFO"
    
    # Business Rules
    MAX_WHATSAPP_CLIENTS: int = 10000
    MAX_BOT_ATTEMPTS: int = 3
    BUSINESS_HOURS_START: int = 8
    BUSINESS_HOURS_END: int = 18
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: str = "image/jpeg,image/png,application/pdf,text/plain"
    
    # WhatsApp Session Settings
    WHATSAPP_SESSION_TIMEOUT_HOURS: int = 24
    WHATSAPP_MAX_RETRIES: int = 3
    WHATSAPP_RETRY_DELAY_SECONDS: float = 1.0
    
    # CORS e Hosts
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # SGP Integration
    # IMPORTANTE: Em produção, armazene no Secrets Manager
    SGP_BASE_URL: str = "http://sua-url-sgp.com.br/api/v1"
    SGP_TOKEN: str = ""
    SGP_APP_NAME: str = "Julio Sistem"
    SGP_USERNAME: str = ""
    SGP_PASSWORD: str = ""
    SGP_TIMEOUT: int = 30
    SGP_MAX_RETRIES: int = 3
    
    # Google Gemini AI
    # IMPORTANTE: Em produção, armazene no Secrets Manager
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar variáveis extras no .env


# Singleton instance
settings = Settings()


# Database configuration
def get_database_url() -> str:
    """Get database URL with proper configuration"""
    return settings.DATABASE_URL


# Redis configuration
def get_redis_config() -> dict:
    """Get Redis configuration"""
    if settings.REDIS_CLUSTER_NODES:
        return {
            "cluster_nodes": [
                {"host": node.split(":")[0], "port": int(node.split(":")[1])}
                for node in settings.REDIS_CLUSTER_NODES
            ],
            "decode_responses": True,
            "skip_full_coverage_check": True,
        }
    else:
        return {"url": settings.REDIS_URL, "decode_responses": True}


# Logging configuration
def get_logging_config() -> dict:
    """Get structured logging configuration"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "structlog.stdlib.ProcessorFormatter",
                "processor": "structlog.dev.ConsoleRenderer",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
        },
    }