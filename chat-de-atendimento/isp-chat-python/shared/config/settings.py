from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "ISP Chat System"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres123@localhost:5432/isp_chat"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    JWT_SECRET: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    
    # WhatsApp (migrar depois)
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    
    # OpenAI (migrar depois)
    OPENAI_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()