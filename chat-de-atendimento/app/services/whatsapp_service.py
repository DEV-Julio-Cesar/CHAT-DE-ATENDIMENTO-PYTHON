"""
Serviço de integração com WhatsApp Business API
"""
import httpx
import structlog
from typing import Optional, Dict, Any, List
import json
from datetime import datetime
import asyncio

from app.core.config import settings
from app.core.redis_client import redis_manager, CacheKeys

logger = structlog.get_logger(__name__)


class WhatsAppBusinessAPI:
    """Cliente para WhatsApp Business API"""
    
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = "https://graph.facebook.com/v18.0"
        self.webhook_verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        
        # Cliente HTTP com timeout e retry
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Obter headers para requisições"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def send_text_message(
        self, 
        to: str, 
        message: str, 
        preview_url: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Enviar mensagem de texto"""
        
        if not self.access_token or not self.phone_number_id:
            logger.error("WhatsApp credentials not configured")
            return None
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message
            }
        }
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    "WhatsApp message sent successfully",
                    to=to,
                    message_id=result.get("messages", [{}])[0].get("id"),
                    message_length=len(message)
                )
                return result
            else:
                logger.error(
                    "Failed to send WhatsApp message",
                    to=to,
                    status_code=response.status_code,
                    response=response.text
                )
                return None
                
        except Exception as e:
            logger.error(
                "Error sending WhatsApp message",
                to=to,
                error=str(e)
            )
            return None
    
    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        parameters: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Enviar mensagem template"""
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        template_payload = {
            "name": template_name,
            "language": {"code": language_code}
        }
        
        if parameters:
            template_payload["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": param} for param in parameters]
            }]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template_payload
        }
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    "WhatsApp template message sent",
                    to=to,
                    template=template_name,
                    message_id=result.get("messages", [{}])[0].get("id")
                )
                return result
            else:
                logger.error(
                    "Failed to send WhatsApp template",
                    to=to,
                    template=template_name,
                    status_code=response.status_code,
                    response=response.text
                )
                return None
                
        except Exception as e:
            logger.error(
                "Error sending WhatsApp template",
                to=to,
                template=template_name,
                error=str(e)
            )
            return None
    
    async def send_media_message(
        self,
        to: str,
        media_type: str,  # image, document, audio, video
        media_url: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Enviar mensagem com mídia"""
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        media_payload = {"link": media_url}
        if caption and media_type in ["image", "video"]:
            media_payload["caption"] = caption
        if filename and media_type == "document":
            media_payload["filename"] = filename
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": media_type,
            media_type: media_payload
        }
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    "WhatsApp media message sent",
                    to=to,
                    media_type=media_type,
                    message_id=result.get("messages", [{}])[0].get("id")
                )
                return result
            else:
                logger.error(
                    "Failed to send WhatsApp media",
                    to=to,
                    media_type=media_type,
                    status_code=response.status_code,
                    response=response.text
                )
                return None
                
        except Exception as e:
            logger.error(
                "Error sending WhatsApp media",
                to=to,
                media_type=media_type,
                error=str(e)
            )
            return None
    
    async def mark_message_as_read(self, message_id: str) -> bool:
        """Marcar mensagem como lida"""
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                logger.debug("Message marked as read", message_id=message_id)
                return True
            else:
                logger.warning(
                    "Failed to mark message as read",
                    message_id=message_id,
                    status_code=response.status_code
                )
                return False
                
        except Exception as e:
            logger.error(
                "Error marking message as read",
                message_id=message_id,
                error=str(e)
            )
            return False
    
    async def get_media_url(self, media_id: str) -> Optional[str]:
        """Obter URL de mídia"""
        
        url = f"{self.base_url}/{media_id}"
        
        try:
            response = await self.client.get(
                url,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("url")
            else:
                logger.error(
                    "Failed to get media URL",
                    media_id=media_id,
                    status_code=response.status_code
                )
                return None
                
        except Exception as e:
            logger.error(
                "Error getting media URL",
                media_id=media_id,
                error=str(e)
            )
            return None
    
    async def download_media(self, media_url: str) -> Optional[bytes]:
        """Baixar mídia"""
        
        try:
            response = await self.client.get(
                media_url,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(
                    "Failed to download media",
                    media_url=media_url,
                    status_code=response.status_code
                )
                return None
                
        except Exception as e:
            logger.error(
                "Error downloading media",
                media_url=media_url,
                error=str(e)
            )
            return None
    
    async def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verificar webhook do WhatsApp"""
        
        if mode == "subscribe" and token == self.webhook_verify_token:
            logger.info("WhatsApp webhook verified successfully")
            return challenge
        else:
            logger.warning(
                "WhatsApp webhook verification failed",
                mode=mode,
                token_match=token == self.webhook_verify_token
            )
            return None
    
    async def process_webhook_message(self, webhook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Processar mensagem recebida via webhook"""
        
        messages = []
        
        try:
            entry = webhook_data.get("entry", [])
            
            for entry_item in entry:
                changes = entry_item.get("changes", [])
                
                for change in changes:
                    value = change.get("value", {})
                    
                    # Processar mensagens recebidas
                    if "messages" in value:
                        for message in value["messages"]:
                            processed_message = await self._process_incoming_message(message, value)
                            if processed_message:
                                messages.append(processed_message)
                    
                    # Processar status de mensagens enviadas
                    if "statuses" in value:
                        for status in value["statuses"]:
                            await self._process_message_status(status)
            
            return messages
            
        except Exception as e:
            logger.error("Error processing webhook message", error=str(e))
            return []
    
    async def _process_incoming_message(
        self, 
        message: Dict[str, Any], 
        value: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Processar mensagem recebida"""
        
        try:
            # Extrair informações básicas
            message_id = message.get("id")
            from_number = message.get("from")
            timestamp = message.get("timestamp")
            message_type = message.get("type")
            
            # Extrair informações do contato
            contacts = value.get("contacts", [])
            contact_name = None
            if contacts:
                contact = contacts[0]
                profile = contact.get("profile", {})
                contact_name = profile.get("name")
            
            # Extrair conteúdo da mensagem
            content = ""
            media_info = None
            
            if message_type == "text":
                content = message.get("text", {}).get("body", "")
            
            elif message_type in ["image", "document", "audio", "video"]:
                media_data = message.get(message_type, {})
                media_info = {
                    "id": media_data.get("id"),
                    "mime_type": media_data.get("mime_type"),
                    "sha256": media_data.get("sha256"),
                    "filename": media_data.get("filename")
                }
                content = media_data.get("caption", "")
            
            elif message_type == "location":
                location = message.get("location", {})
                content = f"Localização: {location.get('latitude')}, {location.get('longitude')}"
            
            elif message_type == "contacts":
                contacts_data = message.get("contacts", [])
                content = f"Contato compartilhado: {len(contacts_data)} contato(s)"
            
            # Marcar mensagem como lida
            await self.mark_message_as_read(message_id)
            
            processed_message = {
                "id": message_id,
                "from": from_number,
                "contact_name": contact_name,
                "timestamp": datetime.fromtimestamp(int(timestamp)),
                "type": message_type,
                "content": content,
                "media_info": media_info
            }
            
            logger.info(
                "Incoming WhatsApp message processed",
                message_id=message_id,
                from_number=from_number,
                message_type=message_type
            )
            
            return processed_message
            
        except Exception as e:
            logger.error(
                "Error processing incoming message",
                message=message,
                error=str(e)
            )
            return None
    
    async def _process_message_status(self, status: Dict[str, Any]):
        """Processar status de mensagem enviada"""
        
        try:
            message_id = status.get("id")
            recipient_id = status.get("recipient_id")
            status_type = status.get("status")
            timestamp = status.get("timestamp")
            
            logger.info(
                "Message status update",
                message_id=message_id,
                recipient_id=recipient_id,
                status=status_type,
                timestamp=timestamp
            )
            
            # Atualizar status no cache/banco
            cache_key = f"message_status:{message_id}"
            await redis_manager.set_json(cache_key, {
                "status": status_type,
                "timestamp": timestamp,
                "recipient_id": recipient_id
            }, ex=86400)  # 24 horas
            
        except Exception as e:
            logger.error(
                "Error processing message status",
                status=status,
                error=str(e)
            )
    
    async def get_business_profile(self) -> Optional[Dict[str, Any]]:
        """Obter perfil do negócio"""
        
        url = f"{self.base_url}/{self.phone_number_id}"
        
        try:
            response = await self.client.get(
                url,
                headers=self._get_headers(),
                params={"fields": "name,status,quality_rating,messaging_limit_tier"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Failed to get business profile",
                    status_code=response.status_code
                )
                return None
                
        except Exception as e:
            logger.error("Error getting business profile", error=str(e))
            return None
    
    async def health_check(self) -> bool:
        """Verificar saúde da conexão com WhatsApp"""
        
        try:
            profile = await self.get_business_profile()
            return profile is not None
        except Exception as e:
            logger.error("WhatsApp health check failed", error=str(e))
            return False


# Instância global do serviço
whatsapp_service = WhatsAppBusinessAPI()