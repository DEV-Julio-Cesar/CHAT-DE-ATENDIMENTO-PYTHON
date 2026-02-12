"""
Endpoints para WhatsApp usando biblioteca Python
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import httpx

from app.services.whatsapp_python import whatsapp_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp-python"])


# ============================================================================
# MODELS
# ============================================================================

class SendMessageRequest(BaseModel):
    """Requisição para enviar mensagem"""
    phone_number: str = Field(..., description="Número com código do país (ex: +5511999999999)")
    message: str = Field(..., description="Mensagem a ser enviada")
    wait_time: int = Field(15, description="Tempo de espera em segundos")
    close_tab: bool = Field(True, description="Fechar aba após enviar")


class ScheduleMessageRequest(BaseModel):
    """Requisição para agendar mensagem"""
    phone_number: str = Field(..., description="Número com código do país")
    message: str = Field(..., description="Mensagem a ser enviada")
    hour: int = Field(..., ge=0, le=23, description="Hora do envio (0-23)")
    minute: int = Field(..., ge=0, le=59, description="Minuto do envio (0-59)")
    close_tab: bool = Field(True, description="Fechar aba após enviar")


class SendImageRequest(BaseModel):
    """Requisição para enviar imagem"""
    phone_number: str = Field(..., description="Número com código do país")
    image_path: str = Field(..., description="Caminho da imagem")
    caption: Optional[str] = Field(None, description="Legenda da imagem")
    wait_time: int = Field(15, description="Tempo de espera em segundos")


class BulkContact(BaseModel):
    """Contato para envio em massa"""
    phone: str = Field(..., description="Número com código do país")
    message: str = Field(..., description="Mensagem personalizada")


class SendBulkRequest(BaseModel):
    """Requisição para envio em massa"""
    contacts: List[BulkContact] = Field(..., description="Lista de contatos")
    wait_time: int = Field(15, description="Tempo de espera entre mensagens")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/send")
async def send_message(request: SendMessageRequest):
    """
    Enviar mensagem via WhatsApp Web
    
    IMPORTANTE:
    - WhatsApp Web deve estar logado no navegador Chrome
    - A primeira vez pode demorar mais para abrir o navegador
    - O navegador será aberto automaticamente
    """
    try:
        result = await whatsapp_service.send_message(
            phone_number=request.phone_number,
            message=request.message,
            wait_time=request.wait_time,
            close_tab=request.close_tab
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Erro ao enviar mensagem")
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no endpoint send_message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/schedule")
async def schedule_message(request: ScheduleMessageRequest):
    """
    Agendar mensagem para horário específico
    
    A mensagem será enviada no horário especificado (hora e minuto).
    O navegador será aberto automaticamente no horário agendado.
    """
    try:
        result = await whatsapp_service.send_message_scheduled(
            phone_number=request.phone_number,
            message=request.message,
            hour=request.hour,
            minute=request.minute,
            close_tab=request.close_tab
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Erro ao agendar mensagem")
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no endpoint schedule_message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/send-image")
async def send_image(request: SendImageRequest):
    """
    Enviar imagem via WhatsApp Web
    
    A imagem deve estar salva localmente no servidor.
    Formatos suportados: JPG, PNG, GIF
    """
    try:
        result = await whatsapp_service.send_image(
            phone_number=request.phone_number,
            image_path=request.image_path,
            caption=request.caption,
            wait_time=request.wait_time
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Erro ao enviar imagem")
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no endpoint send_image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/send-bulk")
async def send_bulk(request: SendBulkRequest):
    """
    Enviar mensagens em massa
    
    ATENÇÃO:
    - Envios em massa podem ser detectados pelo WhatsApp
    - Use com moderação para evitar bloqueio
    - Há um delay de 5 segundos entre cada mensagem
    """
    try:
        contacts_dict = [
            {"phone": c.phone, "message": c.message}
            for c in request.contacts
        ]
        
        result = await whatsapp_service.send_bulk_messages(
            contacts=contacts_dict,
            wait_time=request.wait_time
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no endpoint send_bulk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status")
async def get_status():
    """
    Verificar status do serviço WhatsApp
    
    Retorna informações sobre o serviço e requisitos.
    """
    return whatsapp_service.get_status()


@router.get("/qr-code")
async def generate_qr_code():
    """
    Gerar QR Code para WhatsApp Web
    
    Retorna um QR Code REAL do WhatsApp Web para conectar.
    Requer que o serviço Node.js esteja rodando na porta 3001.
    """
    from app.services.whatsapp_web_qr import whatsapp_qr_service
    
    result = await whatsapp_qr_service.generate_qr_code()
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("error", "Erro ao gerar QR Code")
        )
    
    return result


@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """
    Verificar status de uma sessão WhatsApp
    
    Retorna o status da conexão (waiting, connected, disconnected).
    """
    from app.services.whatsapp_web_qr import whatsapp_qr_service
    
    result = await whatsapp_qr_service.get_session_status(session_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Sessão não encontrada")
        )
    
    return result


@router.post("/send-message-web")
async def send_message_web(phone: str, message: str):
    """
    Enviar mensagem via WhatsApp Web (serviço Node.js)
    
    Requer que o WhatsApp Web esteja conectado.
    """
    from app.services.whatsapp_web_qr import whatsapp_qr_service
    
    try:
        result = await whatsapp_qr_service.send_message(phone, message)
        
        if not result.get("success"):
            error_msg = result.get("error", "Erro desconhecido ao enviar mensagem")
            # Se error for um objeto, converter para string
            if isinstance(error_msg, dict):
                error_msg = str(error_msg)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao enviar mensagem: {str(e)}"
        )


@router.post("/disconnect")
async def disconnect_whatsapp():
    """Desconectar WhatsApp Web"""
    from app.services.whatsapp_web_qr import whatsapp_qr_service
    
    result = await whatsapp_qr_service.disconnect()
    return result


@router.post("/reconnect")
async def reconnect_whatsapp():
    """Reconectar WhatsApp Web (gera novo QR Code)"""
    from app.services.whatsapp_web_qr import whatsapp_qr_service
    
    result = await whatsapp_qr_service.reconnect()
    return result


@router.get("/chats")
async def get_whatsapp_chats():
    """
    Listar conversas do WhatsApp conectado
    
    Retorna lista de chats/conversas reais do WhatsApp.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get('http://localhost:3001/chats')
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço WhatsApp não está rodando"
        )
    except Exception as e:
        logger.error(f"Erro ao buscar chats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar chats: {str(e)}"
        )


@router.get("/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: str, limit: int = 50):
    """
    Obter mensagens de uma conversa específica
    
    Retorna histórico de mensagens de um chat.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f'http://localhost:3001/chats/{chat_id}/messages?limit={limit}')
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço WhatsApp não está rodando"
        )
    except Exception as e:
        logger.error(f"Erro ao buscar mensagens: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar mensagens: {str(e)}"
        )
