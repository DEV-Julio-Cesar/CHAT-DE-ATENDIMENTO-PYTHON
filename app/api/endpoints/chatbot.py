"""
Endpoints do Chatbot AI Enterprise
API para interação com o chatbot de atendimento

Features:
- Envio de mensagens e respostas automáticas
- Métricas e estatísticas do chatbot
- Gerenciamento de conversas
- Integração com WhatsApp
"""

from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.services.chatbot_ai import (
    chatbot_ai,
    ChatResponse,
    IntentType,
    SentimentType,
    process_whatsapp_message,
    is_business_hours
)
from app.core.rate_limiter import rate_limiter, RateLimitConfig
from app.core.audit_logger import audit_logger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chatbot", tags=["Chatbot AI"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ChatMessageRequest(BaseModel):
    """Requisição de mensagem para o chatbot"""
    message: str = Field(..., min_length=1, max_length=4000, description="Mensagem do usuário")
    conversation_id: Optional[str] = Field(None, description="ID da conversa (opcional)")
    cliente_info: Optional[Dict[str, Any]] = Field(None, description="Informações do cliente")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Minha internet está muito lenta",
                "conversation_id": "whatsapp:5511999999999",
                "cliente_info": {
                    "nome": "João Silva",
                    "telefone": "5511999999999",
                    "plano": "Plus 200MB"
                }
            }
        }


class ChatMessageResponse(BaseModel):
    """Resposta do chatbot"""
    success: bool
    message: str
    intent: str
    sentiment: str
    confidence: float
    should_escalate: bool
    escalation_reason: Optional[str] = None
    quick_replies: List[str] = []
    suggested_actions: List[str] = []
    metadata: Dict[str, Any] = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Entendo que sua internet está lenta...",
                "intent": "internet_lenta",
                "sentiment": "negativo",
                "confidence": 0.85,
                "should_escalate": False,
                "quick_replies": ["Já reiniciei o roteador", "Agendar visita técnica"],
                "metadata": {"response_time_ms": 150}
            }
        }


class WhatsAppWebhookRequest(BaseModel):
    """Requisição do webhook do WhatsApp"""
    phone_number: str = Field(..., description="Número de telefone do remetente")
    message: str = Field(..., description="Conteúdo da mensagem")
    message_id: Optional[str] = Field(None, description="ID da mensagem no WhatsApp")
    timestamp: Optional[str] = Field(None, description="Timestamp da mensagem")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "5511999999999",
                "message": "Olá, preciso de ajuda",
                "message_id": "wamid.xxx",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ChatMetricsResponse(BaseModel):
    """Métricas do chatbot"""
    total_messages: int
    successful_resolutions: int
    resolution_rate: float
    escalations: int
    escalation_rate: float
    avg_response_time_ms: int
    top_intents: Dict[str, int]
    is_business_hours: bool


class ConversationHistoryResponse(BaseModel):
    """Histórico de uma conversa"""
    conversation_id: str
    cliente_nome: Optional[str]
    cliente_telefone: Optional[str]
    state: str
    current_intent: Optional[str]
    sentiment: str
    bot_attempts: int
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_chatbot_status():
    """
    Status do chatbot
    
    Retorna informações sobre o estado atual do chatbot
    """
    return {
        "status": "active" if chatbot_ai.initialized else "initializing",
        "model": "gemini-1.5-flash" if chatbot_ai.model else "fallback",
        "is_business_hours": is_business_hours(),
        "company_name": chatbot_ai.company_name,
        "max_bot_attempts": chatbot_ai.max_bot_attempts
    }


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: Request,
    payload: ChatMessageRequest
):
    """
    Enviar mensagem para o chatbot
    
    Processa a mensagem do usuário e retorna a resposta do chatbot
    com análise de intenção e sentimento.
    
    Rate limit: 30 requisições por minuto
    """
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Rate limiting
        identifier = f"chatbot:{client_ip}"
        allowed, remaining = await rate_limiter.is_allowed(
            identifier=identifier,
            max_requests=RateLimitConfig.AI_CHAT["max_requests"],
            window_seconds=RateLimitConfig.AI_CHAT["window_seconds"]
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later."
            )
        
        # Gerar ID de conversa se não fornecido
        conversation_id = payload.conversation_id or f"web:{client_ip}:{datetime.now().timestamp()}"
        
        # Processar mensagem
        response: ChatResponse = await chatbot_ai.generate_response(
            conversation_id=conversation_id,
            user_message=payload.message,
            cliente_info=payload.cliente_info
        )
        
        # Log de auditoria
        await audit_logger.log(
            event_type="chatbot_interaction",
            user_id=payload.cliente_info.get("id") if payload.cliente_info else None,
            action="chat_message",
            resource_type="conversation",
            resource_id=conversation_id,
            ip_address=client_ip,
            details={
                "intent": response.intent.value,
                "sentiment": response.sentiment.value,
                "escalated": response.should_escalate
            }
        )
        
        return ChatMessageResponse(
            success=True,
            message=response.message,
            intent=response.intent.value,
            sentiment=response.sentiment.value,
            confidence=response.confidence,
            should_escalate=response.should_escalate,
            escalation_reason=response.escalation_reason,
            quick_replies=response.quick_replies,
            suggested_actions=response.suggested_actions,
            metadata=response.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chatbot message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.post("/whatsapp/process", response_model=ChatMessageResponse)
async def process_whatsapp(
    request: Request,
    payload: WhatsAppWebhookRequest
):
    """
    Processar mensagem do WhatsApp
    
    Endpoint específico para integração com WhatsApp Business API.
    Processa mensagens recebidas e retorna resposta formatada.
    """
    try:
        # Processar mensagem
        response = await process_whatsapp_message(
            phone_number=payload.phone_number,
            message=payload.message
        )
        
        logger.info(
            f"WhatsApp message processed",
            extra={
                "phone": payload.phone_number[-4:],  # Últimos 4 dígitos
                "intent": response.intent.value,
                "escalated": response.should_escalate
            }
        )
        
        return ChatMessageResponse(
            success=True,
            message=response.message,
            intent=response.intent.value,
            sentiment=response.sentiment.value,
            confidence=response.confidence,
            should_escalate=response.should_escalate,
            escalation_reason=response.escalation_reason,
            quick_replies=response.quick_replies,
            suggested_actions=response.suggested_actions,
            metadata={
                **response.metadata,
                "whatsapp_message_id": payload.message_id
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process WhatsApp message"
        )


@router.get("/metrics", response_model=ChatMetricsResponse)
async def get_chatbot_metrics():
    """
    Obter métricas do chatbot
    
    Retorna estatísticas de uso, taxa de resolução,
    escalações e tempos de resposta.
    """
    try:
        metrics = await chatbot_ai.get_metrics()
        
        return ChatMetricsResponse(
            total_messages=metrics["total_messages"],
            successful_resolutions=metrics["successful_resolutions"],
            resolution_rate=round(metrics["resolution_rate"], 2),
            escalations=metrics["escalations"],
            escalation_rate=round(metrics["escalation_rate"], 2),
            avg_response_time_ms=metrics["avg_response_time_ms"],
            top_intents=metrics["top_intents"],
            is_business_hours=is_business_hours()
        )
        
    except Exception as e:
        logger.error(f"Error getting chatbot metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        )


@router.get("/conversation/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str):
    """
    Obter histórico de uma conversa
    
    Retorna todas as mensagens e contexto de uma conversa específica.
    """
    try:
        ctx = await chatbot_ai.get_or_create_context(conversation_id)
        
        if not ctx.messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return ConversationHistoryResponse(
            conversation_id=ctx.conversation_id,
            cliente_nome=ctx.cliente_nome,
            cliente_telefone=ctx.cliente_telefone,
            state=ctx.state.value,
            current_intent=ctx.current_intent.value if ctx.current_intent else None,
            sentiment=ctx.sentiment.value,
            bot_attempts=ctx.bot_attempts,
            messages=ctx.messages,
            created_at=ctx.created_at.isoformat(),
            updated_at=ctx.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation"
        )


@router.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """
    Limpar/encerrar uma conversa
    
    Remove o contexto da conversa do cache.
    Útil quando o atendimento é finalizado.
    """
    try:
        await chatbot_ai.clear_conversation(conversation_id)
        
        return {
            "success": True,
            "message": f"Conversation {conversation_id} cleared"
        }
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear conversation"
        )


@router.get("/intents")
async def list_intents():
    """
    Listar todas as intenções reconhecidas
    
    Retorna lista de intenções que o chatbot pode classificar.
    """
    return {
        "intents": [
            {
                "value": intent.value,
                "category": _get_intent_category(intent)
            }
            for intent in IntentType
        ]
    }


@router.get("/quick-replies/{intent}")
async def get_quick_replies(intent: str):
    """
    Obter sugestões de resposta rápida para uma intenção
    """
    try:
        intent_type = IntentType(intent)
        replies = chatbot_ai.get_quick_replies(intent_type)
        
        return {
            "intent": intent,
            "quick_replies": replies
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid intent: {intent}"
        )


# =============================================================================
# HELPERS
# =============================================================================

def _get_intent_category(intent: IntentType) -> str:
    """Obter categoria de uma intenção"""
    categories = {
        # Suporte Técnico
        IntentType.INTERNET_LENTA: "suporte_tecnico",
        IntentType.SEM_CONEXAO: "suporte_tecnico",
        IntentType.WIFI_PROBLEMA: "suporte_tecnico",
        IntentType.ROTEADOR_CONFIG: "suporte_tecnico",
        IntentType.VISITA_TECNICA: "suporte_tecnico",
        IntentType.INSTALACAO: "suporte_tecnico",
        
        # Financeiro
        IntentType.SEGUNDA_VIA_BOLETO: "financeiro",
        IntentType.PAGAMENTO: "financeiro",
        IntentType.NEGOCIACAO_DIVIDA: "financeiro",
        IntentType.FATURA_DUVIDA: "financeiro",
        
        # Comercial
        IntentType.UPGRADE_PLANO: "comercial",
        IntentType.DOWNGRADE_PLANO: "comercial",
        IntentType.NOVO_PLANO: "comercial",
        IntentType.CANCELAMENTO: "comercial",
        IntentType.PROMOCAO: "comercial",
        
        # Cadastro
        IntentType.ALTERACAO_CADASTRO: "cadastro",
        IntentType.MUDANCA_ENDERECO: "cadastro",
        IntentType.ALTERACAO_VENCIMENTO: "cadastro",
        
        # Interação
        IntentType.SAUDACAO: "interacao",
        IntentType.DESPEDIDA: "interacao",
        IntentType.AGRADECIMENTO: "interacao",
        IntentType.RECLAMACAO: "interacao",
        IntentType.ELOGIO: "interacao",
        IntentType.FALAR_HUMANO: "interacao",
        IntentType.DESCONHECIDO: "outros",
    }
    
    return categories.get(intent, "outros")