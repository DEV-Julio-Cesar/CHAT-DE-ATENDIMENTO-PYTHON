"""
Endpoints do WhatsApp
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.api.endpoints.auth import get_current_user

router = APIRouter()

@router.get("/clients")
async def list_whatsapp_clients(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Lista clientes WhatsApp"""
    # Implementação básica para demonstração
    return [
        {
            "id": "client_001",
            "phone": "+55 11 99999-9999",
            "status": "connected",
            "name": "Cliente Principal"
        }
    ]

@router.post("/send-message")
async def send_whatsapp_message(message_data: Dict[str, Any], current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Envia mensagem via WhatsApp"""
    return {
        "success": True,
        "message_id": "msg_123",
        "status": "sent",
        "message": "Mensagem enviada com sucesso"
    }

@router.get("/webhook")
async def whatsapp_webhook_verify(hub_mode: str = None, hub_verify_token: str = None, hub_challenge: str = None):
    """Verificação do webhook do WhatsApp"""
    if hub_mode == "subscribe" and hub_verify_token == "your_verify_token":
        return int(hub_challenge)
    return {"error": "Invalid verification token"}

@router.post("/webhook")
async def whatsapp_webhook_receive(webhook_data: Dict[str, Any]):
    """Recebe webhooks do WhatsApp"""
    return {"success": True, "message": "Webhook processado"}