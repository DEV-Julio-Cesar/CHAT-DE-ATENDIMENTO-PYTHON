"""
API Endpoints para Chat WhatsApp
Integração com o sistema de fluxo de 3 etapas
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import structlog
from datetime import datetime

from services.whatsapp_chat_flow import (
    whatsapp_chat_flow,
    ConversationStatus,
    SenderType,
    MessageType
)

logger = structlog.get_logger(__name__)

# Router para endpoints de chat
router = APIRouter(prefix="/api", tags=["chat"])

# Modelos Pydantic para requests
class MessageRequest(BaseModel):
    content: str
    message_type: str = "text"

class ConversationCreateRequest(BaseModel):
    customer_name: str
    customer_phone: str
    initial_message: Optional[str] = None

class AssignRequest(BaseModel):
    agent_id: Optional[str] = "agent_1"  # Default agent

class CloseRequest(BaseModel):
    reason: Optional[str] = "Resolvido"

# Endpoints de Conversas
@router.get("/conversations")
async def get_conversations():
    """Listar todas as conversas"""
    try:
        conversations = []
        
        for conv in whatsapp_chat_flow.conversations.values():
            conversations.append({
                "id": conv.id,
                "customer_name": conv.customer_name,
                "customer_phone": conv.customer_phone,
                "status": conv.status.value,
                "assigned_agent_id": conv.assigned_agent_id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "last_message": conv.last_message,
                "messages_count": conv.messages_count,
                "priority": conv.priority,
                "tags": conv.tags
            })
        
        # Ordenar por data de atualização (mais recente primeiro)
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return {
            "success": True,
            "data": conversations,
            "total": len(conversations),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Erro ao listar conversas", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Obter conversa específica"""
    try:
        conversation = whatsapp_chat_flow.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        return {
            "success": True,
            "data": {
                "id": conversation.id,
                "customer_name": conversation.customer_name,
                "customer_phone": conversation.customer_phone,
                "status": conversation.status.value,
                "assigned_agent_id": conversation.assigned_agent_id,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "last_message": conversation.last_message,
                "messages_count": conversation.messages_count,
                "priority": conversation.priority,
                "tags": conversation.tags,
                "metadata": conversation.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao obter conversa", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/conversations")
async def create_conversation(request: ConversationCreateRequest):
    """Criar nova conversa"""
    try:
        conversation = await whatsapp_chat_flow.create_conversation(
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            initial_message=request.initial_message
        )
        
        return {
            "success": True,
            "data": {
                "id": conversation.id,
                "customer_name": conversation.customer_name,
                "status": conversation.status.value,
                "created_at": conversation.created_at.isoformat()
            },
            "message": "Conversa criada com sucesso"
        }
        
    except Exception as e:
        logger.error("Erro ao criar conversa", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao criar conversa")

# Endpoints de Mensagens
@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    """Obter mensagens de uma conversa"""
    try:
        # Verificar se conversa existe
        conversation = whatsapp_chat_flow.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        messages = whatsapp_chat_flow.get_messages(conversation_id)
        
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_type": msg.sender_type.value,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "message_type": msg.message_type.value,
                "created_at": msg.timestamp.isoformat(),
                "whatsapp_message_id": msg.whatsapp_message_id,
                "metadata": msg.metadata
            })
        
        return {
            "success": True,
            "messages": formatted_messages,
            "total": len(formatted_messages),
            "conversation_id": conversation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao obter mensagens", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: MessageRequest):
    """Enviar mensagem para uma conversa"""
    try:
        # Verificar se conversa existe
        conversation = whatsapp_chat_flow.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        # Determinar tipo de remetente baseado no status da conversa
        if conversation.status == ConversationStatus.AUTOMACAO:
            sender_type = SenderType.BOT
            sender_id = "bot"
        else:
            sender_type = SenderType.AGENT
            sender_id = conversation.assigned_agent_id or "agent_1"
        
        # Adicionar mensagem
        message = await whatsapp_chat_flow.add_message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=request.content,
            message_type=MessageType(request.message_type)
        )
        
        return {
            "success": True,
            "data": {
                "id": message.id,
                "content": message.content,
                "sender_type": message.sender_type.value,
                "created_at": message.timestamp.isoformat()
            },
            "message": "Mensagem enviada com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao enviar mensagem", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao enviar mensagem")

# Endpoints de Fluxo (3 Etapas)
@router.post("/conversations/{conversation_id}/assign")
async def assign_conversation(conversation_id: str, request: AssignRequest = AssignRequest()):
    """Atribuir conversa a um agente (ESPERA → ATRIBUÍDO)"""
    try:
        success = await whatsapp_chat_flow.assign_conversation(
            conversation_id=conversation_id,
            agent_id=request.agent_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Não foi possível atribuir a conversa")
        
        return {
            "success": True,
            "message": f"Conversa atribuída ao agente {request.agent_id}",
            "status_change": "waiting → assigned"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao atribuir conversa", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao atribuir conversa")

@router.post("/conversations/{conversation_id}/automate")
async def start_automation(conversation_id: str):
    """Iniciar automação (ATRIBUÍDO → AUTOMAÇÃO)"""
    try:
        success = await whatsapp_chat_flow.start_automation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Não foi possível iniciar automação")
        
        return {
            "success": True,
            "message": "Automação iniciada com sucesso",
            "status_change": "assigned → automation"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao iniciar automação", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao iniciar automação")

@router.post("/conversations/{conversation_id}/takeover")
async def takeover_conversation(conversation_id: str, request: AssignRequest = AssignRequest()):
    """Agente assume conversa da automação (AUTOMAÇÃO → ATRIBUÍDO)"""
    try:
        success = await whatsapp_chat_flow.takeover_conversation(
            conversation_id=conversation_id,
            agent_id=request.agent_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Não foi possível assumir a conversa")
        
        return {
            "success": True,
            "message": f"Conversa assumida pelo agente {request.agent_id}",
            "status_change": "automation → assigned"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao assumir conversa", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao assumir conversa")

@router.post("/conversations/{conversation_id}/close")
async def close_conversation(conversation_id: str, request: CloseRequest = CloseRequest()):
    """Encerrar conversa (qualquer status → ENCERRADO)"""
    try:
        success = await whatsapp_chat_flow.close_conversation(
            conversation_id=conversation_id,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Não foi possível encerrar a conversa")
        
        return {
            "success": True,
            "message": f"Conversa encerrada: {request.reason}",
            "status_change": "* → closed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao encerrar conversa", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao encerrar conversa")

# Endpoints de Estatísticas
@router.get("/chat/stats")
async def get_chat_stats():
    """Obter estatísticas do sistema de chat"""
    try:
        stats = whatsapp_chat_flow.get_stats()
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Erro ao obter estatísticas", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/agents/{agent_id}/workload")
async def get_agent_workload(agent_id: str):
    """Obter carga de trabalho de um agente"""
    try:
        workload = whatsapp_chat_flow.get_agent_workload(agent_id)
        
        return {
            "success": True,
            "data": workload,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Erro ao obter carga de trabalho", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# Endpoint para simular mensagens de clientes (para testes)
@router.post("/conversations/{conversation_id}/simulate-customer-message")
async def simulate_customer_message(conversation_id: str, request: MessageRequest):
    """Simular mensagem de cliente (para testes)"""
    try:
        conversation = whatsapp_chat_flow.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        # Adicionar mensagem do cliente
        message = await whatsapp_chat_flow.add_message(
            conversation_id=conversation_id,
            sender_type=SenderType.CUSTOMER,
            sender_id=conversation.customer_phone,
            content=request.content,
            message_type=MessageType(request.message_type)
        )
        
        return {
            "success": True,
            "data": {
                "id": message.id,
                "content": message.content,
                "sender_type": message.sender_type.value,
                "created_at": message.timestamp.isoformat()
            },
            "message": "Mensagem de cliente simulada com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao simular mensagem", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao simular mensagem")