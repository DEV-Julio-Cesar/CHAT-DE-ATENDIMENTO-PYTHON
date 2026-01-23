"""
Chatbot Inteligente para ISP - Google Gemini AI
Sistema avançado de atendimento automatizado
"""
import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog
from app.core.config import settings
from app.core.redis_client import redis_manager
from app.core.monitoring import monitoring
import google.generativeai as genai

logger = structlog.get_logger(__name__)

# Configurar Gemini AI
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


@dataclass
class ChatContext:
    """Contexto da conversa"""
    customer_id: str
    customer_name: str
    customer_phone: str
    conversation_history: List[Dict]
    customer_data: Optional[Dict] = None
    current_intent: Optional[str] = None
    confidence_score: float = 0.0
    last_interaction: Optional[datetime] = None


@dataclass
class ChatbotResponse:
    """Resposta do chatbot"""
    message: str
    intent: str
    confidence: float
    actions: List[str]
    escalate_to_human: bool
    suggested_responses: List[str]
    metadata: Dict[str, Any]


class ISPChatbotAI:
    """Chatbot inteligente para ISP com Google Gemini"""
    
    def __init__(self):
        self.model = None
        self.knowledge_base = {}
        self.intents = {}
        self.conversation_contexts = {}
        
        # Inicializar modelo Gemini
        if settings.GEMINI_API_KEY:
            self.model = genai.GenerativeModel('gemini-pro')
            
    async def initialize(self):
        """Inicializa o chatbot"""
        await self._load_knowledge_base()
        await self._load_intents()
        logger.info("ISP Chatbot AI initialized successfully")
        
    async def process_message(
        self,
        customer_id: str,
        message: str,
        customer_data: Optional[Dict] = None
    ) -> ChatbotResponse:
        """
        Processa mensagem do cliente e gera resposta inteligente
        """
        try:
            # Obtém contexto da conversa
            context = await self._get_conversation_context(customer_id, customer_data)
            
            # Adiciona mensagem ao histórico
            context.conversation_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'sender': 'customer',
                'message': message,
                'type': 'text'
            })
            
            # Detecta intenção
            intent, confidence = await self._detect_intent(message, context)
            context.current_intent = intent
            context.confidence_score = confidence
            
            # Gera resposta baseada na intenção
            if confidence >= 0.8:
                response = await self._generate_response(intent, message, context)
            else:
                response = await self._generate_ai_response(message, context)
                
            # Salva contexto atualizado
            await self._save_conversation_context(customer_id, context)
            
            # Registra métricas
            await self._log_interaction(customer_id, intent, confidence, response.escalate_to_human)
            
            return response
            
        except Exception as e:
            logger.error("Error processing chatbot message", error=str(e))
            return ChatbotResponse(
                message="Desculpe, estou com dificuldades técnicas. Um atendente humano irá ajudá-lo em breve.",
                intent="error",
                confidence=0.0,
                actions=["escalate_to_human"],
                escalate_to_human=True,
                suggested_responses=[],
                metadata={"error": str(e)}
            )
            
    async def _get_conversation_context(
        self,
        customer_id: str,
        customer_data: Optional[Dict] = None
    ) -> ChatContext:
        """Obtém contexto da conversa"""
        
        # Verifica cache Redis
        cached_context = await redis_manager.get(f"chatbot:context:{customer_id}")
        if cached_context:
            context_data = json.loads(cached_context)
            context = ChatContext(**context_data)
            context.last_interaction = datetime.fromisoformat(context_data['last_interaction'])
            return context
            
        # Cria novo contexto
        context = ChatContext(
            customer_id=customer_id,
            customer_name=customer_data.get('name', 'Cliente') if customer_data else 'Cliente',
            customer_phone=customer_data.get('phone', '') if customer_data else '',
            conversation_history=[],
            customer_data=customer_data,
            last_interaction=datetime.utcnow()
        )
        
        return context
        
    async def _save_conversation_context(self, customer_id: str, context: ChatContext):
        """Salva contexto da conversa"""
        context_data = asdict(context)
        context_data['last_interaction'] = context.last_interaction.isoformat()
        
        await redis_manager.setex(
            f"chatbot:context:{customer_id}",
            3600,  # 1 hora
            json.dumps(context_data)
        )
        
    async def _detect_intent(self, message: str, context: ChatContext) -> Tuple[str, float]:
        """Detecta intenção da mensagem"""
        message_lower = message.lower()
        
        # Intenções com padrões regex
        intent_patterns = {
            'saudacao': [
                r'\b(oi|olá|ola|bom dia|boa tarde|boa noite|hey|e aí)\b',
                r'\b(tudo bem|como vai|opa)\b'
            ],
            'problema_internet': [
                r'\b(internet|conexão|wifi|wi-fi|rede|sinal)\b.*\b(lenta|devagar|ruim|caiu|parou|não funciona|problema)\b',
                r'\b(sem internet|internet parou|não conecta|não carrega)\b',
                r'\b(velocidade|lentidão|demora|travando)\b'
            ],
            'problema_financeiro': [
                r'\b(boleto|fatura|conta|pagamento|vencimento|débito)\b',
                r'\b(pagar|quitar|parcelar|negociar|desconto)\b',
                r'\b(em atraso|vencida|pendente|bloqueado por falta de pagamento)\b'
            ],
            'suporte_tecnico': [
                r'\b(roteador|modem|equipamento|instalação|técnico)\b',
                r'\b(configurar|instalar|trocar|defeito|quebrou)\b',
                r'\b(senha|login|acesso|configuração)\b'
            ],
            'comercial': [
                r'\b(plano|pacote|velocidade|upgrade|mudar|contratar)\b',
                r'\b(preço|valor|promoção|oferta|desconto)\b',
                r'\b(fibra|banda larga|mega|giga)\b'
            ],
            'cancelamento': [
                r'\b(cancelar|desistir|não quero mais|encerrar)\b',
                r'\b(sair|deixar|parar de usar)\b'
            ],
            'elogio': [
                r'\b(obrigado|obrigada|valeu|muito bom|excelente|parabéns)\b',
                r'\b(gostei|satisfeito|recomendo)\b'
            ],
            'reclamacao': [
                r'\b(reclamar|insatisfeito|péssimo|horrível|revoltado)\b',
                r'\b(procon|anatel|justiça|processo)\b'
            ]
        }
        
        best_intent = 'unknown'
        best_confidence = 0.0
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                if matches:
                    confidence = len(matches) * 0.3 + 0.7  # Base confidence + matches
                    if confidence > best_confidence:
                        best_confidence = min(confidence, 1.0)
                        best_intent = intent
                        
        return best_intent, best_confidence
        
    async def _generate_response(
        self,
        intent: str,
        message: str,
        context: ChatContext
    ) -> ChatbotResponse:
        """Gera resposta baseada na intenção detectada"""
        
        responses = {
            'saudacao': {
                'message': f"Olá {context.customer_name}! 👋 Sou o assistente virtual da {settings.APP_NAME}. Como posso ajudá-lo hoje?",
                'actions': ['show_menu'],
                'escalate': False,
                'suggestions': [
                    "Problema com internet",
                    "Consultar fatura",
                    "Suporte técnico",
                    "Falar com atendente"
                ]
            },
            'problema_internet': {
                'message': f"Entendo que você está com problemas na internet, {context.customer_name}. Vou verificar sua conexão e te ajudar a resolver isso rapidamente! 🔧\n\nPrimeiro, me diga: o problema é com a velocidade ou a internet parou completamente?",
                'actions': ['check_connection', 'diagnostic'],
                'escalate': False,
                'suggestions': [
                    "Internet muito lenta",
                    "Internet parou completamente",
                    "Só alguns sites não abrem",
                    "Falar com técnico"
                ]
            },
            'problema_financeiro': {
                'message': f"Vou te ajudar com a questão financeira, {context.customer_name}! 💳\n\nPosso consultar sua fatura, gerar segunda via do boleto ou verificar opções de parcelamento. O que você precisa?",
                'actions': ['check_billing', 'generate_invoice'],
                'escalate': False,
                'suggestions': [
                    "Ver minha fatura",
                    "Segunda via do boleto",
                    "Negociar parcelamento",
                    "Falar com financeiro"
                ]
            },
            'suporte_tecnico': {
                'message': f"Perfeito, {context.customer_name}! Vou te ajudar com o suporte técnico. 🔧\n\nPara eu te ajudar melhor, me conte: é sobre configuração do roteador, instalação de equipamento ou outro problema técnico?",
                'actions': ['technical_support'],
                'escalate': False,
                'suggestions': [
                    "Configurar roteador",
                    "Problema no equipamento",
                    "Instalação nova",
                    "Falar com técnico"
                ]
            },
            'comercial': {
                'message': f"Ótimo, {context.customer_name}! Vou te mostrar nossas melhores ofertas! 🚀\n\nTemos planos de fibra óptica com velocidades de 100MB a 1GB. Qual velocidade você tem interesse?",
                'actions': ['show_plans', 'commercial'],
                'escalate': False,
                'suggestions': [
                    "Planos disponíveis",
                    "Upgrade de velocidade",
                    "Promoções atuais",
                    "Falar com vendas"
                ]
            },
            'cancelamento': {
                'message': f"Entendo sua situação, {context.customer_name}. Antes de prosseguir com o cancelamento, que tal conversarmos sobre o que está acontecendo? Talvez eu possa te ajudar a resolver! 🤝\n\nPosso transferir você para nossa equipe de retenção que tem ofertas especiais.",
                'actions': ['retention', 'escalate_retention'],
                'escalate': True,
                'suggestions': [
                    "Ver ofertas especiais",
                    "Falar com retenção",
                    "Continuar cancelamento",
                    "Resolver problema primeiro"
                ]
            },
            'elogio': {
                'message': f"Muito obrigado pelo elogio, {context.customer_name}! 😊 Ficamos muito felizes em saber que você está satisfeito com nossos serviços. Sua opinião é muito importante para nós!\n\nHá mais alguma coisa em que posso ajudá-lo?",
                'actions': ['thank_customer'],
                'escalate': False,
                'suggestions': [
                    "Indicar para amigos",
                    "Avaliar no Google",
                    "Ver novos serviços",
                    "Não, obrigado"
                ]
            },
            'reclamacao': {
                'message': f"Lamento muito pelo inconveniente, {context.customer_name}. 😔 Sua reclamação é muito importante para nós e vamos resolver isso imediatamente!\n\nVou transferir você para um supervisor que poderá te ajudar da melhor forma possível.",
                'actions': ['escalate_supervisor', 'log_complaint'],
                'escalate': True,
                'suggestions': [
                    "Falar com supervisor",
                    "Registrar reclamação formal",
                    "Ver compensação",
                    "Protocolo de atendimento"
                ]
            }
        }
        
        response_data = responses.get(intent, {
            'message': "Entendi. Deixe-me transferir você para um atendente humano que poderá te ajudar melhor.",
            'actions': ['escalate_to_human'],
            'escalate': True,
            'suggestions': ["Falar com atendente"]
        })
        
        return ChatbotResponse(
            message=response_data['message'],
            intent=intent,
            confidence=0.9,
            actions=response_data['actions'],
            escalate_to_human=response_data['escalate'],
            suggested_responses=response_data['suggestions'],
            metadata={'response_type': 'template', 'intent': intent}
        )
        
    async def _generate_ai_response(
        self,
        message: str,
        context: ChatContext
    ) -> ChatbotResponse:
        """Gera resposta usando IA quando intenção não é clara"""
        
        if not self.model:
            return ChatbotResponse(
                message="Desculpe, não entendi sua solicitação. Pode reformular ou escolher uma das opções abaixo?",
                intent="unknown",
                confidence=0.0,
                actions=["show_menu"],
                escalate_to_human=False,
                suggested_responses=[
                    "Problema com internet",
                    "Consultar fatura", 
                    "Suporte técnico",
                    "Falar com atendente"
                ],
                metadata={"ai_available": False}
            )
            
        try:
            # Prompt contextualizado para ISP
            prompt = f"""
Você é um assistente virtual de um provedor de internet (ISP) chamado {settings.APP_NAME}.
Você deve ser prestativo, profissional e resolver problemas dos clientes.

Contexto do cliente:
- Nome: {context.customer_name}
- Telefone: {context.customer_phone}
- Histórico recente: {context.conversation_history[-3:] if context.conversation_history else 'Primeira interação'}

Mensagem do cliente: "{message}"

Responda de forma:
1. Amigável e profissional
2. Focada em resolver o problema
3. Oferecendo opções claras
4. Máximo 200 caracteres
5. Use emojis apropriados

Se não conseguir resolver, sugira falar com atendente humano.
"""

            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            ai_message = response.text.strip()
            
            # Verifica se deve escalar para humano
            escalate_keywords = ['não consigo', 'não sei', 'atendente', 'humano', 'supervisor']
            should_escalate = any(keyword in ai_message.lower() for keyword in escalate_keywords)
            
            return ChatbotResponse(
                message=ai_message,
                intent="ai_generated",
                confidence=0.7,
                actions=["ai_response"],
                escalate_to_human=should_escalate,
                suggested_responses=[
                    "Isso resolve meu problema",
                    "Preciso de mais ajuda",
                    "Falar com atendente",
                    "Obrigado"
                ],
                metadata={"ai_generated": True, "model": "gemini-pro"}
            )
            
        except Exception as e:
            logger.error("Error generating AI response", error=str(e))
            return ChatbotResponse(
                message="Desculpe, estou com dificuldades no momento. Vou transferir você para um atendente humano.",
                intent="ai_error",
                confidence=0.0,
                actions=["escalate_to_human"],
                escalate_to_human=True,
                suggested_responses=["Falar com atendente"],
                metadata={"ai_error": str(e)}
            )
            
    async def _load_knowledge_base(self):
        """Carrega base de conhecimento do ISP"""
        self.knowledge_base = {
            'planos': {
                '100mb': {'velocidade': '100 Mbps', 'preco': 'R$ 79,90', 'tipo': 'fibra'},
                '200mb': {'velocidade': '200 Mbps', 'preco': 'R$ 99,90', 'tipo': 'fibra'},
                '500mb': {'velocidade': '500 Mbps', 'preco': 'R$ 149,90', 'tipo': 'fibra'},
                '1gb': {'velocidade': '1 Gbps', 'preco': 'R$ 199,90', 'tipo': 'fibra'}
            },
            'problemas_comuns': {
                'internet_lenta': {
                    'solucoes': [
                        'Reiniciar o roteador',
                        'Verificar cabos',
                        'Testar velocidade',
                        'Verificar dispositivos conectados'
                    ]
                },
                'sem_internet': {
                    'solucoes': [
                        'Verificar energia do roteador',
                        'Verificar cabos',
                        'Verificar status da rede',
                        'Contatar suporte técnico'
                    ]
                }
            },
            'horarios_atendimento': {
                'segunda_sexta': '08:00 às 18:00',
                'sabado': '08:00 às 14:00',
                'domingo': 'Emergências apenas'
            }
        }
        
    async def _load_intents(self):
        """Carrega configurações de intenções"""
        self.intents = {
            'confidence_threshold': 0.7,
            'escalation_threshold': 0.5,
            'max_bot_attempts': 3
        }
        
    async def _log_interaction(
        self,
        customer_id: str,
        intent: str,
        confidence: float,
        escalated: bool
    ):
        """Registra interação para métricas"""
        interaction_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'customer_id': customer_id,
            'intent': intent,
            'confidence': confidence,
            'escalated': escalated
        }
        
        # Salva no Redis para métricas
        await redis_manager.lpush(
            'chatbot:interactions',
            json.dumps(interaction_data)
        )
        
        # Mantém apenas últimas 10000 interações
        await redis_manager.ltrim('chatbot:interactions', 0, 9999)
        
    async def get_analytics(self) -> Dict[str, Any]:
        """Obtém analytics do chatbot"""
        try:
            # Obtém interações recentes
            interactions_data = await redis_manager.lrange('chatbot:interactions', 0, -1)
            interactions = [json.loads(data) for data in interactions_data]
            
            if not interactions:
                return {
                    'total_interactions': 0,
                    'resolution_rate': 0,
                    'avg_confidence': 0,
                    'top_intents': [],
                    'escalation_rate': 0
                }
                
            total = len(interactions)
            escalated = sum(1 for i in interactions if i['escalated'])
            avg_confidence = sum(i['confidence'] for i in interactions) / total
            
            # Top intenções
            intent_counts = {}
            for interaction in interactions:
                intent = interaction['intent']
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
                
            top_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'total_interactions': total,
                'resolution_rate': ((total - escalated) / total * 100) if total > 0 else 0,
                'avg_confidence': avg_confidence,
                'top_intents': top_intents,
                'escalation_rate': (escalated / total * 100) if total > 0 else 0,
                'period': '24h'
            }
            
        except Exception as e:
            logger.error("Error getting chatbot analytics", error=str(e))
            return {'error': str(e)}


# Instância global
chatbot_ai = ISPChatbotAI()