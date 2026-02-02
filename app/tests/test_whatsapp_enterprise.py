"""
Testes para WhatsApp Enterprise API
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.whatsapp_enterprise import (
    WhatsAppEnterpriseAPI,
    WhatsAppMessage,
    WhatsAppContact,
    MessageType,
    MessageStatus,
    WebhookEvent,
    WebhookEventType,
    MessageTemplate,
    TemplateLibrary,
    WhatsAppAPIError
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def whatsapp_api():
    """API para testes"""
    api = WhatsAppEnterpriseAPI()
    api.access_token = "test_token"
    api.phone_number_id = "123456789"
    api.business_account_id = "987654321"
    api.webhook_verify_token = "my_verify_token"
    api.app_secret = "my_app_secret"
    return api


@pytest.fixture
def mock_client():
    """Mock do cliente HTTP"""
    client = AsyncMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    return client


@pytest.fixture
def sample_webhook_message():
    """Payload de webhook com mensagem"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "5511999999999",
                        "phone_number_id": "123456789"
                    },
                    "contacts": [{
                        "profile": {"name": "João Silva"},
                        "wa_id": "5511999999999"
                    }],
                    "messages": [{
                        "from": "5511999999999",
                        "id": "wamid.123",
                        "timestamp": "1704067200",
                        "type": "text",
                        "text": {"body": "Olá, preciso de ajuda!"}
                    }]
                }
            }]
        }]
    }


@pytest.fixture
def sample_webhook_status():
    """Payload de webhook com status"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "5511999999999",
                        "phone_number_id": "123456789"
                    },
                    "statuses": [{
                        "id": "wamid.123",
                        "status": "delivered",
                        "timestamp": "1704067200",
                        "recipient_id": "5511888888888"
                    }]
                }
            }]
        }]
    }


# =============================================================================
# TESTES DE DATA CLASSES
# =============================================================================

class TestWhatsAppContact:
    """Testes para WhatsAppContact"""
    
    def test_create_contact(self):
        """Criar contato"""
        contact = WhatsAppContact(
            wa_id="5511999999999",
            profile_name="João"
        )
        
        assert contact.wa_id == "5511999999999"
        assert contact.profile_name == "João"
    
    def test_formatted_number_brazilian(self):
        """Formatar número brasileiro"""
        contact = WhatsAppContact(wa_id="5511999999999")
        assert contact.formatted_number == "+55 (11) 99999-9999"
    
    def test_formatted_number_other(self):
        """Formatar número de outro país"""
        contact = WhatsAppContact(wa_id="1555123456")
        assert contact.formatted_number == "+1555123456"


class TestWhatsAppMessage:
    """Testes para WhatsAppMessage"""
    
    def test_create_message(self):
        """Criar mensagem"""
        msg = WhatsAppMessage(
            id="msg_123",
            from_number="5511999999999",
            to_number="5511888888888",
            type=MessageType.TEXT,
            timestamp=datetime.now(timezone.utc),
            content={"body": "Olá!"}
        )
        
        assert msg.id == "msg_123"
        assert msg.type == MessageType.TEXT
        assert msg.status == MessageStatus.PENDING
    
    def test_message_to_dict(self):
        """Converter mensagem para dict"""
        msg = WhatsAppMessage(
            id="msg_123",
            from_number="5511999999999",
            to_number="5511888888888",
            type=MessageType.TEXT,
            timestamp=datetime.now(timezone.utc),
            content={"body": "Olá!"}
        )
        
        data = msg.to_dict()
        
        assert data["id"] == "msg_123"
        assert data["type"] == "text"
        assert data["status"] == "pending"


class TestMessageTemplate:
    """Testes para MessageTemplate"""
    
    def test_create_template(self):
        """Criar template"""
        template = MessageTemplate(
            name="test_template",
            language="pt_BR",
            components=[{"type": "body", "parameters": []}]
        )
        
        assert template.name == "test_template"
        assert template.language == "pt_BR"
    
    def test_template_to_api_format(self):
        """Converter template para formato API"""
        template = MessageTemplate(
            name="test_template",
            components=[{"type": "body", "parameters": [{"type": "text", "text": "Test"}]}]
        )
        
        api_format = template.to_api_format()
        
        assert api_format["name"] == "test_template"
        assert api_format["language"]["code"] == "pt_BR"
        assert len(api_format["components"]) == 1


class TestTemplateLibrary:
    """Testes para biblioteca de templates"""
    
    def test_welcome_template(self):
        """Template de boas-vindas"""
        assert TemplateLibrary.WELCOME.name == "welcome_message"
        assert len(TemplateLibrary.WELCOME.components) > 0
    
    def test_invoice_template(self):
        """Template de fatura"""
        assert TemplateLibrary.INVOICE_READY.name == "invoice_ready"
    
    def test_payment_reminder_template(self):
        """Template de lembrete de pagamento"""
        assert TemplateLibrary.PAYMENT_REMINDER.name == "payment_reminder"


# =============================================================================
# TESTES DE WhatsAppEnterpriseAPI
# =============================================================================

class TestWhatsAppEnterpriseAPI:
    """Testes para WhatsAppEnterpriseAPI"""
    
    def test_api_urls(self, whatsapp_api):
        """URLs da API"""
        assert "graph.facebook.com" in whatsapp_api.api_url
        assert "v18.0" in whatsapp_api.api_url
        assert whatsapp_api.phone_number_id in whatsapp_api.messages_url
    
    def test_normalize_phone_with_ddd(self, whatsapp_api):
        """Normalizar telefone com DDD"""
        # Número com código do país
        assert whatsapp_api._normalize_phone("5511999999999") == "5511999999999"
        
        # Número sem código do país (11 dígitos)
        assert whatsapp_api._normalize_phone("11999999999") == "5511999999999"
        
        # Número com formatação
        assert whatsapp_api._normalize_phone("+55 (11) 99999-9999") == "5511999999999"
    
    def test_verify_webhook_success(self, whatsapp_api):
        """Verificar webhook com sucesso"""
        result = whatsapp_api.verify_webhook(
            mode="subscribe",
            token="my_verify_token",
            challenge="challenge_123"
        )
        
        assert result == "challenge_123"
    
    def test_verify_webhook_failure(self, whatsapp_api):
        """Verificar webhook com falha"""
        result = whatsapp_api.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="challenge_123"
        )
        
        assert result is None
    
    def test_is_session_active_no_session(self, whatsapp_api):
        """Sessão não existe"""
        assert whatsapp_api.is_session_active("5511999999999") is False
    
    def test_get_metrics(self, whatsapp_api):
        """Obter métricas"""
        metrics = whatsapp_api.get_metrics()
        
        assert "messages_sent" in metrics
        assert "messages_received" in metrics
        assert "api_calls" in metrics
        assert "initialized" in metrics


# =============================================================================
# TESTES DE WEBHOOK PROCESSING
# =============================================================================

class TestWebhookProcessing:
    """Testes para processamento de webhook"""
    
    @pytest.mark.asyncio
    async def test_process_text_message(self, whatsapp_api, sample_webhook_message):
        """Processar mensagem de texto"""
        with patch.object(whatsapp_api, '_cache_incoming_message', new_callable=AsyncMock):
            events = await whatsapp_api.process_webhook(sample_webhook_message)
        
        assert len(events) == 1
        event = events[0]
        
        assert event.event_type == WebhookEventType.MESSAGE
        assert event.data["from"] == "5511999999999"
        assert event.data["type"] == "text"
        assert event.data["content"]["body"] == "Olá, preciso de ajuda!"
    
    @pytest.mark.asyncio
    async def test_process_status_update(self, whatsapp_api, sample_webhook_status):
        """Processar atualização de status"""
        events = await whatsapp_api.process_webhook(sample_webhook_status)
        
        assert len(events) == 1
        event = events[0]
        
        assert event.event_type == WebhookEventType.STATUS
        assert event.data["status"] == "delivered"
        assert event.data["message_id"] == "wamid.123"
    
    @pytest.mark.asyncio
    async def test_process_invalid_object(self, whatsapp_api):
        """Ignorar objeto inválido"""
        payload = {"object": "invalid"}
        events = await whatsapp_api.process_webhook(payload)
        
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_metrics_update_on_message(self, whatsapp_api, sample_webhook_message):
        """Métricas atualizadas ao receber mensagem"""
        initial = whatsapp_api._metrics["messages_received"]
        
        with patch.object(whatsapp_api, '_cache_incoming_message', new_callable=AsyncMock):
            await whatsapp_api.process_webhook(sample_webhook_message)
        
        assert whatsapp_api._metrics["messages_received"] == initial + 1


# =============================================================================
# TESTES DE ENVIO DE MENSAGENS
# =============================================================================

class TestMessageSending:
    """Testes para envio de mensagens"""
    
    @pytest.mark.asyncio
    async def test_send_text_message_payload(self, whatsapp_api, mock_client):
        """Verificar payload de mensagem de texto"""
        whatsapp_api._client = mock_client
        whatsapp_api._initialized = True
        
        mock_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "msg_123"}]}
        )
        
        with patch.object(whatsapp_api, '_check_rate_limit', new_callable=AsyncMock):
            result = await whatsapp_api.send_text_message(
                to="5511999999999",
                text="Olá, tudo bem?"
            )
        
        # Verificar chamada
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json", call_args[1].get("json", {}))
        
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Olá, tudo bem?"
    
    @pytest.mark.asyncio
    async def test_send_button_message_limit(self, whatsapp_api, mock_client):
        """Limite de 3 botões"""
        whatsapp_api._client = mock_client
        whatsapp_api._initialized = True
        
        # Mais de 3 botões deve dar erro
        with pytest.raises(ValueError, match="Maximum 3 buttons"):
            await whatsapp_api.send_button_message(
                to="5511999999999",
                body_text="Escolha uma opção",
                buttons=[
                    {"id": "1", "title": "Um"},
                    {"id": "2", "title": "Dois"},
                    {"id": "3", "title": "Três"},
                    {"id": "4", "title": "Quatro"}
                ]
            )
    
    @pytest.mark.asyncio
    async def test_send_image_requires_url_or_id(self, whatsapp_api):
        """Imagem requer URL ou ID"""
        whatsapp_api._initialized = True
        
        with pytest.raises(ValueError, match="Either image_url or image_id"):
            await whatsapp_api.send_image(to="5511999999999")


# =============================================================================
# TESTES DE SIGNATURE VERIFICATION
# =============================================================================

class TestSignatureVerification:
    """Testes para verificação de assinatura"""
    
    def test_verify_signature_valid(self, whatsapp_api):
        """Assinatura válida"""
        import hmac
        import hashlib
        
        payload = b'{"test": "data"}'
        expected_sig = "sha256=" + hmac.new(
            whatsapp_api.app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        result = whatsapp_api.verify_signature(payload, expected_sig)
        assert result is True
    
    def test_verify_signature_invalid(self, whatsapp_api):
        """Assinatura inválida"""
        payload = b'{"test": "data"}'
        result = whatsapp_api.verify_signature(payload, "sha256=invalid")
        assert result is False
    
    def test_verify_signature_no_secret(self, whatsapp_api):
        """Sem app_secret configurado"""
        whatsapp_api.app_secret = None
        result = whatsapp_api.verify_signature(b"test", "sha256=test")
        assert result is True  # Deve passar quando não há secret


# =============================================================================
# EXECUTAR TESTES
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
