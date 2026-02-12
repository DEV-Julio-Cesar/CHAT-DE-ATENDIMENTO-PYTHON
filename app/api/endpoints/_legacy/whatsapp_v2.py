"""
WhatsApp Webhook Endpoints V2
CIANET PROVEDOR - v3.0

Endpoints para:
- Receber mensagens via webhook do Meta
- Verificar webhook
- Processar callbacks de status
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status, Request, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse

from app.services.whatsapp_cloud_api import whatsapp_client, WebhookMessage
from app.core.database import db_manager
from app.models.database import ClienteWhatsApp, Conversa, Mensagem, ConversationState, SenderType, MessageType
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp/v2", tags=["WhatsApp Cloud API"])


# ============================================================================
# WEBHOOK VERIFICATION
# ============================================================================

@router.get(
    "/webhook",
    response_class=PlainTextResponse,
    summary="Verificar Webhook"
)
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge")
):
    """
    Endpoint de verificação do webhook do Meta.
    
    O Meta envia uma requisição GET para verificar o webhook.
    Devemos retornar o hub.challenge se o token estiver correto.
    """
    challenge = whatsapp_client.verify_webhook(
        mode=hub_mode,
        token=hub_verify_token,
        challenge=hub_challenge
    )
    
    if challenge:
        return challenge
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Token de verificação inválido"
    )


# ============================================================================
# WEBHOOK RECEIVER
# ============================================================================

@router.post(
    "/webhook",
    summary="Receber Webhook"
)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receber notificações do WhatsApp.
    
    Tipos de notificação:
    - messages: Mensagens recebidas
    - statuses: Status de entrega (sent, delivered, read)
    """
    try:
        # Verificar assinatura (X-Hub-Signature-256)
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = await request.body()
        
        if not whatsapp_client.verify_signature(body, signature):
            logger.warning("Assinatura de webhook inválida")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assinatura inválida"
            )
        
        # Parsear payload
        data = await request.json()
        
        # Log do webhook recebido
        logger.info(f"Webhook recebido: {data.get('object', 'unknown')}")
        
        # Processar mensagens
        messages = whatsapp_client.parse_webhook(data)
        
        for msg in messages:
            # Processar em background para responder rápido ao Meta
            background_tasks.add_task(process_incoming_message, msg)
        
        # Processar status updates
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                if "statuses" in value:
                    for status_update in value.get("statuses", []):
                        background_tasks.add_task(
                            process_status_update,
                            status_update
                        )
        
        # Sempre retornar 200 para o Meta
        return {"status": "received"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        # Ainda assim retornar 200 para não receber retries
        return {"status": "error", "message": str(e)}


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def process_incoming_message(msg: WebhookMessage):
    """
    Processar mensagem recebida.
    
    1. Buscar/criar cliente
    2. Buscar/criar conversa ativa
    3. Salvar mensagem
    4. Notificar via WebSocket
    5. Acionar chatbot se configurado
    """
    try:
        logger.info(f"Processando mensagem de {msg.from_number}: {msg.type}")
        client = await get_client_by_phone_async(msg.from_number)
        if not client:
            client = await create_client_async(msg.from_number, f"Cliente {msg.from_number[-4:]}")
        if not client:
            logger.error(f"Erro ao criar cliente: {msg.from_number}")
            return
        client_id = str(client.id)
        conversation = await get_active_conversation_async(client_id)
        if not conversation:
            conversation = await create_conversation_async(client_id, "Atendimento WhatsApp", "whatsapp", "normal")
        if not conversation:
            logger.error(f"Erro ao criar conversa para cliente: {client_id}")
            return
        conversation_id = str(conversation.id)
        content = extract_message_content(msg)
        await create_message_async(conversation_id, SenderType.CLIENTE, msg.from_number, content, MessageType.TEXTO)
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}


async def process_status_update(status_data: Dict[str, Any]):
    """
    Processar atualização de status de mensagem.
    
    Status:
    - sent: Enviada para o WhatsApp
    - delivered: Entregue ao dispositivo
    - read: Lida pelo destinatário
    - failed: Falha no envio
    """
    try:
        message_id = status_data.get("id")
        status_value = status_data.get("status")
        recipient = status_data.get("recipient_id")
        timestamp = status_data.get("timestamp")
        
        logger.info(f"Status update: {message_id} -> {status_value}")
        
        # Atualizar status no banco
        # TODO: Implementar update_message_status
        
        # Se falhou, logar erro
        if status_value == "failed":
            errors = status_data.get("errors", [])
            for error in errors:
                logger.error(f"Falha no envio: {error.get('message')} - {error.get('error_data')}")
    
    except Exception as e:
        logger.error(f"Erro ao processar status: {e}")


# ============================================================================
# HELPERS
# ============================================================================

async def get_client_by_phone_async(phone: str):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(ClienteWhatsApp).where(ClienteWhatsApp.telefone == phone))
        return result.scalar_one_or_none()

async def create_client_async(phone: str, name: str):
    async with db_manager.session_factory() as session:
        new_client = ClienteWhatsApp(
            client_id=f"cli_{phone}",
            nome=name,
            telefone=phone,
            status=ConversationState.AUTOMACAO
        )
        session.add(new_client)
        await session.commit()
        await session.refresh(new_client)
        return new_client

async def get_active_conversation_async(client_id: str):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Conversa).where(Conversa.cliente_id == client_id, Conversa.estado.in_([ConversationState.ESPERA, ConversationState.ATENDIMENTO])))
        return result.scalar_one_or_none()

async def create_conversation_async(client_id: str, subject: str, category: str, priority: str):
    async with db_manager.session_factory() as session:
        conversa = Conversa(
            cliente_id=client_id,
            chat_id=f"chat_{client_id}_{datetime.now().timestamp()}",
            estado=ConversationState.ESPERA,
            prioridade=priority,
            conversation_metadata={"subject": subject, "category": category}
        )
        session.add(conversa)
        await session.commit()
        await session.refresh(conversa)
        return conversa

async def create_message_async(conversation_id: str, sender_type: str, sender_id: str, content: str, message_type: str):
    async with db_manager.session_factory() as session:
        mensagem = Mensagem(
            conversa_id=conversation_id,
            remetente_tipo=sender_type,
            remetente_id=sender_id,
            conteudo=content,
            tipo_mensagem=message_type
        )
        session.add(mensagem)
        await session.commit()
        await session.refresh(mensagem)
        return mensagem

def extract_message_content(msg: WebhookMessage) -> str:
    """Extrair conteúdo textual da mensagem"""
    content = msg.content
    
    if msg.type == "text":
        return content.get("text", "")
    
    elif msg.type == "button":
        return content.get("text", "")
    
    elif msg.type == "interactive":
        return content.get("button_text") or content.get("list_title", "")
    
    elif msg.type == "image":
        caption = content.get("caption", "")
        return f"[IMAGEM] {caption}" if caption else "[IMAGEM]"
    
    elif msg.type == "document":
        filename = content.get("filename", "documento")
        caption = content.get("caption", "")
        return f"[DOCUMENTO: {filename}] {caption}" if caption else f"[DOCUMENTO: {filename}]"
    
    elif msg.type == "audio":
        return "[ÁUDIO]" if not content.get("voice") else "[MENSAGEM DE VOZ]"
    
    elif msg.type == "location":
        name = content.get("name", "")
        address = content.get("address", "")
        return f"[LOCALIZAÇÃO] {name} - {address}" if name else "[LOCALIZAÇÃO]"
    
    return f"[{msg.type.upper()}]"
