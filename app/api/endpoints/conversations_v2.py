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
from app.core.database import db_manager
from app.models.database import ClienteWhatsApp, Conversa, Usuario, ConversationState, Mensagem
from sqlalchemy import select, and_, or_
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

# Helper assíncrono para buscar ou criar cliente
async def get_or_create_client_async(phone: str, name: Optional[str] = None) -> str:
    async with db_manager.session_factory() as session:
        result = await session.execute(select(ClienteWhatsApp).where(ClienteWhatsApp.telefone == phone))
        client = result.scalar_one_or_none()
        if client:
            return str(client.id)
        # Criar novo cliente
        new_client = ClienteWhatsApp(
            client_id=f"cli_{phone}",
            nome=name or f"Cliente {phone[-4:]}",
            telefone=phone,
            status=ConversationState.AUTOMACAO
        )
        session.add(new_client)
        await session.commit()
        await session.refresh(new_client)
        return str(new_client.id)

# Helper assíncrono para listar conversas
async def list_conversations_async(limit, offset, status, priority, attendant_id, date_from, date_to):
    async with db_manager.session_factory() as session:
        query = select(Conversa)
        filters = []
        if status:
            filters.append(Conversa.estado == status)
        if priority:
            filters.append(Conversa.prioridade == priority)
        if attendant_id:
            filters.append(Conversa.atendente_id == attendant_id)
        if date_from:
            filters.append(Conversa.created_at >= date_from)
        if date_to:
            filters.append(Conversa.created_at <= date_to)
        if filters:
            query = query.where(and_(*filters))
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

# Helpers assíncronos para conversas e mensagens
async def get_conversation_stats_async():
    async with db_manager.session_factory() as session:
        total_today = await session.execute(select(Conversa).where(Conversa.created_at >= datetime.now().date()))
        waiting = await session.execute(select(Conversa).where(Conversa.estado == ConversationState.ESPERA))
        in_progress = await session.execute(select(Conversa).where(Conversa.estado == ConversationState.ATENDIMENTO))
        resolved_today = await session.execute(select(Conversa).where(Conversa.estado == ConversationState.ENCERRADO, Conversa.created_at >= datetime.now().date()))
        return {
            "total_today": total_today.rowcount,
            "waiting": waiting.rowcount,
            "in_progress": in_progress.rowcount,
            "resolved_today": resolved_today.rowcount,
            "avg_response_time_minutes": None,
            "avg_resolution_time_minutes": None
        }

async def get_waiting_conversations_async():
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Conversa).where(Conversa.estado == ConversationState.ESPERA))
        return result.scalars().all()

async def create_conversation_async(cliente_id, chat_id, estado, atendente_id=None, prioridade=0, tags=None, conversation_metadata=None):
    async with db_manager.session_factory() as session:
        conversa = Conversa(
            cliente_id=cliente_id,
            chat_id=chat_id,
            estado=estado,
            atendente_id=atendente_id,
            prioridade=prioridade,
            tags=tags,
            conversation_metadata=conversation_metadata
        )
        session.add(conversa)
        await session.commit()
        await session.refresh(conversa)
        return conversa

async def get_conversation_async(conversation_id):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Conversa).where(Conversa.id == conversation_id))
        return result.scalar_one_or_none()

async def update_conversation_async(conversation_id, **kwargs):
    async with db_manager.session_factory() as session:
        conversa = await get_conversation_async(conversation_id)
        if not conversa:
            return None
        for key, value in kwargs.items():
            setattr(conversa, key, value)
        await session.commit()
        await session.refresh(conversa)
        return conversa

async def assign_conversation_async(conversation_id, atendente_id):
    return await update_conversation_async(conversation_id, atendente_id=atendente_id)

async def transfer_conversation_async(conversation_id, new_atendente_id):
    return await update_conversation_async(conversation_id, atendente_id=new_atendente_id)

async def close_conversation_async(conversation_id, encerrada_em=None):
    return await update_conversation_async(conversation_id, estado=ConversationState.ENCERRADO, encerrada_em=encerrada_em or datetime.now())

async def list_messages_async(conversa_id):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Mensagem).where(Mensagem.conversa_id == conversa_id))
        return result.scalars().all()

async def create_message_async(conversa_id, remetente_tipo, remetente_id, conteudo, tipo_mensagem, arquivo_url=None, message_metadata=None):
    async with db_manager.session_factory() as session:
        mensagem = Mensagem(
            conversa_id=conversa_id,
            remetente_tipo=remetente_tipo,
            remetente_id=remetente_id,
            conteudo=conteudo,
            tipo_mensagem=tipo_mensagem,
            arquivo_url=arquivo_url,
            message_metadata=message_metadata
        )
        session.add(mensagem)
        await session.commit()
        await session.refresh(mensagem)
        return mensagem


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
    attendant_id: Optional[str] = Query(None, description="Filtrar por atendente"),
    date_from: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    offset = (page - 1) * per_page
    if current_user["role"] == "atendente":
        attendant_id = current_user["id"]
    conversations = await list_conversations_async(
        limit=per_page,
        offset=offset,
        status=status,
        priority=priority,
        attendant_id=attendant_id,
        date_from=date_from,
        date_to=date_to
    )
    # TODO: Implementar count_conversations_async se necessário
    total = len(conversations)
    return ConversationListResponse(
        conversations=conversations,
        total=total,
        page=page,
        pages=(total // per_page) + 1
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
    stats = await get_conversation_stats_async()
    
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
    conversations = await get_waiting_conversations_async()
    
    return {
        "queue": [
            {
                "id": c.id,
                "client_phone": c.cliente_id,
                "client_name": c.cliente_id,
                "subject": c.tags,
                "priority": c.prioridade,
                "waiting_since": str(c.created_at),
                "waiting_minutes": (datetime.now() - c.created_at).total_seconds() // 60
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
    client_id = await get_or_create_client_async(data.client_phone, data.client_name)
    
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar cliente"
        )
    
    # Criar conversa
    conversation = await create_conversation_async(
        cliente_id=client_id,
        chat_id=None,
        estado=ConversationState.ESPERA,
        prioridade=data.priority,
        tags=data.category,
        conversation_metadata={"subject": data.subject}
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
        resource_id=str(conversation.id),
        ip_address=client_ip,
        status="success"
    )
    
    return ConversationResponse(
        id=conversation.id,
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
    conversation = await get_conversation_async(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Verificar permissão
    if (current_user["role"] == "atendente" and 
        conversation.atendente_id != current_user["id"] and
        conversation.estado != ConversationState.ESPERA):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para visualizar esta conversa"
        )
    
    return ConversationResponse(
        id=conversation.id,
        client_id=conversation.cliente_id,
        client_phone=conversation.cliente_id,
        client_name=conversation.cliente_id,
        attendant_id=conversation.atendente_id,
        attendant_name=None,
        status=conversation.estado,
        priority=conversation.prioridade,
        category=conversation.tags,
        subject=conversation.conversation_metadata.get("subject"),
        total_messages=0,
        rating=None,
        started_at=str(conversation.created_at),
        last_message_at=None,
        resolved_at=None
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
    conversation = await get_conversation_async(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Atualizar
    update_fields = data.dict(exclude_unset=True)
    
    if update_fields:
        updated_conversation = await update_conversation_async(
            conversation_id=conversation_id,
            **update_fields
        )
        
        if not updated_conversation:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar conversa"
            )
    
    # Retornar atualizada
    updated = await get_conversation_async(conversation_id)
    
    return ConversationResponse(
        id=updated.id,
        client_id=updated.cliente_id,
        client_phone=updated.cliente_id,
        client_name=updated.cliente_id,
        attendant_id=updated.atendente_id,
        attendant_name=None,
        status=updated.estado,
        priority=updated.prioridade,
        category=updated.tags,
        subject=updated.conversation_metadata.get("subject"),
        total_messages=0,
        rating=None,
        started_at=str(updated.created_at),
        last_message_at=None,
        resolved_at=None
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
    conversation = await get_conversation_async(conversation_id)
    
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
    updated_conversation = await assign_conversation_async(
        conversation_id=conversation_id,
        atendente_id=target_attendant
    )
    
    if not updated_conversation:
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
    conversation = await get_conversation_async(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Verificar se é o atendente atual ou supervisor
    if (conversation.atendente_id != current_user["id"] and 
        current_user["role"] == "atendente"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o atendente atual pode transferir"
        )
    
    # Transferir
    updated_conversation = await transfer_conversation_async(
        conversation_id=conversation_id,
        new_atendente_id=target_attendant_id
    )
    
    if not updated_conversation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao transferir conversa"
        )
    
    return {
        "message": "Conversa transferida com sucesso",
        "from_attendant": conversation.atendente_id,
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
    conversation = await get_conversation_async(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Verificar permissão
    if (conversation.atendente_id != current_user["id"] and 
        current_user["role"] == "atendente"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para encerrar esta conversa"
        )
    
    # Encerrar
    updated_conversation = await close_conversation_async(
        conversation_id=conversation_id,
        encerrada_em=datetime.now()
    )
    
    if not updated_conversation:
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
    conversation = await get_conversation_async(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    offset = (page - 1) * per_page
    messages = await list_messages_async(conversation_id)
    
    return [
        MessageResponse(
            id=m.id,
            conversation_id=conversation_id,
            sender_type=m.remetente_tipo,
            sender_id=m.remetente_id,
            content=m.conteudo,
            message_type=m.tipo_mensagem,
            status="sent",
            is_from_me=m.remetente_id == current_user["id"],
            created_at=str(m.created_at)
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
    conversation = await get_conversation_async(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Criar mensagem
    message = await create_message_async(
        conversa_id=conversation_id,
        remetente_tipo="attendant",
        remetente_id=current_user["id"],
        conteudo=data.content,
        tipo_mensagem=data.message_type,
        arquivo_url=data.media_url
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao enviar mensagem"
        )
    
    return MessageResponse(
        id=message.id,
        conversation_id=conversation_id,
        sender_type="attendant",
        sender_id=current_user["id"],
        content=data.content,
        message_type=message.tipo_mensagem,
        status="sent",
        is_from_me=True,
        created_at=str(datetime.now())
    )
