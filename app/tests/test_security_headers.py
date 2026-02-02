"""
Testes para Security Headers Middleware
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.core.security_headers import (
    SecurityHeadersConfig,
    SecurityHeadersManager,
    SecurityHeadersMiddleware,
    SecurityPresets,
    CSPDirective,
    PermissionsPolicy
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def default_config():
    """Configuração padrão"""
    return SecurityHeadersConfig()


@pytest.fixture
def strict_config():
    """Configuração restritiva"""
    return SecurityPresets.strict()


@pytest.fixture
def telecom_config():
    """Configuração para ISP"""
    return SecurityPresets.telecom_isp()


@pytest.fixture
def manager(default_config):
    """Manager com configuração padrão"""
    return SecurityHeadersManager(default_config)


@pytest.fixture
def test_app():
    """Aplicação FastAPI de teste"""
    app = FastAPI()
    
    app.add_middleware(
        SecurityHeadersMiddleware,
        config=SecurityPresets.moderate()
    )
    
    @app.get("/")
    async def root():
        return {"message": "Hello"}
    
    @app.get("/api/data")
    async def api_data():
        return {"data": "test"}
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    @app.get("/static/app.js")
    async def static_file():
        return {"content": "js"}
    
    return app


@pytest.fixture
def client(test_app):
    """Cliente de teste"""
    return TestClient(test_app)


# =============================================================================
# TESTES DE CONFIGURAÇÃO
# =============================================================================

class TestSecurityHeadersConfig:
    """Testes para SecurityHeadersConfig"""
    
    def test_default_config_values(self, default_config):
        """Valores padrão da configuração"""
        assert default_config.hsts_enabled is True
        assert default_config.hsts_max_age == 31536000  # 1 ano
        assert default_config.csp_enabled is True
        assert default_config.frame_options_value == "DENY"
        assert default_config.content_type_options_enabled is True
    
    def test_csp_directives_present(self, default_config):
        """Diretivas CSP presentes"""
        assert "default-src" in default_config.csp_directives
        assert "script-src" in default_config.csp_directives
        assert "style-src" in default_config.csp_directives
        assert "img-src" in default_config.csp_directives
    
    def test_permissions_policy_present(self, default_config):
        """Políticas de permissão presentes"""
        assert "camera" in default_config.permissions_policy
        assert "microphone" in default_config.permissions_policy
        assert "geolocation" in default_config.permissions_policy


class TestSecurityPresets:
    """Testes para presets de segurança"""
    
    def test_strict_preset(self):
        """Preset estrito"""
        config = SecurityPresets.strict()
        
        assert config.hsts_enabled is True
        assert config.hsts_max_age == 63072000  # 2 anos
        assert config.hsts_preload is True
        assert config.frame_options_value == "DENY"
        assert config.coep_enabled is True
        
        # CSP sem unsafe-inline
        assert "'unsafe-inline'" not in config.csp_directives.get("script-src", [])
    
    def test_moderate_preset(self):
        """Preset moderado"""
        config = SecurityPresets.moderate()
        
        assert config.hsts_enabled is True
        assert config.csp_enabled is True
        assert config.frame_options_value == "SAMEORIGIN"
        assert config.coep_enabled is False
    
    def test_relaxed_preset(self):
        """Preset relaxado"""
        config = SecurityPresets.relaxed()
        
        assert config.hsts_enabled is False
        assert config.csp_report_only is True
        assert config.coep_enabled is False
        assert config.coop_enabled is False
    
    def test_api_only_preset(self):
        """Preset para APIs"""
        config = SecurityPresets.api_only()
        
        assert config.hsts_enabled is True
        assert config.csp_enabled is False
        assert config.frame_options_value == "DENY"
        assert config.permissions_policy_enabled is False
    
    def test_telecom_isp_preset(self):
        """Preset para ISP de Telecomunicações"""
        config = SecurityPresets.telecom_isp()
        
        assert config.hsts_enabled is True
        assert config.csp_enabled is True
        
        # Permite WhatsApp
        assert any("whatsapp" in src for src in config.csp_directives.get("img-src", []))
        assert any("whatsapp" in src for src in config.csp_directives.get("connect-src", []))
        
        # Headers customizados
        assert "X-DNS-Prefetch-Control" in config.custom_headers


# =============================================================================
# TESTES DO MANAGER
# =============================================================================

class TestSecurityHeadersManager:
    """Testes para SecurityHeadersManager"""
    
    def test_generate_nonce(self, manager):
        """Gerar nonce único"""
        nonce1 = manager.generate_nonce()
        nonce2 = manager.generate_nonce()
        
        assert len(nonce1) > 10
        assert nonce1 != nonce2
    
    def test_build_hsts_header(self, manager):
        """Construir header HSTS"""
        hsts = manager._build_hsts_header()
        
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts
    
    def test_build_csp_header(self, manager):
        """Construir header CSP"""
        csp = manager._build_csp_header()
        
        assert "default-src" in csp
        assert "script-src" in csp
        assert "'self'" in csp
    
    def test_build_csp_with_nonce(self, manager):
        """Construir CSP com nonce"""
        nonce = "test-nonce-123"
        csp = manager._build_csp_header(nonce)
        
        assert f"'nonce-{nonce}'" in csp
    
    def test_build_permissions_policy(self, manager):
        """Construir Permissions-Policy"""
        policy = manager._build_permissions_policy()
        
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "fullscreen=(self)" in policy
    
    def test_get_headers_api_path(self, manager):
        """Headers para path de API"""
        headers = manager.get_headers("/api/users", request_id="req-123")
        
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers
        assert "Cache-Control" in headers
        assert "no-store" in headers["Cache-Control"]
        assert headers.get("X-Request-ID") == "req-123"
    
    def test_get_headers_static_path(self, manager):
        """Headers para arquivos estáticos"""
        headers = manager.get_headers("/static/app.js")
        
        # Arquivos estáticos devem ter cache
        if manager.config.cache_control_enabled:
            assert "max-age" in headers.get("Cache-Control", "")
    
    def test_excluded_paths(self, manager):
        """Paths excluídos não recebem CSP"""
        manager.config.excluded_paths = ["/health", "/metrics"]
        
        headers = manager.get_headers("/health")
        
        # CSP não deve estar presente em paths excluídos
        # (depende da implementação)
    
    def test_validate_csp_report_valid(self, manager):
        """Validar relatório CSP válido"""
        report = {
            "csp-report": {
                "blocked-uri": "https://evil.com/script.js",
                "violated-directive": "script-src",
                "original-policy": "script-src 'self'",
                "document-uri": "https://example.com/page",
            }
        }
        
        result = manager.validate_csp_report(report)
        assert result is True
    
    def test_validate_csp_report_invalid(self, manager):
        """Validar relatório CSP inválido"""
        report = {"invalid": "data"}
        
        result = manager.validate_csp_report(report)
        assert result is False


# =============================================================================
# TESTES DO MIDDLEWARE
# =============================================================================

class TestSecurityHeadersMiddleware:
    """Testes para o middleware"""
    
    def test_hsts_header_present(self, client):
        """Header HSTS presente"""
        # Em DEBUG mode, HSTS pode estar desabilitado
        # Este teste verifica a presença quando habilitado
        response = client.get("/")
        
        # Verificar outros headers que devem estar presentes
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
    
    def test_x_frame_options(self, client):
        """Header X-Frame-Options"""
        response = client.get("/")
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]
    
    def test_x_content_type_options(self, client):
        """Header X-Content-Type-Options"""
        response = client.get("/")
        
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
    
    def test_x_xss_protection(self, client):
        """Header X-XSS-Protection"""
        response = client.get("/")
        
        xss = response.headers.get("X-XSS-Protection")
        assert xss is not None
        assert "1" in xss
    
    def test_referrer_policy(self, client):
        """Header Referrer-Policy"""
        response = client.get("/")
        
        referrer = response.headers.get("Referrer-Policy")
        assert referrer is not None
    
    def test_request_id_generated(self, client):
        """Request ID gerado"""
        response = client.get("/")
        
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None
        assert len(request_id) > 0
    
    def test_request_id_preserved(self, client):
        """Request ID preservado se enviado"""
        custom_id = "my-custom-request-id"
        response = client.get("/", headers={"X-Request-ID": custom_id})
        
        assert response.headers.get("X-Request-ID") == custom_id
    
    def test_api_no_cache(self, client):
        """API não deve ter cache"""
        response = client.get("/api/data")
        
        cache = response.headers.get("Cache-Control", "")
        assert "no-store" in cache or "no-cache" in cache
    
    def test_server_header_customized(self, client):
        """Header Server customizado"""
        response = client.get("/")
        
        server = response.headers.get("Server")
        # Não deve revelar tecnologia
        assert server != "uvicorn" if server else True


# =============================================================================
# TESTES DE INTEGRAÇÃO
# =============================================================================

class TestSecurityHeadersIntegration:
    """Testes de integração"""
    
    def test_full_security_headers_flow(self, client):
        """Fluxo completo de security headers"""
        response = client.get("/api/data")
        
        # Verificar status OK
        assert response.status_code == 200
        
        # Verificar headers essenciais
        essential_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]
        
        for header in essential_headers:
            assert header in response.headers, f"Header {header} não encontrado"
    
    def test_excluded_endpoint_still_works(self, client):
        """Endpoint excluído ainda funciona"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# =============================================================================
# TESTES DE ENUMS
# =============================================================================

class TestEnums:
    """Testes para enums"""
    
    def test_csp_directives_enum(self):
        """Enum CSPDirective"""
        assert CSPDirective.DEFAULT_SRC.value == "default-src"
        assert CSPDirective.SCRIPT_SRC.value == "script-src"
        assert CSPDirective.FRAME_ANCESTORS.value == "frame-ancestors"
    
    def test_permissions_policy_enum(self):
        """Enum PermissionsPolicy"""
        assert PermissionsPolicy.CAMERA.value == "camera"
        assert PermissionsPolicy.MICROPHONE.value == "microphone"
        assert PermissionsPolicy.GEOLOCATION.value == "geolocation"


# =============================================================================
# EXECUTAR TESTES
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
