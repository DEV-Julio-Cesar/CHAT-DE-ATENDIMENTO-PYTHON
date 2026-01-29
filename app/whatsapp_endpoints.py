"""
Endpoints WhatsApp Business API
"""
from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
import httpx
import os
import structlog
from typing import Optional, Dict, Any

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])

# Configurações WhatsApp
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "webhook_verify_token_123")
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"

# Schemas
class SendMessageRequest(BaseModel):
    to: str
    message: str
    type: str = "text"

class WebhookVerification(BaseModel):
    mode: str
    token: str
    challenge: str

# Cliente HTTP
http_client = httpx.AsyncClient(timeout=30.0)

@router.get("/status")
async def whatsapp_status():
    """Verificar status da configuração WhatsApp"""
    
    config_status = {
        "access_token_configured": bool(WHATSAPP_ACCESS_TOKEN),
        "phone_number_id_configured": bool(WHATSAPP_PHONE_NUMBER_ID),
        "webhook_token_configured": bool(WHATSAPP_WEBHOOK_VERIFY_TOKEN),
    }
    
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return {
            "success": False,
            "message": "WhatsApp credentials not configured",
            "config": config_status,
            "instructions": "Configure WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env file"
        }
    
    # Testar conexão com API do WhatsApp
    try:
        url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
        
        response = await http_client.get(url, headers=headers)
        
        if response.status_code == 200:
            profile_data = response.json()
            return {
                "success": True,
                "message": "WhatsApp Business API connected successfully",
                "config": config_status,
                "profile": {
                    "name": profile_data.get("name", "N/A"),
                    "status": profile_data.get("status", "N/A"),
                    "phone_number_id": WHATSAPP_PHONE_NUMBER_ID
                }
            }
        else:
            return {
                "success": False,
                "message": f"WhatsApp API error: {response.status_code}",
                "config": config_status,
                "error": response.text
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}",
            "config": config_status
        }

@router.post("/send")
async def send_message(request: SendMessageRequest):
    """Enviar mensagem via WhatsApp"""
    
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise HTTPException(
            status_code=400, 
            detail="WhatsApp credentials not configured. Check WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env"
        )
    
    # Validar número de telefone
    phone = request.to.replace("+", "").replace("-", "").replace(" ", "")
    if not phone.isdigit() or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    # Preparar payload para API do WhatsApp
    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": request.message
        }
    }
    
    try:
        response = await http_client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get("messages", [{}])[0].get("id")
            
            logger.info(
                "WhatsApp message sent successfully",
                to=phone,
                message_id=message_id,
                message_length=len(request.message)
            )
            
            return {
                "success": True,
                "message": "Message sent successfully",
                "data": {
                    "message_id": message_id,
                    "to": phone,
                    "status": "sent"
                }
            }
        else:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
            
            logger.error(
                "Failed to send WhatsApp message",
                to=phone,
                status_code=response.status_code,
                error=error_data
            )
            
            raise HTTPException(
                status_code=response.status_code,
                detail=f"WhatsApp API error: {error_data}"
            )
            
    except httpx.RequestError as e:
        logger.error("WhatsApp API request error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

@router.post("/test")
async def test_message():
    """Enviar mensagem de teste"""
    
    test_message = SendMessageRequest(
        to="5511999999999",  # Número de teste - substitua pelo seu
        message="🚀 Teste do ISP Customer Support!\n\nSe você recebeu esta mensagem, a integração WhatsApp está funcionando perfeitamente!\n\n✅ Sistema operacional\n📱 Pronto para atender seus clientes"
    )
    
    return await send_message(test_message)

@router.get("/webhook")
async def webhook_verify(
    hub_mode: str = None,
    hub_verify_token: str = None, 
    hub_challenge: str = None
):
    """Verificar webhook do WhatsApp"""
    
    # Parâmetros podem vir como hub.mode, hub.verify_token, hub.challenge
    mode = hub_mode
    token = hub_verify_token
    challenge = hub_challenge
    
    logger.info(
        "WhatsApp webhook verification attempt",
        mode=mode,
        token_provided=bool(token),
        challenge_provided=bool(challenge)
    )
    
    if mode == "subscribe" and token == WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return int(challenge) if challenge and challenge.isdigit() else challenge
    else:
        logger.warning(
            "WhatsApp webhook verification failed",
            mode=mode,
            token_match=token == WHATSAPP_WEBHOOK_VERIFY_TOKEN if token else False
        )
        raise HTTPException(status_code=403, detail="Webhook verification failed")

@router.post("/webhook")
async def webhook_receive(request: Request):
    """Receber mensagens do WhatsApp"""
    
    try:
        body = await request.json()
        
        logger.info("WhatsApp webhook received", body=body)
        
        # Processar mensagens recebidas
        if "entry" in body:
            for entry in body["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if "value" in change and "messages" in change["value"]:
                            messages = change["value"]["messages"]
                            contacts = change["value"].get("contacts", [])
                            
                            for message in messages:
                                await process_incoming_message(message, contacts)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error("Error processing WhatsApp webhook", error=str(e))
        return {"status": "error", "message": str(e)}

async def process_incoming_message(message: Dict[str, Any], contacts: list):
    """Processar mensagem recebida"""
    
    try:
        message_id = message.get("id")
        from_number = message.get("from")
        timestamp = message.get("timestamp")
        message_type = message.get("type", "text")
        
        # Extrair conteúdo da mensagem
        content = ""
        if message_type == "text":
            content = message.get("text", {}).get("body", "")
        elif message_type == "image":
            content = "[Imagem recebida]"
        elif message_type == "document":
            content = "[Documento recebido]"
        elif message_type == "audio":
            content = "[Áudio recebido]"
        else:
            content = f"[{message_type} recebido]"
        
        # Extrair nome do contato
        contact_name = "Desconhecido"
        if contacts:
            profile = contacts[0].get("profile", {})
            contact_name = profile.get("name", from_number)
        
        logger.info(
            "Incoming WhatsApp message processed",
            message_id=message_id,
            from_number=from_number,
            contact_name=contact_name,
            message_type=message_type,
            content=content[:100] + "..." if len(content) > 100 else content
        )
        
        # Aqui você pode integrar com:
        # 1. Chatbot IA (Google Gemini)
        # 2. Sistema de filas
        # 3. Notificações para atendentes
        # 4. Banco de dados
        
        # Resposta automática simples (remova em produção)
        if "teste" in content.lower():
            auto_response = f"Olá {contact_name}! 👋\n\nRecebemos sua mensagem: \"{content}\"\n\nEm breve um de nossos atendentes entrará em contato.\n\n🤖 Resposta automática do ISP Customer Support"
            
            await send_message(SendMessageRequest(
                to=from_number,
                message=auto_response
            ))
        
    except Exception as e:
        logger.error("Error processing incoming message", error=str(e), message=message)

@router.get("/help")
async def whatsapp_help():
    """Ajuda para configuração WhatsApp"""
    
    return {
        "title": "WhatsApp Business API - Guia de Configuração",
        "steps": [
            {
                "step": 1,
                "title": "Criar conta Meta for Developers",
                "url": "https://developers.facebook.com/",
                "description": "Crie uma conta e um app Business"
            },
            {
                "step": 2,
                "title": "Configurar WhatsApp Business API",
                "description": "Adicione o produto WhatsApp ao seu app"
            },
            {
                "step": 3,
                "title": "Obter credenciais",
                "description": "Copie ACCESS_TOKEN e PHONE_NUMBER_ID"
            },
            {
                "step": 4,
                "title": "Configurar .env",
                "example": {
                    "WHATSAPP_ACCESS_TOKEN": "EAAxxxxxxxxxxxxxxxxxxxxx",
                    "WHATSAPP_PHONE_NUMBER_ID": "1234567890123456",
                    "WHATSAPP_WEBHOOK_VERIFY_TOKEN": "webhook_verify_token_123"
                }
            },
            {
                "step": 5,
                "title": "Testar configuração",
                "endpoint": "/api/v1/whatsapp/status"
            }
        ],
        "endpoints": {
            "status": "GET /api/v1/whatsapp/status",
            "send": "POST /api/v1/whatsapp/send",
            "test": "POST /api/v1/whatsapp/test",
            "webhook": "GET/POST /api/v1/whatsapp/webhook"
        },
        "limits": {
            "test_account": "1,000 messages/month (free)",
            "production": "$0.005 per message"
        }
    }