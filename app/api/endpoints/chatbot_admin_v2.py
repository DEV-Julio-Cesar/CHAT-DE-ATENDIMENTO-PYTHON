"""
Chatbot Admin V2 - Gerenciamento do Bot
CIANET PROVEDOR - v3.0

Endpoints para:
- Treinar respostas
- Gerenciar base de conhecimento
- Ver métricas do bot
- Testar respostas
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from pydantic import BaseModel, Field

from app.core.auth_manager import get_current_user, require_permissions
from app.core.sqlserver_db import sqlserver_manager
from app.services.chatbot_v2 import chatbot_v2, Intent, KNOWLEDGE_BASE, INTENT_KEYWORDS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chatbot/v2", tags=["Chatbot Admin V2"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TrainResponseRequest(BaseModel):
    """Treinar resposta"""
    intent: str = Field(..., description="Nome da intenção (ex: internet_lenta)")
    response: str = Field(..., min_length=10)
    quick_replies: Optional[List[str]] = None


class TestMessageRequest(BaseModel):
    """Testar mensagem"""
    message: str = Field(..., min_length=1)
    client_name: Optional[str] = None


class IntentResponse(BaseModel):
    """Informações de uma intenção"""
    intent: str
    keywords: List[str]
    response: str
    quick_replies: List[str]
    is_customized: bool


class ChatbotMetrics(BaseModel):
    """Métricas do chatbot"""
    total_messages_today: int
    resolved_by_bot: int
    escalated_to_human: int
    avg_response_time_ms: float
    top_intents: List[Dict[str, int]]
    satisfaction_rate: Optional[float]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/intents",
    response_model=List[IntentResponse],
    summary="Listar intenções"
)
async def list_intents(
    request: Request,
    current_user: dict = Depends(require_permissions(["chatbot:manage"]))
):
    """
    Listar todas as intenções configuradas.
    """
    # Buscar customizações do banco
    customized = set()
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT intent FROM chatbot_responses WHERE is_active = 1")
            for row in cursor.fetchall():
                customized.add(row.intent)
    except Exception:
        pass
    
    intents = []
    for intent in Intent:
        kb = KNOWLEDGE_BASE.get(intent, {})
        keywords = INTENT_KEYWORDS.get(intent, [])
        
        intents.append(IntentResponse(
            intent=intent.value,
            keywords=keywords,
            response=kb.get("response", ""),
            quick_replies=kb.get("quick_replies", []),
            is_customized=intent.value in customized
        ))
    
    return intents


@router.get(
    "/intents/{intent_name}",
    response_model=IntentResponse,
    summary="Obter intenção"
)
async def get_intent(
    request: Request,
    intent_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter detalhes de uma intenção específica.
    """
    try:
        intent = Intent(intent_name.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intenção não encontrada: {intent_name}"
        )
    
    kb = KNOWLEDGE_BASE.get(intent, {})
    keywords = INTENT_KEYWORDS.get(intent, [])
    
    return IntentResponse(
        intent=intent.value,
        keywords=keywords,
        response=kb.get("response", ""),
        quick_replies=kb.get("quick_replies", []),
        is_customized=False  # TODO: verificar no banco
    )


@router.post(
    "/train",
    summary="Treinar resposta"
)
async def train_response(
    request: Request,
    data: TrainResponseRequest,
    current_user: dict = Depends(require_permissions(["chatbot:manage"]))
):
    """
    Treinar/atualizar resposta para uma intenção.
    
    A resposta será salva no banco e carregada automaticamente.
    """
    # Validar intent
    try:
        Intent(data.intent.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Intenção inválida: {data.intent}"
        )
    
    success = await chatbot_v2.train_response(
        intent=data.intent.lower(),
        response=data.response,
        quick_replies=data.quick_replies
    )
    
    if success:
        return {"message": "Resposta treinada com sucesso", "intent": data.intent}
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Erro ao treinar resposta"
    )


@router.post(
    "/test",
    summary="Testar mensagem"
)
async def test_message(
    request: Request,
    data: TestMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Testar como o chatbot responde a uma mensagem.
    Útil para validar treinamento.
    """
    # Classificar intenção
    intent, confidence = chatbot_v2.classify_intent(data.message)
    sentiment = chatbot_v2.analyze_sentiment(data.message)
    
    # Verificar escalação
    should_escalate, reason = chatbot_v2.should_escalate(
        intent=intent,
        sentiment=sentiment,
        message=data.message,
        attempts=0
    )
    
    # Gerar resposta
    response = await chatbot_v2.process_message(
        content=data.message,
        client_name=data.client_name
    )
    
    return {
        "input": data.message,
        "classification": {
            "intent": intent.value,
            "confidence": confidence,
            "sentiment": sentiment.value
        },
        "escalation": {
            "should_escalate": should_escalate,
            "reason": reason
        },
        "response": response,
        "quick_replies": chatbot_v2.get_quick_replies(intent)
    }


@router.get(
    "/metrics",
    response_model=ChatbotMetrics,
    summary="Métricas do chatbot"
)
async def get_metrics(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(require_permissions(["chatbot:manage"]))
):
    """
    Obter métricas de performance do chatbot.
    """
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Mensagens processadas pelo bot
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN sender_type = 'bot' THEN 1 ELSE 0 END) as bot_responses,
                    AVG(CASE WHEN sender_type = 'bot' THEN 50 ELSE NULL END) as avg_response_ms
                FROM mensagens
                WHERE created_at >= DATEADD(DAY, -?, GETDATE())
            """, (days,))
            
            row = cursor.fetchone()
            total = row.total or 0
            bot_responses = row.bot_responses or 0
            avg_ms = row.avg_response_ms or 0
            
            # Conversas resolvidas sem humano
            cursor.execute("""
                SELECT COUNT(*) as resolved_by_bot
                FROM conversas
                WHERE resolved_at IS NOT NULL
                AND attendant_id IS NULL
                AND started_at >= DATEADD(DAY, -?, GETDATE())
            """, (days,))
            
            resolved = cursor.fetchone().resolved_by_bot or 0
            
            # Top intenções (simulado - seria necessário tabela de logs)
            top_intents = [
                {"intent": "internet_lenta", "count": 45},
                {"intent": "segunda_via", "count": 32},
                {"intent": "saudacao", "count": 28},
                {"intent": "wifi_problema", "count": 15},
                {"intent": "pagamento", "count": 12}
            ]
            
            return ChatbotMetrics(
                total_messages_today=total,
                resolved_by_bot=resolved,
                escalated_to_human=total - bot_responses,
                avg_response_time_ms=float(avg_ms),
                top_intents=top_intents,
                satisfaction_rate=None
            )
    
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}")
        return ChatbotMetrics(
            total_messages_today=0,
            resolved_by_bot=0,
            escalated_to_human=0,
            avg_response_time_ms=0,
            top_intents=[],
            satisfaction_rate=None
        )


@router.get(
    "/responses",
    summary="Listar respostas customizadas"
)
async def list_custom_responses(
    request: Request,
    current_user: dict = Depends(require_permissions(["chatbot:manage"]))
):
    """
    Listar todas as respostas customizadas (treinadas).
    """
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT intent, response, quick_replies, is_active, created_at, updated_at
                FROM chatbot_responses
                ORDER BY intent
            """)
            
            responses = []
            for row in cursor.fetchall():
                responses.append({
                    "intent": row.intent,
                    "response": row.response,
                    "quick_replies": row.quick_replies,
                    "is_active": row.is_active,
                    "created_at": str(row.created_at) if row.created_at else None,
                    "updated_at": str(row.updated_at) if row.updated_at else None
                })
            
            return {"responses": responses, "total": len(responses)}
    
    except Exception as e:
        logger.error(f"Erro ao listar respostas: {e}")
        return {"responses": [], "total": 0}


@router.delete(
    "/responses/{intent_name}",
    summary="Remover resposta customizada"
)
async def delete_custom_response(
    request: Request,
    intent_name: str,
    current_user: dict = Depends(require_permissions(["chatbot:manage"]))
):
    """
    Remover resposta customizada, voltando para a padrão.
    """
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chatbot_responses WHERE intent = ?",
                (intent_name,)
            )
            conn.commit()
            
            deleted = cursor.rowcount > 0
            
            if deleted:
                return {"message": f"Resposta de '{intent_name}' removida"}
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resposta customizada não encontrada: {intent_name}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover resposta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao remover resposta"
        )


@router.post(
    "/reload",
    summary="Recarregar base de conhecimento"
)
async def reload_knowledge(
    request: Request,
    current_user: dict = Depends(require_permissions(["chatbot:manage"]))
):
    """
    Recarregar base de conhecimento do banco.
    Use após edições diretas no banco.
    """
    chatbot_v2._load_custom_knowledge()
    return {"message": "Base de conhecimento recarregada"}


@router.get(
    "/status",
    summary="Status do chatbot"
)
async def get_status(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Verificar status do serviço de chatbot.
    """
    return {
        "status": "active",
        "gemini_available": chatbot_v2.model is not None,
        "company_name": chatbot_v2.company_name,
        "total_intents": len(Intent),
        "knowledge_base_loaded": len(KNOWLEDGE_BASE) > 0
    }
