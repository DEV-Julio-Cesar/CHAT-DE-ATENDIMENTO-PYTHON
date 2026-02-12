"""
Teste do servidor com Redis
"""
import asyncio
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.redis_client import redis_manager
from app.core.database import db_manager


async def test_connections():
    """Testar conexões"""
    print("🔍 Testando conexões do servidor...\n")
    
    # Testar Redis
    print("1️⃣ Testando Redis...")
    try:
        await redis_manager.initialize()
        health = await redis_manager.health_check()
        if health:
            print("   ✅ Redis: CONECTADO")
        else:
            print("   ❌ Redis: FALHOU no health check")
    except Exception as e:
        print(f"   ❌ Redis: ERRO - {e}")
    
    # Testar Database
    print("\n2️⃣ Testando Database...")
    try:
        await db_manager.initialize()
        health = await db_manager.health_check()
        if health:
            print("   ✅ Database: CONECTADO")
        else:
            print("   ❌ Database: FALHOU no health check")
    except Exception as e:
        print(f"   ❌ Database: ERRO - {e}")
    
    print("\n" + "="*50)
    print("✅ Teste concluído!")
    print("="*50)
    
    # Fechar conexões
    try:
        await redis_manager.close()
        await db_manager.close()
    except:
        pass


if __name__ == "__main__":
    asyncio.run(test_connections())
