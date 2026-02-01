#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat Service - Microserviço de Chat e Atendimento
API FastAPI para gerenciamento de conversas, mensagens e filas
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

# Imports locais
from shared.config.settings import settings
from shared.utils.database import get_db, init_db, close_db, get_database_info
from shared.utils.memory_cache import memory_cache
from shared.middleware.auth import (
    get_current_user, RequireAgentOrAbove, RequireSupervisorOrAdmin,
    CurrentUser
)
from shared.models.user import User

from .services import (
    chat_service, ChatServiceError, ConversationNotFoundError, 
    QueueNotFoundError, AgentNotAvailableError
)
from .models import (
    ConversationCreate, ConversationUpdate, MessageCreate,
    ConversationResponse, MessageResponse,
    ConversationListResponse, MessageListResponse, ChatStats,
    ConversationStatus, MessageType, QueuePriority
)
from .websocket_manager import websocket_manager

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gerenciamento do ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando Chat Service...")
    
    try:
        # Inicializar banco de dados
        await init_db()
        logger.info("✅ Banco de dados inicializado")
        
        # Inicializar cache
        await memory_cache.connect()
        logger.info("✅ Cache inicializado")
        
        # Inicializar WebSocket manager
        await websocket_manager.start()
        logger.info("✅ WebSocket manager iniciado")
        
        # Obter informações do banco
        db_info = await get_database_info()
        if db_info:
            logger.info(f"📊 Banco: {db_info.get('database')} ({db_info.get('size_mb', 0)} MB)")
        
        logger.info("🎉 Chat Service iniciado com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Finalizando Chat Service...")
    
    try:
        await websocket_manager.stop()
        await memory_cache.disconnect()
        await close_db()
        logger.info("✅ Chat Service finalizado")
    except Exception as e:
        logger.error(f"❌ Erro na finalização: {e}")

# Criar aplicação FastAPI
app = FastAPI(
    title="ISP Chat - Chat Service",
    description="""
    💬 **Microserviço de Chat e Atendimento**
    
    Responsável por:
    - Gerenciamento de conversas e mensagens
    - Filas de atendimento inteligentes
    - WebSocket para chat em tempo real
    - Integração com WhatsApp Business API
    - Métricas e relatórios de atendimento
    - Sistema de transferência entre agentes
    
    **Funcionalidades Enterprise:**
    - Chat em tempo real via WebSocket
    - Distribuição automática de conversas
    - Métricas de performance (SLA, tempo resposta)
    - Histórico completo de conversas
    - Suporte a múltiplos canais (WhatsApp, Web)
    
    **Compatível com migração do sistema Node.js**
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    **settings.get_cors_config()
)

# === MIDDLEWARE DE LOGGING ===

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para log de requests"""
    start_time = datetime.utcnow()
    
    # Processar request
    response = await call_next(request)
    
    # Calcular tempo de processamento
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Log da request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s - "
        f"IP: {request.client.host}"
    )
    
    # Adicionar header com tempo de processamento
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# === HANDLERS DE ERRO ===

@app.exception_handler(ChatServiceError)
async def chat_service_error_handler(request: Request, exc: ChatServiceError):
    """Handler para erros do chat service"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "chat_service_error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(ConversationNotFoundError)
async def conversation_not_found_error_handler(request: Request, exc: ConversationNotFoundError):
    """Handler para conversa não encontrada"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "conversation_not_found",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(AgentNotAvailableError)
async def agent_not_available_error_handler(request: Request, exc: AgentNotAvailableError):
    """Handler para agente não disponível"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "agent_not_available",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Dados de entrada inválidos",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# === ENDPOINTS PÚBLICOS ===

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz com informações do serviço"""
    return {
        "service": "ISP Chat - Chat Service",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "features": [
            "Conversas em tempo real",
            "Filas de atendimento",
            "WebSocket support",
            "WhatsApp integration",
            "Métricas e relatórios"
        ],
        "endpoints": {
            "conversations": "GET/POST /conversations",
            "messages": "GET/POST /conversations/{id}/messages",
            "websocket": "WS /ws/{conversation_id}",
            "stats": "GET /stats"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check detalhado"""
    try:
        # Verificar banco de dados
        db_info = await get_database_info()
        db_healthy = bool(db_info)
        
        # Verificar cache
        cache_healthy = await memory_cache.ping() == "PONG"
        
        # Verificar WebSocket manager
        ws_healthy = websocket_manager.is_running
        
        # Status geral
        overall_healthy = db_healthy and cache_healthy and ws_healthy
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "service": "chat-service",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "info": db_info
                },
                "cache": {
                    "status": "healthy" if cache_healthy else "unhealthy",
                    "type": "memory"
                },
                "websocket": {
                    "status": "healthy" if ws_healthy else "unhealthy",
                    "active_connections": len(websocket_manager.active_connections)
                }
            },
            "uptime": "running"
        }
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "chat-service",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# === ENDPOINTS DE CONVERSAS ===

@app.get("/test", tags=["Test"])
async def test_endpoint():
    """Endpoint de teste sem autenticação"""
    return {
        "message": "Chat Service funcionando!",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints_available": [
            "GET /conversations (requer auth)",
            "POST /conversations (requer auth)", 
            "WS /ws/{conversation_id}",
            "GET /stats (requer auth)"
        ]
    }

@app.post("/test/conversation", tags=["Test"])
async def create_test_conversation(
    customer_phone: str = "5511999999999",
    customer_name: str = "Cliente Teste",
    initial_message: str = "Olá, preciso de ajuda!",
    db: AsyncSession = Depends(get_db)
):
    """Criar conversa de teste sem autenticação"""
    try:
        from .models import ConversationCreate, QueuePriority
        
        conversation_data = ConversationCreate(
            customer_phone=customer_phone,
            customer_name=customer_name,
            priority=QueuePriority.NORMAL,
            initial_message=initial_message
        )
        
        result = await chat_service.create_conversation(db, conversation_data)
        
        return {
            "success": True,
            "conversation": result.model_dump(),
            "message": "Conversa de teste criada com sucesso!"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Erro ao criar conversa de teste"
        }

@app.get("/test/conversations", tags=["Test"])
async def list_test_conversations(db: AsyncSession = Depends(get_db)):
    """Listar conversas de teste sem autenticação"""
    try:
        result = await chat_service.list_conversations(db, page=1, per_page=10)
        
        return {
            "success": True,
            "conversations": [conv.model_dump() for conv in result["conversations"]],
            "total": result["total"],
            "message": f"Encontradas {result['total']} conversas"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Erro ao listar conversas"
        }

@app.post("/conversations", response_model=ConversationResponse, tags=["Conversations"])
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = RequireAgentOrAbove,
    db: AsyncSession = Depends(get_db)
):
    """
    **Criar nova conversa**
    
    Cria uma nova conversa de atendimento.
    Requer papel de agente ou superior.
    
    - **customer_phone**: Telefone do cliente (obrigatório)
    - **customer_name**: Nome do cliente (opcional)
    - **customer_email**: Email do cliente (opcional)
    - **priority**: Prioridade da conversa
    - **queue_id**: ID da fila de atendimento
    - **initial_message**: Mensagem inicial (opcional)
    """
    try:
        result = await chat_service.create_conversation(
            db, conversation_data, str(current_user.id)
        )
        
        logger.info(f"Conversa criada por {current_user.username}: {result.id}")
        return result
        
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/conversations", response_model=ConversationListResponse, tags=["Conversations"])
async def list_conversations(
    page: int = Query(1, ge=1, description="Página atual"),
    per_page: int = Query(50, ge=1, le=100, description="Itens por página"),
    status: Optional[ConversationStatus] = Query(None, description="Filtrar por status"),
    agent_id: Optional[str] = Query(None, description="Filtrar por agente"),
    queue_id: Optional[str] = Query(None, description="Filtrar por fila"),
    customer_phone: Optional[str] = Query(None, description="Filtrar por telefone"),
    priority: Optional[QueuePriority] = Query(None, description="Filtrar por prioridade"),
    current_user: User = RequireAgentOrAbove,
    db: AsyncSession = Depends(get_db)
):
    """
    **Listar conversas**
    
    Lista conversas com filtros e paginação.
    Agentes veem apenas suas conversas, supervisores e admins veem todas.
    """
    try:
        # Agentes só veem suas próprias conversas
        if current_user.role.value == "AGENT" and not agent_id:
            agent_id = str(current_user.id)
        
        result = await chat_service.list_conversations(
            db, page, per_page, status, agent_id, queue_id, 
            customer_phone, priority
        )
        
        return ConversationListResponse(**result)
        
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["Conversations"])
async def get_conversation(
    conversation_id: str,
    current_user: User = RequireAgentOrAbove,
    db: AsyncSession = Depends(get_db)
):
    """
    **Obter conversa por ID**
    
    Retorna dados detalhados de uma conversa específica.
    """
    try:
        result = await chat_service.get_conversation(db, conversation_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada"
            )
        
        # Verificar permissão (agentes só veem suas conversas)
        if (current_user.role.value == "AGENT" and 
            result.agent_id and result.agent_id != str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para acessar esta conversa"
            )
        
        return result
        
    except HTTPException:
        raise
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.put("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["Conversations"])
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    current_user: User = RequireAgentOrAbove,
    db: AsyncSession = Depends(get_db)
):
    """
    **Atualizar conversa**
    
    Atualiza dados de uma conversa (status, agente, prioridade, etc).
    """
    try:
        result = await chat_service.update_conversation(
            db, conversation_id, update_data, str(current_user.id)
        )
        
        logger.info(f"Conversa {conversation_id} atualizada por {current_user.username}")
        return result
        
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/conversations/{conversation_id}/assign", response_model=ConversationResponse, tags=["Conversations"])
async def assign_conversation(
    conversation_id: str,
    agent_id: str,
    current_user: User = RequireSupervisorOrAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Atribuir conversa a agente**
    
    Atribui uma conversa a um agente específico.
    Requer papel de supervisor ou administrador.
    """
    try:
        result = await chat_service.assign_conversation_to_agent(
            db, conversation_id, agent_id
        )
        
        logger.info(f"Conversa {conversation_id} atribuída ao agente {agent_id} por {current_user.username}")
        return result
        
    except (ConversationNotFoundError, AgentNotAvailableError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# === ENDPOINTS DE MENSAGENS ===

@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, tags=["Messages"])
async def create_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: User = RequireAgentOrAbove,
    db: AsyncSession = Depends(get_db)
):
    """
    **Criar nova mensagem**
    
    Adiciona uma nova mensagem a uma conversa.
    """
    try:
        # Definir conversation_id automaticamente
        message_data.conversation_id = conversation_id
        
        result = await chat_service.create_message(
            db, message_data, str(current_user.id)
        )
        
        # Notificar via WebSocket
        await websocket_manager.broadcast_to_conversation(
            conversation_id, {
                "type": "new_message",
                "message": result.model_dump()
            }
        )
        
        logger.info(f"Mensagem criada na conversa {conversation_id} por {current_user.username}")
        return result
        
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse, tags=["Messages"])
async def get_conversation_messages(
    conversation_id: str,
    page: int = Query(1, ge=1, description="Página atual"),
    per_page: int = Query(100, ge=1, le=200, description="Mensagens por página"),
    message_type: Optional[MessageType] = Query(None, description="Filtrar por tipo"),
    current_user: User = RequireAgentOrAbove,
    db: AsyncSession = Depends(get_db)
):
    """
    **Obter mensagens da conversa**
    
    Lista todas as mensagens de uma conversa com paginação.
    """
    try:
        result = await chat_service.get_conversation_messages(
            db, conversation_id, page, per_page, message_type
        )
        
        return MessageListResponse(**result)
        
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# === WEBSOCKET ===

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """
    **WebSocket para chat em tempo real**
    
    Conecta ao chat de uma conversa específica para receber/enviar mensagens em tempo real.
    
    **Eventos suportados:**
    - `new_message`: Nova mensagem na conversa
    - `typing`: Usuário digitando
    - `read`: Mensagem lida
    - `agent_joined`: Agente entrou na conversa
    - `agent_left`: Agente saiu da conversa
    """
    await websocket_manager.connect(websocket, conversation_id)
    
    try:
        while True:
            # Receber dados do cliente
            data = await websocket.receive_json()
            
            # Processar diferentes tipos de eventos
            event_type = data.get("type")
            
            if event_type == "typing":
                # Broadcast evento de digitação
                await websocket_manager.broadcast_to_conversation(
                    conversation_id, {
                        "type": "typing",
                        "user": data.get("user"),
                        "is_typing": data.get("is_typing", True)
                    }, exclude_websocket=websocket
                )
            
            elif event_type == "read":
                # Marcar mensagem como lida
                # TODO: Implementar lógica de leitura
                await websocket_manager.broadcast_to_conversation(
                    conversation_id, {
                        "type": "read",
                        "message_id": data.get("message_id"),
                        "user": data.get("user")
                    }, exclude_websocket=websocket
                )
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, conversation_id)
    except Exception as e:
        logger.error(f"Erro no WebSocket {conversation_id}: {e}")
        websocket_manager.disconnect(websocket, conversation_id)

# === ENDPOINTS DE ESTATÍSTICAS ===

@app.get("/stats", response_model=ChatStats, tags=["Statistics"])
async def get_chat_stats(
    date_from: Optional[datetime] = Query(None, description="Data inicial para estatísticas"),
    current_user: User = RequireSupervisorOrAdmin,
    db: AsyncSession = Depends(get_db)
):
    """
    **Obter estatísticas do chat**
    
    Retorna métricas detalhadas de atendimento.
    Requer papel de supervisor ou administrador.
    """
    try:
        result = await chat_service.get_chat_stats(db, date_from)
        return ChatStats(**result)
        
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# === ENDPOINTS DE WEBHOOK (WHATSAPP) ===

@app.get("/webhook/whatsapp", tags=["WhatsApp"])
async def whatsapp_webhook_verify(
    request: Request,
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token")
):
    """
    **Verificação do webhook WhatsApp**
    
    Endpoint para verificação inicial do webhook do WhatsApp Business API.
    """
    try:
        from .whatsapp_service import whatsapp_service
        
        challenge = await whatsapp_service.verify_webhook(
            hub_mode, hub_verify_token, hub_challenge
        )
        
        if challenge:
            logger.info(f"✅ Webhook WhatsApp verificado: {request.client.host}")
            return int(challenge)
        else:
            logger.warning(f"❌ Falha na verificação webhook: {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Token de verificação inválido"
            )
            
    except Exception as e:
        logger.error(f"❌ Erro na verificação webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/webhook/whatsapp", tags=["WhatsApp"])
async def whatsapp_webhook_receive(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """
    **Webhook do WhatsApp Business API**
    
    Recebe mensagens, status e eventos do WhatsApp Business API.
    
    **Funcionalidades:**
    - Receber mensagens de clientes
    - Processar diferentes tipos de mídia
    - Criar conversas automaticamente
    - Atualizar status de entrega
    - Notificar agentes via WebSocket
    """
    try:
        from .whatsapp_service import whatsapp_service
        
        # Obter dados do webhook
        webhook_data = await request.json()
        
        # Processar webhook
        result = await whatsapp_service.process_webhook(webhook_data, db)
        
        logger.info(f"📥 Webhook processado: {result['status']}")
        
        return {
            "status": "received",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook WhatsApp: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/whatsapp/send", tags=["WhatsApp"])
async def send_whatsapp_message(
    to_phone: str,
    message: str,
    message_type: str = "text",
    media_url: Optional[str] = None,
    conversation_id: Optional[str] = None,
    current_user: User = RequireAgentOrAbove,
    db: AsyncSession = Depends(get_db)
):
    """
    **Enviar mensagem via WhatsApp**
    
    Envia mensagem para cliente via WhatsApp Business API.
    
    - **to_phone**: Número do destinatário
    - **message**: Conteúdo da mensagem
    - **message_type**: Tipo (text, image, document)
    - **media_url**: URL da mídia (opcional)
    - **conversation_id**: ID da conversa (opcional)
    """
    try:
        from .whatsapp_service import whatsapp_service
        
        # Enviar via WhatsApp API
        result = await whatsapp_service.send_message(
            to_phone, message, message_type, media_url
        )
        
        # Se enviou com sucesso e tem conversation_id, salvar no banco
        if result["success"] and conversation_id:
            message_data = MessageCreate(
                conversation_id=conversation_id,
                content=message,
                message_type=MessageType(message_type),
                direction=MessageDirection.OUTBOUND,
                sender_name=current_user.username,
                media_url=media_url,
                metadata={
                    "whatsapp_message_id": result.get("message_id"),
                    "sent_via_api": True
                }
            )
            
            # Salvar mensagem
            saved_message = await chat_service.create_message(
                db, message_data, str(current_user.id)
            )
            
            # Notificar via WebSocket
            await websocket_manager.broadcast_to_conversation(
                conversation_id,
                {
                    "type": "new_message",
                    "message": saved_message.model_dump()
                }
            )
        
        logger.info(f"📤 Mensagem WhatsApp enviada por {current_user.username}: {result['status']}")
        
        return {
            "success": result["success"],
            "whatsapp_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar WhatsApp: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# === EXECUTAR APLICAÇÃO ===

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=8002,  # Porta específica do Chat Service
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )