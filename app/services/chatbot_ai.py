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
from app.services.sgp_service import SGPService

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
        
        # Serviço SGP
        self.sgp_service = SGPService()
        
        # Configurações
        self.company_name = "Cianet Provedor"
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
        return """Você é o assistente virtual da Cianet Provedor. Seu objetivo é ajudar clientes com suporte e financeiro.

Siga estas regras de negócio estritamente:

1. IDENTIFICAÇÃO:
   - Se o cliente pedir algo pessoal (boleto, status, suporte técnico, informações da conta), você DEVE solicitar o CPF
   - Só prossiga após validar que o CPF tem 11 dígitos
   - Use a ferramenta 'buscar_cliente_por_cpf' assim que receber o número
   - Valide se o cliente foi encontrado antes de continuar

2. STATUS DO CLIENTE:
   - Se o status for 'Bloqueado' ou 'Suspenso', informe gentilmente e ofereça a 'Promessa de Pagamento'
   - Se estiver 'Ativo' ou 'Online', informe que a conexão está normal
   - Sempre mencione o status atual do cliente após identificá-lo

3. FINANCEIRO:
   - Ao listar boletos, forneça o valor, a data de vencimento e o link para o PDF
   - Priorize boletos vencidos ou próximos do vencimento
   - Se não houver faturas em aberto, parabenize o cliente
   - Sempre ofereça enviar o boleto por WhatsApp ou gerar código PIX

4. PROMESSA DE PAGAMENTO:
   - Só ofereça se o cliente estiver 'Bloqueado' ou 'Suspenso'
   - Explique que a liberação é temporária (48h) e depende de disponibilidade no sistema SGP
   - Após liberar, reforce que o pagamento deve ser feito o quanto antes
   - Ofereça enviar o boleto após a liberação

5. SUPORTE TÉCNICO:
   - Para problemas de conexão, primeiro verifique o status do cliente no SGP
   - Se estiver bloqueado por inadimplência, explique e ofereça soluções financeiras
   - Se estiver ativo, sugira: reiniciar roteador, verificar cabos, testar em outro dispositivo
   - Ofereça agendar visita técnica se o problema persistir

6. RESPOSTAS:
   - Seja sempre profissional, prestativa e direta
   - Use emojis com moderação (máximo 2 por mensagem)
   - Respostas curtas e objetivas (máximo 3 parágrafos)
   - Chame o cliente pelo nome quando souber
   - Nunca invente informações - se não souber, ofereça transferir para atendente humano

7. FLUXO PADRÃO:
   a) Cliente pede boleto/suporte → Solicite CPF
   b) Recebe CPF → Busque no SGP com buscar_cliente_por_cpf
   c) Cliente encontrado → Informe nome e status
   d) Se bloqueado → Ofereça promessa + boleto
   e) Se ativo → Busque faturas ou resolva suporte técnico
   f) Finalize oferecendo mais ajuda

Responda sempre em português brasileiro. Seja empático mas objetivo."""
    
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
            
            # ===== LÓGICA DE INTEGRAÇÃO COM SGP =====
            
            # Verificar se está aguardando CPF (última intenção foi boleto/fatura)
            aguardando_cpf = (
                ctx.current_intent in [IntentType.SEGUNDA_VIA_BOLETO, IntentType.PAGAMENTO, IntentType.FATURA_DUVIDA] or
                (len(ctx.messages) >= 2 and any(
                    msg.get("content", "").lower().find("cpf") != -1 
                    for msg in ctx.messages[-2:] 
                    if msg.get("role") == "assistant"
                ))
            )
            
            # Se a intenção é sobre boleto/fatura OU está aguardando CPF
            if intent in [IntentType.SEGUNDA_VIA_BOLETO, IntentType.PAGAMENTO, IntentType.FATURA_DUVIDA] or (aguardando_cpf and not ctx.cliente_id):
                if not ctx.cliente_id:
                    # Tentar extrair CPF da mensagem
                    cpf = self.extrair_cpf(user_message)
                    
                    if cpf:
                        # Buscar cliente no SGP
                        cliente_sgp = await self.buscar_cliente_sgp(cpf, ctx)
                        
                        if cliente_sgp:
                            # Cliente encontrado! Buscar faturas
                            faturas = await self.obter_faturas_cliente(ctx)
                            
                            # Verificar se está suspenso
                            status = cliente_sgp.get("status", "").lower()
                            
                            if "suspenso" in status or "bloqueado" in status:
                                # Cliente suspenso/bloqueado - oferecer promessa
                                response_text = f"""Olá {ctx.cliente_nome}! 👋

Vi aqui que seu plano está com status: **{cliente_sgp.get('status')}**

💰 **Faturas em aberto:** {len(faturas)} fatura(s)

📋 **Opções disponíveis:**
1️⃣ Enviar boleto/PIX para pagamento
2️⃣ Liberar internet temporariamente (Promessa de Pagamento - 48h)

O que você prefere? Digite 1 ou 2"""
                            else:
                                # Cliente regular - enviar faturas
                                if faturas:
                                    response_text = f"""Olá {ctx.cliente_nome}! 👋

Status: **{cliente_sgp.get('status')}** ✓

Encontrei suas faturas em aberto:

"""
                                    for i, fatura in enumerate(faturas[:3], 1):
                                        vencimento = fatura.get("dataVencimento", "N/A")
                                        valor = fatura.get("valor", 0)
                                        response_text += f"{i}. Vencimento: {vencimento} - R$ {valor:.2f}\n"
                                        if fatura.get("link"):
                                            response_text += f"   Link: {fatura.get('link')}\n"
                                    
                                    response_text += "\n📱 Posso enviar o boleto ou código PIX. Qual você prefere?"
                                else:
                                    response_text = f"""Olá {ctx.cliente_nome}! 👋

Status: **{cliente_sgp.get('status')}** ✓

Ótimas notícias! Não encontrei faturas em aberto no seu nome.

Seu plano está em dia! Se precisar de algo mais, é só avisar!"""
                            
                            # Adicionar resposta ao histórico
                            ctx.add_message("assistant", response_text)
                            await self.save_context(ctx)
                            
                            # Calcular tempo de resposta
                            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                            self._update_metrics(response_time, True)
                            
                            return ChatResponse(
                                message=response_text,
                                intent=intent,
                                sentiment=sentiment,
                                confidence=confidence,
                                quick_replies=["Enviar boleto", "Enviar PIX", "Promessa de pagamento"] if "suspenso" in status.lower() else ["Enviar boleto", "Enviar PIX"],
                                metadata={
                                    "conversation_id": conversation_id,
                                    "cliente_id": ctx.cliente_id,
                                    "status_sgp": cliente_sgp.get("status"),
                                    "total_faturas": len(faturas),
                                    "response_time_ms": int(response_time * 1000)
                                }
                            )
                        else:
                            # CPF não encontrado
                            response_text = """Não encontrei esse CPF no nosso sistema.

Por favor, verifique se digitou corretamente ou tente com outro CPF.

Se o problema persistir, vou transferir você para um atendente!"""
                            
                            ctx.add_message("assistant", response_text)
                            await self.save_context(ctx)
                            
                            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                            self._update_metrics(response_time, False)
                            
                            return ChatResponse(
                                message=response_text,
                                intent=intent,
                                sentiment=sentiment,
                                confidence=confidence,
                                quick_replies=["Tentar outro CPF", "Falar com atendente"]
                            )
                    else:
                        # Não tem CPF na mensagem - pedir
                        response_text = """Para buscar seu boleto, preciso do seu CPF! 📋

Por favor, digite seu CPF (pode ser com ou sem pontos/traços):

Exemplo: 123.456.789-00 ou 12345678900"""
                        
                        ctx.add_message("assistant", response_text)
                        await self.save_context(ctx)
                        
                        response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                        self._update_metrics(response_time, True)
                        
                        return ChatResponse(
                            message=response_text,
                            intent=intent,
                            sentiment=sentiment,
                            confidence=confidence
                        )
                else:
                    # Já tem cliente_id - verificar se é pedido de promessa
                    if "promessa" in user_message.lower() or "liberar" in user_message.lower() or user_message.strip() == "2":
                        sucesso = await self.realizar_promessa_pagamento(ctx)
                        
                        if sucesso:
                            response_text = f"""✓ Pronto, {ctx.cliente_nome}!

Sua internet foi liberada temporariamente por confiança!

⚠️ **IMPORTANTE:** 
- A liberação é temporária (48h)
- Por favor, regularize o pagamento o quanto antes
- Caso contrário, o serviço será suspenso novamente

Precisa do boleto para pagar? É só pedir!"""
                        else:
                            response_text = """Ops! Tive um problema ao liberar sua internet.

Vou transferir você para um atendente que pode ajudar melhor com isso!"""
                        
                        ctx.add_message("assistant", response_text)
                        await self.save_context(ctx)
                        
                        response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                        self._update_metrics(response_time, sucesso)
                        
                        return ChatResponse(
                            message=response_text,
                            intent=intent,
                            sentiment=sentiment,
                            confidence=confidence,
                            should_escalate=not sucesso,
                            escalation_reason="Falha ao realizar promessa de pagamento" if not sucesso else None,
                            quick_replies=["Enviar boleto", "Falar com atendente"] if sucesso else []
                        )
            
            # ===== FIM DA LÓGICA SGP =====
            
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
            
            # Adicionar informações do SGP se disponíveis
            if ctx.cliente_id:
                context_info += f"\nID do cliente no SGP: {ctx.cliente_id}"
                if ctx.collected_data.get("status_sgp"):
                    context_info += f"\nStatus no SGP: {ctx.collected_data['status_sgp']}"
            
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
            IntentType.SAUDACAO: """Olá! Bem-vindo à Cianet Provedor! 👋

Sou seu assistente virtual. Como posso ajudar você hoje?

Posso ajudar com:
• Boletos e pagamentos
• Suporte técnico
• Status da sua conexão
• Informações sobre sua conta

Digite sua dúvida ou escolha uma opção!""",

            IntentType.INTERNET_LENTA: """Entendo que sua internet está lenta. Vamos resolver isso!

Primeiro, preciso do seu CPF para verificar o status da sua conexão no sistema.

Por favor, digite seu CPF (com ou sem pontos/traços):""",

            IntentType.SEM_CONEXAO: """Sem internet é muito frustrante! Vou te ajudar.

Para verificar o status da sua conexão, preciso do seu CPF.

Por favor, digite seu CPF (com ou sem pontos/traços):""",

            IntentType.SEGUNDA_VIA_BOLETO: """Claro! Vou buscar seu boleto.

Para isso, preciso do seu CPF:

Digite seu CPF (pode ser com ou sem pontos/traços)
Exemplo: 123.456.789-00 ou 12345678900""",

            IntentType.PAGAMENTO: """Vou te ajudar com o pagamento!

Preciso do seu CPF para buscar suas faturas:

Digite seu CPF (com ou sem pontos/traços):""",

            IntentType.FATURA_DUVIDA: """Vou verificar suas faturas para você.

Por favor, informe seu CPF:

Digite seu CPF (com ou sem pontos/traços):""",

            IntentType.UPGRADE_PLANO: """Quer melhorar seu plano? Ótimo!

Para verificar as opções disponíveis para você, preciso do seu CPF:

Digite seu CPF (com ou sem pontos/traços):""",

            IntentType.CANCELAMENTO: """Lamento que queira cancelar. 😔

Antes de prosseguir, preciso do seu CPF para verificar sua conta:

Digite seu CPF (com ou sem pontos/traços):

Obs: Vou transferir você para um atendente que pode ajudar melhor com o cancelamento.""",

            IntentType.DESPEDIDA: """Foi um prazer ajudar! 😊

Se precisar de mais alguma coisa, é só chamar!

Tenha um ótimo dia!

*Cianet Provedor - Conectando você ao que importa*""",

            IntentType.AGRADECIMENTO: """Por nada! Fico feliz em ajudar! 😊

Precisa de mais alguma coisa? Estou aqui!""",

            IntentType.FALAR_HUMANO: """Entendido! Vou transferir você para um atendente humano.

⏳ Tempo estimado de espera: 2-5 minutos

Enquanto aguarda, me conte brevemente qual é sua dúvida para que o atendente já receba seu caso com contexto!""",
        }
        
        return fallbacks.get(intent, """Obrigado pela sua mensagem!

Não tenho certeza se entendi corretamente. Você poderia me explicar melhor o que precisa?

Posso ajudar com:
• Boletos e pagamentos
• Suporte técnico
• Status da conexão
• Informações da conta

Ou se preferir, posso chamar um atendente humano!""")
    
    def _get_escalation_message(self, reason: Optional[str]) -> str:
        """Mensagem de escalação para humano"""
        return f"""Vou transferir você agora para um de nossos atendentes. �

📋 **Motivo:** {reason or 'Atendimento personalizado'}

⏳ **Tempo estimado:** 2-5 minutos

Por favor, aguarde que em breve você será atendido! Obrigado pela paciência."""
    
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
    
    async def buscar_cliente_sgp(self, cpf: str, ctx: ConversationContext) -> Optional[Dict[str, Any]]:
        """
        Buscar cliente no SGP por CPF e atualizar contexto
        
        Args:
            cpf: CPF do cliente
            ctx: Contexto da conversa
        
        Returns:
            Dados do cliente ou None se não encontrado
        """
        try:
            logger.info("Buscando cliente no SGP", cpf=cpf[:3] + "***")
            
            cliente = await asyncio.to_thread(
                self.sgp_service.buscar_cliente_por_cpf,
                cpf
            )
            
            if cliente:
                # Atualizar contexto com dados do cliente
                ctx.cliente_id = str(cliente.get("id"))
                ctx.cliente_nome = cliente.get("nome")
                ctx.collected_data["status_sgp"] = cliente.get("status")
                ctx.collected_data["situacao_sgp"] = cliente.get("situacao")
                ctx.collected_data["cpf_cnpj"] = cliente.get("cpf_cnpj")
                ctx.collected_data["titulos"] = cliente.get("titulos", [])
                ctx.collected_data["contratos"] = cliente.get("contratos", [])
                ctx.collected_data["contatos"] = cliente.get("contatos", {})
                
                # Salvar contexto atualizado
                await self.save_context(ctx)
                
                logger.info(
                    "Cliente encontrado no SGP",
                    cliente_id=ctx.cliente_id,
                    nome=ctx.cliente_nome,
                    status=cliente.get("status")
                )
                
                return cliente
            else:
                logger.warning("Cliente não encontrado no SGP", cpf=cpf[:3] + "***")
                return None
                
        except Exception as e:
            logger.error("Erro ao buscar cliente no SGP", error=str(e))
            return None
    
    async def obter_faturas_cliente(self, ctx: ConversationContext) -> List[Dict[str, Any]]:
        """
        Obter faturas abertas do cliente
        
        Args:
            ctx: Contexto da conversa (deve ter cliente_id)
        
        Returns:
            Lista de faturas abertas
        """
        if not ctx.cliente_id:
            logger.warning("Tentativa de buscar faturas sem cliente_id")
            return []
        
        try:
            logger.info("Buscando faturas do cliente", cliente_id=ctx.cliente_id)
            
            # Os títulos já vêm na busca do cliente, então vamos pegar do contexto
            if "titulos" in ctx.collected_data:
                titulos = ctx.collected_data["titulos"]
                # Filtrar apenas títulos em aberto (não cancelados nem pagos)
                faturas_abertas = [
                    t for t in titulos 
                    if t.get("status") not in ["cancelado", "pago"]
                ]
                
                logger.info(
                    "Faturas obtidas do contexto",
                    cliente_id=ctx.cliente_id,
                    total_faturas=len(faturas_abertas)
                )
                
                return faturas_abertas
            
            return []
            
        except Exception as e:
            logger.error("Erro ao obter faturas", error=str(e))
            return []
    
    async def realizar_promessa_pagamento(self, ctx: ConversationContext) -> bool:
        """
        Realizar promessa de pagamento (liberar internet temporariamente)
        
        Args:
            ctx: Contexto da conversa (deve ter cliente_id)
        
        Returns:
            True se sucesso, False caso contrário
        """
        if not ctx.cliente_id:
            logger.warning("Tentativa de promessa sem cliente_id")
            return False
        
        try:
            logger.info("Realizando promessa de pagamento", cliente_id=ctx.cliente_id)
            
            sucesso = await asyncio.to_thread(
                self.sgp_service.realizar_promessa_pagamento,
                ctx.cliente_id
            )
            
            if sucesso:
                ctx.collected_data["promessa_realizada"] = True
                ctx.collected_data["promessa_data"] = datetime.now(timezone.utc).isoformat()
                await self.save_context(ctx)
                
                logger.info("Promessa de pagamento realizada", cliente_id=ctx.cliente_id)
            else:
                logger.warning("Falha ao realizar promessa", cliente_id=ctx.cliente_id)
            
            return sucesso
            
        except Exception as e:
            logger.error("Erro ao realizar promessa", error=str(e))
            return False
    
    def extrair_cpf(self, mensagem: str) -> Optional[str]:
        """
        Extrair e validar CPF de uma mensagem
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            CPF válido ou None
        """
        from app.core.validators import validar_cpf, sanitizar_cpf
        
        # Remover tudo que não é número
        numeros = re.sub(r'\D', '', mensagem)
        
        # CPF tem 11 dígitos
        if len(numeros) == 11:
            cpf_validado = sanitizar_cpf(numeros)
            if cpf_validado:
                return cpf_validado
            else:
                logger.warning("CPF inválido detectado")
                return None
        
        # Tentar encontrar padrão de CPF formatado (XXX.XXX.XXX-XX)
        cpf_pattern = r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'
        match = re.search(cpf_pattern, mensagem)
        
        if match:
            cpf = re.sub(r'\D', '', match.group())
            if len(cpf) == 11:
                cpf_validado = sanitizar_cpf(cpf)
                if cpf_validado:
                    return cpf_validado
                else:
                    logger.warning("CPF inválido detectado")
                    return None
        
        return None
        return None


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
