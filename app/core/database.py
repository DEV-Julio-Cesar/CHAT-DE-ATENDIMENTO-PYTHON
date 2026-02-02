"""
Gerenciador de banco de dados com otimizações
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy.sql import text
from sqlalchemy import event
from app.core.config import settings
from app.models.database import Base

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Gerenciador de conexões de banco de dados"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize(self):
        """Inicializar conexão com banco de dados"""
        if self._initialized:
            return
            
        try:
            # Configurar engine com otimizações
            self.engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=3600,  # Reciclar conexões a cada hora
                poolclass=AsyncAdaptedQueuePool if not settings.DEBUG else NullPool,
                connect_args={
                    "server_settings": {
                        "application_name": settings.APP_NAME,
                        "jit": "off",  # Desabilitar JIT para melhor performance em queries simples
                    }
                }
            )
            
            # Configurar session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,  # Controle manual de flush
                autocommit=False
            )
            
            # Configurar listeners para logging de queries lentas
            if settings.DEBUG:
                self._setup_query_logging()
            
            self._initialized = True
            logger.info("Database connection initialized", 
                       pool_size=settings.DATABASE_POOL_SIZE,
                       max_overflow=settings.DATABASE_MAX_OVERFLOW)
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    def _setup_query_logging(self):
        """Configurar logging de queries lentas"""
        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = asyncio.get_event_loop().time()
        
        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = asyncio.get_event_loop().time() - context._query_start_time
            if total > 0.5:  # Log queries que demoram mais de 500ms
                logger.warning("Slow query detected", 
                             duration=total, 
                             statement=statement[:200])
    
    async def close(self):
        """Fechar conexões"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager para sessões de banco"""
        if not self._initialized:
            await self.initialize()
            
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """Verificar saúde da conexão"""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Instância global
db_manager = DatabaseManager()


async def create_tables():
    """Criar tabelas do banco de dados"""
    if not db_manager._initialized:
        await db_manager.initialize()
    
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created/verified")


# Dependency para FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obter sessão de banco"""
    async with db_manager.get_session() as session:
        yield session


# Utilitários para transações
@asynccontextmanager
async def transaction():
    """Context manager para transações"""
    async with db_manager.get_session() as session:
        async with session.begin():
            yield session


async def execute_in_transaction(func, *args, **kwargs):
    """Executar função em transação"""
    async with transaction() as session:
        return await func(session, *args, **kwargs)