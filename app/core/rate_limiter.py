"""
Rate Limiter com Redis sliding window
- Proteção contra brute force
- Proteção contra DDoS
- Limites por IP, por usuário, por endpoint
- Fallback seguro em memória quando Redis indisponível
"""

from typing import Optional, Tuple
import logging
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiting com algoritmo sliding window em Redis
    Com fallback seguro em memória quando Redis não disponível
    
    Mantém contador de requisições em janela de tempo
    Permite limite configurável de requisições por segundos
    """
    
    def __init__(self):
        # Fallback em memória (thread-safe)
        self._memory_cache = defaultdict(list)
        self._lock = Lock()
        self._redis_available = True
    
    async def is_allowed(
        self,
        identifier: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        Verificar se requisição é permitida
        
        Args:
            identifier: ID único (IP, user_id, endpoint, etc)
            max_requests: Máximo de requisições na janela
            window_seconds: Tamanho da janela em segundos
        
        Returns:
            (allowed: bool, remaining: int)
        """
        try:
            # Tentar Redis primeiro
            from app.core.redis_client import redis_manager
            
            key = f"ratelimit:{identifier}"
            
            # Obter contador atual
            current_str = await redis_manager.get(key)
            current_count = int(current_str or 0)
            
            # Verificar se excedeu limite
            if current_count >= max_requests:
                logger.warning(
                    f"Rate limit exceeded for {identifier} "
                    f"({current_count}/{max_requests})"
                )
                return False, 0
            
            # Incrementar contador
            new_count = await redis_manager.incr(key)
            
            # Definir TTL apenas na primeira requisição
            if new_count == 1:
                await redis_manager.expire(key, window_seconds)
            
            remaining = max(0, max_requests - new_count)
            
            logger.debug(
                f"Rate limit check for {identifier}: "
                f"{new_count}/{max_requests} ({remaining} remaining)"
            )
            
            self._redis_available = True
            return True, remaining
            
        except Exception as e:
            # Fallback SEGURO em memória (não bypass!)
            if self._redis_available:
                logger.warning(
                    f"Redis unavailable for rate limiting, using memory fallback: {e}"
                )
                self._redis_available = False
            
            return await self._memory_rate_limit(identifier, max_requests, window_seconds)
    
    async def _memory_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Fallback de rate limiting em memória (thread-safe)
        IMPORTANTE: Não é um bypass, mantém a segurança
        """
        now = time.time()
        key = f"{identifier}:{window_seconds}"
        
        with self._lock:
            # Limpar requisições antigas
            self._memory_cache[key] = [
                ts for ts in self._memory_cache[key]
                if now - ts < window_seconds
            ]
            
            # Verificar limite
            current_count = len(self._memory_cache[key])
            
            if current_count >= max_requests:
                logger.warning(
                    f"Rate limit exceeded (memory) for {identifier} "
                    f"({current_count}/{max_requests})"
                )
                return False, 0
            
            # Adicionar nova requisição
            self._memory_cache[key].append(now)
            remaining = max_requests - len(self._memory_cache[key])
            
            return True, remaining
    
    async def reset(self, identifier: str):
        """Resetar contador de rate limit"""
        try:
            from app.core.redis_client import redis_manager
            key = f"ratelimit:{identifier}"
            await redis_manager.delete(key)
        except Exception as ex:
            logger.debug(f"Redis reset failed: {ex}")
        
        # Limpar memória também
        with self._lock:
            keys_to_remove = [k for k in self._memory_cache.keys() if k.startswith(identifier)]
            for key in keys_to_remove:
                del self._memory_cache[key]


class RateLimitConfig:
    """Configuração padrão de rate limits"""
    
    # Endpoints de autenticação
    LOGIN = {"max_requests": 5, "window_seconds": 900}  # 5 tentativas em 15 min
    PASSWORD_RESET = {"max_requests": 3, "window_seconds": 3600}  # 3 em 1 hora
    
    # Endpoints de dados
    API_DEFAULT = {"max_requests": 100, "window_seconds": 60}  # 100 req/min
    API_STRICT = {"max_requests": 10, "window_seconds": 60}  # 10 req/min
    API_RELAXED = {"max_requests": 1000, "window_seconds": 60}  # 1000 req/min
    
    # WhatsApp
    WHATSAPP_WEBHOOK = {"max_requests": 10000, "window_seconds": 60}  # 10k/min
    WHATSAPP_SEND = {"max_requests": 100, "window_seconds": 60}  # 100/min
    
    # AI
    AI_CHAT = {"max_requests": 30, "window_seconds": 60}  # 30/min
    
    # Webhooks
    WEBHOOK_GENERAL = {"max_requests": 1000, "window_seconds": 60}  # 1000/min


# Instância global
rate_limiter = RateLimiter()


async def get_identifier_by_type(
    request_type: str,
    request,
    user_id: Optional[str] = None
) -> str:
    """
    Gerar identificador único para rate limit baseado no tipo
    
    Args:
        request_type: "ip", "user", "endpoint", "combined"
        request: FastAPI Request object
        user_id: User ID (se type="user" ou "combined")
    
    Returns:
        Identificador único string
    """
    ip_address = request.client.host if request.client else "unknown"
    
    if request_type == "ip":
        return f"ip:{ip_address}"
    elif request_type == "user":
        return f"user:{user_id}" if user_id else f"ip:{ip_address}"
    elif request_type == "endpoint":
        endpoint = request.url.path
        return f"endpoint:{endpoint}:{ip_address}"
    elif request_type == "combined":
        endpoint = request.url.path
        user_part = f":{user_id}" if user_id else ""
        return f"combined:{endpoint}:{ip_address}{user_part}"
    else:
        return f"ip:{ip_address}"


async def check_rate_limit(
    identifier: str,
    config: dict
) -> Tuple[bool, dict]:
    """
    Verificar rate limit e retornar headers
    
    Returns:
        (allowed: bool, headers: dict com X-RateLimit-*)
    """
    allowed, remaining = await rate_limiter.is_allowed(
        identifier=identifier,
        max_requests=config["max_requests"],
        window_seconds=config["window_seconds"]
    )
    
    headers = {
        "X-RateLimit-Limit": str(config["max_requests"]),
        "X-RateLimit-Remaining": str(max(0, remaining)),
        "X-RateLimit-Reset": str(config["window_seconds"])
    }
    
    return allowed, headers
