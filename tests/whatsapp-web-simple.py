"""
Integração WhatsApp Web simples (sem precisar de Business API)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import qrcode
import io
import base64
from typing import Optional

router = APIRouter(prefix="/api/v1/whatsapp-web", tags=["whatsapp-web"])

class SendMessageRequest(BaseModel):
    phone: str
    message: str

@router.get("/qr")
async def generate_qr():
    """Gerar QR Code para conectar WhatsApp Web"""
    
    # URL do WhatsApp Web
    whatsapp_url = "https://web.whatsapp.com/"
    
    # Gerar QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(whatsapp_url)
    qr.make(fit=True)
    
    # Criar imagem
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        "success": True,
        "qr_code": f"data:image/png;base64,{img_str}",
        "instructions": [
            "1. Abra o WhatsApp no seu celular",
            "2. Toque em 'Mais opções' > 'WhatsApp Web'",
            "3. Escaneie este QR Code",
            "4. Pronto! WhatsApp conectado"
        ]
    }

@router.get("/send-url")
async def get_send_url(phone: str, message: str):
    """Gerar URL para enviar mensagem via WhatsApp"""
    
    # Limpar número de telefone
    clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
    
    # Gerar URL do WhatsApp
    whatsapp_url = f"https://wa.me/{clean_phone}?text={message}"
    
    return {
        "success": True,
        "whatsapp_url": whatsapp_url,
        "phone": clean_phone,
        "message": message,
        "instructions": "Clique no link para abrir o WhatsApp e enviar a mensagem"
    }

@router.get("/status")
async def whatsapp_web_status():
    """Status do WhatsApp Web"""
    return {
        "success": True,
        "type": "WhatsApp Web Integration",
        "features": [
            "✅ Gerar QR Code para conectar",
            "✅ URLs diretas para enviar mensagens",
            "✅ Funciona sem API oficial",
            "✅ Gratuito e ilimitado"
        ],
        "limitations": [
            "⚠️ Precisa escanear QR Code",
            "⚠️ Não recebe mensagens automaticamente",
            "⚠️ Depende do WhatsApp Web estar aberto"
        ]
    }

@router.get("/help")
async def whatsapp_web_help():
    """Ajuda para WhatsApp Web"""
    return {
        "title": "WhatsApp Web - Integração Simples",
        "description": "Alternativa gratuita ao WhatsApp Business API",
        "endpoints": {
            "qr_code": "GET /api/v1/whatsapp-web/qr",
            "send_url": "GET /api/v1/whatsapp-web/send-url?phone=5511999999999&message=Olá",
            "status": "GET /api/v1/whatsapp-web/status"
        },
        "how_to_use": [
            "1. Acesse /qr para gerar QR Code",
            "2. Escaneie com WhatsApp do celular", 
            "3. Use /send-url para criar links de mensagem",
            "4. Clique nos links para enviar mensagens"
        ],
        "advantages": [
            "✅ 100% gratuito",
            "✅ Sem limite de mensagens",
            "✅ Não precisa de aprovação",
            "✅ Funciona imediatamente"
        ]
    }