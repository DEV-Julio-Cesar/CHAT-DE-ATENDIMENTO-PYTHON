"""
Aplicação principal FastAPI
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.core.database import create_tables, db_manager
from app.core.redis_client import redis_manager
from app.core.monitoring import monitoring
from app.core.security_simple import security_manager, SecurityMiddleware
from app.core.metrics import metrics_collector
from app.core.circuit_breaker import circuit_breaker_manager
from app.core.cache_strategy import cache_manager
from app.core.query_optimizer import query_optimizer
from app.core.compression import compression_manager, CompressionMiddleware
from app.services.whatsapp_enterprise import whatsapp_api
from app.services.chatbot_ai import chatbot_ai
from app.services.data_migration import migration_service
from app.services.performance_optimizer import performance_optimizer
from app.api.routes import api_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.websocket.main import websocket_router

# Configurar logging estruturado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Métricas Prometheus
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Counter(
    'websocket_connections_total',
    'Total WebSocket connections',
    ['status']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida da aplicação"""
    # Startup
    logger.info("Starting ISP Customer Support application", version=settings.VERSION)
    
    try:
        # Inicializar banco de dados
        await create_tables()
        logger.info("Database initialized")
        
        # Inicializar Redis
        await redis_manager.initialize()
        logger.info("Redis initialized")
        
        # Inicializar WhatsApp Enterprise API
        await whatsapp_api.initialize()
        logger.info("WhatsApp Enterprise API initialized")
        
        # Inicializar Chatbot AI
        await chatbot_ai.initialize()
        logger.info("Chatbot AI initialized")
        
        # Inicializar Performance Optimizer
        await performance_optimizer.initialize()
        logger.info("Performance Optimizer initialized")
        
        # Inicializar sistema de monitoramento
        await monitoring.start()
        logger.info("Advanced monitoring started")
        
        # Inicializar sistema de cache
        await cache_manager.warm_cache({
            "system_config": {
                "fetch_func": lambda: {"initialized": True, "timestamp": time.time()},
                "ttl": 3600
            }
        })
        logger.info("Cache system initialized and warmed")
        
        # Inicializar métricas
        logger.info("Metrics collector initialized")
        
        # Verificar integrações externas
        await check_external_services()
        
        logger.info("Application startup completed")
        yield
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down application")
        await monitoring.stop()
        await whatsapp_api.close()
        await db_manager.close()
        await redis_manager.close()
        logger.info("Application shutdown completed")


async def check_external_services():
    """Verificar serviços externos na inicialização"""
    services_status = {}
    
    # Verificar banco de dados
    services_status['database'] = await db_manager.health_check()
    
    # Verificar Redis
    services_status['redis'] = await redis_manager.health_check()
    
    # Verificar WhatsApp Business API (se configurado)
    if settings.WHATSAPP_ACCESS_TOKEN:
        # TODO: Implementar verificação da API do WhatsApp
        services_status['whatsapp'] = True
    
    # Verificar Gemini AI (se configurado)
    if settings.GEMINI_API_KEY:
        # TODO: Implementar verificação da API do Gemini
        services_status['gemini'] = True
    
    logger.info("External services status", services=services_status)
    
    # Alertar sobre serviços indisponíveis
    failed_services = [name for name, status in services_status.items() if not status]
    if failed_services:
        logger.warning("Some external services are unavailable", failed_services=failed_services)


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Sistema profissional de atendimento ao cliente via WhatsApp para provedores de internet",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Middleware de compressão (deve vir antes de outros middlewares)
app.add_middleware(CompressionMiddleware)

# Middleware de CORS - Configuração segura
allowed_origins = ["*"] if settings.DEBUG else [
    "https://yourdomain.com",
    "https://app.yourdomain.com",
    "http://localhost:3000",  # Para desenvolvimento local
    "http://localhost:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"]
)

# Middleware de segurança
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
    )


# Middleware para métricas
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Coletar métricas de requests HTTP"""
    start_time = time.time()
    
    # Processar request
    response = await call_next(request)
    
    # Calcular duração
    duration = time.time() - start_time
    
    # Extrair informações
    method = request.method
    endpoint = request.url.path
    status_code = response.status_code
    
    # Atualizar métricas
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    
    # Adicionar headers de resposta
    response.headers["X-Process-Time"] = str(duration)
    
    return response


# Middleware para logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log estruturado de requests"""
    start_time = time.time()
    
    # Log do request
    logger.info(
        "HTTP request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log da resposta
        logger.info(
            "HTTP request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration=duration,
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "HTTP request failed",
            method=request.method,
            url=str(request.url),
            duration=duration,
            error=str(e),
        )
        raise


# Handler de exceções global
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler personalizado para HTTPException"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": time.time(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para exceções não tratadas"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        url=str(request.url),
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": time.time(),
            }
        },
    )


# Rotas principais
app.include_router(api_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ws")

# Importar e incluir novos routers
from app.api.endpoints.chatbot import router as chatbot_router
from app.api.endpoints.migration import router as migration_router
from app.api.endpoints.optimization import router as optimization_router

app.include_router(chatbot_router, prefix="/api/v1")
app.include_router(migration_router, prefix="/api/v1")
app.include_router(optimization_router, prefix="/api/v1")

# Middleware de segurança
app.add_middleware(SecurityMiddleware)


# Endpoint de health check
@app.get("/health")
async def health_check():
    """Verificação de saúde da aplicação"""
    checks = {
        "database": await db_manager.health_check(),
        "redis": await redis_manager.health_check(),
        "timestamp": time.time(),
    }
    
    # Verificar se todos os serviços estão funcionando
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "version": settings.VERSION,
            "checks": checks,
        }
    )


# Endpoint de cache stats
@app.get("/cache/stats")
async def cache_stats():
    """Estatísticas do sistema de cache"""
    cache_stats = cache_manager.get_stats()
    redis_health = await redis_manager.health_check()
    
    return {
        "cache_stats": cache_stats,
        "redis_health": redis_health,
        "timestamp": time.time()
    }


# Endpoint de compressão stats
@app.get("/compression/stats")
async def compression_stats():
    """Estatísticas de compressão"""
    return {
        "compression_stats": compression_manager.get_stats(),
        "timestamp": time.time()
    }


# Endpoint de performance
@app.get("/performance/dashboard")
async def performance_dashboard():
    """Dashboard de performance otimizado"""
    stats = await query_optimizer.get_dashboard_stats_cached()
    return {
        "dashboard_stats": stats,
        "cache_hit": True,  # Sempre vem do cache
        "timestamp": time.time()
    }


# Endpoint de circuit breakers
@app.get("/circuit-breakers")
async def circuit_breakers_status():
    """Status dos circuit breakers"""
    return {
        "circuit_breakers": circuit_breaker_manager.get_all_states(),
        "timestamp": time.time()
    }


# Endpoint para resetar circuit breaker
@app.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str):
    """Resetar circuit breaker específico"""
    await circuit_breaker_manager.reset_breaker(name)
    return {"message": f"Circuit breaker {name} reset successfully"}


# Endpoint de métricas Prometheus
@app.get("/metrics")
async def metrics():
    """Endpoint para métricas Prometheus"""
    from fastapi.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Endpoint de informações da aplicação
@app.get("/info")
async def app_info():
    """Informações da aplicação"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "environment": "development" if settings.DEBUG else "production",
    }


# Endpoint raiz
@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "docs": "/docs" if settings.DEBUG else None,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_config=None,  # Usar nosso logging estruturado
    )