#!/usr/bin/env python3
"""
Executar aplicação localmente para desenvolvimento
"""
import uvicorn
import os
from pathlib import Path

# Configurar variáveis de ambiente para desenvolvimento local
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./isp_support.db")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-change-in-production")
os.environ.setdefault("DEBUG", "true")

if __name__ == "__main__":
    print("🚀 Iniciando ISP Customer Support em modo desenvolvimento")
    print("📍 API será executada em: http://localhost:8000")
    print("📚 Documentação em: http://localhost:8000/docs")
    print("⚠️  Modo desenvolvimento - usando versão simplificada")
    print()
    
    # Verificar se o diretório app existe
    if not Path("app").exists():
        print("❌ Diretório 'app' não encontrado!")
        print("Execute este script na raiz do projeto.")
        exit(1)
    
    try:
        uvicorn.run(
            "app.main_simple:app",  # Usar versão simplificada
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("📦 Instale as dependências com: pip install -r requirements-dev.txt")
    except Exception as e:
        print(f"❌ Erro ao iniciar: {e}")