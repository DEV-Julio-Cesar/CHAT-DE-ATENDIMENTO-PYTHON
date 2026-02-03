"""
Endpoints de Conversas/Atendimentos com SQL Server
CIANET PROVEDOR - v3.0

Gerenciamento completo de conversas:
- Listar, criar, atualizar conversas
- Atribuir/transferir atendentes
- Encerrar com avaliação
- Histórico de mensagens
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Request, Depends, Query, Path
from pydantic import BaseModel, Field

from app.core.auth_manager import get_current_user, require_permissions
from app.core.sqlserver_db import sqlserver_manager
from app.core.audit_logger import audit_logger, AuditEventTypes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["Conversas"])


# ============================================================================
# SCHEMAS
# ============================================================================

class ConversationCreate(BaseModel):
    """Criar nova conversa"""
    client_phone: str = Field(..., description="Telefone do cliente")
    client_name: Optional[str] = None
    subject: Optional[str] = None
    category: Optional[str] = None
    priority: str = Field(default="normal")


class ConversationUpdate(BaseModel):
    """Atualizar conversa"""
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    attendant_id: Optional[int] = None


class ConversationClose(BaseModel):
    """Encerrar conversa"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback: Optional[str] = None
    resolution_notes: Optional[str] = None


class MessageCreate(BaseModel):
    """Enviar mensagem"""
    content: str = Field(..., min_length=1)
    message_type: str = Field(default="text")
    media_url: Optional[str] = None


class ConversationResponse(BaseModel):
    """Resposta de conversa"""
    id: int
    client_id: int
    client_phone: str
    client_name: Optional[str]
    attendant_id: Optional[int]
    attendant_name: Optional[str]
    status: str
    priority: str
    category: Optional[str]
    subject: Optional[str]
    total_messages: int
    rating: Optional[int]
    started_at: str
    last_message_at: Optional[str]
    resolved_at: Optional[str]


class MessageResponse(BaseModel):
    """Resposta de mensagem"""
    id: int
    conversation_id: int
    sender_type: str
    sender_id: Optional[int]
    content: str
    message_type: str
    status: str
    is_from_me: bool
    created_at: str


class ConversationListResponse(BaseModel):
    """Lista paginada de conversas"""
    conversations: List[ConversationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ConversationStats(BaseModel):
    """Estatísticas de conversas"""
    total_today: int
    waiting: int
    in_progress: int
    resolved_today: int
    avg_response_time_minutes: Optional[float]
    avg_resolution_time_minutes: Optional[float]


# ============================================================================
# HELPERS
# ============================================================================

def get_or_create_client(phone: str, name: Optional[str] = None) -> int:
    """Obter ou criar cliente pelo telefone"""
    client = sqlserver_manager.get_client_by_phone(phone)
    
    if client:
        return int(client["id"])
    
    # Criar novo cliente
    new_client = sqlserver_manager.create_client(
        phone=phone,
        name=name or f"Cliente {phone[-4:]}"
    )
    
    return int(new_client["id"]) if new_client else None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/",
    response_model=ConversationListResponse,
    summary="Listar conversas"
)
async def list_conversations(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="waiting, in_progress, resolved, closed"),
    priority: Optional[str] = Query(None, description="low, normal, high, urgent"),
    attendant_id: Optional[int] = Query(None, description="Filtrar por atendente"),
    date_from: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar conversas com filtros.
    
    - Atendentes veem apenas suas conversas
    - Supervisores/Admin veem todas
    """
    offset = (page - 1) * per_page
    
    # Atendente só vê suas próprias conversas
    if current_user["role"] == "atendente":
        attendant_id = current_user["id"]
    
    conversations = sqlserver_manager.list_conversations(
        limit=per_page,
        offset=offset,
        status=status,
        priority=priority,
        attendant_id=attendant_id,
        date_from=date_from,
        date_to=date_to
    )
    
    total = sqlserver_manager.count_conversations(
        status=status,
        priority=priority,
        attendant_id=attendant_id,
        date_from=date_from,
        date_to=date_to
    )
    
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c["id"],
                client_id=c["client_id"],
                client_phone=c.get("client_phone", ""),
                client_name=c.get("client_name"),
                attendant_id=c.get("attendant_id"),
                attendant_name=c.get("attendant_name"),
                status=c["status"],
                priority=c.get("priority", "normal"),
                category=c.get("category"),
                subject=c.get("subject"),
                total_messages=c.get("total_messages", 0),
                rating=c.get("rating"),
                started_at=str(c.get("started_at", "")),
                last_message_at=str(c.get("last_message_at")) if c.get("last_message_at") else None,
                resolved_at=str(c.get("resolved_at")) if c.get("resolved_at") else None
            )
            for c in conversations
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get(
    "/stats",
    response_model=ConversationStats,
    summary="Estatísticas de conversas"
)
async def get_conversation_stats(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter estatísticas de conversas do dia.
    """
    stats = sqlserver_manager.get_conversation_stats()
    
    return ConversationStats(
        total_today=stats.get("total_today", 0),
        waiting=stats.get("waiting", 0),
        in_progress=stats.get("in_progress", 0),
        resolved_today=stats.get("resolved_today", 0),
        avg_response_time_minutes=stats.get("avg_response_time_minutes"),
        avg_resolution_time_minutes=stats.get("avg_resolution_time_minutes")
    )


@router.get(
    "/queue",
    summary="Fila de espera"
)
async def get_queue(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter conversas na fila de espera.
    """
    conversations = sqlserver_manager.get_waiting_conversations()
    
    return {
        "queue": [
            {
                "id": c["id"],
                "client_phone": c.get("client_phone"),
                "client_name": c.get("client_name"),
                "subject": c.get("subject"),
                "priority": c.get("priority", "normal"),
                "waiting_since": str(c.get("started_at", "")),
                "waiting_minutes": c.get("waiting_minutes", 0)
            }
            for c in conversations
        ],
        "total": len(conversations)
    }


@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar conversa"
)
async def create_conversation(
    request: Request,
    data: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Criar nova conversa/atendimento.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Obter ou criar cliente
    client_id = get_or_create_client(data.client_phone, data.client_name)
    
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar cliente"
        )
    
    # Criar conversa
    conversation = sqlserver_manager.create_conversation(
        client_id=client_id,
        subject=data.subject,
        category=data.category,
        priority=data.priority
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar conversa"
        )
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_CREATED,
        user_id=current_user["id"],
        action="create_conversation",
        resource_type="conversation",
        resource_id=str(conversation["id"]),
        ip_address=client_ip,
        status="success"
    )
    
    return ConversationResponse(
        id=conversation["id"],
        client_id=client_id,
        client_phone=data.client_phone,
        client_name=data.client_name,
        attendant_id=None,
        attendant_name=None,
        status="waiting",
        priority=data.priority,
        category=data.category,
        subject=data.subject,
        total_messages=0,
        rating=None,
        started_at=str(datetime.now()),
        last_message_at=None,
        resolved_at=None
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Obter conversa"
)
async def get_conversation(
    request: Request,
    conversation_id: int = Path(..., description="ID da conversa"),
    current_user: dict = Depends(get_current_user)
):
    """
    Obter detalhes de uma conversa.
    """
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Verificar permissão
    if (current_user["role"] == "atendente" and 
        conversation.get("attendant_id") != current_user["id"] and
        conversation.get("status") != "waiting"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para visualizar esta conversa"
        )
    
    return ConversationResponse(
        id=conversation["id"],
        client_id=conversation["client_id"],
        client_phone=conversation.get("client_phone", ""),
        client_name=conversation.get("client_name"),
        attendant_id=conversation.get("attendant_id"),
        attendant_name=conversation.get("attendant_name"),
        status=conversation["status"],
        priority=conversation.get("priority", "normal"),
        category=conversation.get("category"),
        subject=conversation.get("subject"),
        total_messages=conversation.get("total_messages", 0),
        rating=conversation.get("rating"),
        started_at=str(conversation.get("started_at", "")),
        last_message_at=str(conversation.get("last_message_at")) if conversation.get("last_message_at") else None,
        resolved_at=str(conversation.get("resolved_at")) if conversation.get("resolved_at") else None
    )


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Atualizar conversa"
)
async def update_conversation(
    request: Request,
    conversation_id: int,
    data: ConversationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Atualizar dados da conversa.
    """
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Atualizar
    update_fields = data.dict(exclude_unset=True)
    
    if update_fields:
        success = sqlserver_manager.update_conversation(
            conversation_id=conversation_id,
            **update_fields
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar conversa"
            )
    
    # Retornar atualizada
    updated = sqlserver_manager.get_conversation(conversation_id)
    
    return ConversationResponse(
        id=updated["id"],
        client_id=updated["client_id"],
        client_phone=updated.get("client_phone", ""),
        client_name=updated.get("client_name"),
        attendant_id=updated.get("attendant_id"),
        attendant_name=updated.get("attendant_name"),
        status=updated["status"],
        priority=updated.get("priority", "normal"),
        category=updated.get("category"),
        subject=updated.get("subject"),
        total_messages=updated.get("total_messages", 0),
        rating=updated.get("rating"),
        started_at=str(updated.get("started_at", "")),
        last_message_at=str(updated.get("last_message_at")) if updated.get("last_message_at") else None,
        resolved_at=str(updated.get("resolved_at")) if updated.get("resolved_at") else None
    )


@router.post(
    "/{conversation_id}/assign",
    summary="Assumir/Atribuir conversa"
)
async def assign_conversation(
    request: Request,
    conversation_id: int,
    attendant_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Assumir ou atribuir conversa a um atendente.
    
    - Sem attendant_id: assume para si mesmo
    - Com attendant_id: atribui para outro (requer supervisor/admin)
    """
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Se atribuindo para outro, verificar permissão
    target_attendant = attendant_id or current_user["id"]
    
    if attendant_id and attendant_id != current_user["id"]:
        if current_user["role"] == "atendente":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para atribuir conversas"
            )
    
    # Atribuir
    success = sqlserver_manager.assign_conversation(
        conversation_id=conversation_id,
        attendant_id=target_attendant
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atribuir conversa"
        )
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_UPDATED,
        user_id=current_user["id"],
        action="assign_conversation",
        resource_type="conversation",
        resource_id=str(conversation_id),
        ip_address=request.client.host if request.client else "unknown",
        status="success",
        details={"attendant_id": target_attendant}
    )
    
    return {"message": "Conversa atribuída com sucesso", "attendant_id": target_attendant}


@router.post(
    "/{conversation_id}/transfer",
    summary="Transferir conversa"
)
async def transfer_conversation(
    request: Request,
    conversation_id: int,
    target_attendant_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Transferir conversa para outro atendente.
    """
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Verificar se é o atendente atual ou supervisor
    if (conversation.get("attendant_id") != current_user["id"] and 
        current_user["role"] == "atendente"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o atendente atual pode transferir"
        )
    
    # Transferir
    success = sqlserver_manager.transfer_conversation(
        conversation_id=conversation_id,
        from_attendant_id=conversation.get("attendant_id"),
        to_attendant_id=target_attendant_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao transferir conversa"
        )
    
    return {
        "message": "Conversa transferida com sucesso",
        "from_attendant": conversation.get("attendant_id"),
        "to_attendant": target_attendant_id
    }


@router.post(
    "/{conversation_id}/close",
    summary="Encerrar conversa"
)
async def close_conversation(
    request: Request,
    conversation_id: int,
    data: ConversationClose,
    current_user: dict = Depends(get_current_user)
):
    """
    Encerrar uma conversa com avaliação opcional.
    """
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Verificar permissão
    if (conversation.get("attendant_id") != current_user["id"] and 
        current_user["role"] == "atendente"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para encerrar esta conversa"
        )
    
    # Encerrar
    success = sqlserver_manager.close_conversation(
        conversation_id=conversation_id,
        rating=data.rating,
        feedback=data.feedback,
        resolution_notes=data.resolution_notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao encerrar conversa"
        )
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_UPDATED,
        user_id=current_user["id"],
        action="close_conversation",
        resource_type="conversation",
        resource_id=str(conversation_id),
        ip_address=request.client.host if request.client else "unknown",
        status="success",
        details={"rating": data.rating}
    )
    
    return {
        "message": "Conversa encerrada com sucesso",
        "rating": data.rating
    }


@router.get(
    "/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="Listar mensagens"
)
async def list_messages(
    request: Request,
    conversation_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar mensagens de uma conversa.
    """
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    offset = (page - 1) * per_page
    messages = sqlserver_manager.list_messages(
        conversation_id=conversation_id,
        limit=per_page,
        offset=offset
    )
    
    return [
        MessageResponse(
            id=m["id"],
            conversation_id=conversation_id,
            sender_type=m["sender_type"],
            sender_id=m.get("sender_id"),
            content=m["content"],
            message_type=m.get("message_type", "text"),
            status=m.get("status", "sent"),
            is_from_me=m.get("is_from_me", False),
            created_at=str(m.get("created_at", ""))
        )
        for m in messages
    ]


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensagem"
)
async def send_message(
    request: Request,
    conversation_id: int,
    data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar mensagem em uma conversa.
    """
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Criar mensagem
    message = sqlserver_manager.create_message(
        conversation_id=conversation_id,
        sender_type="attendant",
        sender_id=current_user["id"],
        content=data.content,
        message_type=data.message_type,
        media_url=data.media_url
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao enviar mensagem"
        )
    
    return MessageResponse(
        id=message["id"],
        conversation_id=conversation_id,
        sender_type="attendant",
        sender_id=current_user["id"],
        content=data.content,
        message_type=data.message_type,
        status="sent",
        is_from_me=True,
        created_at=str(datetime.now())
    )
