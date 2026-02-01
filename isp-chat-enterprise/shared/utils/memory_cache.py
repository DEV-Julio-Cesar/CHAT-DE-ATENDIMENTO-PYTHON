#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache em Memória - Substituto do Redis para Desenvolvimento
Implementa interface compatível com Redis para desenvolvimento local
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass

@dataclass
class CacheItem:
    """Item do cache com TTL"""
    value: Any
    expires_at: Optional[float] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
    
    def is_expired(self) -> bool:
        """Verifica se o item expirou"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

class MemoryCache:
    """
    Cache em memória com interface compatível com Redis
    Usado para desenvolvimento quando Redis não está disponível
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._data: Dict[str, CacheItem] = {}
        self._lists: Dict[str, List[Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._cleanup_task = None
        self._running = False
    
    async def connect(self):
        """Inicializar cache (compatibilidade com Redis)"""
        self._running = True
        # Iniciar limpeza automática
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        print("✅ Memory Cache conectado")
    
    async def disconnect(self):
        """Desconectar cache"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        print("✅ Memory Cache desconectado")
    
    async def _cleanup_expired(self):
        """Limpeza automática de itens expirados"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Limpar a cada 5 minutos
                with self._lock:
                    expired_keys = [
                        key for key, item in self._data.items()
                        if item.is_expired()
                    ]
                    for key in expired_keys:
                        del self._data[key]
                    
                    # Limpar listas vazias
                    empty_lists = [
                        key for key, lst in self._lists.items()
                        if len(lst) == 0
                    ]
                    for key in empty_lists:
                        del self._lists[key]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Erro na limpeza do cache: {e}")
    
    def _ensure_space(self):
        """Garantir espaço no cache"""
        with self._lock:
            if len(self._data) >= self._max_size:
                # Remover 10% dos itens mais antigos
                items_to_remove = int(self._max_size * 0.1)
                sorted_items = sorted(
                    self._data.items(),
                    key=lambda x: x[1].created_at
                )
                for key, _ in sorted_items[:items_to_remove]:
                    del self._data[key]
    
    # === OPERAÇÕES BÁSICAS (compatível com Redis) ===
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Definir valor com TTL opcional"""
        self._ensure_space()
        
        expires_at = None
        if ex is not None:
            expires_at = time.time() + ex
        elif self._default_ttl > 0:
            expires_at = time.time() + self._default_ttl
        
        with self._lock:
            self._data[key] = CacheItem(value=value, expires_at=expires_at)
        
        return True
    
    async def get(self, key: str) -> Optional[Any]:
        """Obter valor"""
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            
            if item.is_expired():
                del self._data[key]
                return None
            
            return item.value
    
    async def delete(self, key: str) -> int:
        """Deletar chave"""
        with self._lock:
            if key in self._data:
                del self._data[key]
                return 1
            if key in self._lists:
                del self._lists[key]
                return 1
            return 0
    
    async def exists(self, key: str) -> bool:
        """Verificar se chave existe"""
        with self._lock:
            if key in self._data:
                item = self._data[key]
                if item.is_expired():
                    del self._data[key]
                    return False
                return True
            return key in self._lists
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Definir TTL para chave existente"""
        with self._lock:
            if key in self._data:
                item = self._data[key]
                item.expires_at = time.time() + seconds
                return True
            return False
    
    async def ttl(self, key: str) -> int:
        """Obter TTL restante"""
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return -2  # Chave não existe
            
            if item.expires_at is None:
                return -1  # Sem TTL
            
            remaining = item.expires_at - time.time()
            return int(remaining) if remaining > 0 else -2
    
    # === OPERAÇÕES DE LISTA (para filas) ===
    
    async def lpush(self, key: str, *values) -> int:
        """Adicionar valores ao início da lista"""
        with self._lock:
            if key not in self._lists:
                self._lists[key] = []
            
            for value in reversed(values):
                self._lists[key].insert(0, value)
            
            return len(self._lists[key])
    
    async def rpush(self, key: str, *values) -> int:
        """Adicionar valores ao final da lista"""
        with self._lock:
            if key not in self._lists:
                self._lists[key] = []
            
            self._lists[key].extend(values)
            return len(self._lists[key])
    
    async def lpop(self, key: str) -> Optional[Any]:
        """Remover e retornar primeiro item da lista"""
        with self._lock:
            if key not in self._lists or len(self._lists[key]) == 0:
                return None
            
            return self._lists[key].pop(0)
    
    async def rpop(self, key: str) -> Optional[Any]:
        """Remover e retornar último item da lista"""
        with self._lock:
            if key not in self._lists or len(self._lists[key]) == 0:
                return None
            
            return self._lists[key].pop()
    
    async def llen(self, key: str) -> int:
        """Obter tamanho da lista"""
        with self._lock:
            return len(self._lists.get(key, []))
    
    async def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        """Obter range da lista"""
        with self._lock:
            if key not in self._lists:
                return []
            
            lst = self._lists[key]
            if stop == -1:
                return lst[start:]
            else:
                return lst[start:stop+1]
    
    async def lrem(self, key: str, count: int, value: Any) -> int:
        """Remover itens da lista"""
        with self._lock:
            if key not in self._lists:
                return 0
            
            lst = self._lists[key]
            removed = 0
            
            if count == 0:
                # Remover todas as ocorrências
                original_len = len(lst)
                self._lists[key] = [item for item in lst if item != value]
                removed = original_len - len(self._lists[key])
            elif count > 0:
                # Remover do início
                for i in range(len(lst)):
                    if lst[i] == value and removed < count:
                        lst.pop(i)
                        removed += 1
                        break
            else:
                # Remover do final
                count = abs(count)
                for i in range(len(lst) - 1, -1, -1):
                    if lst[i] == value and removed < count:
                        lst.pop(i)
                        removed += 1
                        if removed >= count:
                            break
            
            return removed
    
    # === OPERAÇÕES DE HASH ===
    
    async def hset(self, key: str, field: str, value: Any) -> int:
        """Definir campo em hash"""
        hash_data = await self.get(key) or {}
        if not isinstance(hash_data, dict):
            hash_data = {}
        
        is_new = field not in hash_data
        hash_data[field] = value
        await self.set(key, hash_data)
        
        return 1 if is_new else 0
    
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """Obter campo de hash"""
        hash_data = await self.get(key)
        if not isinstance(hash_data, dict):
            return None
        
        return hash_data.get(field)
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Obter todos os campos de hash"""
        hash_data = await self.get(key)
        if not isinstance(hash_data, dict):
            return {}
        
        return hash_data
    
    async def hdel(self, key: str, *fields) -> int:
        """Deletar campos de hash"""
        hash_data = await self.get(key)
        if not isinstance(hash_data, dict):
            return 0
        
        deleted = 0
        for field in fields:
            if field in hash_data:
                del hash_data[field]
                deleted += 1
        
        if hash_data:
            await self.set(key, hash_data)
        else:
            await self.delete(key)
        
        return deleted
    
    # === OPERAÇÕES DE INFORMAÇÃO ===
    
    async def ping(self) -> str:
        """Ping (compatibilidade com Redis)"""
        return "PONG"
    
    async def info(self) -> Dict[str, Any]:
        """Informações do cache"""
        with self._lock:
            return {
                "cache_type": "memory",
                "keys_count": len(self._data),
                "lists_count": len(self._lists),
                "max_size": self._max_size,
                "default_ttl": self._default_ttl,
                "uptime": time.time() - getattr(self, '_start_time', time.time())
            }
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Listar chaves (use com cuidado)"""
        with self._lock:
            all_keys = list(self._data.keys()) + list(self._lists.keys())
            
            if pattern == "*":
                return all_keys
            
            # Implementação simples de pattern matching
            import fnmatch
            return [key for key in all_keys if fnmatch.fnmatch(key, pattern)]
    
    async def flushdb(self) -> bool:
        """Limpar todos os dados"""
        with self._lock:
            self._data.clear()
            self._lists.clear()
        return True

# Instância global do cache
memory_cache = MemoryCache()

# Função para obter cache (compatibilidade com Redis)
async def get_cache():
    """Obter instância do cache"""
    return memory_cache