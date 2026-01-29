"""
Cliente Redis para cache distribuído e sessões
"""
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
import structlog
import json
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta

from app.core.config import settings, get_redis_config

logger = structlog.get_logger(__name__)


class RedisManager:
    """Gerenciador de conexões Redis com suporte a cluster"""
    
    def __init__(self):
        self.client: Optional[Union[redis.Redis, RedisCluster]] = None
        self._is_cluster = bool(settings.REDIS_CLUSTER_NODES)
    
    async def initialize(self):
        """Inicializar conexão Redis"""
        try:
            config = get_redis_config()
            
            if self._is_cluster:
                self.client = RedisCluster(**config)
            else:
                self.client = redis.from_url(**config)
            
            # Testar conexão
            await self.client.ping()
            logger.info("Redis connection established", is_cluster=self._is_cluster)
            
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def close(self):
        """Fechar conexão Redis"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")
    
    async def health_check(self) -> bool:
        """Verificar se Redis está acessível"""
        try:
            if self.client:
                await self.client.ping()
                return True
            return False
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False
    
    # Operações básicas
    async def get(self, key: str) -> Optional[str]:
        """Obter valor por chave"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error("Redis GET failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Definir valor com TTL opcional"""
        try:
            return await self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
        except Exception as e:
            logger.error("Redis SET failed", key=key, error=str(e))
            return False
    
    async def delete(self, *keys: str) -> int:
        """Deletar chaves"""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error("Redis DELETE failed", keys=keys, error=str(e))
            return 0
    
    async def exists(self, *keys: str) -> int:
        """Verificar se chaves existem"""
        try:
            return await self.client.exists(*keys)
        except Exception as e:
            logger.error("Redis EXISTS failed", keys=keys, error=str(e))
            return 0
    
    async def expire(self, key: str, time: int) -> bool:
        """Definir TTL para chave"""
        try:
            return await self.client.expire(key, time)
        except Exception as e:
            logger.error("Redis EXPIRE failed", key=key, error=str(e))
            return False
    
    # Operações com JSON
    async def get_json(self, key: str) -> Optional[Dict]:
        """Obter objeto JSON"""
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON from Redis", key=key, error=str(e))
            return None
    
    async def set_json(
        self, 
        key: str, 
        value: Dict, 
        ex: Optional[int] = None
    ) -> bool:
        """Definir objeto JSON"""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_str, ex=ex)
        except (TypeError, ValueError) as e:
            logger.error("Failed to encode JSON for Redis", key=key, error=str(e))
            return False
    
    # Operações com Hash
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Obter campo de hash"""
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error("Redis HGET failed", name=name, key=key, error=str(e))
            return None
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Definir campo de hash"""
        try:
            return await self.client.hset(name, key, value)
        except Exception as e:
            logger.error("Redis HSET failed", name=name, key=key, error=str(e))
            return 0
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Obter todos os campos de hash"""
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error("Redis HGETALL failed", name=name, error=str(e))
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Deletar campos de hash"""
        try:
            return await self.client.hdel(name, *keys)
        except Exception as e:
            logger.error("Redis HDEL failed", name=name, keys=keys, error=str(e))
            return 0
    
    # Operações com Set
    async def sadd(self, name: str, *values: str) -> int:
        """Adicionar membros ao set"""
        try:
            return await self.client.sadd(name, *values)
        except Exception as e:
            logger.error("Redis SADD failed", name=name, error=str(e))
            return 0
    
    async def srem(self, name: str, *values: str) -> int:
        """Remover membros do set"""
        try:
            return await self.client.srem(name, *values)
        except Exception as e:
            logger.error("Redis SREM failed", name=name, error=str(e))
            return 0
    
    async def smembers(self, name: str) -> set:
        """Obter todos os membros do set"""
        try:
            return await self.client.smembers(name)
        except Exception as e:
            logger.error("Redis SMEMBERS failed", name=name, error=str(e))
            return set()
    
    async def sismember(self, name: str, value: str) -> bool:
        """Verificar se valor está no set"""
        try:
            return await self.client.sismember(name, value)
        except Exception as e:
            logger.error("Redis SISMEMBER failed", name=name, value=value, error=str(e))
            return False
    
    # Operações com List
    async def lpush(self, name: str, *values: str) -> int:
        """Adicionar valores no início da lista"""
        try:
            return await self.client.lpush(name, *values)
        except Exception as e:
            logger.error("Redis LPUSH failed", name=name, error=str(e))
            return 0
    
    async def rpush(self, name: str, *values: str) -> int:
        """Adicionar valores no final da lista"""
        try:
            return await self.client.rpush(name, *values)
        except Exception as e:
            logger.error("Redis RPUSH failed", name=name, error=str(e))
            return 0
    
    async def lpop(self, name: str) -> Optional[str]:
        """Remover e retornar primeiro elemento da lista"""
        try:
            return await self.client.lpop(name)
        except Exception as e:
            logger.error("Redis LPOP failed", name=name, error=str(e))
            return None
    
    async def rpop(self, name: str) -> Optional[str]:
        """Remover e retornar último elemento da lista"""
        try:
            return await self.client.rpop(name)
        except Exception as e:
            logger.error("Redis RPOP failed", name=name, error=str(e))
            return None
    
    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Obter range de elementos da lista"""
        try:
            return await self.client.lrange(name, start, end)
        except Exception as e:
            logger.error("Redis LRANGE failed", name=name, error=str(e))
            return []
    
    # Rate Limiting
    async def rate_limit_check(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> tuple[bool, int]:
        """
        Verificar rate limit usando sliding window
        Retorna (permitido, tentativas_restantes)
        """
        try:
            pipe = self.client.pipeline()
            now = int(time.time())
            
            # Remover entradas antigas
            pipe.zremrangebyscore(key, 0, now - window)
            
            # Contar tentativas atuais
            pipe.zcard(key)
            
            # Adicionar tentativa atual
            pipe.zadd(key, {str(now): now})
            
            # Definir TTL
            pipe.expire(key, window)
            
            results = await pipe.execute()
            current_count = results[1]
            
            if current_count < limit:
                return True, limit - current_count - 1
            else:
                # Remover a tentativa que acabamos de adicionar
                await self.client.zrem(key, str(now))
                return False, 0
                
        except Exception as e:
            logger.error("Rate limit check failed", key=key, error=str(e))
            # Em caso de erro, permitir a operação
            return True, limit
    
    # Cache com TTL automático
    async def cache_set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 3600
    ) -> bool:
        """Cache com serialização automática"""
        try:
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value, ensure_ascii=False)
            else:
                serialized = str(value)
            
            return await self.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Cache com deserialização automática"""
        try:
            value = await self.get(key)
            if value is None:
                return None
            
            # Tentar deserializar como JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Se não for JSON, retornar como string
                return value
                
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None


# Instância global
redis_manager = RedisManager()


# Utilitários para chaves de cache
class CacheKeys:
    """Constantes para chaves de cache"""
    
    # Sessões de usuário
    USER_SESSION = "session:{user_id}"
    USER_PERMISSIONS = "permissions:{user_id}"
    
    # WhatsApp
    WHATSAPP_CLIENT = "wa_client:{client_id}"
    WHATSAPP_SESSION = "wa_session:{client_id}"
    
    # Conversas
    CONVERSATION_STATE = "conv:{conversation_id}"
    CONVERSATION_MESSAGES = "conv_msgs:{conversation_id}"
    
    # Rate limiting
    RATE_LIMIT_USER = "rate:{user_id}:{endpoint}"
    RATE_LIMIT_IP = "rate:ip:{ip}:{endpoint}"
    
    # Métricas
    METRICS_DAILY = "metrics:{date}:{type}"
    METRICS_HOURLY = "metrics:{date}:{hour}:{type}"
    
    # Configurações
    SYSTEM_CONFIG = "config:{key}"
    
    # Filas
    QUEUE_WAITING = "queue:waiting"
    QUEUE_PROCESSING = "queue:processing"
    
    @staticmethod
    def format_key(template: str, **kwargs) -> str:
        """Formatar chave de cache com parâmetros"""
        return template.format(**kwargs)


import time