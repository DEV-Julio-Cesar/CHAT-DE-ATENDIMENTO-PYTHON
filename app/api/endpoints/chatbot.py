"""
API Endpoints para Chatbot IA
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.services.chatbot_ai import chatbot_ai
from app.api.endpoints.auth import get_current_user
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


class ChatMessage(BaseModel):
    customer_id: str
    message: str
    customer_data: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: str
    intent: str
    confidence: float
    actions: list
    escalate_to_human: bool
    suggested_responses: list
    metadata: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def process_chat_message(
    chat_data: ChatMessage,
    current_user: dict = Depends(get_current_user)
) -> ChatResponse:
    """
    Processa mensagem do cliente através do chatbot IA
    """
    try:
        response = await chatbot_ai.process_message(
            customer_id=chat_data.customer_id,
            message=chat_data.message,
            customer_data=chat_data.customer_data
        )
        
        return ChatResponse(
            message=response.message,
            intent=response.intent,
            confidence=response.confidence,
            actions=response.actions,
            escalate_to_human=response.escalate_to_human,
            suggested_responses=response.suggested_responses,
            metadata=response.metadata
        )
        
    except Exception as e:
        logger.error("Error processing chat message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_chatbot_analytics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtém analytics do chatbot
    """
    try:
        analytics = await chatbot_ai.get_analytics()
        return analytics
        
    except Exception as e:
        logger.error("Error getting chatbot analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chatbot_health_check() -> Dict[str, Any]:
    """
    Verifica saúde do chatbot
    """
    return {
        "status": "healthy",
        "ai_model_available": chatbot_ai.model is not None,
        "knowledge_base_loaded": len(chatbot_ai.knowledge_base) > 0
    }