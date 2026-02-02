"""
Chatbot Treinável - Sistema de IA baseado em conhecimento personalizado
Gratuito e sem dependência de APIs externas
"""
import json
import re
import difflib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class TrainableChatbot:
    """
    Chatbot treinável com base de conhecimento personalizável.
    Funciona offline, sem necessidade de APIs externas.
    """
    
    def __init__(self, knowledge_file: str = "knowledge_base.json"):
        self.knowledge_path = Path(__file__).parent.parent.parent / "data" / knowledge_file
        self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configurações
        self.company_name = "TelecomISP"
        self.similarity_threshold = 0.6  # Mínimo de similaridade para match
        self.max_suggestions = 3
        
        # Carregar ou criar base de conhecimento
        self.knowledge_base = self._load_knowledge()
        
        # Estatísticas
        self.stats = {
            "total_queries": 0,
            "matched_queries": 0,
            "unmatched_queries": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def _load_knowledge(self) -> Dict[str, Any]:
        """Carregar base de conhecimento do arquivo"""
        if self.knowledge_path.exists():
            try:
                with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar knowledge base: {e}")
        
        # Criar base de conhecimento padrão para ISP
        return self._create_default_knowledge()
    
    def _create_default_knowledge(self) -> Dict[str, Any]:
        """Criar base de conhecimento padrão para empresa de telecomunicações"""
        knowledge = {
            "config": {
                "company_name": "TelecomISP",
                "welcome_message": "Olá! 👋 Sou o assistente virtual da {company}. Como posso ajudar?",
                "fallback_message": "Desculpe, não entendi sua pergunta. Vou transferir para um atendente humano. 🙋",
                "transfer_message": "Aguarde um momento, estou transferindo para um de nossos atendentes... ⏳",
                "goodbye_message": "Obrigado pelo contato! Se precisar de mais ajuda, é só chamar. 😊",
                "business_hours": "Segunda a Sexta: 08h às 18h | Sábado: 08h às 12h"
            },
            "intents": [
                {
                    "id": "saudacao",
                    "name": "Saudação",
                    "patterns": [
                        "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
                        "hey", "e aí", "eai", "oie", "opa", "salve"
                    ],
                    "responses": [
                        "Olá! 👋 Bem-vindo à {company}! Como posso ajudar você hoje?",
                        "Oi! 😊 Sou o assistente virtual da {company}. Em que posso ser útil?"
                    ],
                    "category": "geral"
                },
                {
                    "id": "despedida",
                    "name": "Despedida",
                    "patterns": [
                        "tchau", "até mais", "ate mais", "adeus", "flw", "falou",
                        "obrigado", "obrigada", "valeu", "thanks"
                    ],
                    "responses": [
                        "Até mais! 👋 Foi um prazer atendê-lo. Qualquer dúvida, estamos aqui!",
                        "Obrigado pelo contato! 😊 Tenha um ótimo dia!"
                    ],
                    "category": "geral"
                },
                {
                    "id": "internet_lenta",
                    "name": "Internet Lenta",
                    "patterns": [
                        "internet lenta", "lenta", "devagar", "travando",
                        "internet ruim", "não carrega", "demora para carregar",
                        "velocidade baixa", "ping alto", "lag"
                    ],
                    "responses": [
                        "Entendo que sua internet está lenta. 🔧 Vamos resolver!\n\n**Tente estes passos:**\n1️⃣ Reinicie seu roteador (desligue, aguarde 30 seg, ligue)\n2️⃣ Verifique se há muitos dispositivos conectados\n3️⃣ Faça um teste em speedtest.net\n\nSe o problema persistir, posso abrir um chamado técnico. Deseja?"
                    ],
                    "category": "suporte_tecnico",
                    "tags": ["internet", "lentidao", "velocidade"]
                },
                {
                    "id": "sem_internet",
                    "name": "Sem Internet",
                    "patterns": [
                        "sem internet", "internet caiu", "não tenho internet",
                        "sem conexão", "sem conexao", "caiu a internet",
                        "offline", "não conecta", "wifi não funciona"
                    ],
                    "responses": [
                        "Sem internet? Vamos verificar! 🔍\n\n**Checklist rápido:**\n1️⃣ As luzes do roteador estão acesas?\n2️⃣ O cabo de rede está conectado?\n3️⃣ Já tentou reiniciar o equipamento?\n\n📍 Se as luzes estiverem apagadas ou vermelhas, pode ser um problema na rede. Informo seu endereço para verificar?"
                    ],
                    "category": "suporte_tecnico",
                    "tags": ["internet", "conexao", "offline"]
                },
                {
                    "id": "segunda_via",
                    "name": "Segunda Via de Boleto",
                    "patterns": [
                        "segunda via", "2 via", "boleto", "fatura",
                        "conta", "pagar", "pagamento", "vencimento",
                        "codigo de barras", "pix da fatura"
                    ],
                    "responses": [
                        "Para segunda via do boleto: 📄\n\n**Opções:**\n1️⃣ Acesse nosso portal: portal.telecom.com.br\n2️⃣ Ou informe seu CPF que envio o código PIX aqui mesmo!\n\nQual sua preferência?"
                    ],
                    "category": "financeiro",
                    "tags": ["boleto", "pagamento", "fatura"]
                },
                {
                    "id": "cancelamento",
                    "name": "Cancelamento",
                    "patterns": [
                        "cancelar", "cancela", "cancelamento", "desistir",
                        "encerrar contrato", "não quero mais", "rescindir"
                    ],
                    "responses": [
                        "Que pena que deseja cancelar! 😢\n\nAntes de prosseguir, posso verificar se há algo que possamos fazer para melhorar sua experiência?\n\nSe preferir continuar com o cancelamento, vou transferir para nossa equipe de retenção que poderá apresentar condições especiais."
                    ],
                    "category": "comercial",
                    "tags": ["cancelamento", "retencao"]
                },
                {
                    "id": "upgrade_plano",
                    "name": "Upgrade de Plano",
                    "patterns": [
                        "mudar plano", "upgrade", "aumentar velocidade",
                        "plano melhor", "mais internet", "trocar plano",
                        "planos disponíveis", "quanto custa"
                    ],
                    "responses": [
                        "Ótimo interesse em melhorar seu plano! 🚀\n\n**Nossos planos:**\n📶 100 Mbps - R$ 79,90/mês\n📶 200 Mbps - R$ 99,90/mês\n📶 400 Mbps - R$ 129,90/mês\n📶 600 Mbps - R$ 159,90/mês\n\nQual velocidade te interessa? Posso verificar disponibilidade no seu endereço!"
                    ],
                    "category": "comercial",
                    "tags": ["planos", "upgrade", "vendas"]
                },
                {
                    "id": "horario_atendimento",
                    "name": "Horário de Atendimento",
                    "patterns": [
                        "horário", "horario", "funcionamento", "atendimento",
                        "que horas", "abre", "fecha", "plantão"
                    ],
                    "responses": [
                        "⏰ **Nossos horários:**\n\n📞 Central de Atendimento:\nSeg-Sex: 08h às 22h\nSáb-Dom: 08h às 18h\n\n🔧 Suporte Técnico:\n24 horas, 7 dias por semana\n\n🏢 Loja Física:\nSeg-Sex: 09h às 18h\nSáb: 09h às 13h"
                    ],
                    "category": "geral",
                    "tags": ["horario", "atendimento"]
                },
                {
                    "id": "visita_tecnica",
                    "name": "Visita Técnica",
                    "patterns": [
                        "visita", "técnico", "tecnico", "agendar visita",
                        "mandar alguém", "enviar técnico", "instalação"
                    ],
                    "responses": [
                        "Vou agendar uma visita técnica! 🔧\n\nPara isso, preciso de algumas informações:\n1️⃣ Seu nome completo\n2️⃣ Endereço com número\n3️⃣ Melhor período (manhã/tarde)\n\nPode me informar?"
                    ],
                    "category": "suporte_tecnico",
                    "tags": ["visita", "tecnico", "agendamento"]
                },
                {
                    "id": "atendente_humano",
                    "name": "Falar com Atendente",
                    "patterns": [
                        "atendente", "humano", "pessoa", "falar com alguém",
                        "quero falar", "transferir", "não é robô"
                    ],
                    "responses": [
                        "Claro! 🙋 Vou transferir você para um de nossos atendentes.\n\nPor favor, aguarde um momento enquanto localizo um especialista disponível..."
                    ],
                    "category": "geral",
                    "action": "transfer_to_human",
                    "tags": ["atendente", "humano", "transferir"]
                }
            ],
            "faq": [
                {
                    "question": "Como faço para trocar a senha do WiFi?",
                    "answer": "Para trocar a senha do WiFi:\n\n1️⃣ Acesse 192.168.1.1 no navegador\n2️⃣ Login: admin | Senha: admin (ou está na etiqueta do roteador)\n3️⃣ Vá em Wireless > Segurança\n4️⃣ Altere a senha e salve\n\nSe precisar de ajuda, é só chamar!",
                    "category": "suporte_tecnico"
                },
                {
                    "question": "Qual o prazo para instalação?",
                    "answer": "O prazo padrão é de até 5 dias úteis após a aprovação do cadastro. Em alguns bairros, conseguimos instalar em até 48 horas! 🚀",
                    "category": "comercial"
                },
                {
                    "question": "Vocês têm fidelidade?",
                    "answer": "Nossos planos SEM fidelidade têm um pequeno acréscimo. Planos com fidelidade de 12 meses têm os melhores preços! Qual prefere? 📋",
                    "category": "comercial"
                }
            ],
            "quick_replies": {
                "menu_principal": [
                    "💰 Segunda via de boleto",
                    "🔧 Suporte técnico",
                    "📦 Mudar de plano",
                    "🙋 Falar com atendente"
                ],
                "confirmar": ["✅ Sim", "❌ Não"],
                "periodo": ["🌅 Manhã", "🌇 Tarde"],
                "satisfacao": ["😊 Satisfeito", "😐 Neutro", "😞 Insatisfeito"]
            },
            "metadata": {
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "total_intents": 11,
                "total_faq": 3
            }
        }
        
        # Salvar base inicial
        self._save_knowledge(knowledge)
        return knowledge
    
    def _save_knowledge(self, knowledge: Optional[Dict] = None) -> bool:
        """Salvar base de conhecimento no arquivo"""
        try:
            data = knowledge or self.knowledge_base
            data["metadata"]["last_modified"] = datetime.now().isoformat()
            
            with open(self.knowledge_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar knowledge base: {e}")
            return False
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto para comparação"""
        # Remover acentos simplificado
        replacements = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'ü': 'u',
            'ç': 'c'
        }
        text = text.lower().strip()
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remover pontuação
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcular similaridade entre dois textos"""
        return difflib.SequenceMatcher(
            None, 
            self._normalize_text(text1), 
            self._normalize_text(text2)
        ).ratio()
    
    def _find_best_match(self, user_message: str) -> Tuple[Optional[Dict], float]:
        """Encontrar melhor match na base de conhecimento"""
        normalized_msg = self._normalize_text(user_message)
        best_match = None
        best_score = 0.0
        
        # Buscar nos intents
        for intent in self.knowledge_base.get("intents", []):
            for pattern in intent.get("patterns", []):
                # Match exato
                if self._normalize_text(pattern) in normalized_msg:
                    score = 0.95
                else:
                    score = self._calculate_similarity(user_message, pattern)
                
                if score > best_score:
                    best_score = score
                    best_match = intent
        
        # Buscar no FAQ se não encontrou bom match
        if best_score < self.similarity_threshold:
            for faq in self.knowledge_base.get("faq", []):
                score = self._calculate_similarity(user_message, faq["question"])
                if score > best_score:
                    best_score = score
                    best_match = {
                        "id": "faq",
                        "name": "FAQ",
                        "responses": [faq["answer"]],
                        "category": faq.get("category", "geral")
                    }
        
        return best_match, best_score
    
    def get_response(self, user_message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Obter resposta para mensagem do usuário
        
        Args:
            user_message: Mensagem do usuário
            context: Contexto da conversa (opcional)
            
        Returns:
            Dict com resposta, confiança, ação sugerida, etc.
        """
        self.stats["total_queries"] += 1
        
        # Buscar melhor match
        match, confidence = self._find_best_match(user_message)
        
        config = self.knowledge_base.get("config", {})
        company = config.get("company_name", self.company_name)
        
        if match and confidence >= self.similarity_threshold:
            self.stats["matched_queries"] += 1
            
            # Escolher resposta (pode ter várias)
            import random
            responses = match.get("responses", [config.get("fallback_message")])
            response_text = random.choice(responses).replace("{company}", company)
            
            return {
                "success": True,
                "response": response_text,
                "confidence": round(confidence, 2),
                "intent": match.get("id"),
                "intent_name": match.get("name"),
                "category": match.get("category", "geral"),
                "action": match.get("action"),
                "quick_replies": self._get_quick_replies(match),
                "requires_human": match.get("action") == "transfer_to_human"
            }
        else:
            # Não encontrou match - registrar para treinamento
            self.stats["unmatched_queries"].append({
                "message": user_message,
                "timestamp": datetime.now().isoformat(),
                "best_confidence": round(confidence, 2)
            })
            
            # Limitar lista de não-matches
            if len(self.stats["unmatched_queries"]) > 100:
                self.stats["unmatched_queries"] = self.stats["unmatched_queries"][-100:]
            
            return {
                "success": False,
                "response": config.get("fallback_message", "Desculpe, não entendi. Posso transferir para um atendente?").replace("{company}", company),
                "confidence": round(confidence, 2),
                "intent": None,
                "category": "unknown",
                "requires_human": True,
                "suggestions": self._get_suggestions(user_message),
                "quick_replies": self.knowledge_base.get("quick_replies", {}).get("menu_principal", [])
            }
    
    def _get_quick_replies(self, intent: Dict) -> List[str]:
        """Obter quick replies baseado no intent"""
        quick_replies = self.knowledge_base.get("quick_replies", {})
        
        # Quick replies específicos por ação
        if intent.get("action") == "transfer_to_human":
            return []
        
        if intent.get("id") in ["segunda_via", "internet_lenta", "sem_internet"]:
            return quick_replies.get("confirmar", [])
        
        if intent.get("id") == "visita_tecnica":
            return quick_replies.get("periodo", [])
        
        return quick_replies.get("menu_principal", [])
    
    def _get_suggestions(self, user_message: str) -> List[str]:
        """Obter sugestões de perguntas similares"""
        suggestions = []
        scores = []
        
        for intent in self.knowledge_base.get("intents", []):
            for pattern in intent.get("patterns", [])[:2]:
                score = self._calculate_similarity(user_message, pattern)
                if score > 0.3:
                    scores.append((pattern.capitalize(), score))
        
        # Ordenar por score e pegar top N
        scores.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scores[:self.max_suggestions]]
    
    # =========================================================================
    # MÉTODOS DE TREINAMENTO / ADMINISTRAÇÃO
    # =========================================================================
    
    def add_intent(
        self, 
        intent_id: str, 
        name: str, 
        patterns: List[str], 
        responses: List[str],
        category: str = "geral",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Adicionar novo intent à base de conhecimento"""
        new_intent = {
            "id": intent_id,
            "name": name,
            "patterns": patterns,
            "responses": responses,
            "category": category,
            "tags": tags or []
        }
        
        # Verificar se já existe
        for i, intent in enumerate(self.knowledge_base["intents"]):
            if intent["id"] == intent_id:
                self.knowledge_base["intents"][i] = new_intent
                self._save_knowledge()
                return {"success": True, "message": "Intent atualizado", "intent": new_intent}
        
        self.knowledge_base["intents"].append(new_intent)
        self.knowledge_base["metadata"]["total_intents"] = len(self.knowledge_base["intents"])
        self._save_knowledge()
        
        return {"success": True, "message": "Intent adicionado", "intent": new_intent}
    
    def add_pattern(self, intent_id: str, pattern: str) -> Dict[str, Any]:
        """Adicionar padrão a um intent existente"""
        for intent in self.knowledge_base["intents"]:
            if intent["id"] == intent_id:
                if pattern not in intent["patterns"]:
                    intent["patterns"].append(pattern)
                    self._save_knowledge()
                    return {"success": True, "message": f"Padrão '{pattern}' adicionado ao intent '{intent_id}'"}
                return {"success": False, "message": "Padrão já existe"}
        
        return {"success": False, "message": f"Intent '{intent_id}' não encontrado"}
    
    def add_response(self, intent_id: str, response: str) -> Dict[str, Any]:
        """Adicionar resposta a um intent existente"""
        for intent in self.knowledge_base["intents"]:
            if intent["id"] == intent_id:
                if response not in intent["responses"]:
                    intent["responses"].append(response)
                    self._save_knowledge()
                    return {"success": True, "message": f"Resposta adicionada ao intent '{intent_id}'"}
                return {"success": False, "message": "Resposta já existe"}
        
        return {"success": False, "message": f"Intent '{intent_id}' não encontrado"}
    
    def add_faq(self, question: str, answer: str, category: str = "geral") -> Dict[str, Any]:
        """Adicionar pergunta frequente"""
        new_faq = {
            "question": question,
            "answer": answer,
            "category": category
        }
        
        self.knowledge_base["faq"].append(new_faq)
        self.knowledge_base["metadata"]["total_faq"] = len(self.knowledge_base["faq"])
        self._save_knowledge()
        
        return {"success": True, "message": "FAQ adicionado", "faq": new_faq}
    
    def remove_intent(self, intent_id: str) -> Dict[str, Any]:
        """Remover intent da base"""
        for i, intent in enumerate(self.knowledge_base["intents"]):
            if intent["id"] == intent_id:
                removed = self.knowledge_base["intents"].pop(i)
                self.knowledge_base["metadata"]["total_intents"] = len(self.knowledge_base["intents"])
                self._save_knowledge()
                return {"success": True, "message": f"Intent '{intent_id}' removido", "removed": removed}
        
        return {"success": False, "message": f"Intent '{intent_id}' não encontrado"}
    
    def update_config(self, key: str, value: str) -> Dict[str, Any]:
        """Atualizar configuração do chatbot"""
        if key in self.knowledge_base["config"]:
            self.knowledge_base["config"][key] = value
            self._save_knowledge()
            return {"success": True, "message": f"Configuração '{key}' atualizada"}
        return {"success": False, "message": f"Configuração '{key}' não encontrada"}
    
    def get_all_intents(self) -> List[Dict]:
        """Obter todos os intents"""
        return self.knowledge_base.get("intents", [])
    
    def get_all_faq(self) -> List[Dict]:
        """Obter todas as FAQs"""
        return self.knowledge_base.get("faq", [])
    
    def get_config(self) -> Dict:
        """Obter configurações"""
        return self.knowledge_base.get("config", {})
    
    def get_stats(self) -> Dict:
        """Obter estatísticas de uso"""
        total = self.stats["total_queries"]
        matched = self.stats["matched_queries"]
        
        return {
            "total_queries": total,
            "matched_queries": matched,
            "match_rate": round(matched / total * 100, 1) if total > 0 else 0,
            "unmatched_count": len(self.stats["unmatched_queries"]),
            "recent_unmatched": self.stats["unmatched_queries"][-10:],
            "total_intents": len(self.knowledge_base.get("intents", [])),
            "total_faq": len(self.knowledge_base.get("faq", []))
        }
    
    def get_unmatched_queries(self) -> List[Dict]:
        """Obter perguntas não respondidas (para treinamento)"""
        return self.stats["unmatched_queries"]
    
    def export_knowledge(self) -> Dict:
        """Exportar base de conhecimento completa"""
        return self.knowledge_base
    
    def import_knowledge(self, data: Dict) -> Dict[str, Any]:
        """Importar base de conhecimento"""
        try:
            self.knowledge_base = data
            self._save_knowledge()
            return {"success": True, "message": "Base de conhecimento importada com sucesso"}
        except Exception as e:
            return {"success": False, "message": f"Erro ao importar: {str(e)}"}


# Instância global do chatbot
chatbot = TrainableChatbot()


def get_chatbot() -> TrainableChatbot:
    """Obter instância do chatbot"""
    return chatbot
