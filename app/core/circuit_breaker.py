"""
Circuit Breaker Pattern para resiliência
"""
import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Estados do circuit breaker"""
    CLOSED = "closed"      # Funcionando normalmente
    OPEN = "open"          # Circuito aberto, rejeitando chamadas
    HALF_OPEN = "half_open"  # Testando se o serviço voltou


@dataclass
class CircuitBreakerConfig:
    """Configuração do circuit breaker"""
    failure_threshold: int = 5          # Número de falhas para abrir
    recovery_timeout: int = 60          # Tempo para tentar fechar (segundos)
    expected_exception: type = Exception # Tipo de exceção que conta como falha
    success_threshold: int = 3          # Sucessos necessários para fechar


class CircuitBreakerError(Exception):
    """Exceção quando circuit breaker está aberto"""
    pass


class CircuitBreaker:
    """Implementação do Circuit Breaker Pattern"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Executar função com circuit breaker"""
        async with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info("Circuit breaker half-open", name=self.name)
                else:
                    logger.warning("Circuit breaker open, rejecting call", name=self.name)
                    raise CircuitBreakerError(f"Circuit breaker {self.name} is open")
        
        try:
            # Executar função
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Sucesso - resetar contadores
            await self._on_success()
            return result
            
        except self.config.expected_exception as e:
            # Falha esperada - incrementar contador
            await self._on_failure()
            raise
        except Exception as e:
            # Falha inesperada - não contar para circuit breaker
            logger.error("Unexpected error in circuit breaker", 
                        name=self.name, error=str(e))
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Verificar se deve tentar resetar o circuit breaker"""
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    async def _on_success(self):
        """Processar sucesso"""
        async with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info("Circuit breaker closed", name=self.name)
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    async def _on_failure(self):
        """Processar falha"""
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker opened", 
                             name=self.name, 
                             failure_count=self.failure_count)
    
    def get_state(self) -> Dict[str, Any]:
        """Obter estado atual do circuit breaker"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }


class CircuitBreakerManager:
    """Gerenciador de circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Obter ou criar circuit breaker"""
        if name not in self.breakers:
            if config is None:
                config = CircuitBreakerConfig()
            self.breakers[name] = CircuitBreaker(name, config)
        
        return self.breakers[name]
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Obter estado de todos os circuit breakers"""
        return {name: breaker.get_state() for name, breaker in self.breakers.items()}
    
    async def reset_breaker(self, name: str):
        """Resetar circuit breaker específico"""
        if name in self.breakers:
            breaker = self.breakers[name]
            async with breaker.lock:
                breaker.state = CircuitState.CLOSED
                breaker.failure_count = 0
                breaker.success_count = 0
                logger.info("Circuit breaker manually reset", name=name)


# Instância global
circuit_breaker_manager = CircuitBreakerManager()


# Decorador para circuit breaker
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorador para aplicar circuit breaker"""
    def decorator(func):
        breaker = circuit_breaker_manager.get_breaker(name, config)
        
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(breaker.call(func, *args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Configurações pré-definidas
WHATSAPP_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=Exception,
    success_threshold=2
)

DATABASE_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception,
    success_threshold=3
)

AI_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=45,
    expected_exception=Exception,
    success_threshold=2
)

REDIS_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=Exception,
    success_threshold=2
)