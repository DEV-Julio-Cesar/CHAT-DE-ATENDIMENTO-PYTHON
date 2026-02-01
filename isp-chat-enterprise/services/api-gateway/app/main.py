#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Gateway - Ponto de entrada único para todos os microserviços
Centraliza roteamento, autenticação, rate limiting e load balancing
"""

import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError

# Imports locais
from shared.config.settings import settings
from .gateway import api_gateway
from .middleware import rate_limiter, auth_middleware, metrics_collector
from .config import SERVICES, ROUTES

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gerenciamento do ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida do API Gateway"""
    # Startup
    logger.info("🚀 Iniciando API Gateway...")
    
    try:
        # Inicializar gateway
        await api_gateway.start()
        
        logger.info("🎉 API Gateway iniciado com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Finalizando API Gateway...")
    
    try:
        await api_gateway.stop()
        logger.info("✅ API Gateway finalizado")
    except Exception as e:
        logger.error(f"❌ Erro na finalização: {e}")

# Criar aplicação FastAPI
app = FastAPI(
    title="ISP Chat - API Gateway",
    description="""
    🌐 **API Gateway Centralizado**
    
    Ponto de entrada único para todos os microserviços do ISP Chat:
    
    **Funcionalidades:**
    - 🔀 Roteamento inteligente para microserviços
    - ⚖️ Load balancing automático com múltiplas estratégias
    - 🔐 Autenticação centralizada com JWT
    - 🚦 Rate limiting avançado (IP, usuário, endpoint)
    - 📊 Métricas e monitoramento em tempo real
    - 🔄 Circuit breaker para proteção contra falhas
    - 💾 Cache inteligente de responses
    - 🏥 Health checks automáticos
    
    **Rotas Disponíveis:**
    - `/api/auth/*` → Auth Service (autenticação)
    - `/api/chat/*` → Chat Service (conversas)
    - `/api/ai/*` → AI Service (inteligência artificial)
    - `/webhook/*` → WhatsApp webhooks
    
    **Compatível com migração do sistema Node.js**
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    **settings.get_cors_config()
)

# === MIDDLEWARE DE LOGGING E MÉTRICAS ===

@app.middleware("http")
async def log_and_metrics_middleware(request: Request, call_next):
    """Middleware para logging e coleta de métricas"""
    start_time = datetime.utcnow()
    
    # Log da request
    logger.info(f"📥 {request.method} {request.url.path} - IP: {request.client.host}")
    
    # Processar request
    response = await call_next(request)
    
    # Calcular tempo de processamento
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Log da response
    logger.info(
        f"📤 {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    # Adicionar headers de resposta
    response.headers["X-Gateway-Process-Time"] = str(process_time)
    response.headers["X-Gateway-Version"] = "1.0.0"
    response.headers["X-Gateway-Timestamp"] = start_time.isoformat()
    
    return response

# === HANDLERS DE ERRO ===

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Dados de entrada inválidos",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para HTTPExceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para erros gerais"""
    logger.error(f"❌ Erro não tratado: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "Erro interno do servidor",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# === ENDPOINTS DO GATEWAY ===

@app.get("/", tags=["Gateway"])
async def root():
    """Endpoint raiz com informações do gateway"""
    return {
        "service": "ISP Chat - API Gateway",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "description": "Ponto de entrada único para todos os microserviços",
        "docs": "/docs",
        "services": {
            name: {
                "instances": len(config.instances),
                "health_check": config.health_check_path,
                "require_auth": config.require_auth,
                "rate_limit": config.rate_limit_per_minute
            }
            for name, config in SERVICES.items()
        },
        "routes": [
            {
                "prefix": route.path_prefix,
                "service": route.service_name,
                "cache_ttl": route.cache_ttl,
                "strip_prefix": route.strip_prefix
            }
            for route in ROUTES
        ]
    }

@app.get("/health", tags=["Gateway"])
async def health_check():
    """Health check detalhado do gateway"""
    try:
        # Obter estatísticas completas
        stats = await api_gateway.get_gateway_stats()
        
        # Verificar saúde dos serviços
        healthy_services = 0
        total_services = len(SERVICES)
        
        for service_name, service_stats in stats["services"].items():
            if service_stats.get("healthy_instances", 0) > 0:
                healthy_services += 1
        
        overall_healthy = healthy_services == total_services
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "service": "api-gateway",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "total": total_services,
                "healthy": healthy_services,
                "degraded": total_services - healthy_services
            },
            "gateway": stats["gateway"],
            "uptime": f"{stats['gateway']['uptime']:.2f} seconds"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no health check: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "api-gateway",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/stats", tags=["Gateway"])
async def get_gateway_stats():
    """Obter estatísticas detalhadas do gateway"""
    try:
        stats = await api_gateway.get_gateway_stats()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            **stats
        }
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter estatísticas"
        )

@app.get("/routes", tags=["Gateway"])
async def get_routes():
    """Listar todas as rotas configuradas"""
    return {
        "routes": [
            {
                "path_prefix": route.path_prefix,
                "service_name": route.service_name,
                "strip_prefix": route.strip_prefix,
                "rewrite_path": route.rewrite_path,
                "cache_ttl": route.cache_ttl,
                "rate_limit_override": route.rate_limit_override
            }
            for route in ROUTES
        ],
        "services": {
            name: {
                "instances": config.instances,
                "health_check_path": config.health_check_path,
                "timeout": config.timeout,
                "retries": config.retries,
                "load_balance_strategy": config.load_balance_strategy.value,
                "rate_limit_per_minute": config.rate_limit_per_minute,
                "require_auth": config.require_auth,
                "allowed_roles": config.allowed_roles
            }
            for name, config in SERVICES.items()
        }
    }

# === ROTEAMENTO PRINCIPAL ===

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], tags=["Proxy"])
@app.api_route("/webhook/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], tags=["Proxy"])
async def proxy_request(request: Request):
    """
    **Proxy principal para todos os microserviços**
    
    Este endpoint captura todas as requests para `/api/*` e `/webhook/*`
    e as roteia para os microserviços apropriados baseado na configuração.
    
    **Funcionalidades automáticas:**
    - ✅ Roteamento baseado no path prefix
    - ✅ Load balancing entre instâncias
    - ✅ Autenticação JWT quando necessária
    - ✅ Rate limiting inteligente
    - ✅ Cache de responses (GET requests)
    - ✅ Circuit breaker para proteção
    - ✅ Métricas e logging automáticos
    - ✅ Headers de contexto adicionados
    
    **Exemplos:**
    - `GET /api/auth/users/me` → Auth Service
    - `POST /api/chat/send` → Chat Service  
    - `POST /api/ai/respond` → AI Service
    - `POST /webhook/whatsapp` → Chat Service
    """
    return await api_gateway.handle_request(request)

# === ENDPOINTS DE ADMINISTRAÇÃO ===

@app.post("/admin/cache/clear", tags=["Admin"])
async def clear_cache():
    """Limpar cache do gateway"""
    api_gateway.response_cache.clear()
    await auth_middleware.cleanup_cache()
    
    return {
        "message": "Cache limpo com sucesso",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/admin/rate-limit/blacklist/{ip}", tags=["Admin"])
async def blacklist_ip(ip: str):
    """Adicionar IP à blacklist"""
    rate_limiter.add_to_blacklist(ip)
    
    return {
        "message": f"IP {ip} adicionado à blacklist",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.delete("/admin/rate-limit/blacklist/{ip}", tags=["Admin"])
async def remove_ip_from_blacklist(ip: str):
    """Remover IP da blacklist"""
    rate_limiter.remove_from_blacklist(ip)
    
    return {
        "message": f"IP {ip} removido da blacklist",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/admin/metrics", tags=["Admin"])
async def get_detailed_metrics():
    """Obter métricas detalhadas para monitoramento"""
    try:
        gateway_stats = await api_gateway.get_gateway_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "gateway_version": "1.0.0",
            "metrics": gateway_stats["metrics"],
            "services": gateway_stats["services"],
            "rate_limiter": gateway_stats["rate_limiter"],
            "cache": {
                "response_cache_size": len(api_gateway.response_cache),
                "auth_cache_size": len(auth_middleware.token_cache)
            }
        }
    except Exception as e:
        logger.error(f"❌ Erro ao obter métricas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter métricas"
        )

# === EXECUTAR APLICAÇÃO ===

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=8000,  # Porta principal do gateway
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )