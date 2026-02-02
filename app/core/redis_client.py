"""
Cliente Redis Avançado com Connection Pooling Otimizado
"""
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
from redis.asyncio.connection import ConnectionPool
import structlog
import json
import asyncio
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta
import time

from .config import settings, get_redis_config

logger = structlog.get_logger(__name__)


class AdvancedRedisManager:
    """Gerenciador Redis com connection pooling avançado"""
    
    def __init__(self):
        self.client: Optional[Union[redis.Redis, RedisCluster]] = None
        self.pool: Optional[ConnectionPool] = None
        self._is_cluster = bool(settings.REDIS_CLUSTER_NODES)
        self._connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }
    
    async def initialize(self):
        """Inicializar conexão Redis com pool otimizado"""
        try:
            config = get_redis_config()
            
            if self._is_cluster:
                # Configuração para cluster Redis
                self.client = RedisCluster(
                    **config,
                    max_connections=50,  # Pool maior para cluster
                    retry_on_timeout=True,
                    retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                    health_check_interval=30
                )
            else:
                # Pool de conexões otimizado para instância única
                self.pool = ConnectionPool.from_url(
                    config["url"],
                    max_connections=30,      # Pool de 30 conexões
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={
                        1: 1,  # TCP_KEEPIDLE
                        2: 3,  # TCP_KEEPINTVL  
                        3: 5,  # TCP_KEEPCNT
                    },
                    health_check_interval=30,
                    decode_responses=True
                )
                
                self.client = redis.Redis(
                    connection_pool=self.pool,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    retry_on_error=[redis.ConnectionError, redis.TimeoutError]
                )
            
            # Testar conexão
            await self.client.ping()
            logger.info("Advanced Redis connection established", 
                       is_cluster=self._is_cluster,
                       pool_size=30 if not self._is_cluster else 50)
            
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def close(self):
        """Fechar conexões Redis"""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
        logger.info("Redis connections closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Verificação de saúde avançada"""
        try:
            start_time = time.time()
            
            # Ping básico
            ping_result = await self.client.ping()
            ping_time = time.time() - start_time
            
            # Informações do pool
            pool_info = {}
            if self.pool:
                pool_info = {
                    "created_connections": self.pool.created_connections,
                    "available_connections": len(self.pool._available_connections),
                    "in_use_connections": len(self.pool._in_use_connections)
                }
            
            # Informações do servidor Redis
            info = await self.client.info()
            
            return {
                "status": "healthy" if ping_result else "unhealthy",
                "ping_time_ms": round(ping_time * 1000, 2),
                "pool_info": pool_info,
                "server_info": {
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                },
                "connection_stats": self._connection_stats
            }
            
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_stats": self._connection_stats
            }
    
    # Operações básicas otimizadas
    async def get(self, key: str) -> Optional[str]:
        """Obter valor por chave com retry automático"""
        for attempt in range(3):  # 3 tentativas
            try:
                result = await self.client.get(key)
                self._connection_stats["pool_hits"] += 1
                return result
            except (redis.ConnectionError, redis.TimeoutError) as e:
                self._connection_stats["pool_misses"] += 1
                if attempt == 2:  # Última tentativa
                    logger.error("Redis GET failed after retries", key=key, error=str(e))
                    return None
                await asyncio.sleep(0.1 * (attempt + 1))  # Backoff exponencial
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
        """Definir valor com retry automático"""
        for attempt in range(3):
            try:
                result = await self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
                self._connection_stats["pool_hits"] += 1
                return bool(result)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                self._connection_stats["pool_misses"] += 1
                if attempt == 2:
                    logger.error("Redis SET failed after retries", key=key, error=str(e))
                    return False
                await asyncio.sleep(0.1 * (attempt + 1))
            except Exception as e:
                logger.error("Redis SET failed", key=key, error=str(e))
                return False
    
    async def delete(self, *keys: str) -> int:
        """Deletar chaves"""
        try:
            if not keys:
                return 0
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
    
    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        """Buscar múltiplas chaves de uma vez (otimizado)"""
        try:
            if not keys:
                return []
            
            result = await self.client.mget(keys)
            self._connection_stats["pool_hits"] += 1
            return result
        except Exception as e:
            logger.error("Redis MGET failed", keys_count=len(keys), error=str(e))
            return [None] * len(keys)
    
    async def mset(self, mapping: Dict[str, str]) -> bool:
        """Definir múltiplas chaves de uma vez (otimizado)"""
        try:
            if not mapping:
                return True
            
            result = await self.client.mset(mapping)
            self._connection_stats["pool_hits"] += 1
            return bool(result)
        except Exception as e:
            logger.error("Redis MSET failed", keys_count=len(mapping), error=str(e))
            return False
    
    async def pipeline_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Executar operações em pipeline para melhor performance"""
        try:
            async with self.client.pipeline() as pipe:
                for op in operations:
                    method = getattr(pipe, op["method"])
                    args = op.get("args", [])
                    kwargs = op.get("kwargs", {})
                    method(*args, **kwargs)
                
                results = await pipe.execute()
                self._connection_stats["pool_hits"] += 1
                return results
                
        except Exception as e:
            logger.error("Redis pipeline failed", operations_count=len(operations), error=str(e))
            return [None] * len(operations)
    
    async def cache_with_ttl(self, key: str, data: Any, ttl: int = 3600) -> bool:
        """Cache inteligente com TTL"""
        try:
            serialized = json.dumps(data, default=str)
            return await self.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def get_or_cache(self, key: str, fetch_func, ttl: int = 3600):
        """Get or fetch pattern - busca no cache ou executa função"""
        try:
            # Tentar buscar no cache
            cached = await self.get(key)
            if cached:
                return json.loads(cached)
            
            # Se não encontrou, executar função e cachear
            data = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
            await self.cache_with_ttl(key, data, ttl)
            return data
            
        except Exception as e:
            logger.error("Get or cache failed", key=key, error=str(e))
            # Se falhar, tentar executar função diretamente
            return await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidar chaves que correspondem ao padrão"""
        try:
            keys = await self.client.keys(pattern)
            if keys:
                return await self.delete(*keys)
            return 0
        except Exception as e:
            logger.error("Pattern invalidation failed", pattern=pattern, error=str(e))
            return 0
    
    # Operações de Hash
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Obter valor de hash"""
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error("Redis HGET failed", name=name, key=key, error=str(e))
            return None
    
    async def hset(self, name: str, key: str, value: str) -> bool:
        """Definir valor em hash"""
        try:
            return await self.client.hset(name, key, value)
        except Exception as e:
            logger.error("Redis HSET failed", name=name, key=key, error=str(e))
            return False
    
    async def hgetall(self, name: str) -> dict:
        """Obter todos os valores de hash"""
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error("Redis HGETALL failed", name=name, error=str(e))
            return {}
    
    # Rate Limiting otimizado
    async def rate_limit_check(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Rate limiting com sliding window otimizado"""
        try:
            now = time.time()
            window_start = now - window
            
            async with self.client.pipeline() as pipe:
                # Remover entradas antigas
                pipe.zremrangebyscore(key, 0, window_start)
                
                # Adicionar entrada atual
                pipe.zadd(key, {str(now): now})
                
                # Contar entradas atuais
                pipe.zcard(key)
                
                # Definir TTL
                pipe.expire(key, window)
                
                results = await pipe.execute()
                current_count = results[2]  # Resultado do zcard
                
                if current_count <= limit:
                    return True, limit - current_count
                else:
                    # Remover a tentativa que acabamos de adicionar
                    await self.client.zrem(key, str(now))
                    return False, 0
                    
        except Exception as e:
            logger.error("Rate limit check failed", key=key, error=str(e))
            # Em caso de erro, permitir a operação
            return True, limit
    
    # Pub/Sub para WebSocket
    async def publish(self, channel: str, message: str) -> int:
        """Publicar mensagem em canal pub/sub"""
        try:
            return await self.client.publish(channel, message)
        except Exception as e:
            logger.error("Redis PUBLISH failed", channel=channel, error=str(e))
            return 0
    
    async def subscribe(self, *channels: str):
        """Inscrever em canais pub/sub"""
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error("Redis SUBSCRIBE failed", channels=channels, error=str(e))
            return None
    
    async def listen(self, pubsub):
        """Escutar mensagens de pub/sub"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message
        except Exception as e:
            logger.error("Redis LISTEN failed", error=str(e))
    
    # Operações de List para filas
    async def lpush(self, key: str, *values: str) -> int:
        """Adicionar no início da lista"""
        try:
            return await self.client.lpush(key, *values)
        except Exception as e:
            logger.error("Redis LPUSH failed", key=key, error=str(e))
            return 0
    
    async def rpush(self, key: str, *values: str) -> int:
        """Adicionar no final da lista"""
        try:
            return await self.client.rpush(key, *values)
        except Exception as e:
            logger.error("Redis RPUSH failed", key=key, error=str(e))
            return 0
    
    async def lpop(self, key: str) -> Optional[str]:
        """Remover e retornar do início da lista"""
        try:
            return await self.client.lpop(key)
        except Exception as e:
            logger.error("Redis LPOP failed", key=key, error=str(e))
            return None
    
    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Obter elementos da lista"""
        try:
            return await self.client.lrange(key, start, stop)
        except Exception as e:
            logger.error("Redis LRANGE failed", key=key, error=str(e))
            return []
    
    async def llen(self, key: str) -> int:
        """Obter tamanho da lista"""
        try:
            return await self.client.llen(key)
        except Exception as e:
            logger.error("Redis LLEN failed", key=key, error=str(e))
            return 0


# Instância global
redis_manager = AdvancedRedisManager()


# Chaves de cache padronizadas
class CacheKeys:
    """Chaves de cache padronizadas"""
    
    # Usuários
    USER_SESSION = "session:{user_id}"
    USER_PERMISSIONS = "permissions:{user_id}"
    USER_PROFILE = "profile:{user_id}"
    
    # Conversas
    CONVERSATION = "conv:{conversation_id}"
    CONVERSATION_MESSAGES = "conv_msgs:{conversation_id}"
    ACTIVE_CONVERSATIONS = "active_convs:{user_id}"
    
    # WhatsApp
    WHATSAPP_CLIENT = "wa_client:{client_id}"
    WHATSAPP_SESSION = "wa_session:{session_id}"
    
    # Rate Limiting
    RATE_LIMIT = "rate:{identifier}:{endpoint}"
    
    # Métricas
    METRICS_DAILY = "metrics:{date}"
    METRICS_HOURLY = "metrics:{date}:{hour}"
    
    # Cache de queries
    QUERY_CACHE = "query:{hash}"
    
    @staticmethod
    def user_session(user_id: str) -> str:
        return f"session:{user_id}"
    
    @staticmethod
    def conversation_cache(conversation_id: str) -> str:
        return f"conv:{conversation_id}"
    
    @staticmethod
    def rate_limit_key(identifier: str, endpoint: str = "global") -> str:
        return f"rate:{identifier}:{endpoint}"