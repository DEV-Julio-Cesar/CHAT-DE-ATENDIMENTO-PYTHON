#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Chat Enterprise - Início Rápido
Sistema completo funcionando sem banco de dados (dados em memória)
"""

import asyncio
import subprocess
import sys
import time
import threading
from datetime import datetime, timedelta
import json
import uuid

# Dados em memória para demonstração
USERS_DB = {
    "admin": {
        "id": "1",
        "username": "admin",
        "password": "admin123",  # Em produção seria hash
        "email": "admin@ispchatsystem.com",
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }
}

CONVERSATIONS_DB = {
    "1": {
        "id": "1",
        "customer_phone": "5511999999999",
        "customer_name": "Cliente Teste",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "messages": [
            {
                "id": "1",
                "content": "Olá, preciso de ajuda com meu plano de internet",
                "sender": "customer",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "2", 
                "content": "Olá! Como posso ajudá-lo hoje?",
                "sender": "agent",
                "timestamp": (datetime.now() + timedelta(minutes=1)).isoformat()
            }
        ]
    },
    "2": {
        "id": "2",
        "customer_phone": "5511888888888",
        "customer_name": "Maria Silva",
        "status": "waiting",
        "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "messages": [
            {
                "id": "3",
                "content": "Minha internet está lenta",
                "sender": "customer", 
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat()
            }
        ]
    }
}

def create_auth_server():
    """Criar servidor de autenticação simples"""
    return '''
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime, timedelta
import jwt

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dados em memória
USERS = {
    "admin": {
        "id": "1",
        "username": "admin", 
        "password": "admin123",
        "email": "admin@ispchatsystem.com",
        "role": "admin"
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    user = USERS.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    # Criar token simples (em produção usar JWT real)
    token = f"token_{user['id']}_{datetime.now().timestamp()}"
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/verify")
async def verify():
    return {"valid": True}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
'''

def create_chat_server():
    """Criar servidor de chat simples"""
    return '''
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime
from typing import List, Optional

app = FastAPI(title="Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dados em memória
CONVERSATIONS = {
    "1": {
        "id": "1",
        "customer_phone": "5511999999999",
        "customer_name": "Cliente Teste",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "agent_id": "1"
    },
    "2": {
        "id": "2", 
        "customer_phone": "5511888888888",
        "customer_name": "Maria Silva",
        "status": "waiting",
        "created_at": datetime.now().isoformat(),
        "agent_id": None
    }
}

MESSAGES = {
    "1": [
        {"id": "1", "content": "Olá, preciso de ajuda", "sender": "customer", "timestamp": datetime.now().isoformat()},
        {"id": "2", "content": "Como posso ajudar?", "sender": "agent", "timestamp": datetime.now().isoformat()}
    ],
    "2": [
        {"id": "3", "content": "Internet lenta", "sender": "customer", "timestamp": datetime.now().isoformat()}
    ]
}

@app.get("/api/chat/conversations")
async def get_conversations():
    return {
        "conversations": list(CONVERSATIONS.values()),
        "total": len(CONVERSATIONS)
    }

@app.get("/api/chat/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    messages = MESSAGES.get(conversation_id, [])
    return {
        "messages": messages,
        "total": len(messages)
    }

class MessageCreate(BaseModel):
    content: str
    sender: str = "agent"

@app.post("/api/chat/conversations/{conversation_id}/messages")
async def create_message(conversation_id: str, message: MessageCreate):
    if conversation_id not in MESSAGES:
        MESSAGES[conversation_id] = []
    
    new_message = {
        "id": str(len(MESSAGES[conversation_id]) + 1),
        "content": message.content,
        "sender": message.sender,
        "timestamp": datetime.now().isoformat()
    }
    
    MESSAGES[conversation_id].append(new_message)
    return new_message

@app.get("/api/chat/stats")
async def get_stats():
    return {
        "total_conversations": len(CONVERSATIONS),
        "active_conversations": len([c for c in CONVERSATIONS.values() if c["status"] == "active"]),
        "waiting_conversations": len([c for c in CONVERSATIONS.values() if c["status"] == "waiting"]),
        "total_messages": sum(len(msgs) for msgs in MESSAGES.values())
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chat"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
'''

def create_gateway_server():
    """Criar API Gateway simples"""
    return '''
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
from fastapi.responses import JSONResponse

app = FastAPI(title="API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(request: Request, path: str):
    # Determinar serviço baseado no path
    if path.startswith("auth/"):
        target_url = f"http://localhost:8001/api/{path}"
    elif path.startswith("chat/"):
        target_url = f"http://localhost:8002/api/{path}"
    else:
        return JSONResponse({"error": "Service not found"}, status_code=404)
    
    # Fazer proxy da requisição
    async with httpx.AsyncClient() as client:
        try:
            # Obter dados da requisição
            body = await request.body()
            headers = dict(request.headers)
            
            # Fazer requisição para o serviço
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                params=request.query_params
            )
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
            
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

def start_service(name, code, port):
    """Iniciar um serviço"""
    print(f"🔄 Iniciando {name} na porta {port}...")
    
    # Salvar código do serviço
    filename = f"{name.replace('-', '_')}_server.py"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    
    # Iniciar serviço em thread separada
    def run_service():
        try:
            subprocess.run([sys.executable, filename], check=True)
        except Exception as e:
            print(f"❌ Erro no {name}: {e}")
    
    thread = threading.Thread(target=run_service, daemon=True)
    thread.start()
    
    return thread

def main():
    """Função principal"""
    print("🚀 ISP Chat Enterprise - Início Rápido")
    print("=" * 50)
    print("Iniciando sistema completo com dados em memória...")
    print()
    
    # Instalar httpx se necessário
    try:
        import httpx
    except ImportError:
        print("📦 Instalando httpx...")
        subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], check=True)
    
    # Criar e iniciar serviços
    auth_code = create_auth_server()
    chat_code = create_chat_server() 
    gateway_code = create_gateway_server()
    
    # Iniciar serviços
    auth_thread = start_service("auth-service", auth_code, 8001)
    time.sleep(2)
    
    chat_thread = start_service("chat-service", chat_code, 8002)
    time.sleep(2)
    
    gateway_thread = start_service("api-gateway", gateway_code, 8000)
    time.sleep(2)
    
    # Iniciar servidor web
    print("🌐 Iniciando interface web na porta 3000...")
    web_process = subprocess.Popen([sys.executable, "web-server.py"])
    
    print()
    print("✅ Sistema iniciado com sucesso!")
    print()
    print("🌐 URLs disponíveis:")
    print("  • Interface Web: http://localhost:3000")
    print("  • API Gateway: http://localhost:8000")
    print("  • Auth Service: http://localhost:8001")
    print("  • Chat Service: http://localhost:8002")
    print()
    print("🔐 Credenciais:")
    print("  • Usuário: admin")
    print("  • Senha: admin123")
    print()
    print("Pressione Ctrl+C para parar todos os serviços...")
    
    try:
        # Manter rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\\n🛑 Parando serviços...")
        web_process.terminate()
        print("✅ Serviços parados!")

if __name__ == "__main__":
    main()