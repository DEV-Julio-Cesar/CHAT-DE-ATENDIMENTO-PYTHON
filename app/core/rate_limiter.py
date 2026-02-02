"""
Rate Limiter com Redis sliding window
- Proteção contra brute force
- Proteção contra DDoS
- Limites por IP, por usuário, por endpoint
"""

from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Flag para desabilitar Redis quando não está disponível
REDIS_DISABLED = True  # Desabilitado para performance local


class RateLimiter:
    """
    Rate limiting com algoritmo sliding window em Redis
    
    Mantém contador de requisições em janela de tempo
    Permite limite configurável de requisições por segundos
    """
    
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
        # Bypass quando Redis está desabilitado - resposta instantânea
        if REDIS_DISABLED:
            return True, max_requests - 1
        
        # Importação lazy do redis_manager apenas quando necessário
        from app.core.redis_client import redis_manager
        
        key = f"ratelimit:{identifier}"
        
        try:
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
            
            return True, remaining
            
        except Exception as e:
            logger.error(f"Error in rate limit check: {str(e)}")
            # Em caso de erro, permitir (fail open)
            return True, max_requests - 1


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
