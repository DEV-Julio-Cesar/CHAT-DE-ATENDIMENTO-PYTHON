"""
Configurações centralizadas da aplicação
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ISP Customer Support"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/isp_support"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CLUSTER_NODES: Optional[List[str]] = None
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # WhatsApp Business API
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None
    
    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


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