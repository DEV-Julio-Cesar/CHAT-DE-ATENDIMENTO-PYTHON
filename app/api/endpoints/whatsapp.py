"""
Endpoints do WhatsApp Business API
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Dict, Any, Optional
import structlog
from app.api.endpoints.auth import get_current_user
from app.core.config import settings
from app.services.whatsapp_enterprise import whatsapp_api

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/clients")
async def list_whatsapp_clients(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Lista clientes WhatsApp conectados"""
    try:
        clients = await whatsapp_api.get_connected_clients()
        return clients
    except Exception as e:
        logger.error("Error listing WhatsApp clients", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao listar clientes WhatsApp")

@router.post("/send-message")
async def send_whatsapp_message(
    message_data: Dict[str, Any], 
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Envia mensagem via WhatsApp Business API"""
    try:
        result = await whatsapp_api.send_message(
            phone_number=message_data.get("phone_number"),
            message=message_data.get("message"),
            message_type=message_data.get("type", "text")
        )
        return result
    except Exception as e:
        logger.error("Error sending WhatsApp message", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao enviar mensagem WhatsApp")

@router.get("/webhook")
async def whatsapp_webhook_verify(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """Verificação do webhook do WhatsApp Business API"""
    logger.info("WhatsApp webhook verification", 
                mode=hub_mode, 
                token=hub_verify_token,
                challenge=hub_challenge)
    
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return int(hub_challenge)
    
    logger.warning("WhatsApp webhook verification failed", 
                   expected_token=settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
                   received_token=hub_verify_token)
    raise HTTPException(status_code=403, detail="Token de verificação inválido")

@router.post("/webhook")
async def whatsapp_webhook_receive(request: Request):
    """Recebe webhooks do WhatsApp Business API"""
    try:
        webhook_data = await request.json()
        logger.info("WhatsApp webhook received", data=webhook_data)
        
        # Processar webhook
        result = await whatsapp_api.process_webhook(webhook_data)
        
        return {"success": True, "message": "Webhook processado com sucesso"}
    
    except Exception as e:
        logger.error("Error processing WhatsApp webhook", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao processar webhook")

@router.get("/status")
async def whatsapp_status(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Status da integração WhatsApp"""
    try:
        status = await whatsapp_api.get_status()
        return status
    except Exception as e:
        logger.error("Error getting WhatsApp status", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao obter status do WhatsApp")

@router.post("/configure")
async def configure_whatsapp(
    config_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Configurar WhatsApp Business API"""
    try:
        result = await whatsapp_api.configure(config_data)
        return result
    except Exception as e:
        logger.error("Error configuring WhatsApp", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao configurar WhatsApp")