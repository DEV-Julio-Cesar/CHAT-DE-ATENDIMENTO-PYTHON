"""
Teste rápido de conexão com Redis
"""
import redis
import os
from dotenv import load_dotenv

load_dotenv()

def test_redis():
    """Testar conexão com Redis"""
    redis_url = os.getenv('REDIS_URL', 'redis://:PJPyHvjTbANU3JXK4DKMp2MlS8QV2mzulGUmLXHf@localhost:6379/0')
    
    print(f"🔍 Testando conexão com Redis...")
    print(f"URL: {redis_url.replace(redis_url.split('@')[0].split(':')[-1], '***')}")
    
    try:
        # Conectar
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Testar PING
        response = r.ping()
        print(f"✅ PING: {response}")
        
        # Testar SET/GET
        r.set("test_key", "funcionando!")
        value = r.get("test_key")
        print(f"✅ SET/GET: {value}")
        
        # Testar INFO
        info = r.info("server")
        print(f"✅ Redis versão: {info['redis_version']}")
        
        # Limpar
        r.delete("test_key")
        
        print("\n🎉 Redis está funcionando perfeitamente!")
        return True
        
    except redis.ConnectionError as e:
        print(f"\n❌ Erro de conexão: {e}")
        print("\n💡 Soluções:")
        print("1. Verificar se Redis está rodando:")
        print("   docker ps | grep redis")
        print("\n2. Iniciar Redis:")
        print('   docker run -d --name redis -p 6379:6379 redis:7-alpine redis-server --requirepass "PJPyHvjTbANU3JXK4DKMp2MlS8QV2mzulGUmLXHf"')
        print("\n3. Verificar senha no .env:")
        print("   REDIS_URL=redis://:senha@localhost:6379/0")
        return False
        
    except redis.AuthenticationError as e:
        print(f"\n❌ Erro de autenticação: {e}")
        print("\n💡 Senha incorreta no .env")
        print("Verificar REDIS_URL no arquivo .env")
        return False
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return False


if __name__ == "__main__":
    test_redis()
