"""
Sistema de Chat WhatsApp Completo
Versão integrada com tudo funcionando
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import structlog
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# SISTEMA DE CHAT WHATSAPP INTEGRADO
# ============================================================================

class ConversationStatus(str, Enum):
    """Status das conversas no fluxo"""
    ESPERA = "waiting"        # Aguardando atribuição
    ATRIBUIDO = "assigned"    # Atribuído a um atendente
    AUTOMACAO = "automation"  # Em automação (bot)
    ENCERRADO = "closed"      # Conversa encerrada

class MessageType(str, Enum):
    """Tipos de mensagem"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"

class SenderType(str, Enum):
    """Tipos de remetente"""
    CUSTOMER = "customer"
    AGENT = "agent"
    BOT = "bot"
    SYSTEM = "system"

# Estruturas de dados
conversations_db = {}
messages_db = {}
stats_db = {
    "total_conversations": 0,
    "by_status": {status.value: 0 for status in ConversationStatus},
    "messages_today": 0,
    "requests_total": 0,
    "cache_hits": 0
}

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="ISP Customer Support - Chat WhatsApp",
    version="2.0.0",
    description="Sistema completo de chat WhatsApp com 3 etapas",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar templates e arquivos estáticos
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Middleware para métricas
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    stats_db["requests_total"] += 1
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    response.headers["X-Process-Time"] = str(duration)
    
    return response

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class MessageRequest(BaseModel):
    content: str
    message_type: str = "text"

class ConversationCreateRequest(BaseModel):
    customer_name: str
    customer_phone: str
    initial_message: Optional[str] = None

class AssignRequest(BaseModel):
    agent_id: Optional[str] = "agent_1"

class CloseRequest(BaseModel):
    reason: Optional[str] = "Resolvido"

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def create_conversation_id():
    return f"conv_{len(conversations_db) + 1}_{int(datetime.now().timestamp())}"

def create_message_id(conversation_id):
    return f"msg_{len(messages_db.get(conversation_id, []))}_{int(datetime.now().timestamp())}"

async def add_message(conversation_id: str, sender_type: str, sender_id: str, content: str):
    """Adicionar mensagem à conversa"""
    if conversation_id not in messages_db:
        messages_db[conversation_id] = []
    
    message = {
        "id": create_message_id(conversation_id),
        "conversation_id": conversation_id,
        "sender_type": sender_type,
        "sender_id": sender_id,
        "content": content,
        "message_type": "text",
        "created_at": datetime.now().isoformat(),
        "metadata": {}
    }
    
    messages_db[conversation_id].append(message)
    
    # Atualizar conversa
    if conversation_id in conversations_db:
        conversations_db[conversation_id]["last_message"] = content[:100]
        conversations_db[conversation_id]["messages_count"] = len(messages_db[conversation_id])
        conversations_db[conversation_id]["updated_at"] = datetime.now().isoformat()
    
    stats_db["messages_today"] += 1
    return message

def create_sample_conversations():
    """Criar conversas de exemplo"""
    # Conversa 1: Em espera
    conv1_id = create_conversation_id()
    conversations_db[conv1_id] = {
        "id": conv1_id,
        "customer_name": "João Silva",
        "customer_phone": "+5511999887766",
        "status": ConversationStatus.ESPERA.value,
        "assigned_agent_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_message": "Olá, estou com problemas na minha internet",
        "messages_count": 1,
        "priority": 0,
        "tags": []
    }
    messages_db[conv1_id] = [{
        "id": create_message_id(conv1_id),
        "conversation_id": conv1_id,
        "sender_type": "customer",
        "sender_id": "+5511999887766",
        "content": "Olá, estou com problemas na minha internet",
        "message_type": "text",
        "created_at": datetime.now().isoformat(),
        "metadata": {}
    }]
    
    # Conversa 2: Atribuída
    conv2_id = create_conversation_id()
    conversations_db[conv2_id] = {
        "id": conv2_id,
        "customer_name": "Maria Santos",
        "customer_phone": "+5511888776655",
        "status": ConversationStatus.ATRIBUIDO.value,
        "assigned_agent_id": "agent_1",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_message": "Preciso de ajuda com minha fatura",
        "messages_count": 2,
        "priority": 0,
        "tags": []
    }
    messages_db[conv2_id] = [
        {
            "id": create_message_id(conv2_id),
            "conversation_id": conv2_id,
            "sender_type": "customer",
            "sender_id": "+5511888776655",
            "content": "Preciso de ajuda com minha fatura",
            "message_type": "text",
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        },
        {
            "id": create_message_id(conv2_id),
            "conversation_id": conv2_id,
            "sender_type": "agent",
            "sender_id": "agent_1",
            "content": "Olá Maria! Vou verificar sua fatura. Pode me informar seu CPF?",
            "message_type": "text",
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        }
    ]
    
    # Conversa 3: Em automação
    conv3_id = create_conversation_id()
    conversations_db[conv3_id] = {
        "id": conv3_id,
        "customer_name": "Pedro Costa",
        "customer_phone": "+5511777665544",
        "status": ConversationStatus.AUTOMACAO.value,
        "assigned_agent_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_message": "Boa tarde, como posso contratar um plano?",
        "messages_count": 2,
        "priority": 0,
        "tags": []
    }
    messages_db[conv3_id] = [
        {
            "id": create_message_id(conv3_id),
            "conversation_id": conv3_id,
            "sender_type": "customer",
            "sender_id": "+5511777665544",
            "content": "Boa tarde, como posso contratar um plano?",
            "message_type": "text",
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        },
        {
            "id": create_message_id(conv3_id),
            "conversation_id": conv3_id,
            "sender_type": "bot",
            "sender_id": "bot",
            "content": "Olá! Sou o assistente virtual da ISP. Temos vários planos disponíveis. Qual velocidade você precisa?",
            "message_type": "text",
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        }
    ]
    
    # Atualizar estatísticas
    stats_db["total_conversations"] = 3
    stats_db["by_status"][ConversationStatus.ESPERA.value] = 1
    stats_db["by_status"][ConversationStatus.ATRIBUIDO.value] = 1
    stats_db["by_status"][ConversationStatus.AUTOMACAO.value] = 1
    stats_db["messages_today"] = 5
    
    logger.info("✅ Conversas de exemplo criadas com sucesso!")

# ============================================================================
# ENDPOINTS WEB
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Página inicial"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ISP Customer Support</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0; padding: 20px; background: #f5f5f5; color: #333;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px;
                text-align: center;
            }
            .chat-link {
                background: #48bb78; font-size: 1.2em; padding: 15px 30px;
                margin: 20px 10px; display: inline-block; color: white;
                text-decoration: none; border-radius: 8px;
            }
            .chat-link:hover { background: #38a169; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 ISP Customer Support</h1>
                <p>Sistema de Chat WhatsApp com 3 Etapas</p>
                <div style="margin-top: 20px;">
                    <a href="/chat" class="chat-link">💬 Acessar Chat WhatsApp</a>
                    <a href="/docs" class="chat-link">📚 API Docs</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/test", response_class=HTMLResponse)
async def test_interface():
    """Interface de teste simples"""
    with open("test_chat.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Interface de chat"""
    return templates.TemplateResponse("chat.html", {"request": request})

# ============================================================================
# ENDPOINTS API
# ============================================================================

@app.get("/api/conversations")
async def get_conversations():
    """Listar conversas"""
    conversations = list(conversations_db.values())
    conversations.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return {
        "success": True,
        "data": conversations,
        "total": len(conversations),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Obter conversa específica"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    return {
        "success": True,
        "data": conversations_db[conversation_id]
    }

@app.post("/api/conversations")
async def create_conversation(request: ConversationCreateRequest):
    """Criar nova conversa"""
    conv_id = create_conversation_id()
    
    conversation = {
        "id": conv_id,
        "customer_name": request.customer_name,
        "customer_phone": request.customer_phone,
        "status": ConversationStatus.ESPERA.value,
        "assigned_agent_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_message": request.initial_message or "",
        "messages_count": 0,
        "priority": 0,
        "tags": []
    }
    
    conversations_db[conv_id] = conversation
    messages_db[conv_id] = []
    
    # Adicionar mensagem inicial se fornecida
    if request.initial_message:
        await add_message(conv_id, "customer", request.customer_phone, request.initial_message)
    
    # Atualizar estatísticas
    stats_db["total_conversations"] += 1
    stats_db["by_status"][ConversationStatus.ESPERA.value] += 1
    
    return {
        "success": True,
        "data": conversation,
        "message": "Conversa criada com sucesso"
    }

@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    """Obter mensagens de uma conversa"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    messages = messages_db.get(conversation_id, [])
    
    return {
        "success": True,
        "messages": messages,
        "total": len(messages),
        "conversation_id": conversation_id
    }

@app.post("/api/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: MessageRequest):
    """Enviar mensagem"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    conversation = conversations_db[conversation_id]
    
    # Determinar remetente baseado no status
    if conversation["status"] == ConversationStatus.AUTOMACAO.value:
        sender_type = "bot"
        sender_id = "bot"
    else:
        sender_type = "agent"
        sender_id = conversation["assigned_agent_id"] or "agent_1"
    
    message = await add_message(conversation_id, sender_type, sender_id, request.content)
    
    return {
        "success": True,
        "data": message,
        "message": "Mensagem enviada com sucesso"
    }

@app.post("/api/conversations/{conversation_id}/assign")
async def assign_conversation(conversation_id: str, request: AssignRequest = AssignRequest()):
    """Atribuir conversa (ESPERA → ATRIBUÍDO)"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    conversation = conversations_db[conversation_id]
    
    if conversation["status"] != ConversationStatus.ESPERA.value:
        raise HTTPException(status_code=400, detail="Conversa não está em espera")
    
    # Atualizar status
    old_status = conversation["status"]
    conversation["status"] = ConversationStatus.ATRIBUIDO.value
    conversation["assigned_agent_id"] = request.agent_id
    conversation["updated_at"] = datetime.now().isoformat()
    
    # Atualizar estatísticas
    stats_db["by_status"][old_status] -= 1
    stats_db["by_status"][ConversationStatus.ATRIBUIDO.value] += 1
    
    # Adicionar mensagem do sistema
    await add_message(conversation_id, "system", "system", f"Conversa atribuída ao agente {request.agent_id}")
    
    return {
        "success": True,
        "message": f"Conversa atribuída ao agente {request.agent_id}",
        "status_change": "waiting → assigned"
    }

@app.post("/api/conversations/{conversation_id}/automate")
async def start_automation(conversation_id: str):
    """Iniciar automação (ATRIBUÍDO → AUTOMAÇÃO)"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    conversation = conversations_db[conversation_id]
    
    if conversation["status"] != ConversationStatus.ATRIBUIDO.value:
        raise HTTPException(status_code=400, detail="Conversa não está atribuída")
    
    # Atualizar status
    old_status = conversation["status"]
    conversation["status"] = ConversationStatus.AUTOMACAO.value
    conversation["updated_at"] = datetime.now().isoformat()
    
    # Atualizar estatísticas
    stats_db["by_status"][old_status] -= 1
    stats_db["by_status"][ConversationStatus.AUTOMACAO.value] += 1
    
    # Adicionar mensagens
    await add_message(conversation_id, "system", "system", "Automação iniciada - Bot assumiu a conversa")
    await add_message(conversation_id, "bot", "bot", "Olá! Sou o assistente virtual da ISP. Como posso ajudá-lo hoje?")
    
    return {
        "success": True,
        "message": "Automação iniciada com sucesso",
        "status_change": "assigned → automation"
    }

@app.post("/api/conversations/{conversation_id}/takeover")
async def takeover_conversation(conversation_id: str, request: AssignRequest = AssignRequest()):
    """Assumir conversa (AUTOMAÇÃO → ATRIBUÍDO)"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    conversation = conversations_db[conversation_id]
    
    if conversation["status"] != ConversationStatus.AUTOMACAO.value:
        raise HTTPException(status_code=400, detail="Conversa não está em automação")
    
    # Atualizar status
    old_status = conversation["status"]
    conversation["status"] = ConversationStatus.ATRIBUIDO.value
    conversation["assigned_agent_id"] = request.agent_id
    conversation["updated_at"] = datetime.now().isoformat()
    
    # Atualizar estatísticas
    stats_db["by_status"][old_status] -= 1
    stats_db["by_status"][ConversationStatus.ATRIBUIDO.value] += 1
    
    # Adicionar mensagem do sistema
    await add_message(conversation_id, "system", "system", f"Agente {request.agent_id} assumiu a conversa")
    
    return {
        "success": True,
        "message": f"Conversa assumida pelo agente {request.agent_id}",
        "status_change": "automation → assigned"
    }

@app.post("/api/conversations/{conversation_id}/close")
async def close_conversation(conversation_id: str, request: CloseRequest = CloseRequest()):
    """Encerrar conversa"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    conversation = conversations_db[conversation_id]
    old_status = conversation["status"]
    
    # Atualizar status
    conversation["status"] = ConversationStatus.ENCERRADO.value
    conversation["updated_at"] = datetime.now().isoformat()
    
    # Atualizar estatísticas
    stats_db["by_status"][old_status] -= 1
    stats_db["by_status"][ConversationStatus.ENCERRADO.value] += 1
    
    # Adicionar mensagem do sistema
    await add_message(conversation_id, "system", "system", f"Conversa encerrada: {request.reason}")
    
    return {
        "success": True,
        "message": f"Conversa encerrada: {request.reason}",
        "status_change": f"{old_status} → closed"
    }

@app.get("/api/chat/stats")
async def get_chat_stats():
    """Estatísticas do chat"""
    active_conversations = len([c for c in conversations_db.values() if c["status"] != ConversationStatus.ENCERRADO.value])
    
    return {
        "success": True,
        "data": {
            **stats_db,
            "active_conversations": active_conversations,
            "agents_online": 2,
            "automation_rules": 4
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/conversations/{conversation_id}/simulate-customer-message")
async def simulate_customer_message(conversation_id: str, request: MessageRequest):
    """Simular mensagem de cliente"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    conversation = conversations_db[conversation_id]
    message = await add_message(conversation_id, "customer", conversation["customer_phone"], request.content)
    
    return {
        "success": True,
        "data": message,
        "message": "Mensagem de cliente simulada"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "conversations": len(conversations_db),
        "messages": sum(len(msgs) for msgs in messages_db.values())
    }

@app.post("/api/init-sample-data")
async def init_sample_data():
    """Inicializar dados de exemplo"""
    create_sample_conversations()
    return {
        "success": True,
        "message": "Dados de exemplo criados com sucesso",
        "conversations": len(conversations_db),
        "messages": sum(len(msgs) for msgs in messages_db.values())
    }

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

# Criar conversas de exemplo na inicialização
create_sample_conversations()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando ISP Customer Support - Chat WhatsApp")
    print("💬 Interface: http://localhost:8001/chat")
    print("📚 API Docs: http://localhost:8001/docs")
    
    uvicorn.run(
        "main_chat_complete:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Desabilitar reload para manter dados
        log_level="info"
    )