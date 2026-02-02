"""
Chatbot AI Enterprise com Google Gemini
Sistema inteligente para atendimento de telecomunicações

Features:
- Integração com Google Gemini Pro
- Context management (histórico de conversa)
- Intent classification para telecomunicações
- Fallback handlers inteligentes
- Análise de sentimento
- Escalação automática para humano
- Cache de respostas frequentes
- Métricas de performance
"""

import google.generativeai as genai
import structlog
import json
import re
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio

from app.core.config import settings
from app.core.redis_client import redis_manager

logger = structlog.get_logger(__name__)


# =============================================================================
# ENUMS E CONSTANTES
# =============================================================================

class IntentType(str, Enum):
    """Classificação de intenções para telecomunicações"""
    # Suporte Técnico
    INTERNET_LENTA = "internet_lenta"
    SEM_CONEXAO = "sem_conexao"
    WIFI_PROBLEMA = "wifi_problema"
    ROTEADOR_CONFIG = "roteador_config"
    
    # Financeiro
    SEGUNDA_VIA_BOLETO = "segunda_via_boleto"
    PAGAMENTO = "pagamento"
    NEGOCIACAO_DIVIDA = "negociacao_divida"
    FATURA_DUVIDA = "fatura_duvida"
    
    # Comercial
    UPGRADE_PLANO = "upgrade_plano"
    DOWNGRADE_PLANO = "downgrade_plano"
    NOVO_PLANO = "novo_plano"
    CANCELAMENTO = "cancelamento"
    PROMOCAO = "promocao"
    
    # Cadastro
    ALTERACAO_CADASTRO = "alteracao_cadastro"
    MUDANCA_ENDERECO = "mudanca_endereco"
    ALTERACAO_VENCIMENTO = "alteracao_vencimento"
    
    # Agendamento
    VISITA_TECNICA = "visita_tecnica"
    INSTALACAO = "instalacao"
    
    # Outros
    SAUDACAO = "saudacao"
    DESPEDIDA = "despedida"
    AGRADECIMENTO = "agradecimento"
    RECLAMACAO = "reclamacao"
    ELOGIO = "elogio"
    FALAR_HUMANO = "falar_humano"
    DESCONHECIDO = "desconhecido"


class SentimentType(str, Enum):
    """Análise de sentimento"""
    MUITO_POSITIVO = "muito_positivo"
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"
    MUITO_NEGATIVO = "muito_negativo"


class ConversationState(str, Enum):
    """Estados da conversa"""
    INICIO = "inicio"
    IDENTIFICACAO = "identificacao"
    ATENDIMENTO = "atendimento"
    AGUARDANDO_INFO = "aguardando_info"
    ESCALADO = "escalado"
    FINALIZADO = "finalizado"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ConversationContext:
    """Contexto de uma conversa"""
    conversation_id: str
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    cliente_plano: Optional[str] = None
    
    state: ConversationState = ConversationState.INICIO
    current_intent: Optional[IntentType] = None
    sentiment: SentimentType = SentimentType.NEUTRO
    
    messages: List[Dict[str, str]] = field(default_factory=list)
    collected_data: Dict[str, Any] = field(default_factory=dict)
    
    bot_attempts: int = 0
    max_attempts: int = 3
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_message(self, role: str, content: str):
        """Adicionar mensagem ao histórico"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.updated_at = datetime.now(timezone.utc)
    
    def get_history_for_ai(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Obter histórico formatado para o AI"""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [{"role": m["role"], "parts": [m["content"]]} for m in recent]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            "conversation_id": self.conversation_id,
            "cliente_id": self.cliente_id,
            "cliente_nome": self.cliente_nome,
            "cliente_telefone": self.cliente_telefone,
            "cliente_plano": self.cliente_plano,
            "state": self.state.value,
            "current_intent": self.current_intent.value if self.current_intent else None,
            "sentiment": self.sentiment.value,
            "messages": self.messages,
            "collected_data": self.collected_data,
            "bot_attempts": self.bot_attempts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        """Criar a partir de dicionário"""
        ctx = cls(
            conversation_id=data["conversation_id"],
            cliente_id=data.get("cliente_id"),
            cliente_nome=data.get("cliente_nome"),
            cliente_telefone=data.get("cliente_telefone"),
            cliente_plano=data.get("cliente_plano"),
            state=ConversationState(data.get("state", "inicio")),
            current_intent=IntentType(data["current_intent"]) if data.get("current_intent") else None,
            sentiment=SentimentType(data.get("sentiment", "neutro")),
            messages=data.get("messages", []),
            collected_data=data.get("collected_data", {}),
            bot_attempts=data.get("bot_attempts", 0)
        )
        if data.get("created_at"):
            ctx.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            ctx.updated_at = datetime.fromisoformat(data["updated_at"])
        return ctx


@dataclass
class ChatResponse:
    """Resposta do chatbot"""
    message: str
    intent: IntentType
    sentiment: SentimentType
    confidence: float
    should_escalate: bool = False
    escalation_reason: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)
    quick_replies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CHATBOT AI SERVICE
# =============================================================================

class ChatbotAI:
    """
    Serviço de Chatbot AI com Google Gemini
    Especializado em atendimento de telecomunicações
    """
    
    def __init__(self):
        self.initialized = False
        self.model = None
        self.chat_sessions: Dict[str, Any] = {}
        self.contexts: Dict[str, ConversationContext] = {}
        
        # Configurações
        self.company_name = "TelecomISP"
        self.max_bot_attempts = settings.MAX_BOT_ATTEMPTS
        self.business_hours_start = settings.BUSINESS_HOURS_START
        self.business_hours_end = settings.BUSINESS_HOURS_END
        
        # Métricas
        self.metrics = {
            "total_messages": 0,
            "successful_resolutions": 0,
            "escalations": 0,
            "avg_response_time": 0,
            "intent_counts": defaultdict(int)
        }
        
        # Prompt do sistema
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Construir prompt do sistema para o chatbot"""
        return f"""Você é a ARIA, assistente virtual inteligente da {self.company_name}, 
uma empresa de telecomunicações de alta qualidade.

🎯 **SEU OBJETIVO:**
Fornecer atendimento excepcional aos clientes, resolvendo problemas e respondendo 
dúvidas sobre internet, planos, faturas e suporte técnico.

📋 **REGRAS DE ATENDIMENTO:**

1. **Seja sempre cordial e profissional**
   - Use emojis com moderação para tornar a conversa amigável
   - Chame o cliente pelo nome quando souber
   - Agradeça sempre que apropriado

2. **Mantenha respostas objetivas e claras**
   - Respostas curtas e diretas (máximo 3 parágrafos)
   - Use listas quando necessário
   - Evite jargões técnicos complexos

3. **Sobre problemas técnicos:**
   - Peça detalhes específicos (há quanto tempo, em quais dispositivos)
   - Sugira soluções simples primeiro (reiniciar roteador, verificar cabos)
   - Se o problema persistir, ofereça visita técnica

4. **Sobre questões financeiras:**
   - Seja empático com clientes inadimplentes
   - Ofereça opções de negociação quando possível
   - Nunca julgue ou seja agressivo

5. **Quando NÃO souber ou precisar de um humano:**
   - Admita que precisa de ajuda
   - Ofereça transferir para um atendente
   - Nunca invente informações

6. **IMPORTANTE - Sempre colete:**
   - Nome do cliente (se não souber)
   - Número de contrato/CPF (para questões de conta)
   - Detalhes específicos do problema

📱 **PLANOS DISPONÍVEIS:**
- **Básico 100MB**: R$ 79,90/mês - Internet 100 Mbps
- **Plus 200MB**: R$ 99,90/mês - Internet 200 Mbps
- **Premium 400MB**: R$ 149,90/mês - Internet 400 Mbps + Wi-Fi 6
- **Ultra 600MB**: R$ 199,90/mês - Internet 600 Mbps + Wi-Fi 6 + IP Fixo
- **Empresarial 1GB**: R$ 349,90/mês - Internet 1 Gbps + SLA 99.9%

⏰ **HORÁRIO DE ATENDIMENTO:**
- Segunda a Sexta: 08:00 às 18:00
- Sábado: 08:00 às 12:00
- Suporte técnico 24h: apenas emergências

🔧 **DICAS RÁPIDAS PARA PROBLEMAS COMUNS:**
1. Internet lenta → Reiniciar roteador, verificar número de dispositivos
2. Sem conexão → Verificar se as luzes do roteador estão acesas
3. Wi-Fi fraco → Posicionar roteador em local central e elevado

Responda sempre em português brasileiro. Seja útil, empático e eficiente.
Se for uma emergência técnica fora do horário, direcione para o suporte 24h: 0800-XXX-XXXX."""
    
    async def initialize(self):
        """Inicializar o chatbot com Gemini"""
        try:
            if not settings.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY não configurada - chatbot em modo limitado")
                self.initialized = True
                return
            
            # Configurar Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Configurações de segurança
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            # Configuração de geração
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            # Inicializar modelo
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=self.system_prompt
            )
            
            self.initialized = True
            logger.info("Chatbot AI inicializado com sucesso", model="gemini-1.5-flash")
            
        except Exception as e:
            logger.error("Erro ao inicializar Chatbot AI", error=str(e))
            self.initialized = True  # Continua em modo fallback
    
    async def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Obter ou criar contexto de conversa"""
        # Tentar cache local
        if conversation_id in self.contexts:
            return self.contexts[conversation_id]
        
        # Tentar Redis
        try:
            cached = await redis_manager.get(f"chat_context:{conversation_id}")
            if cached:
                ctx = ConversationContext.from_dict(json.loads(cached))
                self.contexts[conversation_id] = ctx
                return ctx
        except Exception as e:
            logger.warning("Erro ao buscar contexto do Redis", error=str(e))
        
        # Criar novo
        ctx = ConversationContext(conversation_id=conversation_id)
        self.contexts[conversation_id] = ctx
        return ctx
    
    async def save_context(self, ctx: ConversationContext):
        """Salvar contexto no Redis"""
        try:
            await redis_manager.set(
                f"chat_context:{ctx.conversation_id}",
                json.dumps(ctx.to_dict()),
                ex=86400  # 24 horas
            )
        except Exception as e:
            logger.warning("Erro ao salvar contexto no Redis", error=str(e))
    
    async def classify_intent(self, message: str) -> Tuple[IntentType, float]:
        """
        Classificar a intenção da mensagem
        Retorna (intent, confidence)
        """
        message_lower = message.lower().strip()
        
        # Padrões de intenção (keywords)
        intent_patterns = {
            IntentType.SAUDACAO: [
                r'\b(oi|olá|ola|bom dia|boa tarde|boa noite|hey|hello|e ai|eai)\b'
            ],
            IntentType.DESPEDIDA: [
                r'\b(tchau|adeus|até mais|ate mais|bye|flw|falou|vlw)\b'
            ],
            IntentType.AGRADECIMENTO: [
                r'\b(obrigad[oa]|valeu|thanks|agradeço|grat[oa])\b'
            ],
            IntentType.INTERNET_LENTA: [
                r'\b(lent[oa]|devagar|lerda|travando|lag|demora|velocidade baixa)\b',
                r'\b(internet.*ruim|conexão.*ruim|net.*lenta)\b'
            ],
            IntentType.SEM_CONEXAO: [
                r'\b(sem internet|caiu|não funciona|nao funciona|offline|fora do ar)\b',
                r'\b(não conecta|nao conecta|sem conexão|sem conexao)\b'
            ],
            IntentType.WIFI_PROBLEMA: [
                r'\b(wifi|wi-fi|wireless|sinal.*fraco|não pega|nao pega)\b'
            ],
            IntentType.ROTEADOR_CONFIG: [
                r'\b(roteador|modem|configurar|senha.*wifi|trocar.*senha)\b'
            ],
            IntentType.SEGUNDA_VIA_BOLETO: [
                r'\b(segunda via|2[ªa] via|boleto|código.*barras|pix)\b'
            ],
            IntentType.PAGAMENTO: [
                r'\b(pagar|pagamento|paguei|quitação|quitar)\b'
            ],
            IntentType.NEGOCIACAO_DIVIDA: [
                r'\b(dívida|divida|negociar|parcelar|atrasad[oa]|devendo)\b'
            ],
            IntentType.FATURA_DUVIDA: [
                r'\b(fatura|conta|valor.*cobrado|cobrança|porque.*pagar)\b'
            ],
            IntentType.UPGRADE_PLANO: [
                r'\b(upgrade|aumentar.*velocidade|plano.*melhor|mais.*mega)\b'
            ],
            IntentType.DOWNGRADE_PLANO: [
                r'\b(downgrade|diminuir|plano.*menor|mais.*barato|reduzir)\b'
            ],
            IntentType.NOVO_PLANO: [
                r'\b(novo.*plano|contratar|assinar|quero.*internet|planos.*disponíveis)\b'
            ],
            IntentType.CANCELAMENTO: [
                r'\b(cancelar|cancelamento|encerrar|rescindir|desistir)\b'
            ],
            IntentType.PROMOCAO: [
                r'\b(promoção|promocao|desconto|oferta|black friday)\b'
            ],
            IntentType.ALTERACAO_CADASTRO: [
                r'\b(alterar.*cadastro|mudar.*dados|atualizar.*cadastro)\b'
            ],
            IntentType.MUDANCA_ENDERECO: [
                r'\b(mudança|mudanca|mudar.*endereço|trocar.*endereço|transferir)\b'
            ],
            IntentType.ALTERACAO_VENCIMENTO: [
                r'\b(vencimento|data.*pagamento|dia.*pagar|trocar.*dia)\b'
            ],
            IntentType.VISITA_TECNICA: [
                r'\b(visita|técnico|tecnico|agendar.*visita|mandar.*alguém)\b'
            ],
            IntentType.INSTALACAO: [
                r'\b(instala[çc][ãa]o|instalar|nova.*instalação)\b'
            ],
            IntentType.RECLAMACAO: [
                r'\b(reclamação|reclamar|péssimo|pessimo|absurdo|procon|anatel)\b'
            ],
            IntentType.ELOGIO: [
                r'\b(excelente|ótimo|otimo|parabéns|parabens|maravilh|amei)\b'
            ],
            IntentType.FALAR_HUMANO: [
                r'\b(humano|atendente|pessoa|falar.*alguém|alguem|real)\b'
            ],
        }
        
        # Verificar padrões
        best_intent = IntentType.DESCONHECIDO
        best_confidence = 0.0
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    confidence = 0.85  # Alta confiança para padrões específicos
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence
        
        # Se não encontrou padrão, tentar classificação por AI
        if best_confidence < 0.5 and self.model:
            try:
                prompt = f"""Classifique a seguinte mensagem de cliente de telecomunicações em UMA das categorias:
                
Categorias: internet_lenta, sem_conexao, wifi_problema, segunda_via_boleto, pagamento, 
negociacao_divida, upgrade_plano, cancelamento, visita_tecnica, saudacao, despedida, 
falar_humano, desconhecido

Mensagem: "{message}"

Responda APENAS com o nome da categoria, nada mais."""
                
                response = await asyncio.to_thread(
                    self.model.generate_content, prompt
                )
                
                if response.text:
                    classified = response.text.strip().lower()
                    for intent in IntentType:
                        if intent.value == classified:
                            best_intent = intent
                            best_confidence = 0.7
                            break
                            
            except Exception as e:
                logger.warning("Erro na classificação por AI", error=str(e))
        
        # Métricas
        self.metrics["intent_counts"][best_intent.value] += 1
        
        return best_intent, best_confidence
    
    async def analyze_sentiment(self, message: str) -> SentimentType:
        """Analisar sentimento da mensagem"""
        message_lower = message.lower()
        
        # Palavras negativas
        negative_words = [
            'péssimo', 'horrível', 'terrível', 'absurdo', 'lixo', 'raiva',
            'odeio', 'nunca mais', 'procon', 'anatel', 'processo', 'advogado',
            'palhaçada', 'vergonha', 'incompetente', 'roubo'
        ]
        
        # Palavras positivas
        positive_words = [
            'ótimo', 'excelente', 'maravilhoso', 'obrigado', 'perfeito',
            'adorei', 'amei', 'parabéns', 'incrível', 'satisfeito', 'feliz'
        ]
        
        negative_count = sum(1 for word in negative_words if word in message_lower)
        positive_count = sum(1 for word in positive_words if word in message_lower)
        
        # Intensificadores
        if any(word in message_lower for word in ['muito', 'demais', 'extremamente']):
            negative_count *= 1.5
            positive_count *= 1.5
        
        if negative_count >= 2:
            return SentimentType.MUITO_NEGATIVO
        elif negative_count >= 1:
            return SentimentType.NEGATIVO
        elif positive_count >= 2:
            return SentimentType.MUITO_POSITIVO
        elif positive_count >= 1:
            return SentimentType.POSITIVO
        
        return SentimentType.NEUTRO
    
    def should_escalate(self, ctx: ConversationContext, intent: IntentType, sentiment: SentimentType) -> Tuple[bool, Optional[str]]:
        """Verificar se deve escalar para humano"""
        reasons = []
        
        # Escalação por intent
        if intent == IntentType.FALAR_HUMANO:
            return True, "Cliente solicitou atendente humano"
        
        if intent == IntentType.CANCELAMENTO:
            return True, "Solicitação de cancelamento requer atendente"
        
        if intent == IntentType.NEGOCIACAO_DIVIDA:
            return True, "Negociação de dívida requer atendente"
        
        if intent == IntentType.RECLAMACAO:
            reasons.append("Reclamação registrada")
        
        # Escalação por sentimento
        if sentiment == SentimentType.MUITO_NEGATIVO:
            reasons.append("Cliente muito insatisfeito")
        
        # Escalação por tentativas
        if ctx.bot_attempts >= ctx.max_attempts:
            reasons.append(f"Limite de {ctx.max_attempts} tentativas atingido")
        
        if reasons:
            return True, " | ".join(reasons)
        
        return False, None
    
    def get_quick_replies(self, intent: IntentType) -> List[str]:
        """Obter sugestões de resposta rápida"""
        quick_replies = {
            IntentType.SAUDACAO: [
                "Ver meus planos",
                "Suporte técnico",
                "Segunda via de boleto",
                "Falar com atendente"
            ],
            IntentType.INTERNET_LENTA: [
                "Já reiniciei o roteador",
                "Agendar visita técnica",
                "Ver planos mais rápidos",
                "Falar com técnico"
            ],
            IntentType.SEM_CONEXAO: [
                "As luzes estão apagadas",
                "As luzes estão piscando",
                "Já tentei reiniciar",
                "Preciso de visita técnica"
            ],
            IntentType.SEGUNDA_VIA_BOLETO: [
                "Enviar por WhatsApp",
                "Enviar por email",
                "Gerar código PIX",
                "Ver faturas anteriores"
            ],
            IntentType.UPGRADE_PLANO: [
                "Ver plano 200 Mbps",
                "Ver plano 400 Mbps",
                "Ver plano 600 Mbps",
                "Comparar planos"
            ],
        }
        
        return quick_replies.get(intent, [
            "Suporte técnico",
            "Financeiro",
            "Mudar de plano",
            "Falar com atendente"
        ])
    
    async def generate_response(
        self,
        conversation_id: str,
        user_message: str,
        cliente_info: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Gerar resposta para mensagem do usuário
        
        Args:
            conversation_id: ID único da conversa
            user_message: Mensagem do usuário
            cliente_info: Informações do cliente (opcional)
        
        Returns:
            ChatResponse com a resposta e metadados
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Obter contexto
            ctx = await self.get_or_create_context(conversation_id)
            
            # Atualizar info do cliente se fornecida
            if cliente_info:
                ctx.cliente_id = cliente_info.get("id", ctx.cliente_id)
                ctx.cliente_nome = cliente_info.get("nome", ctx.cliente_nome)
                ctx.cliente_telefone = cliente_info.get("telefone", ctx.cliente_telefone)
                ctx.cliente_plano = cliente_info.get("plano", ctx.cliente_plano)
            
            # Adicionar mensagem ao histórico
            ctx.add_message("user", user_message)
            ctx.bot_attempts += 1
            
            # Classificar intenção
            intent, confidence = await self.classify_intent(user_message)
            ctx.current_intent = intent
            
            # Analisar sentimento
            sentiment = await self.analyze_sentiment(user_message)
            ctx.sentiment = sentiment
            
            # Verificar escalação
            should_escalate, escalation_reason = self.should_escalate(ctx, intent, sentiment)
            
            if should_escalate:
                ctx.state = ConversationState.ESCALADO
                response_text = self._get_escalation_message(escalation_reason)
                self.metrics["escalations"] += 1
            else:
                # Gerar resposta com AI
                response_text = await self._generate_ai_response(ctx, user_message, intent)
                
                if not response_text:
                    response_text = self._get_fallback_response(intent)
            
            # Adicionar resposta ao histórico
            ctx.add_message("assistant", response_text)
            
            # Salvar contexto
            await self.save_context(ctx)
            
            # Calcular tempo de resposta
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._update_metrics(response_time, not should_escalate)
            
            # Criar resposta
            return ChatResponse(
                message=response_text,
                intent=intent,
                sentiment=sentiment,
                confidence=confidence,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                suggested_actions=self._get_suggested_actions(intent),
                quick_replies=self.get_quick_replies(intent),
                metadata={
                    "conversation_id": conversation_id,
                    "bot_attempts": ctx.bot_attempts,
                    "response_time_ms": int(response_time * 1000),
                    "state": ctx.state.value
                }
            )
            
        except Exception as e:
            logger.error("Erro ao gerar resposta", error=str(e), conversation_id=conversation_id)
            
            return ChatResponse(
                message="Desculpe, tive um problema técnico. Vou transferir você para um atendente. Um momento, por favor. 🙏",
                intent=IntentType.DESCONHECIDO,
                sentiment=SentimentType.NEUTRO,
                confidence=0.0,
                should_escalate=True,
                escalation_reason=f"Erro técnico: {str(e)}"
            )
    
    async def _generate_ai_response(
        self,
        ctx: ConversationContext,
        user_message: str,
        intent: IntentType
    ) -> Optional[str]:
        """Gerar resposta usando Gemini"""
        if not self.model:
            return None
        
        try:
            # Construir contexto adicional
            context_info = ""
            if ctx.cliente_nome:
                context_info += f"\nNome do cliente: {ctx.cliente_nome}"
            if ctx.cliente_plano:
                context_info += f"\nPlano atual: {ctx.cliente_plano}"
            if ctx.current_intent:
                context_info += f"\nIntenção detectada: {ctx.current_intent.value}"
            
            # Histórico formatado
            history = ctx.get_history_for_ai(max_messages=6)
            
            # Usar chat session para manter contexto
            if ctx.conversation_id not in self.chat_sessions:
                self.chat_sessions[ctx.conversation_id] = self.model.start_chat(history=history[:-1])
            
            chat = self.chat_sessions[ctx.conversation_id]
            
            # Gerar resposta
            response = await asyncio.to_thread(
                chat.send_message,
                user_message
            )
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.warning("Erro na geração AI", error=str(e))
            return None
    
    def _get_fallback_response(self, intent: IntentType) -> str:
        """Obter resposta de fallback por intenção"""
        fallbacks = {
            IntentType.SAUDACAO: """Olá! 👋 Bem-vindo à TelecomISP!

Sou a ARIA, sua assistente virtual. Como posso ajudar você hoje?

📱 **Posso ajudar com:**
• Suporte técnico (internet, Wi-Fi)
• Segunda via de boleto
• Informações sobre planos
• Agendamento de visita técnica

Digite sua dúvida ou escolha uma opção abaixo! 😊""",

            IntentType.INTERNET_LENTA: """Entendo que sua internet está lenta, e isso é muito frustrante! 😟

Vamos resolver isso juntos. Primeiro, tente essas dicas rápidas:

1️⃣ **Reinicie o roteador** - desligue da tomada, aguarde 30 segundos e ligue novamente

2️⃣ **Verifique quantos dispositivos** estão conectados - muitos aparelhos podem dividir a velocidade

3️⃣ **Teste com cabo** - conecte um dispositivo direto no roteador para comparar

Já tentou alguma dessas opções? Me conta o resultado! 🔧""",

            IntentType.SEM_CONEXAO: """Puxa, ficar sem internet é muito chato! 😔 Vamos resolver isso rapidamente.

Por favor, verifique:

🔴 **Luzes do roteador:**
• Todas apagadas? → Verifique se está na tomada
• Piscando vermelho? → Pode ser problema na rede
• Verdes normais? → Problema pode ser no dispositivo

Já verificou as luzes? Me conta como estão! 👀""",

            IntentType.SEGUNDA_VIA_BOLETO: """Claro! Vou te ajudar com a segunda via do boleto! 📄

Para enviar, preciso confirmar alguns dados:

📋 **Por favor, informe:**
• Seu CPF ou número do contrato

Assim que confirmar, envio o boleto por aqui mesmo ou posso gerar um código PIX se preferir! 😊""",

            IntentType.UPGRADE_PLANO: """Que ótimo que quer turbinar sua internet! 🚀

Nossos planos disponíveis:

📱 **Básico 100MB** - R$ 79,90/mês
📱 **Plus 200MB** - R$ 99,90/mês  
📱 **Premium 400MB** - R$ 149,90/mês + Wi-Fi 6
📱 **Ultra 600MB** - R$ 199,90/mês + Wi-Fi 6 + IP Fixo

Qual velocidade você precisa? Posso ajudar a escolher o melhor para você! 💪""",

            IntentType.CANCELAMENTO: """Entendo que deseja cancelar, e lamento muito ouvir isso. 😢

Antes de prosseguir, gostaria de entender melhor:
• Houve algum problema que possamos resolver?
• Podemos oferecer condições especiais?

Para cancelamento, preciso transferir você para um atendente que pode:
✅ Verificar seu contrato
✅ Calcular eventuais multas
✅ Agendar retirada de equipamentos

Vou transferir agora, ok? 🤝""",

            IntentType.DESPEDIDA: """Foi um prazer ajudar! 😊

Se precisar de mais alguma coisa, é só chamar!

⭐ Avalie nosso atendimento respondendo de 1 a 5

Tenha um ótimo dia! 👋

*TelecomISP - Conectando você ao que importa*""",

            IntentType.AGRADECIMENTO: """Por nada! Fico feliz em ajudar! 😊

Precisa de mais alguma coisa? Estou aqui!

Se não, desejo um excelente dia! 🌟""",

            IntentType.FALAR_HUMANO: """Entendido! Vou transferir você para um de nossos atendentes humanos. 🧑‍💼

⏳ **Tempo estimado de espera:** 2-5 minutos

Enquanto aguarda, me conta brevemente qual é sua dúvida para que o atendente já receba seu caso com contexto!""",
        }
        
        return fallbacks.get(intent, """Obrigado pela sua mensagem! 📩

Não tenho certeza se entendi corretamente. Você poderia me explicar melhor o que precisa?

Posso ajudar com:
• 🔧 Suporte técnico
• 💰 Questões financeiras  
• 📱 Mudança de plano
• 📅 Agendamentos

Ou se preferir, posso chamar um atendente humano! 🙋""")
    
    def _get_escalation_message(self, reason: Optional[str]) -> str:
        """Mensagem de escalação para humano"""
        return f"""Entendi! Vou transferir você agora para um de nossos atendentes especializados. 🧑‍💼

📋 **Motivo:** {reason or 'Atendimento personalizado'}

⏳ **Tempo estimado:** 2-5 minutos

Por favor, aguarde que em breve você será atendido! Obrigado pela paciência. 🙏"""
    
    def _get_suggested_actions(self, intent: IntentType) -> List[str]:
        """Obter ações sugeridas para o atendente"""
        actions = {
            IntentType.INTERNET_LENTA: [
                "Verificar histórico de velocidade",
                "Analisar consumo de banda",
                "Verificar se há manutenção na área",
                "Oferecer upgrade de plano"
            ],
            IntentType.SEM_CONEXAO: [
                "Verificar status da porta ONU",
                "Checar se há interrupção na região",
                "Agendar visita técnica urgente"
            ],
            IntentType.CANCELAMENTO: [
                "Verificar motivo do cancelamento",
                "Oferecer promoção de retenção",
                "Calcular multa contratual",
                "Agendar retirada de equipamentos"
            ],
            IntentType.NEGOCIACAO_DIVIDA: [
                "Verificar valor total da dívida",
                "Oferecer parcelamento",
                "Aplicar desconto autorizado",
                "Negociar entrada + parcelas"
            ],
        }
        
        return actions.get(intent, ["Analisar histórico do cliente"])
    
    def _update_metrics(self, response_time: float, resolved: bool):
        """Atualizar métricas do chatbot"""
        self.metrics["total_messages"] += 1
        
        if resolved:
            self.metrics["successful_resolutions"] += 1
        
        # Média móvel do tempo de resposta
        total = self.metrics["total_messages"]
        current_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            (current_avg * (total - 1) + response_time) / total
        )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Obter métricas do chatbot"""
        total = self.metrics["total_messages"] or 1
        
        return {
            "total_messages": self.metrics["total_messages"],
            "successful_resolutions": self.metrics["successful_resolutions"],
            "resolution_rate": self.metrics["successful_resolutions"] / total * 100,
            "escalations": self.metrics["escalations"],
            "escalation_rate": self.metrics["escalations"] / total * 100,
            "avg_response_time_ms": int(self.metrics["avg_response_time"] * 1000),
            "top_intents": dict(sorted(
                self.metrics["intent_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
        }
    
    async def clear_conversation(self, conversation_id: str):
        """Limpar contexto de uma conversa"""
        if conversation_id in self.contexts:
            del self.contexts[conversation_id]
        
        if conversation_id in self.chat_sessions:
            del self.chat_sessions[conversation_id]
        
        try:
            await redis_manager.delete(f"chat_context:{conversation_id}")
        except Exception:
            pass
        
        logger.info("Conversa limpa", conversation_id=conversation_id)


# =============================================================================
# INSTÂNCIA GLOBAL
# =============================================================================

chatbot_ai = ChatbotAI()


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

async def process_whatsapp_message(
    phone_number: str,
    message: str,
    cliente_info: Optional[Dict[str, Any]] = None
) -> ChatResponse:
    """
    Processar mensagem recebida do WhatsApp
    
    Args:
        phone_number: Número de telefone do cliente
        message: Mensagem recebida
        cliente_info: Informações do cliente (opcional)
    
    Returns:
        ChatResponse com a resposta
    """
    # Usar telefone como ID de conversa
    conversation_id = f"whatsapp:{phone_number}"
    
    return await chatbot_ai.generate_response(
        conversation_id=conversation_id,
        user_message=message,
        cliente_info=cliente_info
    )


def is_business_hours() -> bool:
    """Verificar se está em horário comercial"""
    now = datetime.now(timezone.utc)
    # Ajustar para timezone Brasil (UTC-3)
    brazil_hour = (now.hour - 3) % 24
    
    # Segunda a Sexta
    if now.weekday() < 5:
        return settings.BUSINESS_HOURS_START <= brazil_hour < settings.BUSINESS_HOURS_END
    
    # Sábado (8-12)
    if now.weekday() == 5:
        return 8 <= brazil_hour < 12
    
    return False