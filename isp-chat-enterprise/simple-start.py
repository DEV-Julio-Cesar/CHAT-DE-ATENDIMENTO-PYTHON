#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Chat Enterprise - Inicialização Simples
Versão simplificada para teste sem banco de dados
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

def start_simple_service():
    """Iniciar serviço simples de teste"""
    print("🚀 ISP Chat Enterprise - Inicialização Simples")
    print("=" * 50)
    
    # Criar um servidor FastAPI simples
    simple_server_code = '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
from datetime import datetime

app = FastAPI(
    title="ISP Chat Enterprise - Demo",
    description="Sistema de chat enterprise funcionando!",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🎉 ISP Chat Enterprise funcionando!",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "auth": "http://localhost:8001",
            "chat": "http://localhost:8002", 
            "gateway": "http://localhost:8000",
            "web": "http://localhost:3000"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "isp-chat-enterprise",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/demo", response_class=HTMLResponse)
async def demo():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ISP Chat Enterprise - Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
            .status { background: #27ae60; color: white; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0; }
            .feature { background: #ecf0f1; padding: 20px; border-radius: 5px; text-align: center; }
            .feature h3 { color: #34495e; margin-top: 0; }
            .links { text-align: center; margin-top: 30px; }
            .links a { display: inline-block; margin: 10px; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }
            .links a:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 ISP Chat Enterprise</h1>
                <p>Sistema Profissional de Chat de Atendimento</p>
            </div>
            
            <div class="status">
                ✅ Sistema Online e Funcionando!
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>🔐 Autenticação</h3>
                    <p>JWT seguro com refresh tokens</p>
                </div>
                <div class="feature">
                    <h3>💬 Chat em Tempo Real</h3>
                    <p>WebSocket para comunicação instantânea</p>
                </div>
                <div class="feature">
                    <h3>📊 Métricas</h3>
                    <p>Monitoramento completo com dashboards</p>
                </div>
                <div class="feature">
                    <h3>🏗️ Microserviços</h3>
                    <p>Arquitetura escalável e robusta</p>
                </div>
            </div>
            
            <div class="links">
                <a href="/docs">📚 Documentação API</a>
                <a href="/health">🏥 Health Check</a>
                <a href="/">🔄 API Status</a>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #7f8c8d;">
                <p>Desenvolvido com ❤️ para ISPs e Telecoms</p>
                <p>Versão Enterprise 1.0.0</p>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
'''
    
    # Salvar o código do servidor
    server_file = Path("simple_server.py")
    with open(server_file, "w", encoding="utf-8") as f:
        f.write(simple_server_code)
    
    print("✅ Servidor simples criado")
    print("🔄 Iniciando servidor na porta 8000...")
    
    try:
        # Iniciar o servidor
        subprocess.run([sys.executable, "simple_server.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Servidor parado pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
    finally:
        # Limpar arquivo temporário
        if server_file.exists():
            server_file.unlink()

if __name__ == "__main__":
    start_simple_service()