"""
WhatsApp Business API Enterprise Integration
Integração completa com Meta Business API para WhatsApp

Features:
- Envio de mensagens de texto, mídia e templates
- Recebimento de mensagens via webhook
- Templates de mensagem aprovados pela Meta
- Gerenciamento de sessões de conversa
- Rate limiting e retry automático
- Métricas e logging estruturado
- Suporte a múltiplos números de telefone
"""

import httpx
import structlog
import json
import asyncio
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from functools import wraps
import re

from app.core.config import settings
from app.core.redis_client import redis_manager

logger = structlog.get_logger(__name__)


# =============================================================================
# ENUMS E TIPOS
# =============================================================================

class MessageType(str, Enum):
    """Tipos de mensagem WhatsApp"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    REACTION = "reaction"


class MessageStatus(str, Enum):
    """Status de mensagem"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class InteractiveType(str, Enum):
    """Tipos de mensagem interativa"""
    BUTTON = "button"
    LIST = "list"
    PRODUCT = "product"
    PRODUCT_LIST = "product_list"


class WebhookEventType(str, Enum):
    """Tipos de eventos do webhook"""
    MESSAGE = "message"
    STATUS = "status"
    ERROR = "error"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class WhatsAppContact:
    """Contato do WhatsApp"""
    wa_id: str  # Número com código do país (ex: 5511999999999)
    profile_name: Optional[str] = None
    
    @property
    def formatted_number(self) -> str:
        """Número formatado para exibição"""
        if len(self.wa_id) == 13 and self.wa_id.startswith("55"):
            # Brasileiro: +55 (11) 99999-9999
            return f"+{self.wa_id[:2]} ({self.wa_id[2:4]}) {self.wa_id[4:9]}-{self.wa_id[9:]}"
        return f"+{self.wa_id}"


@dataclass
class WhatsAppMessage:
    """Mensagem do WhatsApp"""
    id: str
    from_number: str
    to_number: str
    type: MessageType
    timestamp: datetime
    content: Dict[str, Any]
    status: MessageStatus = MessageStatus.PENDING
    context_message_id: Optional[str] = None  # Para respostas
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_number,
            "to": self.to_number,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "status": self.status.value,
            "context_message_id": self.context_message_id
        }


@dataclass
class MessageTemplate:
    """Template de mensagem aprovado pela Meta"""
    name: str
    language: str = "pt_BR"
    components: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_api_format(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "language": {"code": self.language},
            "components": self.components
        }


@dataclass
class WebhookEvent:
    """Evento recebido via webhook"""
    event_type: WebhookEventType
    timestamp: datetime
    phone_number_id: str
    data: Dict[str, Any]
    raw_payload: Dict[str, Any]


# =============================================================================
# TEMPLATES PRÉ-DEFINIDOS
# =============================================================================

class TemplateLibrary:
    """Biblioteca de templates de mensagem"""
    
    # Template: Boas-vindas
    WELCOME = MessageTemplate(
        name="welcome_message",
        components=[
            {
                "type": "header",
                "parameters": [{"type": "text", "text": "{{1}}"}]  # Nome do cliente
            },
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{1}}"},  # Nome da empresa
                ]
            }
        ]
    )
    
    # Template: Confirmação de atendimento
    TICKET_CREATED = MessageTemplate(
        name="ticket_created",
        components=[
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{1}}"},  # Número do ticket
                    {"type": "text", "text": "{{2}}"},  # Descrição
                ]
            }
        ]
    )
    
    # Template: Atualização de ticket
    TICKET_UPDATE = MessageTemplate(
        name="ticket_update",
        components=[
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{1}}"},  # Número do ticket
                    {"type": "text", "text": "{{2}}"},  # Status
                    {"type": "text", "text": "{{3}}"},  # Mensagem
                ]
            }
        ]
    )
    
    # Template: Fatura disponível
    INVOICE_READY = MessageTemplate(
        name="invoice_ready",
        components=[
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{1}}"},  # Nome do cliente
                    {"type": "text", "text": "{{2}}"},  # Valor
                    {"type": "text", "text": "{{3}}"},  # Vencimento
                ]
            },
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": "{{1}}"}]  # URL do boleto
            }
        ]
    )
    
    # Template: Lembrete de pagamento
    PAYMENT_REMINDER = MessageTemplate(
        name="payment_reminder",
        components=[
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{1}}"},  # Nome
                    {"type": "text", "text": "{{2}}"},  # Valor
                    {"type": "text", "text": "{{3}}"},  # Dias até vencimento
                ]
            }
        ]
    )
    
    # Template: Visita técnica agendada
    TECHNICAL_VISIT = MessageTemplate(
        name="technical_visit_scheduled",
        components=[
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{1}}"},  # Nome
                    {"type": "text", "text": "{{2}}"},  # Data
                    {"type": "text", "text": "{{3}}"},  # Horário
                    {"type": "text", "text": "{{4}}"},  # Técnico
                ]
            }
        ]
    )


# =============================================================================
# WHATSAPP ENTERPRISE API
# =============================================================================

class WhatsAppEnterpriseAPI:
    """
    API Enterprise do WhatsApp (Meta Business API)
    
    Documentação oficial:
    https://developers.facebook.com/docs/whatsapp/cloud-api
    """
    
    # URLs da API
    BASE_URL = "https://graph.facebook.com"
    API_VERSION = "v18.0"
    
    # Limites de rate
    MESSAGES_PER_SECOND = 80  # Limite padrão Meta
    MESSAGES_PER_DAY = 100000  # Tier 1
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.phone_number_id: Optional[str] = None
        self.business_account_id: Optional[str] = None
        self.webhook_verify_token: Optional[str] = None
        self.app_secret: Optional[str] = None
        
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        
        # Métricas
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_delivered": 0,
            "messages_read": 0,
            "messages_failed": 0,
            "templates_sent": 0,
            "media_sent": 0,
            "api_calls": 0,
            "api_errors": 0
        }
        
        # Cache de sessões ativas
        self._active_sessions: Dict[str, datetime] = {}
    
    @property
    def api_url(self) -> str:
        """URL base da API"""
        return f"{self.BASE_URL}/{self.API_VERSION}"
    
    @property
    def messages_url(self) -> str:
        """URL para envio de mensagens"""
        return f"{self.api_url}/{self.phone_number_id}/messages"
    
    @property
    def media_url(self) -> str:
        """URL para upload de mídia"""
        return f"{self.api_url}/{self.phone_number_id}/media"
    
    async def initialize(self):
        """Inicializar conexão com a API"""
        try:
            # Carregar configurações
            self.access_token = settings.WHATSAPP_ACCESS_TOKEN
            self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
            self.business_account_id = settings.WHATSAPP_BUSINESS_ACCOUNT_ID
            self.webhook_verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
            self.app_secret = settings.WHATSAPP_APP_SECRET
            
            # Validar configurações obrigatórias
            if not self.access_token or not self.phone_number_id:
                logger.warning(
                    "WhatsApp API not fully configured",
                    has_token=bool(self.access_token),
                    has_phone_id=bool(self.phone_number_id)
                )
                self._initialized = False
                return
            
            # Criar cliente HTTP
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            # Verificar conexão
            if await self._verify_connection():
                self._initialized = True
                logger.info(
                    "WhatsApp Enterprise API initialized",
                    phone_number_id=self.phone_number_id,
                    api_version=self.API_VERSION
                )
            else:
                logger.error("Failed to verify WhatsApp API connection")
                self._initialized = False
                
        except Exception as e:
            logger.error("Failed to initialize WhatsApp API", error=str(e))
            self._initialized = False
    
    async def close(self):
        """Fechar conexões"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("WhatsApp Enterprise API closed")
    
    async def _verify_connection(self) -> bool:
        """Verificar conexão com a API"""
        try:
            response = await self._client.get(
                f"{self.api_url}/{self.phone_number_id}"
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("Connection verification failed", error=str(e))
            return False
    
    def _ensure_initialized(func):
        """Decorator para verificar inicialização"""
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not self._initialized:
                logger.warning("WhatsApp API not initialized, attempting to initialize...")
                await self.initialize()
                if not self._initialized:
                    raise RuntimeError("WhatsApp API is not initialized")
            return await func(self, *args, **kwargs)
        return wrapper
    
    # =========================================================================
    # ENVIO DE MENSAGENS
    # =========================================================================
    
    @_ensure_initialized
    async def send_text_message(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensagem de texto simples
        
        Args:
            to: Número de destino (com código do país)
            text: Texto da mensagem (máx 4096 caracteres)
            preview_url: Se deve mostrar preview de URLs
            reply_to: ID da mensagem para responder
        """
        to = self._normalize_phone(to)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text[:4096]  # Limite da API
            }
        }
        
        if reply_to:
            payload["context"] = {"message_id": reply_to}
        
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_image(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_id: Optional[str] = None,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar imagem
        
        Args:
            to: Número de destino
            image_url: URL pública da imagem
            image_id: ID de mídia previamente enviada
            caption: Legenda (máx 1024 caracteres)
        """
        to = self._normalize_phone(to)
        
        image_data = {}
        if image_id:
            image_data["id"] = image_id
        elif image_url:
            image_data["link"] = image_url
        else:
            raise ValueError("Either image_url or image_id is required")
        
        if caption:
            image_data["caption"] = caption[:1024]
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image_data
        }
        
        if reply_to:
            payload["context"] = {"message_id": reply_to}
        
        self._metrics["media_sent"] += 1
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_document(
        self,
        to: str,
        document_url: Optional[str] = None,
        document_id: Optional[str] = None,
        filename: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar documento (PDF, DOC, etc.)
        
        Args:
            to: Número de destino
            document_url: URL pública do documento
            document_id: ID de mídia previamente enviada
            filename: Nome do arquivo
            caption: Legenda
        """
        to = self._normalize_phone(to)
        
        doc_data = {}
        if document_id:
            doc_data["id"] = document_id
        elif document_url:
            doc_data["link"] = document_url
        else:
            raise ValueError("Either document_url or document_id is required")
        
        if filename:
            doc_data["filename"] = filename
        if caption:
            doc_data["caption"] = caption[:1024]
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": doc_data
        }
        
        self._metrics["media_sent"] += 1
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_audio(
        self,
        to: str,
        audio_url: Optional[str] = None,
        audio_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enviar áudio"""
        to = self._normalize_phone(to)
        
        audio_data = {}
        if audio_id:
            audio_data["id"] = audio_id
        elif audio_url:
            audio_data["link"] = audio_url
        else:
            raise ValueError("Either audio_url or audio_id is required")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "audio",
            "audio": audio_data
        }
        
        self._metrics["media_sent"] += 1
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_video(
        self,
        to: str,
        video_url: Optional[str] = None,
        video_id: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enviar vídeo"""
        to = self._normalize_phone(to)
        
        video_data = {}
        if video_id:
            video_data["id"] = video_id
        elif video_url:
            video_data["link"] = video_url
        else:
            raise ValueError("Either video_url or video_id is required")
        
        if caption:
            video_data["caption"] = caption[:1024]
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "video",
            "video": video_data
        }
        
        self._metrics["media_sent"] += 1
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar localização
        
        Args:
            to: Número de destino
            latitude: Latitude
            longitude: Longitude
            name: Nome do local
            address: Endereço
        """
        to = self._normalize_phone(to)
        
        location_data = {
            "latitude": latitude,
            "longitude": longitude
        }
        
        if name:
            location_data["name"] = name
        if address:
            location_data["address"] = address
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "location",
            "location": location_data
        }
        
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_contacts(
        self,
        to: str,
        contacts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enviar contatos
        
        Args:
            to: Número de destino
            contacts: Lista de contatos no formato da API
        """
        to = self._normalize_phone(to)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "contacts",
            "contacts": contacts
        }
        
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_reaction(
        self,
        to: str,
        message_id: str,
        emoji: str
    ) -> Dict[str, Any]:
        """
        Enviar reação a uma mensagem
        
        Args:
            to: Número de destino
            message_id: ID da mensagem para reagir
            emoji: Emoji da reação (ou vazio para remover)
        """
        to = self._normalize_phone(to)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "reaction",
            "reaction": {
                "message_id": message_id,
                "emoji": emoji
            }
        }
        
        return await self._send_message(payload)
    
    # =========================================================================
    # MENSAGENS INTERATIVAS
    # =========================================================================
    
    @_ensure_initialized
    async def send_button_message(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensagem com botões
        
        Args:
            to: Número de destino
            body_text: Texto principal
            buttons: Lista de botões [{"id": "btn1", "title": "Opção 1"}, ...]
            header_text: Texto do cabeçalho
            footer_text: Texto do rodapé
        """
        to = self._normalize_phone(to)
        
        if len(buttons) > 3:
            raise ValueError("Maximum 3 buttons allowed")
        
        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": btn["id"], "title": btn["title"][:20]}
                    }
                    for btn in buttons
                ]
            }
        }
        
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }
        
        return await self._send_message(payload)
    
    @_ensure_initialized
    async def send_list_message(
        self,
        to: str,
        body_text: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensagem com lista de opções
        
        Args:
            to: Número de destino
            body_text: Texto principal
            button_text: Texto do botão para abrir lista
            sections: Seções da lista
            header_text: Texto do cabeçalho
            footer_text: Texto do rodapé
        
        Exemplo de sections:
        [
            {
                "title": "Seção 1",
                "rows": [
                    {"id": "opt1", "title": "Opção 1", "description": "Descrição"},
                    {"id": "opt2", "title": "Opção 2", "description": "Descrição"}
                ]
            }
        ]
        """
        to = self._normalize_phone(to)
        
        interactive = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text[:20],
                "sections": sections
            }
        }
        
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }
        
        return await self._send_message(payload)
    
    # =========================================================================
    # TEMPLATES
    # =========================================================================
    
    @_ensure_initialized
    async def send_template(
        self,
        to: str,
        template: Union[MessageTemplate, str],
        parameters: Optional[List[str]] = None,
        language: str = "pt_BR"
    ) -> Dict[str, Any]:
        """
        Enviar mensagem de template
        
        Templates devem ser aprovados pela Meta antes do uso.
        
        Args:
            to: Número de destino
            template: Template ou nome do template
            parameters: Parâmetros para substituição
            language: Código do idioma
        """
        to = self._normalize_phone(to)
        
        if isinstance(template, str):
            template_data = {
                "name": template,
                "language": {"code": language}
            }
            
            if parameters:
                template_data["components"] = [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": p} for p in parameters
                        ]
                    }
                ]
        else:
            template_data = template.to_api_format()
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template_data
        }
        
        self._metrics["templates_sent"] += 1
        return await self._send_message(payload)
    
    async def send_welcome_template(self, to: str, customer_name: str, company_name: str) -> Dict[str, Any]:
        """Enviar template de boas-vindas"""
        return await self.send_template(
            to=to,
            template="welcome_message",
            parameters=[customer_name, company_name]
        )
    
    async def send_invoice_template(
        self,
        to: str,
        customer_name: str,
        amount: str,
        due_date: str,
        invoice_url: str
    ) -> Dict[str, Any]:
        """Enviar template de fatura"""
        return await self.send_template(
            to=to,
            template="invoice_ready",
            parameters=[customer_name, amount, due_date, invoice_url]
        )
    
    async def send_payment_reminder_template(
        self,
        to: str,
        customer_name: str,
        amount: str,
        days_until_due: str
    ) -> Dict[str, Any]:
        """Enviar template de lembrete de pagamento"""
        return await self.send_template(
            to=to,
            template="payment_reminder",
            parameters=[customer_name, amount, days_until_due]
        )
    
    async def send_ticket_template(
        self,
        to: str,
        ticket_number: str,
        description: str
    ) -> Dict[str, Any]:
        """Enviar template de ticket criado"""
        return await self.send_template(
            to=to,
            template="ticket_created",
            parameters=[ticket_number, description]
        )
    
    async def send_visit_template(
        self,
        to: str,
        customer_name: str,
        date: str,
        time: str,
        technician: str
    ) -> Dict[str, Any]:
        """Enviar template de visita técnica agendada"""
        return await self.send_template(
            to=to,
            template="technical_visit_scheduled",
            parameters=[customer_name, date, time, technician]
        )
    
    # =========================================================================
    # UPLOAD DE MÍDIA
    # =========================================================================
    
    @_ensure_initialized
    async def upload_media(
        self,
        file_path: str,
        media_type: str
    ) -> Dict[str, Any]:
        """
        Fazer upload de mídia para a API
        
        Args:
            file_path: Caminho do arquivo local
            media_type: MIME type (ex: image/jpeg, application/pdf)
        
        Returns:
            {"id": "media_id_here"}
        """
        with open(file_path, "rb") as f:
            files = {
                "file": (file_path, f, media_type),
                "messaging_product": (None, "whatsapp"),
                "type": (None, media_type)
            }
            
            response = await self._client.post(
                self.media_url,
                files=files
            )
            
            self._metrics["api_calls"] += 1
            
            if response.status_code == 200:
                return response.json()
            else:
                self._metrics["api_errors"] += 1
                raise Exception(f"Media upload failed: {response.text}")
    
    @_ensure_initialized
    async def get_media_url(self, media_id: str) -> str:
        """
        Obter URL de download de mídia
        
        Args:
            media_id: ID da mídia recebida
        
        Returns:
            URL temporária para download
        """
        response = await self._client.get(f"{self.api_url}/{media_id}")
        
        self._metrics["api_calls"] += 1
        
        if response.status_code == 200:
            data = response.json()
            return data.get("url", "")
        else:
            self._metrics["api_errors"] += 1
            raise Exception(f"Failed to get media URL: {response.text}")
    
    @_ensure_initialized
    async def download_media(self, media_url: str) -> bytes:
        """
        Download de arquivo de mídia
        
        Args:
            media_url: URL obtida via get_media_url()
        
        Returns:
            Conteúdo do arquivo em bytes
        """
        response = await self._client.get(
            media_url,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Media download failed: {response.status_code}")
    
    # =========================================================================
    # WEBHOOK
    # =========================================================================
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verificar webhook (GET request da Meta)
        
        Args:
            mode: hub.mode
            token: hub.verify_token
            challenge: hub.challenge
        
        Returns:
            challenge se válido, None caso contrário
        """
        if mode == "subscribe" and token == self.webhook_verify_token:
            logger.info("Webhook verified successfully")
            return challenge
        
        logger.warning("Webhook verification failed", mode=mode)
        return None
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verificar assinatura do webhook
        
        Args:
            payload: Body da requisição
            signature: Header X-Hub-Signature-256
        
        Returns:
            True se assinatura válida
        """
        if not self.app_secret:
            logger.warning("App secret not configured, skipping signature verification")
            return True
        
        expected = "sha256=" + hmac.new(
            self.app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    async def process_webhook(self, payload: Dict[str, Any]) -> List[WebhookEvent]:
        """
        Processar payload do webhook
        
        Args:
            payload: JSON recebido no webhook
        
        Returns:
            Lista de eventos processados
        """
        events = []
        
        try:
            if payload.get("object") != "whatsapp_business_account":
                return events
            
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") != "messages":
                        continue
                    
                    value = change.get("value", {})
                    phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
                    
                    # Processar mensagens recebidas
                    for message in value.get("messages", []):
                        event = await self._process_incoming_message(message, value, phone_number_id)
                        if event:
                            events.append(event)
                    
                    # Processar status de mensagens
                    for status in value.get("statuses", []):
                        event = await self._process_status_update(status, phone_number_id)
                        if event:
                            events.append(event)
            
        except Exception as e:
            logger.error("Error processing webhook", error=str(e), payload=payload)
        
        return events
    
    async def _process_incoming_message(
        self,
        message: Dict[str, Any],
        value: Dict[str, Any],
        phone_number_id: str
    ) -> Optional[WebhookEvent]:
        """Processar mensagem recebida"""
        try:
            msg_type = message.get("type", "text")
            from_number = message.get("from", "")
            msg_id = message.get("id", "")
            timestamp = datetime.fromtimestamp(
                int(message.get("timestamp", 0)),
                tz=timezone.utc
            )
            
            # Extrair conteúdo baseado no tipo
            content = {}
            
            if msg_type == "text":
                content = {"body": message.get("text", {}).get("body", "")}
            
            elif msg_type == "image":
                img = message.get("image", {})
                content = {
                    "media_id": img.get("id"),
                    "mime_type": img.get("mime_type"),
                    "caption": img.get("caption"),
                    "sha256": img.get("sha256")
                }
            
            elif msg_type == "document":
                doc = message.get("document", {})
                content = {
                    "media_id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "mime_type": doc.get("mime_type"),
                    "caption": doc.get("caption")
                }
            
            elif msg_type == "audio":
                audio = message.get("audio", {})
                content = {
                    "media_id": audio.get("id"),
                    "mime_type": audio.get("mime_type"),
                    "voice": audio.get("voice", False)
                }
            
            elif msg_type == "video":
                video = message.get("video", {})
                content = {
                    "media_id": video.get("id"),
                    "mime_type": video.get("mime_type"),
                    "caption": video.get("caption")
                }
            
            elif msg_type == "location":
                loc = message.get("location", {})
                content = {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                    "name": loc.get("name"),
                    "address": loc.get("address")
                }
            
            elif msg_type == "contacts":
                content = {"contacts": message.get("contacts", [])}
            
            elif msg_type == "interactive":
                interactive = message.get("interactive", {})
                int_type = interactive.get("type", "")
                
                if int_type == "button_reply":
                    reply = interactive.get("button_reply", {})
                    content = {
                        "button_id": reply.get("id"),
                        "button_title": reply.get("title")
                    }
                elif int_type == "list_reply":
                    reply = interactive.get("list_reply", {})
                    content = {
                        "list_id": reply.get("id"),
                        "list_title": reply.get("title"),
                        "list_description": reply.get("description")
                    }
            
            elif msg_type == "button":
                # Resposta de botão de template
                content = {
                    "button_text": message.get("button", {}).get("text"),
                    "button_payload": message.get("button", {}).get("payload")
                }
            
            elif msg_type == "reaction":
                reaction = message.get("reaction", {})
                content = {
                    "message_id": reaction.get("message_id"),
                    "emoji": reaction.get("emoji")
                }
            
            # Contexto (se for resposta)
            context = message.get("context", {})
            
            # Informações do contato
            contacts = value.get("contacts", [])
            contact_name = ""
            if contacts:
                contact_name = contacts[0].get("profile", {}).get("name", "")
            
            self._metrics["messages_received"] += 1
            
            # Atualizar sessão ativa
            self._active_sessions[from_number] = datetime.now(timezone.utc)
            
            # Cachear no Redis
            await self._cache_incoming_message(msg_id, {
                "from": from_number,
                "type": msg_type,
                "content": content,
                "timestamp": timestamp.isoformat(),
                "contact_name": contact_name
            })
            
            return WebhookEvent(
                event_type=WebhookEventType.MESSAGE,
                timestamp=timestamp,
                phone_number_id=phone_number_id,
                data={
                    "message_id": msg_id,
                    "from": from_number,
                    "contact_name": contact_name,
                    "type": msg_type,
                    "content": content,
                    "context": context
                },
                raw_payload=message
            )
            
        except Exception as e:
            logger.error("Error processing incoming message", error=str(e))
            return None
    
    async def _process_status_update(
        self,
        status: Dict[str, Any],
        phone_number_id: str
    ) -> Optional[WebhookEvent]:
        """Processar atualização de status"""
        try:
            msg_id = status.get("id", "")
            status_type = status.get("status", "")
            recipient = status.get("recipient_id", "")
            timestamp = datetime.fromtimestamp(
                int(status.get("timestamp", 0)),
                tz=timezone.utc
            )
            
            # Atualizar métricas
            if status_type == "sent":
                self._metrics["messages_sent"] += 1
            elif status_type == "delivered":
                self._metrics["messages_delivered"] += 1
            elif status_type == "read":
                self._metrics["messages_read"] += 1
            elif status_type == "failed":
                self._metrics["messages_failed"] += 1
                
                # Log de erro
                errors = status.get("errors", [])
                if errors:
                    logger.error(
                        "Message delivery failed",
                        message_id=msg_id,
                        errors=errors
                    )
            
            return WebhookEvent(
                event_type=WebhookEventType.STATUS,
                timestamp=timestamp,
                phone_number_id=phone_number_id,
                data={
                    "message_id": msg_id,
                    "status": status_type,
                    "recipient": recipient,
                    "errors": status.get("errors", [])
                },
                raw_payload=status
            )
            
        except Exception as e:
            logger.error("Error processing status update", error=str(e))
            return None
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    async def _send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enviar mensagem via API"""
        try:
            # Rate limiting
            await self._check_rate_limit()
            
            response = await self._client.post(
                self.messages_url,
                json=payload
            )
            
            self._metrics["api_calls"] += 1
            
            if response.status_code == 200:
                result = response.json()
                
                self._metrics["messages_sent"] += 1
                
                logger.info(
                    "Message sent successfully",
                    to=payload.get("to"),
                    type=payload.get("type"),
                    message_id=result.get("messages", [{}])[0].get("id")
                )
                
                return result
            else:
                self._metrics["api_errors"] += 1
                error_data = response.json()
                
                logger.error(
                    "Failed to send message",
                    status_code=response.status_code,
                    error=error_data
                )
                
                raise WhatsAppAPIError(
                    message=error_data.get("error", {}).get("message", "Unknown error"),
                    code=error_data.get("error", {}).get("code"),
                    details=error_data
                )
                
        except WhatsAppAPIError:
            raise
        except Exception as e:
            self._metrics["api_errors"] += 1
            logger.error("Error sending message", error=str(e))
            raise
    
    async def _check_rate_limit(self):
        """Verificar rate limit"""
        key = "whatsapp:rate_limit:messages"
        
        try:
            current = await redis_manager.get(key)
            if current and int(current) >= self.MESSAGES_PER_SECOND:
                # Aguardar um pouco
                await asyncio.sleep(0.1)
            
            # Incrementar contador
            await redis_manager.client.incr(key)
            await redis_manager.client.expire(key, 1)
            
        except Exception:
            # Em caso de erro no Redis, continuar
            pass
    
    async def _cache_incoming_message(self, msg_id: str, data: Dict[str, Any]):
        """Cachear mensagem recebida no Redis"""
        try:
            key = f"whatsapp:msg:{msg_id}"
            await redis_manager.set(key, json.dumps(data), ex=86400)  # 24h
        except Exception:
            pass
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalizar número de telefone"""
        # Remover caracteres não numéricos
        phone = re.sub(r'\D', '', phone)
        
        # Adicionar código do país se necessário
        if len(phone) == 11 and phone.startswith('0'):
            # Remover zero inicial (DDD brasileiro)
            phone = '55' + phone[1:]
        elif len(phone) == 10 or len(phone) == 11:
            # Adicionar código do Brasil
            phone = '55' + phone
        
        return phone
    
    # =========================================================================
    # MÉTRICAS E HEALTH CHECK
    # =========================================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obter métricas do serviço"""
        return {
            **self._metrics,
            "initialized": self._initialized,
            "active_sessions": len(self._active_sessions)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check do serviço"""
        status = "healthy" if self._initialized else "unhealthy"
        
        details = {
            "status": status,
            "initialized": self._initialized,
            "phone_number_id": self.phone_number_id[:5] + "..." if self.phone_number_id else None,
            "api_version": self.API_VERSION
        }
        
        if self._initialized:
            try:
                # Testar conexão
                response = await self._client.get(
                    f"{self.api_url}/{self.phone_number_id}"
                )
                details["api_connection"] = response.status_code == 200
            except Exception as e:
                details["api_connection"] = False
                details["error"] = str(e)
        
        return details
    
    def is_session_active(self, phone: str) -> bool:
        """
        Verificar se sessão de 24h está ativa
        
        Após a última mensagem do cliente, você pode enviar
        mensagens fora de templates por 24h.
        """
        phone = self._normalize_phone(phone)
        last_message = self._active_sessions.get(phone)
        
        if not last_message:
            return False
        
        return (datetime.now(timezone.utc) - last_message) < timedelta(hours=24)


# =============================================================================
# EXCEÇÕES
# =============================================================================

class WhatsAppAPIError(Exception):
    """Erro da API do WhatsApp"""
    
    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


# =============================================================================
# INSTÂNCIA GLOBAL
# =============================================================================

whatsapp_api = WhatsAppEnterpriseAPI()