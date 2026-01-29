"""
Testes da aplicação principal
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

# Cliente de teste síncrono
client = TestClient(app)


class TestMainApp:
    """Testes da aplicação principal"""
    
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
    
    def test_404_handling(self):
        """Testar tratamento de 404"""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404