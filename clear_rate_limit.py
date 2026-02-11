"""Script para limpar rate limit"""
from app.core.rate_limiter import rate_limiter
import asyncio

async def clear():
    # Limpar rate limit de login
    identifier = "login:127.0.0.1"
    
    # Como Redis está desabilitado, o rate limiter está usando memória
    # Vamos limpar o dicionário em memória
    if hasattr(rate_limiter, '_memory_store'):
        if identifier in rate_limiter._memory_store:
            del rate_limiter._memory_store[identifier]
            print(f"✅ Rate limit limpo para {identifier}")
        else:
            print(f"ℹ️  Nenhum rate limit encontrado para {identifier}")
    else:
        print("ℹ️  Rate limiter não está usando memória ou já foi limpo")
    
    print("\n🔓 Você pode tentar fazer login novamente!")

if __name__ == "__main__":
    asyncio.run(clear())
