#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurações do API Gateway
Define roteamento, load balancing e políticas de acesso
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum

class LoadBalanceStrategy(str, Enum):
    """Estratégias de load balancing"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    HEALTH_BASED = "health_based"

class ServiceConfig(BaseModel):
    """Configuração de um microserviço"""
    name: str
    instances: List[str]  # URLs das instâncias
    health_check_path: str = "/health"
    timeout: int = 30
    retries: int = 3
    load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    rate_limit_per_minute: int = 1000
    require_auth: bool = True
    allowed_roles: Optional[List[str]] = None

class RouteConfig(BaseModel):
    """Configuração de rota"""
    path_prefix: str
    service_name: str
    strip_prefix: bool = True
    rewrite_path: Optional[str] = None
    cache_ttl: Optional[int] = None
    rate_limit_override: Optional[int] = None
    require_auth_override: Optional[bool] = None  # Override da autenticação por rota

# Configuração dos serviços
SERVICES: Dict[str, ServiceConfig] = {
    "auth-service": ServiceConfig(
        name="auth-service",
        instances=["http://localhost:8001"],
        health_check_path="/health",
        timeout=10,
        retries=2,
        rate_limit_per_minute=500,
        require_auth=False,  # Auth service não precisa de auth
        allowed_roles=None
    ),
    
    "chat-service": ServiceConfig(
        name="chat-service", 
        instances=["http://localhost:8002"],
        health_check_path="/health",
        timeout=30,
        retries=3,
        rate_limit_per_minute=2000,
        require_auth=True,
        allowed_roles=["admin", "ADMIN", "supervisor", "SUPERVISOR", "agent", "AGENT"]
    )
}

# Configuração das rotas
ROUTES: List[RouteConfig] = [
    RouteConfig(
        path_prefix="/api/auth",
        service_name="auth-service",
        strip_prefix=True,
        rewrite_path=None,  # Vamos usar strip_prefix customizado
        cache_ttl=None
    ),
    
    # Rotas de teste do chat (sem autenticação)
    RouteConfig(
        path_prefix="/api/chat/test",
        service_name="chat-service",
        strip_prefix=True,
        cache_ttl=None,
        require_auth_override=False  # Endpoints de teste não precisam de auth
    ),
    
    # Rotas normais do chat (com autenticação)
    RouteConfig(
        path_prefix="/api/chat", 
        service_name="chat-service",
        strip_prefix=True,
        cache_ttl=60
    ),
    
    RouteConfig(
        path_prefix="/webhook",
        service_name="chat-service",
        strip_prefix=False,
        rewrite_path="/webhook"
    )
]