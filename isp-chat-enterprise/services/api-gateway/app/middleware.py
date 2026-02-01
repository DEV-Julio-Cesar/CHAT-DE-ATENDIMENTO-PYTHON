#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Middleware do API Gateway
Rate limiting, autenticação, logging e métricas
"""

import time
import json
import asyncio
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import aiohttp

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate Limiter avançado com múltiplas estratégias
    
    Funcionalidades:
    - Rate limiting por IP, usuário, endpoint
    - Sliding window algorithm
    - Burst allowance
    - Whitelist/blacklist
    """
    
    def __init__(self):
        # Estruturas para rate limiting
        self.ip_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.endpoint_requests: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Configurações
        self.window_size = 60  # 1 minuto
        self.cleanup_interval = 300  # 5 minutos
        self.last_cleanup = time.time()
        
        # Whitelist e blacklist
        self.ip_whitelist: Set[str] = {"127.0.0.1", "::1"}
        self.ip_blacklist: Set[str] = set()
        
        # Limites padrão
        self.default_limits = {
            "per_ip": 1000,      # requests por IP por minuto
            "per_user": 500,     # requests por usuário por minuto
            "per_endpoint": 100  # requests por endpoint por minuto
        }
    
    async def check_rate_limit(
        self, 
        request: Request, 
        user_id: Optional[str] = None,
        custom_limits: Optional[Dict[str, int]] = None
    ) -> bool:
        """
        Verificar se request está dentro dos limites
        
        Args:
            request: Request HTTP
            user_id: ID do usuário (se autenticado)
            custom_limits: Limites customizados para este endpoint
            
        Returns:
            True se dentro do limite, False caso contrário
        """
        now = time.time()
        client_ip = self._get_client_ip(request)
        endpoint = f"{request.method} {request.url.path}"
        
        # Verificar blacklist
        if client_ip in self.ip_blacklist:
            logger.warning(f"🚫 IP bloqueado tentou acesso: {client_ip}")
            return False
        
        # Verificar whitelist (bypass rate limiting)
        if client_ip in self.ip_whitelist:
            return True
        
        # Limites efetivos
        limits = {**self.default_limits, **(custom_limits or {})}
        
        # Cleanup periódico
        if now - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_old_requests()
            self.last_cleanup = now
        
        # Verificar limite por IP
        if not self._check_limit(self.ip_requests[client_ip], limits["per_ip"], now):
            logger.warning(f"⚠️ Rate limit excedido por IP: {client_ip}")
            return False
        
        # Verificar limite por usuário (se autenticado)
        if user_id and not self._check_limit(self.user_requests[user_id], limits["per_user"], now):
            logger.warning(f"⚠️ Rate limit excedido por usuário: {user_id}")
            return False
        
        # Verificar limite por endpoint
        if not self._check_limit(self.endpoint_requests[endpoint], limits["per_endpoint"], now):
            logger.warning(f"⚠️ Rate limit excedido por endpoint: {endpoint}")
            return False
        
        # Registrar request
        self.ip_requests[client_ip].append(now)
        if user_id:
            self.user_requests[user_id].append(now)
        self.endpoint_requests[endpoint].append(now)
        
        return True
    
    def _check_limit(self, requests: deque, limit: int, now: float) -> bool:
        """Verificar limite usando sliding window"""
        # Remover requests antigas (fora da janela)
        cutoff = now - self.window_size
        while requests and requests[0] < cutoff:
            requests.popleft()
        
        # Verificar se excedeu limite
        return len(requests) < limit
    
    def _get_client_ip(self, request: Request) -> str:
        """Obter IP real do cliente (considerando proxies)"""
        # Verificar headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host
    
    async def _cleanup_old_requests(self):
        """Limpar requests antigas para economizar memória"""
        now = time.time()
        cutoff = now - self.window_size * 2  # Manter 2x a janela por segurança
        
        # Cleanup IP requests
        for ip, requests in list(self.ip_requests.items()):
            while requests and requests[0] < cutoff:
                requests.popleft()
            if not requests:
                del self.ip_requests[ip]
        
        # Cleanup user requests
        for user_id, requests in list(self.user_requests.items()):
            while requests and requests[0] < cutoff:
                requests.popleft()
            if not requests:
                del self.user_requests[user_id]
        
        # Cleanup endpoint requests
        for endpoint, requests in list(self.endpoint_requests.items()):
            while requests and requests[0] < cutoff:
                requests.popleft()
            if not requests:
                del self.endpoint_requests[endpoint]
    
    def add_to_blacklist(self, ip: str):
        """Adicionar IP à blacklist"""
        self.ip_blacklist.add(ip)
        logger.info(f"🚫 IP adicionado à blacklist: {ip}")
    
    def remove_from_blacklist(self, ip: str):
        """Remover IP da blacklist"""
        self.ip_blacklist.discard(ip)
        logger.info(f"✅ IP removido da blacklist: {ip}")
    
    def get_stats(self) -> Dict:
        """Obter estatísticas do rate limiter"""
        return {
            "active_ips": len(self.ip_requests),
            "active_users": len(self.user_requests),
            "active_endpoints": len(self.endpoint_requests),
            "blacklisted_ips": len(self.ip_blacklist),
            "whitelisted_ips": len(self.ip_whitelist),
            "window_size": self.window_size,
            "default_limits": self.default_limits
        }

class AuthMiddleware:
    """
    Middleware de autenticação para API Gateway
    
    Funcionalidades:
    - Validação de tokens JWT
    - Cache de tokens válidos
    - Integração com Auth Service
    - Extração de dados do usuário
    """
    
    def __init__(self, auth_service_url: str = "http://localhost:8001"):
        self.auth_service_url = auth_service_url
        self.token_cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutos
        self.last_cache_cleanup = time.time()
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validar token JWT
        
        Args:
            token: Token JWT
            
        Returns:
            Dados do usuário se válido, None caso contrário
        """
        # Verificar cache primeiro
        if token in self.token_cache:
            cached_data = self.token_cache[token]
            if time.time() - cached_data["cached_at"] < self.cache_ttl:
                return cached_data["user_data"]
            else:
                # Cache expirado
                del self.token_cache[token]
        
        # Validar com Auth Service
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}
                async with session.post(
                    f"{self.auth_service_url}/auth/verify",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get("valid"):
                            user_data = data.get("user")
                            
                            # Cache resultado
                            self.token_cache[token] = {
                                "user_data": user_data,
                                "cached_at": time.time()
                            }
                            
                            return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de token: {e}")
            return None
    
    async def cleanup_cache(self):
        """Limpar cache de tokens expirados"""
        now = time.time()
        expired_tokens = [
            token for token, data in self.token_cache.items()
            if now - data["cached_at"] > self.cache_ttl
        ]
        
        for token in expired_tokens:
            del self.token_cache[token]
        
        if expired_tokens:
            logger.info(f"🧹 Cache limpo: {len(expired_tokens)} tokens expirados removidos")

class MetricsCollector:
    """
    Coletor de métricas para API Gateway
    
    Funcionalidades:
    - Métricas de requests (count, latency, errors)
    - Métricas por endpoint, método, status
    - Métricas de load balancer
    - Export para Prometheus (futuro)
    """
    
    def __init__(self):
        self.request_count = defaultdict(int)
        self.request_latency = defaultdict(list)
        self.error_count = defaultdict(int)
        self.status_codes = defaultdict(int)
        
        # Métricas por endpoint
        self.endpoint_metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "errors": 0,
            "avg_latency": 0.0
        })
        
        self.start_time = time.time()
    
    def record_request(
        self, 
        method: str, 
        path: str, 
        status_code: int, 
        latency: float,
        service_name: Optional[str] = None
    ):
        """Registrar métricas de uma request"""
        endpoint = f"{method} {path}"
        
        # Métricas gerais
        self.request_count[endpoint] += 1
        self.request_latency[endpoint].append(latency)
        self.status_codes[status_code] += 1
        
        if status_code >= 400:
            self.error_count[endpoint] += 1
        
        # Métricas por endpoint
        metrics = self.endpoint_metrics[endpoint]
        metrics["count"] += 1
        metrics["total_time"] += latency
        metrics["avg_latency"] = metrics["total_time"] / metrics["count"]
        
        if status_code >= 400:
            metrics["errors"] += 1
        
        # Métricas por serviço
        if service_name:
            service_metrics = self.endpoint_metrics[f"service:{service_name}"]
            service_metrics["count"] += 1
            service_metrics["total_time"] += latency
            service_metrics["avg_latency"] = service_metrics["total_time"] / service_metrics["count"]
            
            if status_code >= 400:
                service_metrics["errors"] += 1
    
    def get_metrics(self) -> Dict:
        """Obter todas as métricas"""
        total_requests = sum(self.request_count.values())
        total_errors = sum(self.error_count.values())
        uptime = time.time() - self.start_time
        
        # Calcular latência média geral
        all_latencies = []
        for latencies in self.request_latency.values():
            all_latencies.extend(latencies)
        
        avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
        
        return {
            "uptime_seconds": uptime,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / total_requests if total_requests > 0 else 0,
            "avg_latency_ms": avg_latency * 1000,
            "requests_per_second": total_requests / uptime if uptime > 0 else 0,
            "status_codes": dict(self.status_codes),
            "endpoints": dict(self.endpoint_metrics),
            "top_endpoints": sorted(
                self.endpoint_metrics.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:10]
        }

# Instâncias globais dos middlewares
rate_limiter = RateLimiter()
auth_middleware = AuthMiddleware()
metrics_collector = MetricsCollector()