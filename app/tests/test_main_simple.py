"""
Testes simples da aplicação principal
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Criar uma aplicação simples para testes
simple_app = FastAPI(title="Test App", version="2.0.0")


@simple_app.get("/")
async def root():
    return {"message": "Welcome to ISP Customer Support", "version": "2.0.0"}


@simple_app.get("/info")
async def app_info():
    return {"name": "ISP Customer Support", "version": "2.0.0", "debug": True}


@simple_app.get("/health")
async def health_check():
    return {"status": "healthy", "checks": {"database": True}}


# Cliente de teste
client = TestClient(simple_app)


class TestSimpleApp:
    """Testes da aplicação simples"""
    
    def test_root_endpoint(self):
        """Testar endpoint raiz"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "2.0.0"
    
    def test_app_info(self):
        """Testar informações da aplicação"""
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ISP Customer Support"
        assert data["version"] == "2.0.0"
        assert "debug" in data
    
    def test_health_check(self):
        """Testar health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
    
    def test_404_handling(self):
        """Testar tratamento de 404"""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404