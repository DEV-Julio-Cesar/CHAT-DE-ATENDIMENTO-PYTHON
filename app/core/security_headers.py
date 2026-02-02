"""
Security Headers Middleware
Implementação profissional de headers de segurança HTTP

Headers implementados:
- Content-Security-Policy (CSP)
- Strict-Transport-Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
- Cross-Origin-Embedder-Policy (COEP)
- Cross-Origin-Opener-Policy (COOP)
- Cross-Origin-Resource-Policy (CORP)
- Cache-Control
- X-Request-ID
"""

import uuid
import hashlib
import secrets
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class CSPDirective(Enum):
    """Diretivas CSP disponíveis"""
    DEFAULT_SRC = "default-src"
    SCRIPT_SRC = "script-src"
    STYLE_SRC = "style-src"
    IMG_SRC = "img-src"
    FONT_SRC = "font-src"
    CONNECT_SRC = "connect-src"
    MEDIA_SRC = "media-src"
    OBJECT_SRC = "object-src"
    FRAME_SRC = "frame-src"
    FRAME_ANCESTORS = "frame-ancestors"
    FORM_ACTION = "form-action"
    BASE_URI = "base-uri"
    WORKER_SRC = "worker-src"
    MANIFEST_SRC = "manifest-src"
    UPGRADE_INSECURE_REQUESTS = "upgrade-insecure-requests"
    BLOCK_ALL_MIXED_CONTENT = "block-all-mixed-content"
    REPORT_URI = "report-uri"
    REPORT_TO = "report-to"


class PermissionsPolicy(Enum):
    """Políticas de permissão do navegador"""
    ACCELEROMETER = "accelerometer"
    AMBIENT_LIGHT_SENSOR = "ambient-light-sensor"
    AUTOPLAY = "autoplay"
    BATTERY = "battery"
    CAMERA = "camera"
    DISPLAY_CAPTURE = "display-capture"
    DOCUMENT_DOMAIN = "document-domain"
    ENCRYPTED_MEDIA = "encrypted-media"
    FULLSCREEN = "fullscreen"
    GEOLOCATION = "geolocation"
    GYROSCOPE = "gyroscope"
    MAGNETOMETER = "magnetometer"
    MICROPHONE = "microphone"
    MIDI = "midi"
    PAYMENT = "payment"
    PICTURE_IN_PICTURE = "picture-in-picture"
    PUBLICKEY_CREDENTIALS_GET = "publickey-credentials-get"
    SCREEN_WAKE_LOCK = "screen-wake-lock"
    SYNC_XHR = "sync-xhr"
    USB = "usb"
    WEB_SHARE = "web-share"
    XR_SPATIAL_TRACKING = "xr-spatial-tracking"


@dataclass
class SecurityHeadersConfig:
    """Configuração de security headers"""
    
    # ===== HSTS (HTTP Strict Transport Security) =====
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 ano
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    
    # ===== CSP (Content Security Policy) =====
    csp_enabled: bool = True
    csp_report_only: bool = False  # Modo report-only para teste
    csp_report_uri: Optional[str] = None
    csp_directives: Dict[str, List[str]] = field(default_factory=lambda: {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'"],  # Ajustar em produção
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "img-src": ["'self'", "data:", "https:", "blob:"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "connect-src": ["'self'", "wss:", "https:"],
        "media-src": ["'self'", "https:"],
        "object-src": ["'none'"],
        "frame-src": ["'none'"],
        "frame-ancestors": ["'self'"],
        "form-action": ["'self'"],
        "base-uri": ["'self'"],
        "worker-src": ["'self'", "blob:"],
        "manifest-src": ["'self'"],
    })
    
    # ===== X-Frame-Options =====
    frame_options_enabled: bool = True
    frame_options_value: str = "DENY"  # DENY, SAMEORIGIN, ALLOW-FROM uri
    
    # ===== X-Content-Type-Options =====
    content_type_options_enabled: bool = True
    
    # ===== X-XSS-Protection =====
    xss_protection_enabled: bool = True
    xss_protection_mode: str = "1; mode=block"
    
    # ===== Referrer-Policy =====
    referrer_policy_enabled: bool = True
    referrer_policy_value: str = "strict-origin-when-cross-origin"
    
    # ===== Permissions-Policy =====
    permissions_policy_enabled: bool = True
    permissions_policy: Dict[str, List[str]] = field(default_factory=lambda: {
        "accelerometer": [],
        "ambient-light-sensor": [],
        "autoplay": ["self"],
        "battery": [],
        "camera": [],
        "display-capture": [],
        "document-domain": [],
        "encrypted-media": ["self"],
        "fullscreen": ["self"],
        "geolocation": [],
        "gyroscope": [],
        "magnetometer": [],
        "microphone": [],
        "midi": [],
        "payment": [],
        "picture-in-picture": ["self"],
        "publickey-credentials-get": ["self"],
        "screen-wake-lock": [],
        "sync-xhr": [],
        "usb": [],
        "web-share": ["self"],
        "xr-spatial-tracking": [],
    })
    
    # ===== Cross-Origin Policies =====
    coep_enabled: bool = False  # Pode quebrar recursos de terceiros
    coep_value: str = "require-corp"
    
    coop_enabled: bool = True
    coop_value: str = "same-origin"
    
    corp_enabled: bool = True
    corp_value: str = "same-origin"
    
    # ===== Cache-Control =====
    cache_control_enabled: bool = True
    cache_control_api: str = "no-store, no-cache, must-revalidate, private"
    cache_control_static: str = "public, max-age=31536000, immutable"
    
    # ===== X-Request-ID =====
    request_id_enabled: bool = True
    
    # ===== Custom Headers =====
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # ===== Rotas excluídas =====
    excluded_paths: List[str] = field(default_factory=lambda: [
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json"
    ])


class SecurityHeadersManager:
    """Gerenciador de security headers"""
    
    def __init__(self, config: Optional[SecurityHeadersConfig] = None):
        self.config = config or self._get_default_config()
        self._nonce_cache: Dict[str, str] = {}
        
    def _get_default_config(self) -> SecurityHeadersConfig:
        """Configuração padrão baseada no ambiente"""
        config = SecurityHeadersConfig()
        
        if settings.DEBUG:
            # Configurações mais permissivas para desenvolvimento
            config.hsts_enabled = False
            config.csp_report_only = True
            config.coep_enabled = False
            config.coop_enabled = False
            config.frame_options_value = "SAMEORIGIN"
            
            # CSP mais permissivo para desenvolvimento
            config.csp_directives["script-src"] = ["'self'", "'unsafe-inline'", "'unsafe-eval'"]
            config.csp_directives["connect-src"] = ["'self'", "ws:", "wss:", "http:", "https:"]
        else:
            # Produção: configurações restritivas
            config.hsts_preload = True
            config.frame_options_value = "DENY"
            
        return config
    
    def generate_nonce(self) -> str:
        """Gera nonce único para CSP"""
        nonce = secrets.token_urlsafe(16)
        return nonce
    
    def _build_csp_header(self, nonce: Optional[str] = None) -> str:
        """Constrói header CSP"""
        parts = []
        
        for directive, values in self.config.csp_directives.items():
            if values:
                # Adicionar nonce se fornecido e for diretiva de script/style
                if nonce and directive in ["script-src", "style-src"]:
                    values = values + [f"'nonce-{nonce}'"]
                
                parts.append(f"{directive} {' '.join(values)}")
            else:
                # Diretivas sem valor (ex: upgrade-insecure-requests)
                parts.append(directive)
        
        # Adicionar report-uri se configurado
        if self.config.csp_report_uri:
            parts.append(f"report-uri {self.config.csp_report_uri}")
        
        return "; ".join(parts)
    
    def _build_permissions_policy(self) -> str:
        """Constrói header Permissions-Policy"""
        parts = []
        
        for permission, allowed_origins in self.config.permissions_policy.items():
            if allowed_origins:
                origins = " ".join(allowed_origins)
                parts.append(f"{permission}=({origins})")
            else:
                parts.append(f"{permission}=()")
        
        return ", ".join(parts)
    
    def _build_hsts_header(self) -> str:
        """Constrói header HSTS"""
        parts = [f"max-age={self.config.hsts_max_age}"]
        
        if self.config.hsts_include_subdomains:
            parts.append("includeSubDomains")
        
        if self.config.hsts_preload:
            parts.append("preload")
        
        return "; ".join(parts)
    
    def get_headers(
        self, 
        request_path: str,
        nonce: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Gera todos os security headers"""
        headers: Dict[str, str] = {}
        
        # Verificar se o path está excluído
        is_excluded = any(
            request_path.startswith(excluded) 
            for excluded in self.config.excluded_paths
        )
        
        # ===== HSTS =====
        if self.config.hsts_enabled and not settings.DEBUG:
            headers["Strict-Transport-Security"] = self._build_hsts_header()
        
        # ===== CSP =====
        if self.config.csp_enabled and not is_excluded:
            csp_value = self._build_csp_header(nonce)
            header_name = "Content-Security-Policy-Report-Only" if self.config.csp_report_only else "Content-Security-Policy"
            headers[header_name] = csp_value
        
        # ===== X-Frame-Options =====
        if self.config.frame_options_enabled:
            headers["X-Frame-Options"] = self.config.frame_options_value
        
        # ===== X-Content-Type-Options =====
        if self.config.content_type_options_enabled:
            headers["X-Content-Type-Options"] = "nosniff"
        
        # ===== X-XSS-Protection =====
        if self.config.xss_protection_enabled:
            headers["X-XSS-Protection"] = self.config.xss_protection_mode
        
        # ===== Referrer-Policy =====
        if self.config.referrer_policy_enabled:
            headers["Referrer-Policy"] = self.config.referrer_policy_value
        
        # ===== Permissions-Policy =====
        if self.config.permissions_policy_enabled:
            headers["Permissions-Policy"] = self._build_permissions_policy()
        
        # ===== Cross-Origin Policies =====
        if self.config.coep_enabled:
            headers["Cross-Origin-Embedder-Policy"] = self.config.coep_value
        
        if self.config.coop_enabled:
            headers["Cross-Origin-Opener-Policy"] = self.config.coop_value
        
        if self.config.corp_enabled:
            headers["Cross-Origin-Resource-Policy"] = self.config.corp_value
        
        # ===== Cache-Control =====
        if self.config.cache_control_enabled:
            is_api = request_path.startswith("/api/")
            is_static = request_path.startswith("/static/") or any(
                request_path.endswith(ext) for ext in [".js", ".css", ".png", ".jpg", ".ico", ".woff", ".woff2"]
            )
            
            if is_api:
                headers["Cache-Control"] = self.config.cache_control_api
                headers["Pragma"] = "no-cache"
                headers["Expires"] = "0"
            elif is_static:
                headers["Cache-Control"] = self.config.cache_control_static
        
        # ===== X-Request-ID =====
        if self.config.request_id_enabled and request_id:
            headers["X-Request-ID"] = request_id
        
        # ===== Remover headers sensíveis =====
        headers["X-Powered-By"] = ""  # Será removido
        headers["Server"] = "ISP-Support"
        
        # ===== Custom Headers =====
        headers.update(self.config.custom_headers)
        
        return headers
    
    def validate_csp_report(self, report: Dict[str, Any]) -> bool:
        """Valida relatório CSP recebido"""
        required_fields = ["csp-report"]
        
        if not all(field in report for field in required_fields):
            return False
        
        csp_report = report["csp-report"]
        
        # Log do relatório CSP
        logger.warning(
            "CSP violation report",
            blocked_uri=csp_report.get("blocked-uri"),
            violated_directive=csp_report.get("violated-directive"),
            original_policy=csp_report.get("original-policy"),
            document_uri=csp_report.get("document-uri"),
            referrer=csp_report.get("referrer"),
            source_file=csp_report.get("source-file"),
            line_number=csp_report.get("line-number"),
            column_number=csp_report.get("column-number")
        )
        
        return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para aplicar security headers"""
    
    def __init__(
        self, 
        app: ASGIApp,
        config: Optional[SecurityHeadersConfig] = None
    ):
        super().__init__(app)
        self.manager = SecurityHeadersManager(config)
        
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Gerar request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Gerar nonce para CSP
        nonce = self.manager.generate_nonce()
        
        # Armazenar no request state para uso em templates
        request.state.csp_nonce = nonce
        request.state.request_id = request_id
        
        try:
            # Processar request
            response = await call_next(request)
            
            # Obter security headers
            security_headers = self.manager.get_headers(
                request_path=request.url.path,
                nonce=nonce,
                request_id=request_id
            )
            
            # Aplicar headers na resposta
            for header, value in security_headers.items():
                if value:  # Não adicionar headers vazios
                    response.headers[header] = value
                elif header in response.headers:
                    # Remover headers vazios
                    del response.headers[header]
            
            return response
            
        except Exception as e:
            logger.error("Error in security headers middleware", error=str(e))
            raise


# =============================================================================
# CONFIGURAÇÕES PRÉ-DEFINIDAS
# =============================================================================

class SecurityPresets:
    """Configurações pré-definidas de segurança"""
    
    @staticmethod
    def strict() -> SecurityHeadersConfig:
        """Configuração mais restritiva para máxima segurança"""
        return SecurityHeadersConfig(
            hsts_enabled=True,
            hsts_max_age=63072000,  # 2 anos
            hsts_include_subdomains=True,
            hsts_preload=True,
            csp_enabled=True,
            csp_report_only=False,
            csp_directives={
                "default-src": ["'self'"],
                "script-src": ["'self'"],  # Sem unsafe-inline
                "style-src": ["'self'"],
                "img-src": ["'self'", "data:"],
                "font-src": ["'self'"],
                "connect-src": ["'self'"],
                "media-src": ["'self'"],
                "object-src": ["'none'"],
                "frame-src": ["'none'"],
                "frame-ancestors": ["'none'"],
                "form-action": ["'self'"],
                "base-uri": ["'none'"],
                "upgrade-insecure-requests": [],
                "block-all-mixed-content": [],
            },
            frame_options_value="DENY",
            coep_enabled=True,
            coop_enabled=True,
            corp_enabled=True,
        )
    
    @staticmethod
    def moderate() -> SecurityHeadersConfig:
        """Configuração moderada para balanceamento segurança/funcionalidade"""
        return SecurityHeadersConfig(
            hsts_enabled=True,
            hsts_max_age=31536000,
            csp_enabled=True,
            csp_report_only=False,
            csp_directives={
                "default-src": ["'self'"],
                "script-src": ["'self'", "'unsafe-inline'"],
                "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
                "img-src": ["'self'", "data:", "https:", "blob:"],
                "font-src": ["'self'", "https://fonts.gstatic.com"],
                "connect-src": ["'self'", "wss:", "https:"],
                "media-src": ["'self'", "https:"],
                "object-src": ["'none'"],
                "frame-src": ["'self'"],
                "frame-ancestors": ["'self'"],
                "form-action": ["'self'"],
                "base-uri": ["'self'"],
            },
            frame_options_value="SAMEORIGIN",
            coep_enabled=False,
            coop_enabled=True,
            corp_enabled=True,
        )
    
    @staticmethod
    def relaxed() -> SecurityHeadersConfig:
        """Configuração permissiva para desenvolvimento ou APIs"""
        return SecurityHeadersConfig(
            hsts_enabled=False,
            csp_enabled=True,
            csp_report_only=True,  # Apenas relata, não bloqueia
            csp_directives={
                "default-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'", "*"],
                "img-src": ["*", "data:", "blob:"],
                "connect-src": ["*"],
            },
            frame_options_value="SAMEORIGIN",
            coep_enabled=False,
            coop_enabled=False,
            corp_enabled=False,
        )
    
    @staticmethod
    def api_only() -> SecurityHeadersConfig:
        """Configuração otimizada para APIs (sem CSP, sem cache)"""
        return SecurityHeadersConfig(
            hsts_enabled=True,
            hsts_max_age=31536000,
            csp_enabled=False,  # APIs não precisam de CSP
            frame_options_enabled=True,
            frame_options_value="DENY",
            content_type_options_enabled=True,
            xss_protection_enabled=True,
            referrer_policy_enabled=True,
            referrer_policy_value="no-referrer",
            permissions_policy_enabled=False,
            coep_enabled=False,
            coop_enabled=False,
            corp_enabled=True,
            cache_control_enabled=True,
            cache_control_api="no-store, no-cache, must-revalidate, private, max-age=0",
        )
    
    @staticmethod
    def telecom_isp() -> SecurityHeadersConfig:
        """Configuração personalizada para ISP de Telecomunicações"""
        return SecurityHeadersConfig(
            # HSTS forte
            hsts_enabled=True,
            hsts_max_age=31536000,
            hsts_include_subdomains=True,
            hsts_preload=True,
            
            # CSP moderado para permitir WhatsApp e integrações
            csp_enabled=True,
            csp_report_only=False,
            csp_directives={
                "default-src": ["'self'"],
                "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
                "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net"],
                "img-src": ["'self'", "data:", "https:", "blob:", "https://*.whatsapp.net", "https://*.fbcdn.net"],
                "font-src": ["'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
                "connect-src": ["'self'", "wss:", "https:", "https://graph.facebook.com", "https://*.whatsapp.net"],
                "media-src": ["'self'", "https:", "blob:", "https://*.whatsapp.net"],
                "object-src": ["'none'"],
                "frame-src": ["'self'"],
                "frame-ancestors": ["'self'"],
                "form-action": ["'self'"],
                "base-uri": ["'self'"],
                "worker-src": ["'self'", "blob:"],
            },
            
            # Frame options permite embedding interno
            frame_options_value="SAMEORIGIN",
            
            # Referrer para privacidade
            referrer_policy_value="strict-origin-when-cross-origin",
            
            # Permissões restritas
            permissions_policy={
                "accelerometer": [],
                "ambient-light-sensor": [],
                "autoplay": ["self"],
                "battery": [],
                "camera": [],  # Pode precisar para WhatsApp Web
                "display-capture": [],
                "document-domain": [],
                "encrypted-media": ["self"],
                "fullscreen": ["self"],
                "geolocation": [],
                "gyroscope": [],
                "magnetometer": [],
                "microphone": [],  # Pode precisar para WhatsApp Web
                "midi": [],
                "payment": [],
                "picture-in-picture": ["self"],
                "publickey-credentials-get": ["self"],
                "screen-wake-lock": [],
                "sync-xhr": [],
                "usb": [],
                "web-share": ["self"],
                "xr-spatial-tracking": [],
            },
            
            # Cross-origin policies moderadas
            coep_enabled=False,  # Desabilitado para permitir recursos externos
            coop_enabled=True,
            corp_enabled=True,
            corp_value="same-site",  # Mais permissivo que same-origin
            
            # Cache
            cache_control_enabled=True,
            cache_control_api="no-store, no-cache, must-revalidate, private",
            cache_control_static="public, max-age=604800, immutable",  # 1 semana
            
            # Request ID para rastreamento
            request_id_enabled=True,
            
            # Headers customizados
            custom_headers={
                "X-DNS-Prefetch-Control": "on",
                "X-Download-Options": "noopen",
                "X-Permitted-Cross-Domain-Policies": "none",
            },
            
            # Excluir endpoints de monitoramento
            excluded_paths=[
                "/health",
                "/metrics",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/_internal",
            ],
        )


# =============================================================================
# INSTÂNCIA GLOBAL
# =============================================================================

# Usar configuração específica para ISP de Telecomunicações
security_headers_config = SecurityPresets.telecom_isp()
security_headers_manager = SecurityHeadersManager(security_headers_config)


def get_security_headers_middleware(config: Optional[SecurityHeadersConfig] = None) -> SecurityHeadersMiddleware:
    """Factory para criar middleware com configuração específica"""
    return SecurityHeadersMiddleware(app=None, config=config or security_headers_config)


# =============================================================================
# ENDPOINT PARA RELATÓRIOS CSP
# =============================================================================

async def csp_report_endpoint(request: Request) -> JSONResponse:
    """Endpoint para receber relatórios de violação CSP"""
    try:
        report = await request.json()
        security_headers_manager.validate_csp_report(report)
        return JSONResponse(content={"status": "received"}, status_code=204)
    except Exception as e:
        logger.error("Error processing CSP report", error=str(e))
        return JSONResponse(content={"error": "Invalid report"}, status_code=400)
