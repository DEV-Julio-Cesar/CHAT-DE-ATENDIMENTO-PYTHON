#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitários de Banco de Dados - SQL Server
Configuração e gerenciamento de conexões com SQL Server
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator
import logging
from shared.config.settings import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

# Engine global
engine = None
AsyncSessionLocal = None

async def init_db():
    """
    Inicializar conexão com banco de dados
    """
    global engine, AsyncSessionLocal
    
    try:
        # Criar engine assíncrono
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,  # Log SQL queries em debug
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verificar conexões antes de usar
            pool_recycle=3600,   # Reciclar conexões a cada hora
        )
        
        # Criar session factory
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Testar conexão
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT @@VERSION"))
            version = result.scalar()
            logger.info(f"✅ Conectado ao SQL Server: {version.split('(')[0].strip()}")
        
        logger.info("✅ Banco de dados inicializado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
        raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para obter sessão do banco de dados
    """
    if AsyncSessionLocal is None:
        await init_db()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Erro na sessão do banco: {e}")
            raise
        finally:
            await session.close()

async def close_db():
    """
    Fechar conexões do banco de dados
    """
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("✅ Conexões do banco fechadas")

async def test_connection():
    """
    Testar conexão com banco de dados
    """
    try:
        if engine is None:
            await init_db()
        
        async with engine.begin() as conn:
            # Testar consulta básica
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                logger.info("✅ Teste de conexão bem-sucedido")
                return True
            else:
                logger.error("❌ Teste de conexão falhou")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro no teste de conexão: {e}")
        return False

async def get_database_info():
    """
    Obter informações do banco de dados
    """
    try:
        if engine is None:
            await init_db()
        
        async with engine.begin() as conn:
            # Informações básicas
            info = {}
            
            # Versão do SQL Server
            result = await conn.execute(text("SELECT @@VERSION"))
            info['version'] = result.scalar()
            
            # Nome do banco
            result = await conn.execute(text("SELECT DB_NAME()"))
            info['database'] = result.scalar()
            
            # Número de tabelas
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_CATALOG = DB_NAME()
            """))
            info['tables_count'] = result.scalar()
            
            # Tamanho do banco (em MB)
            result = await conn.execute(text("""
                SELECT 
                    SUM(CAST(FILEPROPERTY(name, 'SpaceUsed') AS bigint) * 8192.) / 1024 / 1024 AS size_mb
                FROM sys.database_files 
                WHERE type = 0
            """))
            info['size_mb'] = round(result.scalar() or 0, 2)
            
            return info
            
    except Exception as e:
        logger.error(f"❌ Erro ao obter informações do banco: {e}")
        return {}

async def execute_raw_sql(sql: str, params: dict = None):
    """
    Executar SQL bruto
    """
    try:
        if engine is None:
            await init_db()
        
        async with engine.begin() as conn:
            if params:
                result = await conn.execute(text(sql), params)
            else:
                result = await conn.execute(text(sql))
            
            return result
            
    except Exception as e:
        logger.error(f"❌ Erro ao executar SQL: {e}")
        raise

async def check_table_exists(table_name: str) -> bool:
    """
    Verificar se tabela existe
    """
    try:
        result = await execute_raw_sql("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = :table_name AND TABLE_CATALOG = DB_NAME()
        """, {"table_name": table_name})
        
        count = result.scalar()
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabela {table_name}: {e}")
        return False

async def get_table_row_count(table_name: str) -> int:
    """
    Obter número de registros em uma tabela
    """
    try:
        result = await execute_raw_sql(f"SELECT COUNT(*) FROM {table_name}")
        return result.scalar()
        
    except Exception as e:
        logger.error(f"❌ Erro ao contar registros da tabela {table_name}: {e}")
        return 0

async def backup_table_to_json(table_name: str, output_file: str):
    """
    Fazer backup de tabela para JSON
    """
    try:
        import json
        from pathlib import Path
        
        # Obter dados da tabela
        result = await execute_raw_sql(f"SELECT * FROM {table_name}")
        rows = result.fetchall()
        
        # Converter para lista de dicionários
        data = []
        for row in rows:
            row_dict = {}
            for i, column in enumerate(result.keys()):
                value = row[i]
                # Converter tipos não serializáveis
                if hasattr(value, 'isoformat'):  # datetime
                    value = value.isoformat()
                elif isinstance(value, bytes):  # binary data
                    value = value.hex()
                row_dict[column] = value
            data.append(row_dict)
        
        # Salvar em arquivo JSON
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'table': table_name,
                'count': len(data),
                'exported_at': datetime.now().isoformat(),
                'data': data
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Backup da tabela {table_name} salvo em {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao fazer backup da tabela {table_name}: {e}")
        return False

# Função de conveniência para importar
__all__ = [
    'Base',
    'init_db',
    'get_db',
    'close_db',
    'test_connection',
    'get_database_info',
    'execute_raw_sql',
    'check_table_exists',
    'get_table_row_count',
    'backup_table_to_json'
]