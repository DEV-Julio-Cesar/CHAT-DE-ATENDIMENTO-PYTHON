"""
Configuração e gerenciamento do banco de dados
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import structlog

from app.core.config import settings
from app.models.database import Base

logger = structlog.get_logger(__name__)

# Engine assíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verifica conexões antes de usar
    pool_recycle=3600,   # Recicla conexões a cada hora
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def create_tables():
    """Criar todas as tabelas do banco de dados"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


async def drop_tables():
    """Dropar todas as tabelas (usar apenas em desenvolvimento)"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error("Failed to drop database tables", error=str(e))
        raise


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para sessões de banco de dados
    Garante que a sessão seja fechada mesmo em caso de erro
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para FastAPI
    Fornece uma sessão de banco de dados para cada request
    """
    async with get_db_session() as session:
        yield session


class DatabaseManager:
    """Gerenciador de operações de banco de dados"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
    
    async def health_check(self) -> bool:
        """Verificar se o banco de dados está acessível"""
        try:
            async with self.session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    async def get_connection_info(self) -> dict:
        """Obter informações sobre as conexões do pool"""
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }
    
    async def close(self):
        """Fechar todas as conexões do pool"""
        await self.engine.dispose()
        logger.info("Database connections closed")


# Instância global do gerenciador
db_manager = DatabaseManager()


# Utilitários para transações
class TransactionManager:
    """Gerenciador de transações com rollback automático"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._savepoints = []
    
    async def __aenter__(self):
        # Criar savepoint para rollback parcial se necessário
        savepoint = await self.session.begin_nested()
        self._savepoints.append(savepoint)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        savepoint = self._savepoints.pop()
        if exc_type is not None:
            await savepoint.rollback()
            logger.warning("Transaction rolled back", error=str(exc_val))
        else:
            await savepoint.commit()
    
    async def rollback_to_savepoint(self):
        """Rollback para o último savepoint"""
        if self._savepoints:
            savepoint = self._savepoints[-1]
            await savepoint.rollback()


# Decorador para retry de operações de banco
import asyncio
from functools import wraps
from typing import Callable, Any

def db_retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorador para retry automático de operações de banco de dados
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            "Database operation failed, retrying",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(e)
                        )
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(
                            "Database operation failed after all retries",
                            attempts=max_attempts,
                            error=str(e)
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


# Utilitário para paginação
from sqlalchemy import select, func
from typing import TypeVar, Generic, List

T = TypeVar('T')

class PaginatedResult(Generic[T]):
    """Resultado paginado com metadados"""
    
    def __init__(
        self,
        items: List[T],
        total: int,
        page: int,
        per_page: int,
        pages: int
    ):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = pages
        self.has_prev = page > 1
        self.has_next = page < pages


async def paginate_query(
    session: AsyncSession,
    query,
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100
) -> PaginatedResult:
    """
    Paginar uma query SQLAlchemy
    """
    # Limitar per_page
    per_page = min(per_page, max_per_page)
    
    # Contar total de registros
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)
    
    # Calcular páginas
    pages = (total + per_page - 1) // per_page
    
    # Aplicar offset e limit
    offset = (page - 1) * per_page
    items_query = query.offset(offset).limit(per_page)
    result = await session.execute(items_query)
    items = result.scalars().all()
    
    return PaginatedResult(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )