"""
WhatsApp Send Endpoints V2
CIANET PROVEDOR - v3.0

Endpoints para envio de mensagens pelo atendente:
- Texto, imagem, documento, áudio
- Templates HSM
- Mensagens em massa
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Request, Depends, Query, UploadFile, File
from pydantic import BaseModel, Field

from app.core.auth_manager import get_current_user, require_permissions
from app.core.database import db_manager
from app.models.database import Usuario
from app.core.audit_logger import audit_logger, AuditEventTypes
from app.services.whatsapp_cloud_api import (
    whatsapp_client, 
    SendMessageRequest, 
    SendMessageResponse,
    MessageText,
    MessageTemplate,
    MessageImage,
    MessageDocument
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp/v2/send", tags=["WhatsApp Envio"])


# ============================================================================
# SCHEMAS
# ============================================================================

class SendTextRequest(BaseModel):
    """Enviar texto"""
    to: str = Field(..., description="Número do destinatário")
    message: str = Field(..., min_length=1, max_length=4096)
    conversation_id: Optional[int] = Field(None, description="ID da conversa (para salvar histórico)")


class SendTemplateRequest(BaseModel):
    """Enviar template HSM"""
    to: str
    template_name: str = Field(..., description="Nome do template aprovado")
    language: str = Field(default="pt_BR")
    header_params: Optional[List[str]] = None
    body_params: Optional[List[str]] = None
    button_params: Optional[List[Dict]] = None
    conversation_id: Optional[int] = None


class SendMediaRequest(BaseModel):
    """Enviar mídia"""
    to: str
    media_url: str = Field(..., description="URL pública da mídia")
    media_type: str = Field(..., description="image, document, audio, video")
    caption: Optional[str] = None
    filename: Optional[str] = None
    conversation_id: Optional[int] = None


class BulkSendRequest(BaseModel):
    """Envio em massa"""
    recipients: List[str] = Field(..., min_items=1, max_items=1000)
    template_name: str
    language: str = "pt_BR"
    body_params: Optional[List[str]] = None
    campaign_id: Optional[int] = None


class QuickReplyRequest(BaseModel):
    """Resposta rápida"""
    conversation_id: int
    quick_reply_id: int


# ============================================================================
# ENDPOINTS DE ENVIO
# ============================================================================

@router.post(
    "/text",
    response_model=SendMessageResponse,
    summary="Enviar texto"
)
async def send_text(
    request: Request,
    data: SendTextRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar mensagem de texto para um número.
    
    Se conversation_id for fornecido, salva no histórico.
    """
    # Enviar via API
    result = await whatsapp_client.send_text(
        to=data.to,
        text=data.message
    )
    
    # Salvar no histórico se tiver conversa
    if result.success and data.conversation_id:
        sqlserver_manager.create_message(
            conversation_id=data.conversation_id,
            sender_type="attendant",
            sender_id=int(current_user["id"]),
            content=data.message,
            message_type="text"
        )
    
    # Audit log
    await audit_logger.log(
        event_type=AuditEventTypes.MESSAGE_SENT,
        user_id=current_user["id"],
        action="send_whatsapp_text",
        resource_type="message",
        resource_id=result.message_id,
        ip_address=request.client.host if request.client else "unknown",
        status="success" if result.success else "failed",
        details={"to": data.to}
    )
    
    return result


@router.post(
    "/template",
    response_model=SendMessageResponse,
    summary="Enviar template HSM"
)
async def send_template(
    request: Request,
    data: SendTemplateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar mensagem de template HSM.
    
    Templates são usados para:
    - Iniciar conversa (janela de 24h)
    - Notificações proativas
    - Mensagens de marketing (se aprovado)
    """
    result = await whatsapp_client.send_template(
        to=data.to,
        template_name=data.template_name,
        language=data.language,
        header_params=data.header_params,
        body_params=data.body_params,
        button_params=data.button_params
    )
    
    # Salvar no histórico
    if result.success and data.conversation_id:
        template_content = f"[TEMPLATE: {data.template_name}] " + " | ".join(data.body_params or [])
        
        sqlserver_manager.create_message(
            conversation_id=data.conversation_id,
            sender_type="attendant",
            sender_id=int(current_user["id"]),
            content=template_content,
            message_type="template"
        )
    
    return result


@router.post(
    "/media",
    response_model=SendMessageResponse,
    summary="Enviar mídia"
)
async def send_media(
    request: Request,
    data: SendMediaRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar imagem, documento, áudio ou vídeo.
    
    A URL deve ser pública e acessível pelo WhatsApp.
    """
    if data.media_type == "image":
        result = await whatsapp_client.send_image(
            to=data.to,
            image_url=data.media_url,
            caption=data.caption
        )
    
    elif data.media_type == "document":
        result = await whatsapp_client.send_document(
            to=data.to,
            document_url=data.media_url,
            filename=data.filename or "documento",
            caption=data.caption
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de mídia não suportado: {data.media_type}"
        )
    
    # Salvar no histórico
    if result.success and data.conversation_id:
        content = f"[{data.media_type.upper()}] {data.caption or data.filename or ''}"
        
        sqlserver_manager.create_message(
            conversation_id=data.conversation_id,
            sender_type="attendant",
            sender_id=int(current_user["id"]),
            content=content,
            message_type=data.media_type
        )
    
    return result


@router.post(
    "/conversation/{conversation_id}/message",
    response_model=SendMessageResponse,
    summary="Enviar mensagem em conversa"
)
async def send_conversation_message(
    request: Request,
    conversation_id: int,
    data: SendTextRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar mensagem em uma conversa existente.
    Busca automaticamente o número do cliente.
    """
    # Buscar conversa
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Verificar permissão
    if (conversation.get("attendant_id") != int(current_user["id"]) and 
        current_user["role"] == "atendente"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para esta conversa"
        )
    
    # Obter número do cliente
    client_phone = conversation.get("client_phone")
    
    if not client_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número do cliente não encontrado"
        )
    
    # Enviar
    result = await whatsapp_client.send_text(
        to=client_phone,
        text=data.message
    )
    
    # Salvar no histórico
    if result.success:
        sqlserver_manager.create_message(
            conversation_id=conversation_id,
            sender_type="attendant",
            sender_id=int(current_user["id"]),
            content=data.message,
            message_type="text"
        )
    
    return result


# ============================================================================
# ENVIO EM MASSA
# ============================================================================

@router.post(
    "/bulk",
    summary="Envio em massa",
    dependencies=[Depends(require_permissions(["whatsapp:bulk_send"]))]
)
async def send_bulk(
    request: Request,
    data: BulkSendRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar template para múltiplos destinatários.
    
    Requer permissão whatsapp:bulk_send.
    Máximo de 1000 destinatários por requisição.
    """
    results = {
        "total": len(data.recipients),
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    for recipient in data.recipients:
        result = await whatsapp_client.send_template(
            to=recipient,
            template_name=data.template_name,
            language=data.language,
            body_params=data.body_params
        )
        
        if result.success:
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({
                "to": recipient,
                "error": result.error
            })
    
    # Audit log
    await audit_logger.log(
        event_type=AuditEventTypes.BULK_MESSAGE_SENT,
        user_id=current_user["id"],
        action="bulk_send_whatsapp",
        resource_type="campaign",
        resource_id=str(data.campaign_id) if data.campaign_id else None,
        ip_address=request.client.host if request.client else "unknown",
        status="success" if results["failed"] == 0 else "partial",
        details=results
    )
    
    return results


# ============================================================================
# RESPOSTAS RÁPIDAS
# ============================================================================

@router.post(
    "/quick-reply",
    response_model=SendMessageResponse,
    summary="Enviar resposta rápida"
)
async def send_quick_reply(
    request: Request,
    data: QuickReplyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar resposta rápida pré-configurada.
    """
    # Buscar conversa
    conversation = sqlserver_manager.get_conversation(data.conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Buscar resposta rápida
    quick_reply = get_quick_reply(data.quick_reply_id)
    
    if not quick_reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resposta rápida não encontrada"
        )
    
    # Enviar
    client_phone = conversation.get("client_phone")
    message_text = quick_reply.get("content", "")
    
    result = await whatsapp_client.send_text(
        to=client_phone,
        text=message_text
    )
    
    # Salvar no histórico
    if result.success:
        sqlserver_manager.create_message(
            conversation_id=data.conversation_id,
            sender_type="attendant",
            sender_id=int(current_user["id"]),
            content=message_text,
            message_type="text"
        )
    
    return result


# ============================================================================
# TEMPLATES
# ============================================================================

@router.get(
    "/templates",
    summary="Listar templates disponíveis"
)
async def list_templates(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Listar templates HSM aprovados.
    """
    templates = await whatsapp_client.get_templates()
    
    return {
        "templates": [
            {
                "name": t.name,
                "status": t.status,
                "category": t.category,
                "language": t.language,
                "components": t.components
            }
            for t in templates
            if t.status == "APPROVED"
        ]
    }


@router.get(
    "/health",
    summary="Status da conexão WhatsApp"
)
async def whatsapp_health(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Verificar status da conexão com WhatsApp Business API.
    """
    return await whatsapp_client.health_check()


# ============================================================================
# HELPERS
# ============================================================================

def get_quick_reply(reply_id: int) -> Optional[Dict]:
    """Buscar resposta rápida por ID"""
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, category, shortcut
                FROM quick_replies
                WHERE id = ? AND is_active = 1
            """, (reply_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "id": row.id,
                    "title": row.title,
                    "content": row.content,
                    "category": row.category,
                    "shortcut": row.shortcut
                }
            
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar quick reply: {e}")
        return None
