"""
WhatsApp Webhook Endpoints
Endpoints para receber eventos da Meta Business API

Documentação:
https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
"""

from fastapi import APIRouter, Request, Response, HTTPException, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import Optional, Dict, Any
import structlog
import json
from datetime import datetime, timezone

from app.services.whatsapp_enterprise import whatsapp_api, WebhookEvent, WebhookEventType
from app.services.chatbot_ai import chatbot_ai
from app.core.redis_client import redis_manager
from app.websocket.main import manager as ws_manager, WebSocketMessage, EventType

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default="")
) -> Response:
    """
    Verificação do webhook pela Meta
    
    A Meta envia um GET request para verificar o webhook durante a configuração.
    Você deve responder com o hub.challenge se o token for válido.
    """
    logger.info(
        "Webhook verification request",
        mode=hub_mode,
        has_token=bool(hub_verify_token),
        has_challenge=bool(hub_challenge)
    )
    
    result = whatsapp_api.verify_webhook(
        mode=hub_mode,
        token=hub_verify_token,
        challenge=hub_challenge
    )
    
    if result:
        return PlainTextResponse(content=result, status_code=200)
    else:
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receber eventos do webhook da Meta
    
    A Meta envia um POST request com eventos de mensagens e status.
    Deve retornar 200 rapidamente e processar em background.
    """
    # Verificar assinatura
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    
    if not whatsapp_api.verify_signature(body, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    logger.info("Webhook received", object=payload.get("object"))
    
    # Processar em background para responder rápido
    background_tasks.add_task(process_webhook_events, payload)
    
    # Retornar 200 imediatamente (requisito da Meta)
    return Response(status_code=200)


async def process_webhook_events(payload: Dict[str, Any]):
    """Processar eventos do webhook em background"""
    try:
        events = await whatsapp_api.process_webhook(payload)
        
        for event in events:
            if event.event_type == WebhookEventType.MESSAGE:
                await handle_incoming_message(event)
            elif event.event_type == WebhookEventType.STATUS:
                await handle_status_update(event)
            elif event.event_type == WebhookEventType.ERROR:
                await handle_error_event(event)
        
        logger.info(f"Processed {len(events)} webhook events")
        
    except Exception as e:
        logger.error("Error processing webhook events", error=str(e))


async def handle_incoming_message(event: WebhookEvent):
    """Processar mensagem recebida"""
    data = event.data
    from_number = data.get("from", "")
    contact_name = data.get("contact_name", "")
    msg_type = data.get("type", "text")
    content = data.get("content", {})
    message_id = data.get("message_id", "")
    
    logger.info(
        "Incoming WhatsApp message",
        from_number=from_number[-4:] + "****",  # Mascarar número
        contact_name=contact_name,
        type=msg_type
    )
    
    # Criar ou obter conversa
    conversation_id = f"wa_{from_number}"
    
    # Notificar via WebSocket se houver atendentes conectados
    if ws_manager.available_agents:
        from app.websocket.main import UserRole
        await ws_manager.broadcast_to_role(
            role=UserRole.ATENDENTE,
            message=WebSocketMessage(
                event=EventType.MESSAGE,
                data={
                    "source": "whatsapp",
                    "conversation_id": conversation_id,
                    "from": from_number,
                    "contact_name": contact_name,
                    "type": msg_type,
                    "content": content,
                    "timestamp": event.timestamp.isoformat()
                }
            )
        )
    
    # Se for mensagem de texto, processar com chatbot
    if msg_type == "text":
        text_content = content.get("body", "")
        
        # Verificar se há atendente atribuído
        agent_assigned = await redis_manager.get(f"wa:agent:{from_number}")
        
        if not agent_assigned:
            # Processar com chatbot AI
            await process_with_chatbot(
                from_number=from_number,
                contact_name=contact_name,
                message=text_content,
                conversation_id=conversation_id,
                reply_to=message_id
            )
        else:
            # Encaminhar para atendente via WebSocket
            await forward_to_agent(
                agent_id=agent_assigned,
                from_number=from_number,
                contact_name=contact_name,
                message=text_content,
                conversation_id=conversation_id
            )
    
    elif msg_type == "interactive":
        # Resposta de botão ou lista
        button_id = content.get("button_id") or content.get("list_id")
        button_title = content.get("button_title") or content.get("list_title")
        
        logger.info(
            "Interactive response received",
            button_id=button_id,
            button_title=button_title
        )
        
        # Processar resposta interativa
        await process_interactive_response(
            from_number=from_number,
            button_id=button_id,
            button_title=button_title,
            conversation_id=conversation_id
        )
    
    elif msg_type in ["image", "document", "audio", "video"]:
        # Notificar sobre mídia recebida
        await whatsapp_api.send_text_message(
            to=from_number,
            text="Recebi seu arquivo! Um atendente irá analisá-lo em breve. 📎",
            reply_to=message_id
        )
        
        # Adicionar à fila para atendente
        await add_to_human_queue(
            from_number=from_number,
            contact_name=contact_name,
            reason="Mídia recebida",
            conversation_id=conversation_id
        )
    
    elif msg_type == "location":
        # Processar localização
        lat = content.get("latitude")
        lng = content.get("longitude")
        
        await whatsapp_api.send_text_message(
            to=from_number,
            text=f"Recebi sua localização! 📍\nVou verificar a cobertura na sua região.",
            reply_to=message_id
        )
    
    # Cachear mensagem no Redis
    await cache_message(
        conversation_id=conversation_id,
        message={
            "id": message_id,
            "from": "customer",
            "type": msg_type,
            "content": content,
            "timestamp": event.timestamp.isoformat()
        }
    )


async def process_with_chatbot(
    from_number: str,
    contact_name: str,
    message: str,
    conversation_id: str,
    reply_to: Optional[str] = None
):
    """Processar mensagem com chatbot AI"""
    try:
        # Gerar resposta do chatbot
        cliente_info = {
            "id": from_number,
            "nome": contact_name,
            "telefone": from_number
        }
        
        response = await chatbot_ai.generate_response(
            conversation_id=conversation_id,
            user_message=message,
            cliente_info=cliente_info
        )
        
        # Verificar se deve escalar para humano
        if response.should_escalate:
            # Enviar mensagem de transição
            await whatsapp_api.send_text_message(
                to=from_number,
                text=response.message,
                reply_to=reply_to
            )
            
            # Adicionar à fila de atendimento humano
            await add_to_human_queue(
                from_number=from_number,
                contact_name=contact_name,
                reason=response.escalation_reason,
                conversation_id=conversation_id
            )
        else:
            # Enviar resposta do chatbot
            if response.quick_replies:
                # Usar botões se houver quick replies
                buttons = [
                    {"id": f"btn_{i}", "title": reply[:20]}
                    for i, reply in enumerate(response.quick_replies[:3])
                ]
                
                await whatsapp_api.send_button_message(
                    to=from_number,
                    body_text=response.message,
                    buttons=buttons,
                    footer_text="🤖 Assistente Virtual"
                )
            else:
                # Mensagem de texto simples
                await whatsapp_api.send_text_message(
                    to=from_number,
                    text=response.message,
                    reply_to=reply_to
                )
        
        # Cachear resposta
        await cache_message(
            conversation_id=conversation_id,
            message={
                "id": f"bot_{datetime.now(timezone.utc).timestamp()}",
                "from": "bot",
                "type": "text",
                "content": {"body": response.message},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "intent": response.intent.value,
                    "sentiment": response.sentiment.value,
                    "confidence": response.confidence
                }
            }
        )
        
        logger.info(
            "Chatbot response sent",
            to=from_number[-4:] + "****",
            intent=response.intent.value,
            escalated=response.should_escalate
        )
        
    except Exception as e:
        logger.error("Error processing with chatbot", error=str(e))
        
        # Mensagem de fallback
        await whatsapp_api.send_text_message(
            to=from_number,
            text="Desculpe, tive um problema técnico. Vou transferir você para um atendente humano.",
            reply_to=reply_to
        )
        
        await add_to_human_queue(
            from_number=from_number,
            contact_name=contact_name,
            reason="Erro no chatbot",
            conversation_id=conversation_id
        )


async def process_interactive_response(
    from_number: str,
    button_id: str,
    button_title: str,
    conversation_id: str
):
    """Processar resposta de botão/lista"""
    # Mapear botões para ações
    button_actions = {
        "btn_0": lambda: chatbot_ai.generate_response(conversation_id, button_title, {}),
        "btn_1": lambda: chatbot_ai.generate_response(conversation_id, button_title, {}),
        "btn_2": lambda: chatbot_ai.generate_response(conversation_id, button_title, {}),
        "talk_human": lambda: add_to_human_queue(from_number, "", "Solicitado pelo cliente", conversation_id),
        "see_invoice": lambda: handle_invoice_request(from_number),
        "technical_support": lambda: handle_technical_support(from_number, conversation_id),
    }
    
    action = button_actions.get(button_id)
    
    if action:
        result = await action()
        
        if hasattr(result, 'message'):
            # É uma resposta do chatbot
            await whatsapp_api.send_text_message(
                to=from_number,
                text=result.message
            )
    else:
        # Tratar como nova mensagem
        await process_with_chatbot(
            from_number=from_number,
            contact_name="",
            message=button_title,
            conversation_id=conversation_id
        )


async def forward_to_agent(
    agent_id: str,
    from_number: str,
    contact_name: str,
    message: str,
    conversation_id: str
):
    """Encaminhar mensagem para atendente via WebSocket"""
    await ws_manager.send_personal(
        user_id=agent_id,
        message=WebSocketMessage(
            event=EventType.MESSAGE,
            data={
                "source": "whatsapp",
                "conversation_id": conversation_id,
                "from": from_number,
                "contact_name": contact_name,
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    )


async def add_to_human_queue(
    from_number: str,
    contact_name: str,
    reason: str,
    conversation_id: str
):
    """Adicionar à fila de atendimento humano"""
    # Salvar no Redis
    queue_item = {
        "from_number": from_number,
        "contact_name": contact_name,
        "reason": reason,
        "conversation_id": conversation_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await redis_manager.rpush("whatsapp:queue", json.dumps(queue_item))
    
    # Obter posição na fila
    queue_length = await redis_manager.llen("whatsapp:queue")
    
    # Notificar atendentes via WebSocket
    await ws_manager.broadcast_to_role(
        role=None,  # Será filtrado no broadcast
        message=WebSocketMessage(
            event=EventType.QUEUE_UPDATE,
            data={
                "source": "whatsapp",
                "queue_size": queue_length,
                "new_item": queue_item
            }
        )
    )
    
    # Informar cliente sobre a fila
    await whatsapp_api.send_text_message(
        to=from_number,
        text=f"Você está na fila de atendimento. Posição: {queue_length}\n"
             f"Tempo estimado de espera: {queue_length * 3}-{queue_length * 5} minutos.\n"
             f"Um atendente entrará em contato em breve! 🙋‍♂️"
    )
    
    logger.info(
        "Added to human queue",
        conversation_id=conversation_id,
        position=queue_length,
        reason=reason
    )


async def handle_status_update(event: WebhookEvent):
    """Processar atualização de status de mensagem"""
    data = event.data
    message_id = data.get("message_id", "")
    status = data.get("status", "")
    recipient = data.get("recipient", "")
    
    logger.debug(
        "Message status update",
        message_id=message_id[:10] + "...",
        status=status
    )
    
    # Atualizar status no Redis
    await redis_manager.set(
        f"wa:msg_status:{message_id}",
        json.dumps({
            "status": status,
            "timestamp": event.timestamp.isoformat()
        }),
        ex=86400  # 24h
    )
    
    # Notificar via WebSocket se houver atendente na conversa
    conversation_id = f"wa_{recipient}"
    await ws_manager.broadcast_to_room(
        room_id=conversation_id,
        message=WebSocketMessage(
            event=EventType.MESSAGE_DELIVERED if status == "delivered" else EventType.MESSAGE_READ,
            data={
                "message_id": message_id,
                "status": status,
                "timestamp": event.timestamp.isoformat()
            }
        )
    )


async def handle_error_event(event: WebhookEvent):
    """Processar evento de erro"""
    logger.error(
        "WhatsApp error event",
        data=event.data,
        timestamp=event.timestamp.isoformat()
    )


async def cache_message(conversation_id: str, message: Dict[str, Any]):
    """Cachear mensagem no Redis"""
    key = f"wa:messages:{conversation_id}"
    await redis_manager.rpush(key, json.dumps(message))
    await redis_manager.client.expire(key, 86400 * 7)  # 7 dias


async def handle_invoice_request(from_number: str):
    """Processar solicitação de fatura"""
    # TODO: Integrar com sistema de billing
    await whatsapp_api.send_text_message(
        to=from_number,
        text="Estou buscando sua fatura mais recente... 📄"
    )


async def handle_technical_support(from_number: str, conversation_id: str):
    """Processar solicitação de suporte técnico"""
    await whatsapp_api.send_list_message(
        to=from_number,
        body_text="Selecione o tipo de problema técnico:",
        button_text="Ver opções",
        sections=[
            {
                "title": "Problemas de Internet",
                "rows": [
                    {"id": "no_internet", "title": "Sem internet", "description": "Conexão completamente fora"},
                    {"id": "slow_internet", "title": "Internet lenta", "description": "Velocidade abaixo do contratado"},
                    {"id": "intermittent", "title": "Conexão instável", "description": "Quedas frequentes"}
                ]
            },
            {
                "title": "Outros",
                "rows": [
                    {"id": "equipment", "title": "Problema no equipamento", "description": "Roteador, modem, etc."},
                    {"id": "other", "title": "Outro problema", "description": "Falar com atendente"}
                ]
            }
        ],
        header_text="🔧 Suporte Técnico"
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/send/text")
async def send_text_message(
    to: str,
    text: str,
    reply_to: Optional[str] = None
):
    """Enviar mensagem de texto via API"""
    try:
        result = await whatsapp_api.send_text_message(
            to=to,
            text=text,
            reply_to=reply_to
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Failed to send text message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/template")
async def send_template_message(
    to: str,
    template_name: str,
    parameters: Optional[list] = None,
    language: str = "pt_BR"
):
    """Enviar mensagem de template"""
    try:
        result = await whatsapp_api.send_template(
            to=to,
            template=template_name,
            parameters=parameters,
            language=language
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Failed to send template", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/buttons")
async def send_button_message(
    to: str,
    body_text: str,
    buttons: list,
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None
):
    """Enviar mensagem com botões"""
    try:
        result = await whatsapp_api.send_button_message(
            to=to,
            body_text=body_text,
            buttons=buttons,
            header_text=header_text,
            footer_text=footer_text
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Failed to send button message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/image")
async def send_image_message(
    to: str,
    image_url: str,
    caption: Optional[str] = None
):
    """Enviar imagem"""
    try:
        result = await whatsapp_api.send_image(
            to=to,
            image_url=image_url,
            caption=caption
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Failed to send image", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/document")
async def send_document_message(
    to: str,
    document_url: str,
    filename: Optional[str] = None,
    caption: Optional[str] = None
):
    """Enviar documento"""
    try:
        result = await whatsapp_api.send_document(
            to=to,
            document_url=document_url,
            filename=filename,
            caption=caption
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Failed to send document", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
async def get_queue():
    """Obter fila de atendimento WhatsApp"""
    try:
        items = await redis_manager.lrange("whatsapp:queue", 0, -1)
        queue = [json.loads(item) for item in items]
        return {"queue": queue, "size": len(queue)}
    except Exception as e:
        logger.error("Failed to get queue", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/assign/{index}")
async def assign_from_queue(index: int, agent_id: str):
    """Atribuir item da fila a um atendente"""
    try:
        # Obter item da fila
        items = await redis_manager.lrange("whatsapp:queue", index, index)
        if not items:
            raise HTTPException(status_code=404, detail="Item not found in queue")
        
        item = json.loads(items[0])
        from_number = item.get("from_number")
        
        # Atribuir agente
        await redis_manager.set(f"wa:agent:{from_number}", agent_id, ex=86400)
        
        # Remover da fila (simplificado)
        await redis_manager.client.lrem("whatsapp:queue", 1, items[0])
        
        # Notificar cliente
        await whatsapp_api.send_text_message(
            to=from_number,
            text="Um atendente foi designado para você! 🙋‍♂️\n"
                 "Ele responderá em instantes."
        )
        
        return {"success": True, "assigned_to": agent_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to assign from queue", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_whatsapp_metrics():
    """Obter métricas do WhatsApp"""
    return whatsapp_api.get_metrics()


@router.get("/health")
async def health_check():
    """Health check do serviço WhatsApp"""
    return await whatsapp_api.health_check()


@router.get("/conversation/{phone_number}/messages")
async def get_conversation_messages(phone_number: str, limit: int = 50):
    """Obter histórico de mensagens de uma conversa"""
    try:
        conversation_id = f"wa_{whatsapp_api._normalize_phone(phone_number)}"
        key = f"wa:messages:{conversation_id}"
        
        items = await redis_manager.lrange(key, -limit, -1)
        messages = [json.loads(item) for item in items]
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error("Failed to get conversation messages", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))