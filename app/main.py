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
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

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
from app.core.rate_limiter import rate_limiter, RateLimitConfig  # SEMANA 1
from app.core.audit_logger import audit_logger  # SEMANA 1
from app.core.security_headers import SecurityHeadersMiddleware, SecurityPresets  # SEMANA 1 - Security Headers
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida da aplicação"""
    # Startup
    logger.info("Starting ISP Customer Support application", version=settings.VERSION)
    
    # Flags para rastrear o que foi inicializado
    db_initialized = False
    redis_initialized = False
    whatsapp_initialized = False
    chatbot_initialized = False
    monitoring_started = False
    
    try:
        # Inicializar banco de dados (opcional - modo gracioso)
        try:
            await create_tables()
            logger.info("Database initialized")
            db_initialized = True
        except Exception as e:
            logger.warning("Database unavailable - running in limited mode", error=str(e))
        
        # Inicializar Redis (DESABILITADO - para performance local)
        # Para habilitar Redis: remover comentário abaixo e instalar Redis
        # try:
        #     await redis_manager.initialize()
        #     logger.info("Redis initialized")
        #     redis_initialized = True
        # except Exception as e:
        #     logger.warning("Redis unavailable - running without cache", error=str(e))
        redis_initialized = False  # Redis desabilitado para performance
        
        # Inicializar WhatsApp Enterprise API
        try:
            await whatsapp_api.initialize()
            logger.info("WhatsApp Enterprise API initialized")
            whatsapp_initialized = True
        except Exception as e:
            logger.warning("WhatsApp API initialization failed", error=str(e))
        
        # Inicializar Chatbot AI
        try:
            await chatbot_ai.initialize()
            logger.info("Chatbot AI initialized")
            chatbot_initialized = True
        except Exception as e:
            logger.warning("Chatbot AI initialization failed", error=str(e))
        
        # Inicializar Performance Optimizer
        try:
            await performance_optimizer.initialize()
            logger.info("Performance Optimizer initialized")
        except Exception as e:
            logger.warning("Performance Optimizer initialization failed", error=str(e))
        
        # Inicializar sistema de monitoramento
        try:
            await monitoring.start()
            logger.info("Advanced monitoring started")
            monitoring_started = True
        except Exception as e:
            logger.warning("Monitoring initialization failed", error=str(e))
        
        # Inicializar sistema de cache
        if redis_initialized:
            try:
                await cache_manager.warm_cache({
                    "system_config": {
                        "fetch_func": lambda: {"initialized": True, "timestamp": time.time()},
                        "ttl": 3600
                    }
                })
                logger.info("Cache system initialized and warmed")
            except Exception as e:
                logger.warning("Cache warm-up failed", error=str(e))
        
        # Inicializar métricas
        logger.info("Metrics collector initialized")
        
        # Verificar integrações externas
        await check_external_services()
        
        logger.info("Application startup completed", 
                   db=db_initialized, 
                   redis=redis_initialized,
                   whatsapp=whatsapp_initialized,
                   chatbot=chatbot_initialized)
        yield
        
    except Exception as e:
        logger.error("Critical failure during startup", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down application")
        if monitoring_started:
            try:
                await monitoring.stop()
            except Exception:
                pass
        if whatsapp_initialized:
            try:
                await whatsapp_api.close()
            except Exception:
                pass
        if db_initialized:
            try:
                await db_manager.close()
            except Exception:
                pass
        if redis_initialized:
            try:
                await redis_manager.close()
            except Exception:
                pass
        logger.info("Application shutdown completed")


async def check_external_services():
    """Verificar serviços externos na inicialização"""
    services_status = {}
    
    # Verificar banco de dados
    services_status['database'] = await db_manager.health_check()
    
    # Redis DESABILITADO para performance local
    services_status['redis'] = False  # Desabilitado
    
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


# ============================================================================
# ROTAS DE PÁGINAS WEB - Configurar ANTES dos middlewares
# ============================================================================
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "web" / "templates"
STATIC_DIR = Path(__file__).parent / "web" / "static"

# Criar aplicação FastAPI com documentação completa
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="""
## 🚀 Sistema de Chat de Atendimento - Telecomunicações

Sistema profissional de atendimento ao cliente via WhatsApp para provedores de internet (ISP).
Desenvolvido para escalar até **10.000+ clientes** com alta disponibilidade.

### 📋 Funcionalidades Principais

* **🤖 Chatbot com IA** - Atendimento automático inicial usando Google Gemini
* **💬 WhatsApp Business API** - Integração completa com Meta Cloud API
* **🔄 WebSocket** - Comunicação em tempo real para atendentes
* **🔐 Autenticação JWT** - Segurança com tokens e roles (admin/atendente/user)
* **📊 Métricas** - Dashboard com Prometheus/Grafana
* **🛡️ Rate Limiting** - Proteção contra brute force e DDoS

### 🏗️ Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│  FastAPI    │────▶│  SQL Server │
│ (Load Bal)  │     │  (API)      │     │  (Auth)     │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Redis     │────▶│  PostgreSQL │
                    │  (Cache)    │     │   (Data)    │
                    └─────────────┘     └─────────────┘
```

### 🔑 Autenticação

Todos os endpoints protegidos requerem o header:
```
Authorization: Bearer <seu_token_jwt>
```

### 📞 Contato

* **Documentação**: [docs/README.md](docs/README.md)
* **Repositório**: GitHub
""",
    openapi_tags=[
        {
            "name": "auth",
            "description": "🔐 **Autenticação e Autorização** - Login, logout, registro e gerenciamento de tokens JWT",
        },
        {
            "name": "users",
            "description": "👥 **Gerenciamento de Usuários** - CRUD de usuários com RBAC (Role-Based Access Control)",
        },
        {
            "name": "conversations",
            "description": "💬 **Conversas** - Gerenciamento de atendimentos e histórico de mensagens",
        },
        {
            "name": "whatsapp",
            "description": "📱 **WhatsApp Business API** - Webhook, envio de mensagens e templates",
        },
        {
            "name": "chatbot",
            "description": "🤖 **Chatbot IA** - Respostas automáticas com Google Gemini AI",
        },
        {
            "name": "campaigns",
            "description": "📢 **Campanhas** - Envio em massa e agendamento de mensagens",
        },
        {
            "name": "dashboard",
            "description": "📊 **Dashboard** - Métricas, relatórios e analytics em tempo real",
        },
        {
            "name": "websocket",
            "description": "🔄 **WebSocket** - Comunicação em tempo real para chat",
        },
        {
            "name": "health",
            "description": "❤️ **Health Check** - Status da aplicação e dependências",
        },
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "filter": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
        "syntaxHighlight.theme": "monokai"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://yourdomain.com/license",
    },
    contact={
        "name": "Suporte Técnico",
        "email": "suporte@yourdomain.com",
    },
)

# ============================================================================
# MONTAR ARQUIVOS ESTÁTICOS - Antes dos middlewares
# ============================================================================
try:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.warning(f"Failed to mount static files: {e}")

# Middleware de compressão (deve vir antes de outros middlewares)
app.add_middleware(CompressionMiddleware)

# Middleware de Security Headers (CSP, HSTS, X-Frame-Options, etc.)
# DESATIVADO TEMPORARIAMENTE - estava bloqueando estilos inline
# app.add_middleware(
#     SecurityHeadersMiddleware,
#     config=SecurityPresets.telecom_isp()
# )

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


# ============================================================================
# MIDDLEWARE DE RATE LIMITING (SEMANA 1)
# ============================================================================
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware de rate limiting global
    Protege contra brute force e DDoS
    """
    
    # Endpoints que precisam de rate limiting
    path = request.url.path
    method = request.method
    
    # Identificar cliente
    client_ip = request.client.host if request.client else "unknown"
    
    # ===== LOGIN: 5 tentativas em 15 minutos =====
    if method == "POST" and "/auth/login" in path:
        allowed, remaining = await rate_limiter.is_allowed(
            identifier=f"login:{client_ip}",
            max_requests=RateLimitConfig.LOGIN["max_requests"],
            window_seconds=RateLimitConfig.LOGIN["window_seconds"]
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many login attempts. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(RateLimitConfig.LOGIN["max_requests"]),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(RateLimitConfig.LOGIN["window_seconds"])
                }
            )
    
    # ===== GENERAL API: 100 requisições por minuto =====
    elif "/api/" in path and method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
        allowed, remaining = await rate_limiter.is_allowed(
            identifier=f"api:{client_ip}",
            max_requests=RateLimitConfig.API_DEFAULT["max_requests"],
            window_seconds=RateLimitConfig.API_DEFAULT["window_seconds"]
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
                headers={
                    "X-RateLimit-Limit": str(RateLimitConfig.API_DEFAULT["max_requests"]),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(RateLimitConfig.API_DEFAULT["window_seconds"])
                }
            )
    
    response = await call_next(request)
    return response


# ============================================================================
# MIDDLEWARE DE AUDITORIA (SEMANA 1)
# ============================================================================
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """
    Middleware de auditoria para endpoints sensíveis
    """
    
    # Endpoints auditados
    if request.url.path.startswith("/api/users") or \
       request.url.path.startswith("/api/gdpr") or \
       request.url.path.startswith("/api/auth"):
        
        client_ip = request.client.host if request.client else "unknown"
        
        # Log de tentativa de acesso
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            logger.info(
                "Sensitive endpoint access",
                method=request.method,
                path=request.url.path,
                client_ip=client_ip
            )
    
    response = await call_next(request)
    return response


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
    metrics_collector.REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    metrics_collector.REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    
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

# Rotas PWA Mobile (na raiz, sem prefixo)
from app.api.endpoints.mobile_pwa import router as mobile_pwa_router
app.include_router(mobile_pwa_router)

# Middleware de segurança
app.add_middleware(SecurityMiddleware)


# Endpoint de health check
@app.get("/health")
async def health_check():
    """Verificação de saúde da aplicação"""
    checks = {
        "database": await db_manager.health_check(),
        "redis": False,  # Redis desabilitado para performance
        "timestamp": time.time(),
    }
    
    # Verificar se todos os serviços estão funcionando (ignora Redis)
    all_healthy = checks["database"]
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
    
    return {
        "cache_stats": cache_stats,
        "redis_health": False,  # Redis desabilitado
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
        "chatbot_admin": "/chatbot-admin",
    }


# ============================================================================
# ROTAS DE PÁGINAS WEB
# ============================================================================

@app.get("/login", include_in_schema=False)
async def login_page():
    """Página de login com autenticação JWT v2"""
    return FileResponse(TEMPLATES_DIR / "login_v2.html", media_type="text/html")


@app.get("/login-legacy", include_in_schema=False)
async def login_legacy_page():
    """Página de login legada"""
    return FileResponse(TEMPLATES_DIR / "login.html", media_type="text/html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    """Dashboard principal"""
    return FileResponse(TEMPLATES_DIR / "dashboard.html", media_type="text/html")


@app.get("/chat", include_in_schema=False)
async def chat_page():
    """Página de chat/atendimento"""
    return FileResponse(TEMPLATES_DIR / "chat.html", media_type="text/html")


@app.get("/chatbot-admin", include_in_schema=False)
async def chatbot_admin_page():
    """Interface de treinamento do chatbot"""
    return FileResponse(TEMPLATES_DIR / "chatbot_admin.html", media_type="text/html")


@app.get("/customers", include_in_schema=False)
async def customers_page():
    """Página de clientes"""
    return FileResponse(TEMPLATES_DIR / "customers.html", media_type="text/html")


@app.get("/whatsapp", include_in_schema=False)
async def whatsapp_config_page():
    """Página de configuração do WhatsApp"""
    return FileResponse(TEMPLATES_DIR / "whatsapp_config.html", media_type="text/html")


@app.get("/agents", include_in_schema=False)
async def agents_page():
    """Página de agentes"""
    return FileResponse(TEMPLATES_DIR / "agents.html", media_type="text/html")


@app.get("/settings", include_in_schema=False)
async def settings_page():
    """Página de configurações"""
    return FileResponse(TEMPLATES_DIR / "settings.html", media_type="text/html")


@app.get("/campaigns", include_in_schema=False)
async def campaigns_page():
    """Página de campanhas de marketing"""
    return FileResponse(TEMPLATES_DIR / "campaigns.html", media_type="text/html")


@app.get("/users", include_in_schema=False)
async def users_page():
    """Página de gerenciamento de usuários"""
    return FileResponse(TEMPLATES_DIR / "users.html", media_type="text/html")


@app.get("/teste", include_in_schema=False)
async def teste_page():
    """Página de teste"""
    return FileResponse(TEMPLATES_DIR / "teste.html", media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_config=None,  # Usar nosso logging estruturado
    )