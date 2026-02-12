"""
Chatbot IA v2 - Treinável com Base de Conhecimento
CIANET PROVEDOR - v3.0

Features:
- Base de conhecimento customizável
- Treinamento com perguntas frequentes
- Contexto de ISP brasileiro
- Fallback inteligente para humano
- Análise de intenção e sentimento
- Respostas em português natural
"""
import logging
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass, field

# Tentar importar Gemini ou usar fallback
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from app.core.config import settings
from app.core.redis_client import redis_manager
from app.core.database import db_manager
from app.models.database import Usuario

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class Intent(str, Enum):
    """Intenções do cliente"""
    # Técnico
    INTERNET_LENTA = "internet_lenta"
    SEM_CONEXAO = "sem_conexao"
    WIFI_PROBLEMA = "wifi_problema"
    ROTEADOR = "roteador"
    
    # Financeiro
    SEGUNDA_VIA = "segunda_via"
    PAGAMENTO = "pagamento"
    NEGOCIACAO = "negociacao"
    
    # Comercial
    UPGRADE = "upgrade"
    CANCELAMENTO = "cancelamento"
    NOVO_PLANO = "novo_plano"
    
    # Cadastro
    ALTERACAO_DADOS = "alteracao_dados"
    MUDANCA_ENDERECO = "mudanca_endereco"
    
    # Agendamento
    VISITA_TECNICA = "visita_tecnica"
    INSTALACAO = "instalacao"
    
    # Geral
    SAUDACAO = "saudacao"
    DESPEDIDA = "despedida"
    FALAR_HUMANO = "falar_humano"
    OUTRO = "outro"


class Sentiment(str, Enum):
    """Sentimento do cliente"""
    MUITO_POSITIVO = "muito_positivo"
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"
    MUITO_NEGATIVO = "muito_negativo"


# ============================================================================
# BASE DE CONHECIMENTO
# ============================================================================

# Respostas padrão por intenção (ISP brasileiro)
KNOWLEDGE_BASE = {
    Intent.INTERNET_LENTA: {
        "response": """Entendo sua frustração com a velocidade da internet. Vamos resolver isso! 🚀

Por favor, tente estes passos:
1️⃣ Desligue o roteador da tomada por 30 segundos
2️⃣ Ligue novamente e aguarde as luzes estabilizarem (2-3 min)
3️⃣ Faça um teste de velocidade em speedtest.net

Se o problema persistir, posso agendar uma visita técnica. Deseja?""",
        "quick_replies": ["Testar velocidade", "Agendar visita", "Falar com técnico"],
        "escalate_keywords": ["ainda lento", "não resolveu", "piorou", "sempre assim"]
    },
    
    Intent.SEM_CONEXAO: {
        "response": """Vou te ajudar a restabelecer sua conexão! 🔌

Verifique por favor:
1️⃣ Se o roteador está ligado (luzes acesas)
2️⃣ Se o cabo de rede está bem conectado
3️⃣ Se há alguma luz vermelha no equipamento

Enquanto isso, vou verificar se há alguma ocorrência na sua região. Qual seu endereço ou número do contrato?""",
        "quick_replies": ["Verificar minha região", "Roteador desligado", "Luzes vermelhas"],
        "collect_data": ["endereco", "contrato"]
    },
    
    Intent.WIFI_PROBLEMA: {
        "response": """Problemas com WiFi são comuns! Vamos resolver 📶

Algumas dicas:
1️⃣ Aproxime-se do roteador para testar
2️⃣ Verifique se o nome da rede está correto
3️⃣ Tente esquecer a rede e conectar novamente

Se estiver distante do roteador, um repetidor pode ajudar. Quer saber mais sobre nossos repetidores WiFi?""",
        "quick_replies": ["Ver repetidores", "Trocar senha WiFi", "Falar com técnico"]
    },
    
    Intent.ROTEADOR: {
        "response": """Posso te ajudar com a configuração do roteador! 🔧

O que você precisa?
• Trocar a senha do WiFi
• Acessar as configurações
• Reiniciar o equipamento
• Verificar conexões

Geralmente, você acessa o roteador pelo navegador em 192.168.0.1 ou 192.168.1.1""",
        "quick_replies": ["Trocar senha", "Acessar configurações", "Preciso de técnico"]
    },
    
    Intent.SEGUNDA_VIA: {
        "response": """Claro! Posso enviar a 2ª via do boleto agora mesmo! 💳

Informe seu CPF ou número do contrato para eu localizar sua fatura.

Também posso enviar:
• Por e-mail
• Por WhatsApp (PDF)
• Código PIX para pagamento instantâneo""",
        "quick_replies": ["Enviar por WhatsApp", "Código PIX", "Ver todas as faturas"],
        "collect_data": ["cpf", "contrato"]
    },
    
    Intent.PAGAMENTO: {
        "response": """Sobre seu pagamento: 💰

Aceitamos:
• Boleto bancário
• PIX (compensação imediata)
• Cartão de crédito (via app)
• Débito automático

Já fez o pagamento? Se for hoje, a compensação pode levar até 3h úteis para liberar a internet.""",
        "quick_replies": ["Já paguei hoje", "Gerar PIX", "Débito automático"]
    },
    
    Intent.NEGOCIACAO: {
        "response": """Entendo a situação. Temos opções para te ajudar! 🤝

Posso verificar:
• Parcelamento da dívida
• Desconto para pagamento à vista
• Mudança para um plano mais acessível

Para isso, preciso verificar seu cadastro. Pode informar seu CPF?""",
        "quick_replies": ["Informar CPF", "Ver opções de planos", "Falar com financeiro"],
        "collect_data": ["cpf"]
    },
    
    Intent.UPGRADE: {
        "response": """Que ótimo que quer mais velocidade! 🚀

Nossos planos disponíveis:
📶 100 Mbps - R$ 79,90/mês
📶 200 Mbps - R$ 99,90/mês  
📶 400 Mbps - R$ 129,90/mês
📶 600 Mbps - R$ 159,90/mês

O upgrade é feito remotamente, sem visita técnica!""",
        "quick_replies": ["Quero 200 Mbps", "Quero 400 Mbps", "Mais detalhes"]
    },
    
    Intent.CANCELAMENTO: {
        "response": """Sentiremos sua falta! 😢 Mas antes de prosseguir...

Posso verificar:
• Se há algum problema que possamos resolver
• Condições especiais para você ficar
• Planos mais em conta

Gostaria de falar com um especialista que pode te oferecer uma condição especial?""",
        "quick_replies": ["Tenho um problema", "Ver ofertas especiais", "Prosseguir com cancelamento"],
        "escalate": True
    },
    
    Intent.VISITA_TECNICA: {
        "response": """Vou agendar uma visita técnica para você! 🔧

Dias disponíveis esta semana:
📅 Terça-feira (manhã ou tarde)
📅 Quarta-feira (manhã ou tarde)
📅 Quinta-feira (manhã ou tarde)

Qual horário funciona melhor para você?""",
        "quick_replies": ["Terça manhã", "Quarta tarde", "Outro dia"],
        "collect_data": ["data_visita", "turno"]
    },
    
    Intent.INSTALACAO: {
        "response": """Oba, novo cliente! Seja bem-vindo à CIANET! 🎉

Para agendar sua instalação, preciso de:
1️⃣ Seu nome completo
2️⃣ CPF
3️⃣ Endereço com número e complemento

Qual plano você escolheu?""",
        "quick_replies": ["Ver planos", "Já escolhi o plano", "Tenho dúvidas"],
        "collect_data": ["nome", "cpf", "endereco", "plano"]
    },
    
    Intent.ALTERACAO_DADOS: {
        "response": """Posso atualizar seus dados cadastrais! 📝

O que você precisa alterar?
• E-mail
• Telefone
• Forma de pagamento
• Nome do titular

Informe seu CPF para eu acessar seu cadastro.""",
        "quick_replies": ["Alterar e-mail", "Alterar telefone", "Alterar pagamento"],
        "collect_data": ["cpf"]
    },
    
    Intent.MUDANCA_ENDERECO: {
        "response": """Mudança de endereço! 🏠

Preciso verificar se atendemos o novo local. Qual o endereço completo?

Se atendermos, agendamos a transferência. Importante:
• A mudança leva até 5 dias úteis
• Não há cobrança de instalação
• Você escolhe o melhor dia""",
        "quick_replies": ["Informar novo endereço", "Verificar cobertura", "Falar com atendente"]
    },
    
    Intent.SAUDACAO: {
        "response": """Olá! 👋 Seja bem-vindo ao atendimento da CIANET!

Sou o assistente virtual e posso te ajudar com:
• 🌐 Problemas de conexão
• 💳 Faturas e pagamentos
• 📶 Upgrade de plano
• 📅 Agendamento de visita

Como posso te ajudar hoje?""",
        "quick_replies": ["Problema na internet", "2ª via de boleto", "Falar com atendente"]
    },
    
    Intent.DESPEDIDA: {
        "response": """Foi um prazer te atender! 😊

Se precisar de mais alguma coisa, é só chamar aqui no WhatsApp.

Avalie nosso atendimento de 1 a 5 estrelas ⭐""",
        "quick_replies": ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    },
    
    Intent.FALAR_HUMANO: {
        "response": """Claro! Vou te transferir para um de nossos atendentes. 👤

Tempo médio de espera: 2 minutos

Enquanto aguarda, posso te ajudar com algo rápido?""",
        "escalate": True,
        "quick_replies": ["Aguardar atendente", "Ver minhas faturas", "Testar conexão"]
    },
    
    Intent.OUTRO: {
        "response": """Hmm, não tenho certeza se entendi corretamente. 🤔

Posso te ajudar com:
• Problemas técnicos (internet, WiFi)
• Faturas e pagamentos
• Mudança de plano
• Agendamentos

Pode me explicar melhor o que precisa?""",
        "quick_replies": ["Problema técnico", "Financeiro", "Comercial", "Falar com atendente"]
    }
}

# Palavras-chave para classificação de intenção
INTENT_KEYWORDS = {
    Intent.INTERNET_LENTA: ["lenta", "devagar", "velocidade", "lentidão", "demora", "travando"],
    Intent.SEM_CONEXAO: ["sem internet", "não conecta", "caiu", "offline", "sem acesso", "não funciona"],
    Intent.WIFI_PROBLEMA: ["wifi", "wi-fi", "wireless", "sem fio", "sinal fraco"],
    Intent.ROTEADOR: ["roteador", "modem", "equipamento", "aparelho", "configurar"],
    Intent.SEGUNDA_VIA: ["segunda via", "2 via", "boleto", "fatura", "conta"],
    Intent.PAGAMENTO: ["paguei", "pagamento", "pagar", "pix", "débito"],
    Intent.NEGOCIACAO: ["negociar", "parcelar", "dívida", "atraso", "acordo"],
    Intent.UPGRADE: ["upgrade", "aumentar", "plano maior", "mais velocidade", "melhorar"],
    Intent.CANCELAMENTO: ["cancelar", "desistir", "encerrar", "não quero mais"],
    Intent.VISITA_TECNICA: ["visita", "técnico", "agendar", "mandar alguém"],
    Intent.INSTALACAO: ["instalar", "instalação", "novo cliente", "contratar"],
    Intent.ALTERACAO_DADOS: ["alterar", "mudar dados", "atualizar cadastro", "email", "telefone"],
    Intent.MUDANCA_ENDERECO: ["mudança", "mudar endereço", "novo endereço", "mudei"],
    Intent.SAUDACAO: ["oi", "olá", "bom dia", "boa tarde", "boa noite", "hey"],
    Intent.DESPEDIDA: ["tchau", "obrigado", "valeu", "até mais", "falou"],
    Intent.FALAR_HUMANO: ["atendente", "humano", "pessoa", "falar com alguém", "operador"]
}

# Palavras para análise de sentimento
SENTIMENT_KEYWORDS = {
    Sentiment.MUITO_NEGATIVO: ["péssimo", "horrível", "pior", "vergonha", "absurdo", "processarem"],
    Sentiment.NEGATIVO: ["ruim", "problema", "frustrado", "irritado", "decepcionado", "caro"],
    Sentiment.POSITIVO: ["bom", "legal", "gostei", "ajudou", "resolveu"],
    Sentiment.MUITO_POSITIVO: ["excelente", "ótimo", "maravilhoso", "perfeito", "incrível", "parabéns"]
}


# ============================================================================
# CHATBOT V2
# ============================================================================

class ChatbotV2:
    """
    Chatbot treinável com base de conhecimento ISP.
    Usa Gemini para processamento avançado com fallback local.
    """
    
    def __init__(self):
        self.model = None
        self.company_name = getattr(settings, 'CHATBOT_COMPANY_NAME', 'CIANET')
        self._init_gemini()
        self._load_custom_knowledge()
    
    def _init_gemini(self):
        """Inicializar modelo Gemini"""
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini não disponível, usando modo local")
            return
        
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            logger.warning("GEMINI_API_KEY não configurada")
            return
        
        try:
            genai.configure(api_key=api_key)
            
            # Configurações de segurança
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
            
            # System prompt
            system_instruction = f"""Você é um assistente virtual da {self.company_name}, um provedor de internet brasileiro.

REGRAS IMPORTANTES:
1. Sempre responda em português brasileiro, de forma amigável e profissional
2. Use emojis com moderação para deixar a conversa mais leve
3. Seja objetivo e direto nas respostas
4. Se não souber algo, sugira falar com um atendente
5. Nunca invente informações sobre planos ou preços
6. Mostre empatia quando o cliente estiver com problemas

CONTEXTO DA EMPRESA:
- Provedor de internet fibra óptica
- Atendemos residências e empresas
- Planos de 100Mbps a 1Gbps
- Suporte 24/7 por WhatsApp e telefone
- Área de cobertura: região local

VOCÊ PODE AJUDAR COM:
- Problemas técnicos (internet lenta, sem conexão, WiFi)
- Faturas e pagamentos (2ª via, PIX, negociação)
- Planos e upgrades
- Agendamento de visita técnica
- Atualização de cadastro"""

            self.model = genai.GenerativeModel(
                model_name=getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
                safety_settings=safety_settings,
                system_instruction=system_instruction
            )
            
            logger.info("Gemini inicializado com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao inicializar Gemini: {e}")
            self.model = None
    
    def _load_custom_knowledge(self):
        """Carregar conhecimento customizado do banco"""
        try:
            # Carregar respostas do admin (tabela chatbot_responses)
            with sqlserver_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT intent, response, quick_replies, is_active
                    FROM chatbot_responses
                    WHERE is_active = 1
                """)
                
                for row in cursor.fetchall():
                    intent_key = row.intent
                    if hasattr(Intent, intent_key.upper()):
                        intent = Intent(intent_key.lower())
                        if intent in KNOWLEDGE_BASE:
                            KNOWLEDGE_BASE[intent]["response"] = row.response
                            if row.quick_replies:
                                KNOWLEDGE_BASE[intent]["quick_replies"] = json.loads(row.quick_replies)
                
                logger.info("Conhecimento customizado carregado")
        
        except Exception as e:
            logger.debug(f"Tabela chatbot_responses não existe ou erro: {e}")
    
    def classify_intent(self, message: str) -> Tuple[Intent, float]:
        """
        Classificar intenção da mensagem.
        Retorna (intent, confidence).
        """
        message_lower = message.lower()
        
        best_intent = Intent.OUTRO
        best_score = 0.0
        
        for intent, keywords in INTENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches > 0:
                score = matches / len(keywords)
                if score > best_score:
                    best_score = score
                    best_intent = intent
        
        # Ajustar confiança
        confidence = min(0.9, best_score * 1.5) if best_score > 0 else 0.3
        
        return best_intent, confidence
    
    def analyze_sentiment(self, message: str) -> Sentiment:
        """Analisar sentimento da mensagem"""
        message_lower = message.lower()
        
        # Verificar keywords de sentimento
        for sentiment, keywords in SENTIMENT_KEYWORDS.items():
            for kw in keywords:
                if kw in message_lower:
                    return sentiment
        
        return Sentiment.NEUTRO
    
    def should_escalate(
        self, 
        intent: Intent, 
        sentiment: Sentiment, 
        message: str,
        attempts: int = 0
    ) -> Tuple[bool, str]:
        """
        Verificar se deve escalar para humano.
        Retorna (should_escalate, reason).
        """
        # Solicitação explícita
        if intent == Intent.FALAR_HUMANO:
            return True, "Cliente solicitou atendente"
        
        # Cancelamento sempre escala
        if intent == Intent.CANCELAMENTO:
            return True, "Solicitação de cancelamento"
        
        # Sentimento muito negativo
        if sentiment == Sentiment.MUITO_NEGATIVO:
            return True, "Cliente muito insatisfeito"
        
        # Muitas tentativas
        if attempts >= 3:
            return True, "Limite de tentativas do bot"
        
        # Verificar keywords de escalação
        kb = KNOWLEDGE_BASE.get(intent, {})
        escalate_keywords = kb.get("escalate_keywords", [])
        
        message_lower = message.lower()
        for kw in escalate_keywords:
            if kw in message_lower:
                return True, f"Keyword de escalação: {kw}"
        
        # Escalação forçada no KB
        if kb.get("escalate"):
            return True, "Intenção requer atendimento humano"
        
        return False, ""
    
    async def process_message(
        self,
        content: str,
        conversation_id: int = None,
        client_name: str = None,
        context_messages: List[Dict] = None
    ) -> Optional[str]:
        """
        Processar mensagem e gerar resposta.
        
        1. Classificar intenção
        2. Analisar sentimento
        3. Verificar escalação
        4. Gerar resposta (Gemini ou KB)
        """
        try:
            # 1. Classificar intenção
            intent, confidence = self.classify_intent(content)
            logger.info(f"Intent: {intent.value} (confidence: {confidence:.2f})")
            
            # 2. Analisar sentimento
            sentiment = self.analyze_sentiment(content)
            logger.info(f"Sentiment: {sentiment.value}")
            
            # 3. Verificar se deve escalar
            should_escalate, reason = self.should_escalate(
                intent=intent,
                sentiment=sentiment,
                message=content,
                attempts=0  # TODO: rastrear tentativas
            )
            
            if should_escalate:
                logger.info(f"Escalando para humano: {reason}")
                return None  # Retorna None para indicar escalação
            
            # 4. Gerar resposta
            response = await self._generate_response(
                message=content,
                intent=intent,
                client_name=client_name,
                context_messages=context_messages
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return None
    
    async def _generate_response(
        self,
        message: str,
        intent: Intent,
        client_name: str = None,
        context_messages: List[Dict] = None
    ) -> str:
        """
        Gerar resposta usando Gemini ou fallback para KB.
        """
        # Tentar Gemini primeiro
        if self.model:
            try:
                # Construir histórico
                history = []
                if context_messages:
                    for msg in context_messages[-5:]:  # Últimas 5
                        role = "user" if msg.get("sender_type") == "client" else "model"
                        history.append({"role": role, "parts": [msg.get("content", "")]})
                
                # Adicionar contexto do cliente
                user_context = ""
                if client_name:
                    user_context = f"[Cliente: {client_name}] "
                
                # Gerar com Gemini
                chat = self.model.start_chat(history=history)
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: chat.send_message(user_context + message)
                )
                
                return response.text
            
            except Exception as e:
                logger.warning(f"Gemini falhou, usando fallback: {e}")
        
        # Fallback: usar base de conhecimento
        kb = KNOWLEDGE_BASE.get(intent, KNOWLEDGE_BASE[Intent.OUTRO])
        response = kb.get("response", "Desculpe, não entendi. Pode reformular?")
        
        # Personalizar com nome
        if client_name:
            response = f"Olá, {client_name}! " + response
        
        return response
    
    def get_quick_replies(self, intent: Intent) -> List[str]:
        """Obter sugestões de resposta rápida"""
        kb = KNOWLEDGE_BASE.get(intent, {})
        return kb.get("quick_replies", [])
    
    def get_required_data(self, intent: Intent) -> List[str]:
        """Obter dados que precisam ser coletados"""
        kb = KNOWLEDGE_BASE.get(intent, {})
        return kb.get("collect_data", [])
    
    async def train_response(
        self,
        intent: str,
        response: str,
        quick_replies: List[str] = None
    ) -> bool:
        """
        Treinar/atualizar resposta para uma intenção.
        Salva no banco para persistência.
        """
        try:
            with sqlserver_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar se existe
                cursor.execute(
                    "SELECT id FROM chatbot_responses WHERE intent = ?",
                    (intent,)
                )
                exists = cursor.fetchone()
                
                qr_json = json.dumps(quick_replies) if quick_replies else None
                
                if exists:
                    cursor.execute("""
                        UPDATE chatbot_responses 
                        SET response = ?, quick_replies = ?, updated_at = GETDATE()
                        WHERE intent = ?
                    """, (response, qr_json, intent))
                else:
                    cursor.execute("""
                        INSERT INTO chatbot_responses (intent, response, quick_replies, is_active)
                        VALUES (?, ?, ?, 1)
                    """, (intent, response, qr_json))
                
                conn.commit()
                
                # Atualizar KB em memória
                if hasattr(Intent, intent.upper()):
                    intent_enum = Intent(intent.lower())
                    if intent_enum in KNOWLEDGE_BASE:
                        KNOWLEDGE_BASE[intent_enum]["response"] = response
                        if quick_replies:
                            KNOWLEDGE_BASE[intent_enum]["quick_replies"] = quick_replies
                
                logger.info(f"Resposta treinada: {intent}")
                return True
        
        except Exception as e:
            logger.error(f"Erro ao treinar resposta: {e}")
            return False


# Instância singleton
chatbot_v2 = ChatbotV2()


# Função para uso pelo webhook
async def process_with_chatbot(
    content: str,
    conversation_id: int = None,
    client_name: str = None
) -> Optional[str]:
    """Função wrapper para processamento de mensagens"""
    return await chatbot_v2.process_message(
        content=content,
        conversation_id=conversation_id,
        client_name=client_name
    )
