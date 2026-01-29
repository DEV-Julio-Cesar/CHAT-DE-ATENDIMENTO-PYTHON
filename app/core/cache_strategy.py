"""
Sistema de Cache Avançado em Camadas
"""
import asyncio
import json
import hashlib
from typing import Any, Optional, Dict, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog
from enum import Enum

from .redis_client import redis_manager, CacheKeys
from .metrics import metrics_collector

logger = structlog.get_logger(__name__)


class CacheLevel(Enum):
    """Níveis de cache"""
    L1_MEMORY = "l1_memory"      # Cache em memória (mais rápido)
    L2_REDIS = "l2_redis"        # Cache Redis (distribuído)
    L3_DATABASE = "l3_database"   # Cache de queries de banco


@dataclass
class CacheConfig:
    """Configuração de cache"""
    ttl: int = 3600              # TTL padrão (1 hora)
    max_size: int = 1000         # Tamanho máximo do cache L1
    enable_l1: bool = True       # Habilitar cache L1 (memória)
    enable_l2: bool = True       # Habilitar cache L2 (Redis)
    enable_warming: bool = True   # Habilitar cache warming
    compression: bool = False     # Compressão de dados
    serialize_complex: bool = True # Serializar objetos complexos


class CacheStats:
    """Estatísticas de cache"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
    
    @property
    def hit_rate(self) -> float:
        """Taxa de acerto do cache"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def reset(self):
        """Resetar estatísticas"""
        self.hits = self.misses = self.sets = self.deletes = self.errors = 0


class MultiLevelCache:
    """Cache em múltiplas camadas (L1: Memória, L2: Redis)"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.l1_cache: Dict[str, Dict] = {}  # Cache L1 (memória)
        self.stats = CacheStats()
        self.warming_tasks: Dict[str, asyncio.Task] = {}
        
    async def get(self, key: str, level: CacheLevel = None) -> Optional[Any]:
        """Buscar valor no cache (L1 → L2)"""
        try:
            # L1 Cache (Memória) - mais rápido
            if self.config.enable_l1 and (level is None or level == CacheLevel.L1_MEMORY):
                if key in self.l1_cache:
                    cache_entry = self.l1_cache[key]
                    if not self._is_expired(cache_entry):
                        self.stats.hits += 1
                        metrics_collector.record_cache_operation("get", "hit_l1")
                        logger.debug("Cache L1 hit", key=key)
                        return cache_entry["data"]
                    else:
                        # Remover entrada expirada
                        del self.l1_cache[key]
            
            # L2 Cache (Redis) - distribuído
            if self.config.enable_l2 and (level is None or level == CacheLevel.L2_REDIS):
                cached_data = await redis_manager.get(key)
                if cached_data:
                    try:
                        data = json.loads(cached_data)
                        
                        # Promover para L1 se habilitado
                        if self.config.enable_l1:
                            await self._set_l1(key, data, self.config.ttl)
                        
                        self.stats.hits += 1
                        metrics_collector.record_cache_operation("get", "hit_l2")
                        logger.debug("Cache L2 hit", key=key)
                        return data
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON in cache", key=key)
            
            # Cache miss
            self.stats.misses += 1
            metrics_collector.record_cache_operation("get", "miss")
            logger.debug("Cache miss", key=key)
            return None
            
        except Exception as e:
            self.stats.errors += 1
            metrics_collector.record_cache_operation("get", "error")
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, data: Any, ttl: int = None, level: CacheLevel = None) -> bool:
        """Definir valor no cache"""
        ttl = ttl or self.config.ttl
        
        try:
            # Serializar dados complexos
            if self.config.serialize_complex:
                serialized_data = self._serialize_data(data)
            else:
                serialized_data = data
            
            success = True
            
            # L1 Cache (Memória)
            if self.config.enable_l1 and (level is None or level == CacheLevel.L1_MEMORY):
                success &= await self._set_l1(key, serialized_data, ttl)
            
            # L2 Cache (Redis)
            if self.config.enable_l2 and (level is None or level == CacheLevel.L2_REDIS):
                success &= await self._set_l2(key, serialized_data, ttl)
            
            if success:
                self.stats.sets += 1
                metrics_collector.record_cache_operation("set", "success")
                logger.debug("Cache set success", key=key, ttl=ttl)
            
            return success
            
        except Exception as e:
            self.stats.errors += 1
            metrics_collector.record_cache_operation("set", "error")
            logger.error("Cache set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Remover do cache"""
        try:
            success = True
            
            # Remover do L1
            if key in self.l1_cache:
                del self.l1_cache[key]
            
            # Remover do L2
            deleted_count = await redis_manager.delete(key)
            success = deleted_count > 0
            
            if success:
                self.stats.deletes += 1
                metrics_collector.record_cache_operation("delete", "success")
                logger.debug("Cache delete success", key=key)
            
            return success
            
        except Exception as e:
            self.stats.errors += 1
            metrics_collector.record_cache_operation("delete", "error")
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    async def get_or_set(self, key: str, fetch_func: Callable, ttl: int = None) -> Any:
        """Padrão get-or-set otimizado"""
        # Tentar buscar no cache
        cached_data = await self.get(key)
        if cached_data is not None:
            return cached_data
        
        # Se não encontrou, executar função e cachear
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                data = await fetch_func()
            else:
                data = fetch_func()
            
            # Cachear resultado
            await self.set(key, data, ttl)
            return data
            
        except Exception as e:
            logger.error("Get-or-set fetch error", key=key, error=str(e))
            raise
    
    async def warm_cache(self, warming_config: Dict[str, Dict]) -> Dict[str, bool]:
        """Cache warming - pré-carregar dados importantes"""
        if not self.config.enable_warming:
            return {}
        
        results = {}
        
        for cache_key, config in warming_config.items():
            try:
                fetch_func = config.get("fetch_func")
                ttl = config.get("ttl", self.config.ttl)
                
                if fetch_func:
                    # Executar em background
                    task = asyncio.create_task(
                        self._warm_single_key(cache_key, fetch_func, ttl)
                    )
                    self.warming_tasks[cache_key] = task
                    results[cache_key] = True
                    
            except Exception as e:
                logger.error("Cache warming error", key=cache_key, error=str(e))
                results[cache_key] = False
        
        logger.info("Cache warming initiated", keys=list(results.keys()))
        return results
    
    async def _warm_single_key(self, key: str, fetch_func: Callable, ttl: int):
        """Aquecer uma chave específica"""
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                data = await fetch_func()
            else:
                data = fetch_func()
            
            await self.set(key, data, ttl)
            logger.debug("Cache warmed", key=key)
            
        except Exception as e:
            logger.error("Cache warming failed", key=key, error=str(e))
        finally:
            # Remover task da lista
            if key in self.warming_tasks:
                del self.warming_tasks[key]
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidar chaves que correspondem ao padrão"""
        try:
            # Invalidar L1 (busca por padrão simples)
            l1_deleted = 0
            keys_to_delete = [k for k in self.l1_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.l1_cache[key]
                l1_deleted += 1
            
            # Invalidar L2 (Redis)
            l2_deleted = await redis_manager.invalidate_pattern(pattern)
            
            total_deleted = l1_deleted + l2_deleted
            logger.info("Pattern invalidation", pattern=pattern, deleted=total_deleted)
            
            return total_deleted
            
        except Exception as e:
            logger.error("Pattern invalidation error", pattern=pattern, error=str(e))
            return 0
    
    async def _set_l1(self, key: str, data: Any, ttl: int) -> bool:
        """Definir no cache L1 (memória)"""
        try:
            # Verificar tamanho máximo
            if len(self.l1_cache) >= self.config.max_size:
                # Remover entrada mais antiga (LRU simples)
                oldest_key = next(iter(self.l1_cache))
                del self.l1_cache[oldest_key]
            
            self.l1_cache[key] = {
                "data": data,
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
                "created_at": datetime.utcnow()
            }
            return True
            
        except Exception as e:
            logger.error("L1 cache set error", key=key, error=str(e))
            return False
    
    async def _set_l2(self, key: str, data: Any, ttl: int) -> bool:
        """Definir no cache L2 (Redis)"""
        try:
            serialized = json.dumps(data, default=str)
            return await redis_manager.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.error("L2 cache set error", key=key, error=str(e))
            return False
    
    def _is_expired(self, cache_entry: Dict) -> bool:
        """Verificar se entrada do cache expirou"""
        return datetime.utcnow() > cache_entry["expires_at"]
    
    def _serialize_data(self, data: Any) -> Any:
        """Serializar dados complexos"""
        if hasattr(data, '__dict__'):
            return asdict(data) if hasattr(data, '__dataclass_fields__') else data.__dict__
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do cache"""
        return {
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            "errors": self.stats.errors,
            "hit_rate": self.stats.hit_rate,
            "l1_size": len(self.l1_cache),
            "warming_tasks": len(self.warming_tasks)
        }
    
    async def clear_all(self):
        """Limpar todo o cache"""
        self.l1_cache.clear()
        # Note: Não limpar todo o Redis, apenas as chaves específicas
        logger.info("Cache cleared")


# Instância global
cache_manager = MultiLevelCache()


# Decorador para cache automático
def cached(key_template: str, ttl: int = 3600, level: CacheLevel = None):
    """Decorador para cache automático de funções"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Gerar chave baseada nos argumentos
            key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = key_template.format(
                func_name=func.__name__,
                hash=hashlib.md5(key_data.encode()).hexdigest()[:8]
            )
            
            # Tentar buscar no cache
            cached_result = await cache_manager.get(cache_key, level)
            if cached_result is not None:
                return cached_result
            
            # Executar função e cachear resultado
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl, level)
            return result
        
        def sync_wrapper(*args, **kwargs):
            # Para funções síncronas, usar asyncio.run
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Configurações de cache pré-definidas
USER_CACHE_CONFIG = CacheConfig(ttl=1800, max_size=500)  # 30 min
CONVERSATION_CACHE_CONFIG = CacheConfig(ttl=3600, max_size=1000)  # 1 hora
METRICS_CACHE_CONFIG = CacheConfig(ttl=300, max_size=100)  # 5 min