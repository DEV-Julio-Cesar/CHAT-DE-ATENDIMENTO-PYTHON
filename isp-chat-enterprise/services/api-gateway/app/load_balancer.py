#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load Balancer para API Gateway
Implementa diferentes estratégias de distribuição de carga
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import logging

from .config import LoadBalanceStrategy, ServiceConfig

logger = logging.getLogger(__name__)

@dataclass
class ServiceInstance:
    """Instância de um serviço"""
    url: str
    healthy: bool = True
    last_health_check: float = field(default_factory=time.time)
    response_time: float = 0.0
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    weight: int = 1

class CircuitBreakerState(Enum):
    """Estados do Circuit Breaker"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreaker:
    """Circuit Breaker para proteção contra falhas"""
    failure_threshold: int = 5
    timeout: int = 60
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0
    next_attempt_time: float = 0

class LoadBalancer:
    """
    Load Balancer inteligente com múltiplas estratégias
    
    Funcionalidades:
    - Round Robin, Least Connections, Weighted, Health-based
    - Health checks automáticos
    - Circuit breaker pattern
    - Métricas de performance
    """
    
    def __init__(self):
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.round_robin_counters: Dict[str, int] = {}
        self.health_check_interval = 30  # segundos
        self.health_check_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Iniciar load balancer"""
        logger.info("🚀 Iniciando Load Balancer...")
        
        # Iniciar health checks periódicos
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("✅ Load Balancer iniciado")
    
    async def stop(self):
        """Parar load balancer"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Load Balancer parado")
    
    def register_service(self, service_name: str, config: ServiceConfig):
        """Registrar serviço no load balancer"""
        instances = []
        
        for url in config.instances:
            instance = ServiceInstance(url=url, weight=1)
            instances.append(instance)
        
        self.services[service_name] = instances
        self.circuit_breakers[service_name] = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout
        )
        self.round_robin_counters[service_name] = 0
        
        logger.info(f"📝 Serviço registrado: {service_name} ({len(instances)} instâncias)")
    
    async def get_instance(
        self, 
        service_name: str, 
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    ) -> Optional[ServiceInstance]:
        """
        Obter instância do serviço usando estratégia especificada
        
        Args:
            service_name: Nome do serviço
            strategy: Estratégia de load balancing
            
        Returns:
            Instância selecionada ou None se nenhuma disponível
        """
        if service_name not in self.services:
            logger.error(f"❌ Serviço não encontrado: {service_name}")
            return None
        
        # Verificar circuit breaker
        circuit_breaker = self.circuit_breakers[service_name]
        if not self._can_attempt_request(circuit_breaker):
            logger.warning(f"⚡ Circuit breaker OPEN para {service_name}")
            return None
        
        instances = self.services[service_name]
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            logger.error(f"❌ Nenhuma instância saudável para {service_name}")
            return None
        
        # Selecionar instância baseada na estratégia
        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            instance = self._round_robin_select(service_name, healthy_instances)
        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            instance = self._least_connections_select(healthy_instances)
        elif strategy == LoadBalanceStrategy.WEIGHTED:
            instance = self._weighted_select(healthy_instances)
        elif strategy == LoadBalanceStrategy.HEALTH_BASED:
            instance = self._health_based_select(healthy_instances)
        else:
            instance = healthy_instances[0]  # Fallback
        
        # Incrementar contador de conexões ativas
        instance.active_connections += 1
        instance.total_requests += 1
        
        return instance
    
    def _round_robin_select(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """Seleção Round Robin"""
        counter = self.round_robin_counters[service_name]
        instance = instances[counter % len(instances)]
        self.round_robin_counters[service_name] = (counter + 1) % len(instances)
        return instance
    
    def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Seleção por menor número de conexões"""
        return min(instances, key=lambda i: i.active_connections)
    
    def _weighted_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Seleção baseada em pesos"""
        total_weight = sum(i.weight for i in instances)
        if total_weight == 0:
            return instances[0]
        
        r = random.uniform(0, total_weight)
        current_weight = 0
        
        for instance in instances:
            current_weight += instance.weight
            if r <= current_weight:
                return instance
        
        return instances[-1]  # Fallback
    
    def _health_based_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Seleção baseada em saúde e performance"""
        # Calcular score baseado em response time e taxa de sucesso
        def calculate_score(instance: ServiceInstance) -> float:
            if instance.total_requests == 0:
                return 1.0
            
            success_rate = 1.0 - (instance.failed_requests / instance.total_requests)
            response_score = 1.0 / (1.0 + instance.response_time)  # Menor tempo = maior score
            
            return success_rate * response_score
        
        return max(instances, key=calculate_score)
    
    def _can_attempt_request(self, circuit_breaker: CircuitBreaker) -> bool:
        """Verificar se pode tentar request baseado no circuit breaker"""
        now = time.time()
        
        if circuit_breaker.state == CircuitBreakerState.CLOSED:
            return True
        elif circuit_breaker.state == CircuitBreakerState.OPEN:
            if now >= circuit_breaker.next_attempt_time:
                circuit_breaker.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        elif circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    async def record_request_result(
        self, 
        service_name: str, 
        instance: ServiceInstance, 
        success: bool, 
        response_time: float
    ):
        """Registrar resultado de request para métricas"""
        instance.active_connections = max(0, instance.active_connections - 1)
        instance.response_time = (instance.response_time + response_time) / 2  # Média móvel
        
        circuit_breaker = self.circuit_breakers[service_name]
        
        if success:
            # Reset circuit breaker em caso de sucesso
            if circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                circuit_breaker.state = CircuitBreakerState.CLOSED
                circuit_breaker.failure_count = 0
        else:
            instance.failed_requests += 1
            circuit_breaker.failure_count += 1
            circuit_breaker.last_failure_time = time.time()
            
            # Abrir circuit breaker se exceder threshold
            if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
                circuit_breaker.state = CircuitBreakerState.OPEN
                circuit_breaker.next_attempt_time = time.time() + circuit_breaker.timeout
                logger.warning(f"⚡ Circuit breaker ABERTO para {service_name}")
    
    async def _health_check_loop(self):
        """Loop de health checks periódicos"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Erro no health check: {e}")
    
    async def _perform_health_checks(self):
        """Realizar health checks em todas as instâncias"""
        tasks = []
        
        for service_name, instances in self.services.items():
            for instance in instances:
                task = asyncio.create_task(
                    self._check_instance_health(service_name, instance)
                )
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_instance_health(self, service_name: str, instance: ServiceInstance):
        """Verificar saúde de uma instância específica"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                health_url = f"{instance.url}/health"
                async with session.get(health_url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        instance.healthy = True
                        instance.response_time = response_time
                        instance.last_health_check = time.time()
                    else:
                        instance.healthy = False
                        logger.warning(f"⚠️ Health check falhou para {instance.url}: {response.status}")
        
        except Exception as e:
            instance.healthy = False
            logger.warning(f"⚠️ Health check erro para {instance.url}: {e}")
    
    def get_service_stats(self, service_name: str) -> Dict:
        """Obter estatísticas de um serviço"""
        if service_name not in self.services:
            return {}
        
        instances = self.services[service_name]
        circuit_breaker = self.circuit_breakers[service_name]
        
        healthy_count = sum(1 for i in instances if i.healthy)
        total_requests = sum(i.total_requests for i in instances)
        total_failures = sum(i.failed_requests for i in instances)
        avg_response_time = sum(i.response_time for i in instances) / len(instances) if instances else 0
        
        return {
            "service_name": service_name,
            "total_instances": len(instances),
            "healthy_instances": healthy_count,
            "circuit_breaker_state": circuit_breaker.state.value,
            "total_requests": total_requests,
            "total_failures": total_failures,
            "success_rate": (total_requests - total_failures) / total_requests if total_requests > 0 else 1.0,
            "avg_response_time": avg_response_time,
            "instances": [
                {
                    "url": i.url,
                    "healthy": i.healthy,
                    "active_connections": i.active_connections,
                    "total_requests": i.total_requests,
                    "failed_requests": i.failed_requests,
                    "response_time": i.response_time
                }
                for i in instances
            ]
        }

# Instância global do load balancer
load_balancer = LoadBalancer()