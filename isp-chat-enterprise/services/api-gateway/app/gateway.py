#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core do API Gateway
Roteamento, proxy de requests e orquestração de serviços
"""

import time
import asyncio
import json
from typing import Dict, Optional, Any, List
from urllib.parse import urljoin, urlparse
import logging

import aiohttp
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse

from .config import SERVICES, ROUTES, RouteConfig, ServiceConfig, LoadBalanceStrategy
from .load_balancer import load_balancer, ServiceInstance
from .middleware import rate_limiter, auth_middleware, metrics_collector

logger = logging.getLogger(__name__)

class APIGateway:
    """
    API Gateway principal
    
    Funcionalidades:
    - Roteamento inteligente de requests
    - Proxy transparente para microserviços
    - Load balancing automático
    - Cache de responses
    - Transformação de requests/responses
    """
    
    def __init__(self):
        self.response_cache: Dict[str, Dict] = {}
        self.cache_ttl_default = 60  # 1 minuto
        self.max_cache_size = 1000
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Inicializar API Gateway"""
        logger.info("🚀 Iniciando API Gateway...")
        
        # Inicializar load balancer
        await load_balancer.start()
        
        # Registrar serviços no load balancer
        for service_name, config in SERVICES.items():
            load_balancer.register_service(service_name, config)
        
        # Criar sessão HTTP reutilizável
        connector = aiohttp.TCPConnector(
            limit=100,  # Pool de conexões
            limit_per_host=30,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "ISP-Chat-Gateway/1.0"}
        )
        
        logger.info("✅ API Gateway iniciado")
    
    async def stop(self):
        """Parar API Gateway"""
        logger.info("🛑 Parando API Gateway...")
        
        if self.session:
            await self.session.close()
        
        await load_balancer.stop()
        
        logger.info("✅ API Gateway parado")
    
    async def handle_request(self, request: Request) -> Response:
        """
        Processar request principal
        
        Args:
            request: Request HTTP recebida
            
        Returns:
            Response do microserviço ou erro
        """
        start_time = time.time()
        path = request.url.path
        method = request.method
        
        logger.info(f"🔍 Processando: {method} {path}")
        
        try:
            # 1. Encontrar rota correspondente
            route_config = self._find_route(path)
            logger.info(f"🗺️ Rota encontrada: {route_config.path_prefix if route_config else 'NENHUMA'}")
            
            if not route_config:
                logger.warning(f"❌ Rota não encontrada para: {path}")
                logger.info(f"📋 Rotas disponíveis: {[r.path_prefix for r in ROUTES]}")
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "route_not_found",
                        "message": f"Rota não encontrada: {method} {path}",
                        "available_routes": [r.path_prefix for r in ROUTES]
                    }
                )
            
            # 2. Obter configuração do serviço
            service_config = SERVICES.get(route_config.service_name)
            if not service_config:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "service_not_configured",
                        "message": f"Serviço não configurado: {route_config.service_name}"
                    }
                )
            
            # 3. Verificar autenticação se necessário
            user_data = None
            
            # Verificar se há override de autenticação para esta rota
            require_auth = service_config.require_auth
            if route_config.require_auth_override is not None:
                require_auth = route_config.require_auth_override
            
            if require_auth:
                auth_header = request.headers.get("authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "authentication_required",
                            "message": "Token de autenticação necessário"
                        }
                    )
                
                token = auth_header.split(" ")[1]
                user_data = await auth_middleware.validate_token(token)
                
                if not user_data:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "invalid_token",
                            "message": "Token inválido ou expirado"
                        }
                    )
                
                # Verificar papéis permitidos
                if service_config.allowed_roles:
                    user_role = user_data.get("role")
                    if user_role not in service_config.allowed_roles:
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": "insufficient_permissions",
                                "message": f"Papel '{user_role}' não tem acesso a este serviço"
                            }
                        )
            
            # 4. Verificar rate limiting
            rate_limit_override = route_config.rate_limit_override or service_config.rate_limit_per_minute
            custom_limits = {"per_endpoint": rate_limit_override}
            
            user_id = user_data.get("id") if user_data else None
            if not await rate_limiter.check_rate_limit(request, user_id, custom_limits):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Muitas requisições. Tente novamente mais tarde."
                    }
                )
            
            # 5. Verificar cache
            if route_config.cache_ttl and method == "GET":
                cache_key = self._generate_cache_key(request, user_id)
                cached_response = self._get_cached_response(cache_key)
                if cached_response:
                    logger.info(f"📦 Cache hit: {method} {path}")
                    return JSONResponse(
                        status_code=cached_response["status_code"],
                        content=cached_response["content"],
                        headers=cached_response.get("headers", {})
                    )
            
            # 6. Obter instância do serviço
            instance = await load_balancer.get_instance(
                route_config.service_name,
                service_config.load_balance_strategy
            )
            
            if not instance:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "service_unavailable",
                        "message": f"Serviço {route_config.service_name} indisponível"
                    }
                )
            
            # 7. Fazer proxy da request
            response = await self._proxy_request(
                request, instance, route_config, service_config, user_data
            )
            
            # 8. Cache da response se configurado
            if route_config.cache_ttl and method == "GET" and response.status_code == 200:
                cache_key = self._generate_cache_key(request, user_id)
                await self._cache_response(cache_key, response, route_config.cache_ttl)
            
            # 9. Registrar métricas
            latency = time.time() - start_time
            await load_balancer.record_request_result(
                route_config.service_name,
                instance,
                response.status_code < 400,
                latency
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Erro no gateway: {e}")
            latency = time.time() - start_time
            
            # Registrar erro nas métricas
            metrics_collector.record_request(method, path, 500, latency)
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "gateway_error",
                    "message": "Erro interno do gateway"
                }
            )
    
    def _find_route(self, path: str) -> Optional[RouteConfig]:
        """Encontrar configuração de rota para o path"""
        for route in ROUTES:
            if path.startswith(route.path_prefix):
                return route
        return None
    
    async def _proxy_request(
        self,
        request: Request,
        instance: ServiceInstance,
        route_config: RouteConfig,
        service_config: ServiceConfig,
        user_data: Optional[Dict] = None
    ) -> Response:
        """
        Fazer proxy da request para o microserviço
        
        Args:
            request: Request original
            instance: Instância do serviço
            route_config: Configuração da rota
            service_config: Configuração do serviço
            user_data: Dados do usuário autenticado
            
        Returns:
            Response do microserviço
        """
        # Construir URL de destino
        target_path = self._build_target_path(request.url.path, route_config)
        target_url = urljoin(instance.url, target_path)
        
        logger.info(f"🎯 Proxy: {request.method} {request.url.path} -> {target_url}")
        
        # Preparar headers
        headers = dict(request.headers)
        
        # Remover headers que podem causar problemas
        headers.pop("host", None)
        headers.pop("content-length", None)
        
        # Adicionar headers customizados
        if user_data:
            headers["X-User-ID"] = str(user_data.get("id", ""))
            headers["X-User-Role"] = user_data.get("role", "")
            headers["X-User-Email"] = user_data.get("email", "")
        
        headers["X-Gateway-Request-ID"] = f"gw-{int(time.time() * 1000)}"
        headers["X-Forwarded-For"] = request.client.host
        headers["X-Forwarded-Proto"] = request.url.scheme
        
        # Preparar dados do corpo
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Fazer request para o microserviço
        try:
            async with self.session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=dict(request.query_params),
                data=body,
                timeout=aiohttp.ClientTimeout(total=service_config.timeout)
            ) as response:
                
                # Ler conteúdo da response
                content = await response.read()
                
                # Preparar headers de resposta
                response_headers = {}
                for key, value in response.headers.items():
                    # Filtrar headers que não devem ser repassados
                    if key.lower() not in ["content-encoding", "content-length", "transfer-encoding"]:
                        response_headers[key] = value
                
                # Adicionar headers do gateway
                response_headers["X-Gateway-Service"] = route_config.service_name
                response_headers["X-Gateway-Instance"] = instance.url
                response_headers["X-Gateway-Latency"] = str(int((time.time() - time.time()) * 1000))
                
                # Retornar response
                return Response(
                    content=content,
                    status_code=response.status,
                    headers=response_headers,
                    media_type=response.headers.get("content-type", "application/json")
                )
                
        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout na request para {target_url}")
            return JSONResponse(
                status_code=504,
                content={
                    "error": "gateway_timeout",
                    "message": f"Timeout na comunicação com {route_config.service_name}"
                }
            )
        
        except Exception as e:
            logger.error(f"❌ Erro no proxy para {target_url}: {e}")
            return JSONResponse(
                status_code=502,
                content={
                    "error": "bad_gateway",
                    "message": f"Erro na comunicação com {route_config.service_name}"
                }
            )
    
    def _build_target_path(self, original_path: str, route_config: RouteConfig) -> str:
        """Construir path de destino baseado na configuração"""
        logger.info(f"🔧 Construindo path: {original_path} -> config: {route_config.path_prefix}")
        
        if route_config.rewrite_path:
            logger.info(f"🔄 Rewrite path: {route_config.rewrite_path}")
            return route_config.rewrite_path
        
        if route_config.strip_prefix:
            # Remover prefix da rota
            if original_path.startswith(route_config.path_prefix):
                remaining_path = original_path[len(route_config.path_prefix):]
                
                # Caso especial para auth: /api/auth/login -> /auth/login
                if route_config.path_prefix == "/api/auth":
                    final_path = f"/auth{remaining_path}"
                # Caso especial para chat test: /api/chat/test/conversations -> /test/conversations
                elif route_config.path_prefix == "/api/chat/test":
                    final_path = f"/test{remaining_path}"
                else:
                    final_path = remaining_path if remaining_path.startswith("/") else f"/{remaining_path}"
                
                logger.info(f"🎯 Path final: {final_path}")
                return final_path
        
        logger.info(f"📍 Path original mantido: {original_path}")
        return original_path
    
    def _generate_cache_key(self, request: Request, user_id: Optional[str] = None) -> str:
        """Gerar chave de cache para a request"""
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
        ]
        
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        return "|".join(key_parts)
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Obter response do cache se válida"""
        if cache_key not in self.response_cache:
            return None
        
        cached_data = self.response_cache[cache_key]
        if time.time() - cached_data["cached_at"] > cached_data["ttl"]:
            # Cache expirado
            del self.response_cache[cache_key]
            return None
        
        return cached_data
    
    async def _cache_response(self, cache_key: str, response: Response, ttl: int):
        """Cachear response"""
        # Limitar tamanho do cache
        if len(self.response_cache) >= self.max_cache_size:
            # Remover entrada mais antiga
            oldest_key = min(
                self.response_cache.keys(),
                key=lambda k: self.response_cache[k]["cached_at"]
            )
            del self.response_cache[oldest_key]
        
        # Cachear apenas responses pequenas (< 1MB)
        if hasattr(response, 'body') and len(response.body) < 1024 * 1024:
            self.response_cache[cache_key] = {
                "status_code": response.status_code,
                "content": response.body.decode() if isinstance(response.body, bytes) else response.body,
                "headers": dict(response.headers),
                "cached_at": time.time(),
                "ttl": ttl
            }
    
    async def get_gateway_stats(self) -> Dict:
        """Obter estatísticas do gateway"""
        # Estatísticas dos serviços
        service_stats = {}
        for service_name in SERVICES.keys():
            service_stats[service_name] = load_balancer.get_service_stats(service_name)
        
        # Estatísticas gerais
        return {
            "gateway": {
                "uptime": time.time() - metrics_collector.start_time,
                "cache_size": len(self.response_cache),
                "max_cache_size": self.max_cache_size,
                "services_registered": len(SERVICES),
                "routes_configured": len(ROUTES)
            },
            "services": service_stats,
            "metrics": metrics_collector.get_metrics(),
            "rate_limiter": rate_limiter.get_stats(),
            "load_balancer": {
                "strategies_available": [s.value for s in LoadBalanceStrategy],
                "health_check_interval": load_balancer.health_check_interval
            }
        }

# Instância global do gateway
api_gateway = APIGateway()