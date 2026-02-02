"""
Testes para o Chatbot AI Enterprise
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.chatbot_ai import (
    ChatbotAI,
    IntentType,
    SentimentType,
    ConversationContext,
    ConversationState,
    ChatResponse,
    process_whatsapp_message,
    is_business_hours
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def chatbot():
    """Criar instância do chatbot para testes"""
    bot = ChatbotAI()
    bot.initialized = True
    return bot


@pytest.fixture
def conversation_context():
    """Criar contexto de conversa para testes"""
    return ConversationContext(
        conversation_id="test:123",
        cliente_nome="João Silva",
        cliente_telefone="5511999999999",
        cliente_plano="Plus 200MB"
    )


# =============================================================================
# TESTES DE CLASSIFICAÇÃO DE INTENÇÃO
# =============================================================================

class TestIntentClassification:
    """Testes para classificação de intenções"""
    
    @pytest.mark.asyncio
    async def test_classify_saudacao(self, chatbot):
        """Deve classificar saudações corretamente"""
        messages = ["Olá", "Oi", "Bom dia", "Boa tarde", "Boa noite"]
        
        for msg in messages:
            intent, confidence = await chatbot.classify_intent(msg)
            assert intent == IntentType.SAUDACAO, f"Falhou para: {msg}"
            assert confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_classify_internet_lenta(self, chatbot):
        """Deve classificar problemas de internet lenta"""
        messages = [
            "Minha internet está muito lenta",
            "A velocidade está baixa",
            "Tá travando muito",
            "Internet devagar demais"
        ]
        
        for msg in messages:
            intent, confidence = await chatbot.classify_intent(msg)
            assert intent == IntentType.INTERNET_LENTA, f"Falhou para: {msg}"
    
    @pytest.mark.asyncio
    async def test_classify_sem_conexao(self, chatbot):
        """Deve classificar problemas de conexão"""
        messages = [
            "Estou sem internet",
            "A internet caiu",
            "Não conecta de jeito nenhum",
            "Tô offline"
        ]
        
        for msg in messages:
            intent, confidence = await chatbot.classify_intent(msg)
            assert intent == IntentType.SEM_CONEXAO, f"Falhou para: {msg}"
    
    @pytest.mark.asyncio
    async def test_classify_segunda_via(self, chatbot):
        """Deve classificar pedidos de segunda via"""
        messages = [
            "Preciso da segunda via do boleto",
            "Me manda o boleto por favor",
            "Quero pagar via PIX"
        ]
        
        for msg in messages:
            intent, confidence = await chatbot.classify_intent(msg)
            assert intent == IntentType.SEGUNDA_VIA_BOLETO, f"Falhou para: {msg}"
    
    @pytest.mark.asyncio
    async def test_classify_cancelamento(self, chatbot):
        """Deve classificar pedidos de cancelamento"""
        messages = [
            "Quero cancelar meu plano",
            "Cancelamento por favor",
            "Preciso encerrar o contrato"
        ]
        
        for msg in messages:
            intent, confidence = await chatbot.classify_intent(msg)
            assert intent == IntentType.CANCELAMENTO, f"Falhou para: {msg}"
    
    @pytest.mark.asyncio
    async def test_classify_falar_humano(self, chatbot):
        """Deve classificar pedidos de atendente humano"""
        messages = [
            "Quero falar com um humano",
            "Me transfere para um atendente",
            "Quero falar com uma pessoa real"
        ]
        
        for msg in messages:
            intent, confidence = await chatbot.classify_intent(msg)
            assert intent == IntentType.FALAR_HUMANO, f"Falhou para: {msg}"


# =============================================================================
# TESTES DE ANÁLISE DE SENTIMENTO
# =============================================================================

class TestSentimentAnalysis:
    """Testes para análise de sentimento"""
    
    @pytest.mark.asyncio
    async def test_sentiment_positivo(self, chatbot):
        """Deve identificar sentimento positivo"""
        messages = [
            "Muito obrigado pela ajuda!",
            "Excelente atendimento!",
            "Adorei o serviço de vocês"
        ]
        
        for msg in messages:
            sentiment = await chatbot.analyze_sentiment(msg)
            assert sentiment in [SentimentType.POSITIVO, SentimentType.MUITO_POSITIVO], f"Falhou para: {msg}"
    
    @pytest.mark.asyncio
    async def test_sentiment_negativo(self, chatbot):
        """Deve identificar sentimento negativo"""
        messages = [
            "Serviço péssimo!",
            "Isso é um absurdo!",
            "Vou reclamar no Procon"
        ]
        
        for msg in messages:
            sentiment = await chatbot.analyze_sentiment(msg)
            assert sentiment in [SentimentType.NEGATIVO, SentimentType.MUITO_NEGATIVO], f"Falhou para: {msg}"
    
    @pytest.mark.asyncio
    async def test_sentiment_neutro(self, chatbot):
        """Deve identificar sentimento neutro"""
        messages = [
            "Qual o valor do plano?",
            "Quero saber sobre os serviços",
            "Me explica como funciona"
        ]
        
        for msg in messages:
            sentiment = await chatbot.analyze_sentiment(msg)
            assert sentiment == SentimentType.NEUTRO, f"Falhou para: {msg}"


# =============================================================================
# TESTES DE ESCALAÇÃO
# =============================================================================

class TestEscalation:
    """Testes para lógica de escalação"""
    
    def test_escalate_on_cancelamento(self, chatbot, conversation_context):
        """Deve escalar pedidos de cancelamento"""
        should_escalate, reason = chatbot.should_escalate(
            conversation_context,
            IntentType.CANCELAMENTO,
            SentimentType.NEUTRO
        )
        
        assert should_escalate is True
        assert "cancelamento" in reason.lower()
    
    def test_escalate_on_falar_humano(self, chatbot, conversation_context):
        """Deve escalar quando cliente pede humano"""
        should_escalate, reason = chatbot.should_escalate(
            conversation_context,
            IntentType.FALAR_HUMANO,
            SentimentType.NEUTRO
        )
        
        assert should_escalate is True
        assert "humano" in reason.lower()
    
    def test_escalate_on_muito_negativo(self, chatbot, conversation_context):
        """Deve escalar quando sentimento muito negativo"""
        should_escalate, reason = chatbot.should_escalate(
            conversation_context,
            IntentType.INTERNET_LENTA,
            SentimentType.MUITO_NEGATIVO
        )
        
        assert should_escalate is True
        assert "insatisfeito" in reason.lower()
    
    def test_escalate_on_max_attempts(self, chatbot, conversation_context):
        """Deve escalar após máximo de tentativas"""
        conversation_context.bot_attempts = 3
        
        should_escalate, reason = chatbot.should_escalate(
            conversation_context,
            IntentType.DESCONHECIDO,
            SentimentType.NEUTRO
        )
        
        assert should_escalate is True
        assert "tentativas" in reason.lower()
    
    def test_no_escalate_normal_flow(self, chatbot, conversation_context):
        """Não deve escalar em fluxo normal"""
        should_escalate, reason = chatbot.should_escalate(
            conversation_context,
            IntentType.INTERNET_LENTA,
            SentimentType.NEUTRO
        )
        
        assert should_escalate is False


# =============================================================================
# TESTES DE CONTEXTO
# =============================================================================

class TestConversationContext:
    """Testes para contexto de conversa"""
    
    def test_add_message(self, conversation_context):
        """Deve adicionar mensagens ao histórico"""
        conversation_context.add_message("user", "Olá")
        conversation_context.add_message("assistant", "Oi! Como posso ajudar?")
        
        assert len(conversation_context.messages) == 2
        assert conversation_context.messages[0]["role"] == "user"
        assert conversation_context.messages[1]["role"] == "assistant"
    
    def test_to_dict_and_from_dict(self, conversation_context):
        """Deve serializar e deserializar corretamente"""
        conversation_context.add_message("user", "Teste")
        conversation_context.current_intent = IntentType.SAUDACAO
        
        data = conversation_context.to_dict()
        restored = ConversationContext.from_dict(data)
        
        assert restored.conversation_id == conversation_context.conversation_id
        assert restored.cliente_nome == conversation_context.cliente_nome
        assert restored.current_intent == conversation_context.current_intent
        assert len(restored.messages) == 1
    
    def test_get_history_for_ai(self, conversation_context):
        """Deve formatar histórico para AI"""
        for i in range(15):
            conversation_context.add_message("user", f"Mensagem {i}")
        
        history = conversation_context.get_history_for_ai(max_messages=10)
        
        assert len(history) == 10
        assert all("role" in msg and "parts" in msg for msg in history)


# =============================================================================
# TESTES DE RESPOSTA
# =============================================================================

class TestGenerateResponse:
    """Testes para geração de resposta"""
    
    @pytest.mark.asyncio
    async def test_generate_response_saudacao(self, chatbot):
        """Deve responder saudações corretamente"""
        with patch.object(chatbot, 'save_context', new_callable=AsyncMock):
            response = await chatbot.generate_response(
                conversation_id="test:001",
                user_message="Olá, bom dia!"
            )
        
        assert isinstance(response, ChatResponse)
        assert response.intent == IntentType.SAUDACAO
        assert len(response.message) > 0
        assert len(response.quick_replies) > 0
    
    @pytest.mark.asyncio
    async def test_generate_response_with_cliente_info(self, chatbot):
        """Deve usar informações do cliente"""
        with patch.object(chatbot, 'save_context', new_callable=AsyncMock):
            response = await chatbot.generate_response(
                conversation_id="test:002",
                user_message="Minha internet está lenta",
                cliente_info={
                    "nome": "Maria",
                    "plano": "Premium 400MB"
                }
            )
        
        assert response.intent == IntentType.INTERNET_LENTA
        assert not response.should_escalate
    
    @pytest.mark.asyncio
    async def test_generate_response_escalation(self, chatbot):
        """Deve escalar quando necessário"""
        with patch.object(chatbot, 'save_context', new_callable=AsyncMock):
            response = await chatbot.generate_response(
                conversation_id="test:003",
                user_message="Quero cancelar meu plano"
            )
        
        assert response.intent == IntentType.CANCELAMENTO
        assert response.should_escalate is True
        assert response.escalation_reason is not None


# =============================================================================
# TESTES DE QUICK REPLIES
# =============================================================================

class TestQuickReplies:
    """Testes para sugestões de resposta rápida"""
    
    def test_quick_replies_saudacao(self, chatbot):
        """Deve retornar quick replies para saudação"""
        replies = chatbot.get_quick_replies(IntentType.SAUDACAO)
        
        assert len(replies) > 0
        assert "Suporte técnico" in replies or any("técnico" in r.lower() for r in replies)
    
    def test_quick_replies_internet_lenta(self, chatbot):
        """Deve retornar quick replies para internet lenta"""
        replies = chatbot.get_quick_replies(IntentType.INTERNET_LENTA)
        
        assert len(replies) > 0
        assert any("roteador" in r.lower() for r in replies)
    
    def test_quick_replies_default(self, chatbot):
        """Deve retornar quick replies padrão para intent desconhecido"""
        replies = chatbot.get_quick_replies(IntentType.DESCONHECIDO)
        
        assert len(replies) > 0


# =============================================================================
# TESTES DE MÉTRICAS
# =============================================================================

class TestMetrics:
    """Testes para métricas do chatbot"""
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, chatbot):
        """Deve retornar métricas válidas"""
        metrics = await chatbot.get_metrics()
        
        assert "total_messages" in metrics
        assert "successful_resolutions" in metrics
        assert "resolution_rate" in metrics
        assert "escalations" in metrics
        assert "avg_response_time_ms" in metrics
        assert "top_intents" in metrics
    
    def test_update_metrics(self, chatbot):
        """Deve atualizar métricas corretamente"""
        initial_total = chatbot.metrics["total_messages"]
        
        chatbot._update_metrics(0.5, resolved=True)
        
        assert chatbot.metrics["total_messages"] == initial_total + 1
        assert chatbot.metrics["successful_resolutions"] >= 1


# =============================================================================
# TESTES DE FUNÇÕES AUXILIARES
# =============================================================================

class TestHelperFunctions:
    """Testes para funções auxiliares"""
    
    @pytest.mark.asyncio
    async def test_process_whatsapp_message(self):
        """Deve processar mensagem do WhatsApp"""
        with patch('app.services.chatbot_ai.chatbot_ai') as mock_chatbot:
            mock_chatbot.generate_response = AsyncMock(return_value=ChatResponse(
                message="Resposta teste",
                intent=IntentType.SAUDACAO,
                sentiment=SentimentType.NEUTRO,
                confidence=0.9
            ))
            
            response = await process_whatsapp_message(
                phone_number="5511999999999",
                message="Olá"
            )
            
            assert response.message == "Resposta teste"
    
    def test_is_business_hours(self):
        """Deve verificar horário comercial"""
        # Este teste é dependente do horário atual
        result = is_business_hours()
        assert isinstance(result, bool)


# =============================================================================
# EXECUÇÃO DOS TESTES
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
