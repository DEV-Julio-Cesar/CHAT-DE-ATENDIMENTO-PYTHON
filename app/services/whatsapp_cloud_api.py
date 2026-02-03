"""
WhatsApp Business Cloud API - Meta Integration
CIANET PROVEDOR - v3.0

Integração completa com WhatsApp Business API:
- Envio de mensagens (texto, template, mídia)
- Recebimento via Webhook
- Templates HSM
- Gerenciamento de contatos
"""
import logging
import httpx
import json
import hashlib
import hmac
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

class WhatsAppConfig:
    """Configurações do WhatsApp Business API"""
    
    # Meta Cloud API
    API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
    
    # Tokens (devem vir do settings/env)
    @property
    def access_token(self) -> str:
        return getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
    
    @property
    def phone_number_id(self) -> str:
        return getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
    
    @property
    def business_account_id(self) -> str:
        return getattr(settings, 'WHATSAPP_BUSINESS_ACCOUNT_ID', '')
    
    @property
    def webhook_verify_token(self) -> str:
        return getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'cianet_verify_token_2024')
    
    @property
    def app_secret(self) -> str:
        return getattr(settings, 'WHATSAPP_APP_SECRET', '')


config = WhatsAppConfig()


# ============================================================================
# SCHEMAS
# ============================================================================

class MessageText(BaseModel):
    """Mensagem de texto"""
    body: str = Field(..., min_length=1, max_length=4096)
    preview_url: bool = False


class MessageTemplate(BaseModel):
    """Mensagem de template HSM"""
    name: str
    language: str = "pt_BR"
    components: List[Dict[str, Any]] = []


class MessageImage(BaseModel):
    """Mensagem de imagem"""
    link: Optional[str] = None
    id: Optional[str] = None  # Media ID
    caption: Optional[str] = None


class MessageDocument(BaseModel):
    """Mensagem de documento"""
    link: Optional[str] = None
    id: Optional[str] = None
    filename: str
    caption: Optional[str] = None


class MessageAudio(BaseModel):
    """Mensagem de áudio"""
    link: Optional[str] = None
    id: Optional[str] = None


class MessageLocation(BaseModel):
    """Mensagem de localização"""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


class MessageContact(BaseModel):
    """Contato para envio"""
    name: Dict[str, str]  # {"formatted_name": "...", "first_name": "..."}
    phones: List[Dict[str, str]]  # [{"phone": "...", "type": "CELL"}]


class SendMessageRequest(BaseModel):
    """Request para envio de mensagem"""
    to: str = Field(..., description="Número do destinatário (55119...)")
    type: str = Field(default="text", description="text, template, image, document, audio, location, contacts")
    
    # Conteúdo (apenas um deve ser preenchido)
    text: Optional[MessageText] = None
    template: Optional[MessageTemplate] = None
    image: Optional[MessageImage] = None
    document: Optional[MessageDocument] = None
    audio: Optional[MessageAudio] = None
    location: Optional[MessageLocation] = None
    contacts: Optional[List[MessageContact]] = None


class SendMessageResponse(BaseModel):
    """Resposta do envio"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class WebhookMessage(BaseModel):
    """Mensagem recebida via webhook"""
    message_id: str
    from_number: str
    timestamp: datetime
    type: str
    content: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None  # Mensagem respondida


class TemplateInfo(BaseModel):
    """Informações do template"""
    name: str
    status: str
    category: str
    language: str
    components: List[Dict[str, Any]]


# ============================================================================
# CLIENTE WHATSAPP
# ============================================================================

class WhatsAppClient:
    """Cliente para WhatsApp Business Cloud API"""
    
    def __init__(self):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Client HTTP assíncrono"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.BASE_URL,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.config.access_token}",
                    "Content-Type": "application/json"
                }
            )
        return self._client
    
    async def close(self):
        """Fechar cliente"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # =========================================================================
    # ENVIO DE MENSAGENS
    # =========================================================================
    
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """
        Enviar mensagem pelo WhatsApp.
        
        Suporta:
        - Texto simples
        - Templates HSM
        - Imagem, documento, áudio
        - Localização
        - Contatos
        """
        try:
            # Construir payload
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self._format_phone(request.to),
                "type": request.type
            }
            
            # Adicionar conteúdo conforme tipo
            if request.type == "text" and request.text:
                payload["text"] = request.text.dict()
            
            elif request.type == "template" and request.template:
                payload["template"] = {
                    "name": request.template.name,
                    "language": {"code": request.template.language},
                    "components": request.template.components
                }
            
            elif request.type == "image" and request.image:
                img = request.image.dict(exclude_none=True)
                payload["image"] = img
            
            elif request.type == "document" and request.document:
                doc = request.document.dict(exclude_none=True)
                payload["document"] = doc
            
            elif request.type == "audio" and request.audio:
                aud = request.audio.dict(exclude_none=True)
                payload["audio"] = aud
            
            elif request.type == "location" and request.location:
                payload["location"] = request.location.dict()
            
            elif request.type == "contacts" and request.contacts:
                payload["contacts"] = [c.dict() for c in request.contacts]
            
            else:
                return SendMessageResponse(
                    success=False,
                    error=f"Conteúdo não fornecido para tipo: {request.type}"
                )
            
            # Enviar
            response = await self.client.post(
                f"/{self.config.phone_number_id}/messages",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                
                logger.info(f"Mensagem enviada: {message_id} para {request.to}")
                
                return SendMessageResponse(
                    success=True,
                    message_id=message_id,
                    details=data
                )
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Erro desconhecido")
                
                logger.error(f"Erro ao enviar mensagem: {error_msg}")
                
                return SendMessageResponse(
                    success=False,
                    error=error_msg,
                    details=error_data
                )
        
        except Exception as e:
            logger.error(f"Exception ao enviar mensagem: {e}")
            return SendMessageResponse(success=False, error=str(e))
    
    async def send_text(self, to: str, text: str, preview_url: bool = False) -> SendMessageResponse:
        """Atalho para enviar texto simples"""
        return await self.send_message(SendMessageRequest(
            to=to,
            type="text",
            text=MessageText(body=text, preview_url=preview_url)
        ))
    
    async def send_template(
        self, 
        to: str, 
        template_name: str,
        language: str = "pt_BR",
        header_params: List[str] = None,
        body_params: List[str] = None,
        button_params: List[Dict] = None
    ) -> SendMessageResponse:
        """
        Enviar mensagem de template HSM.
        
        Templates são mensagens pré-aprovadas pelo Meta.
        Usados para iniciar conversas (24h window).
        """
        components = []
        
        # Header (ex: imagem, documento, vídeo ou texto)
        if header_params:
            components.append({
                "type": "header",
                "parameters": [
                    {"type": "text", "text": p} for p in header_params
                ]
            })
        
        # Body (variáveis {{1}}, {{2}}, etc)
        if body_params:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": p} for p in body_params
                ]
            })
        
        # Botões
        if button_params:
            for idx, btn in enumerate(button_params):
                components.append({
                    "type": "button",
                    "sub_type": btn.get("sub_type", "quick_reply"),
                    "index": str(idx),
                    "parameters": btn.get("parameters", [])
                })
        
        return await self.send_message(SendMessageRequest(
            to=to,
            type="template",
            template=MessageTemplate(
                name=template_name,
                language=language,
                components=components
            )
        ))
    
    async def send_image(
        self, 
        to: str, 
        image_url: str = None,
        media_id: str = None,
        caption: str = None
    ) -> SendMessageResponse:
        """Enviar imagem"""
        return await self.send_message(SendMessageRequest(
            to=to,
            type="image",
            image=MessageImage(link=image_url, id=media_id, caption=caption)
        ))
    
    async def send_document(
        self, 
        to: str, 
        document_url: str = None,
        media_id: str = None,
        filename: str = "document.pdf",
        caption: str = None
    ) -> SendMessageResponse:
        """Enviar documento"""
        return await self.send_message(SendMessageRequest(
            to=to,
            type="document",
            document=MessageDocument(
                link=document_url, 
                id=media_id, 
                filename=filename, 
                caption=caption
            )
        ))
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Marcar mensagem como lida"""
        try:
            response = await self.client.post(
                f"/{self.config.phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao marcar como lido: {e}")
            return False
    
    # =========================================================================
    # TEMPLATES
    # =========================================================================
    
    async def get_templates(self) -> List[TemplateInfo]:
        """Listar templates disponíveis"""
        try:
            response = await self.client.get(
                f"/{self.config.business_account_id}/message_templates",
                params={"limit": 100}
            )
            
            if response.status_code == 200:
                data = response.json()
                templates = []
                
                for t in data.get("data", []):
                    templates.append(TemplateInfo(
                        name=t.get("name"),
                        status=t.get("status"),
                        category=t.get("category"),
                        language=t.get("language"),
                        components=t.get("components", [])
                    ))
                
                return templates
            
            return []
        except Exception as e:
            logger.error(f"Erro ao listar templates: {e}")
            return []
    
    async def create_template(
        self,
        name: str,
        category: str,
        language: str,
        components: List[Dict]
    ) -> Dict[str, Any]:
        """
        Criar template (requer aprovação do Meta).
        
        Categories: MARKETING, UTILITY, AUTHENTICATION
        """
        try:
            response = await self.client.post(
                f"/{self.config.business_account_id}/message_templates",
                json={
                    "name": name,
                    "category": category,
                    "language": language,
                    "components": components
                }
            )
            
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao criar template: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # UPLOAD DE MÍDIA
    # =========================================================================
    
    async def upload_media(self, file_path: str, mime_type: str) -> Optional[str]:
        """
        Upload de mídia para o WhatsApp.
        Retorna o media_id para uso em mensagens.
        """
        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (file_path, f, mime_type),
                    "messaging_product": (None, "whatsapp"),
                    "type": (None, mime_type)
                }
                
                response = await self.client.post(
                    f"/{self.config.phone_number_id}/media",
                    files=files
                )
                
                if response.status_code == 200:
                    return response.json().get("id")
                
                return None
        except Exception as e:
            logger.error(f"Erro no upload: {e}")
            return None
    
    async def get_media_url(self, media_id: str) -> Optional[str]:
        """Obter URL de download de mídia"""
        try:
            response = await self.client.get(f"/{media_id}")
            
            if response.status_code == 200:
                return response.json().get("url")
            
            return None
        except Exception as e:
            logger.error(f"Erro ao obter URL da mídia: {e}")
            return None
    
    # =========================================================================
    # WEBHOOK
    # =========================================================================
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verificar webhook do Meta.
        Retorna o challenge se válido, None se inválido.
        """
        if mode == "subscribe" and token == self.config.webhook_verify_token:
            logger.info("Webhook verificado com sucesso")
            return challenge
        
        logger.warning(f"Verificação de webhook falhou: mode={mode}")
        return None
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verificar assinatura do webhook (X-Hub-Signature-256).
        Garante que a requisição veio do Meta.
        """
        if not self.config.app_secret:
            logger.warning("App secret não configurado, pulando verificação")
            return True
        
        expected = hmac.new(
            self.config.app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    def parse_webhook(self, data: Dict) -> List[WebhookMessage]:
        """
        Parsear webhook do WhatsApp.
        Extrai mensagens recebidas.
        """
        messages = []
        
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Ignorar se não for mensagem
                    if "messages" not in value:
                        continue
                    
                    contacts = {
                        c["wa_id"]: c.get("profile", {}).get("name", "")
                        for c in value.get("contacts", [])
                    }
                    
                    for msg in value.get("messages", []):
                        msg_type = msg.get("type", "text")
                        content = {}
                        
                        # Extrair conteúdo conforme tipo
                        if msg_type == "text":
                            content = {"text": msg.get("text", {}).get("body", "")}
                        
                        elif msg_type == "image":
                            img = msg.get("image", {})
                            content = {
                                "media_id": img.get("id"),
                                "mime_type": img.get("mime_type"),
                                "caption": img.get("caption")
                            }
                        
                        elif msg_type == "document":
                            doc = msg.get("document", {})
                            content = {
                                "media_id": doc.get("id"),
                                "mime_type": doc.get("mime_type"),
                                "filename": doc.get("filename"),
                                "caption": doc.get("caption")
                            }
                        
                        elif msg_type == "audio":
                            aud = msg.get("audio", {})
                            content = {
                                "media_id": aud.get("id"),
                                "mime_type": aud.get("mime_type"),
                                "voice": aud.get("voice", False)
                            }
                        
                        elif msg_type == "location":
                            loc = msg.get("location", {})
                            content = {
                                "latitude": loc.get("latitude"),
                                "longitude": loc.get("longitude"),
                                "name": loc.get("name"),
                                "address": loc.get("address")
                            }
                        
                        elif msg_type == "button":
                            content = {"text": msg.get("button", {}).get("text", "")}
                        
                        elif msg_type == "interactive":
                            interactive = msg.get("interactive", {})
                            int_type = interactive.get("type")
                            
                            if int_type == "button_reply":
                                content = {
                                    "button_id": interactive.get("button_reply", {}).get("id"),
                                    "button_text": interactive.get("button_reply", {}).get("title")
                                }
                            elif int_type == "list_reply":
                                content = {
                                    "list_id": interactive.get("list_reply", {}).get("id"),
                                    "list_title": interactive.get("list_reply", {}).get("title")
                                }
                        
                        # Contexto (mensagem respondida)
                        context = None
                        if "context" in msg:
                            context = {
                                "message_id": msg["context"].get("id"),
                                "from": msg["context"].get("from")
                            }
                        
                        from_number = msg.get("from", "")
                        
                        messages.append(WebhookMessage(
                            message_id=msg.get("id", ""),
                            from_number=from_number,
                            timestamp=datetime.fromtimestamp(int(msg.get("timestamp", 0))),
                            type=msg_type,
                            content=content,
                            context=context
                        ))
        
        except Exception as e:
            logger.error(f"Erro ao parsear webhook: {e}")
        
        return messages
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _format_phone(self, phone: str) -> str:
        """
        Formatar número de telefone para o padrão WhatsApp.
        Remove caracteres especiais, adiciona código do país.
        """
        # Remover tudo que não é dígito
        digits = ''.join(filter(str.isdigit, phone))
        
        # Se não começar com código do país, adicionar 55 (Brasil)
        if len(digits) <= 11:
            digits = "55" + digits
        
        # Garantir 9 dígitos no celular (alguns ainda têm 8)
        if len(digits) == 12 and digits[4] != '9':
            # Formato antigo: 55XX8XXXXXXX -> 55XX9XXXXXXXX
            digits = digits[:4] + '9' + digits[4:]
        
        return digits
    
    async def health_check(self) -> Dict[str, Any]:
        """Verificar status da API"""
        try:
            response = await self.client.get(
                f"/{self.config.phone_number_id}",
                params={"fields": "verified_name,quality_rating"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "verified_name": data.get("verified_name"),
                    "quality_rating": data.get("quality_rating"),
                    "phone_number_id": self.config.phone_number_id
                }
            
            return {"status": "unhealthy", "error": "API não respondeu corretamente"}
        
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Instância singleton
whatsapp_client = WhatsAppClient()
