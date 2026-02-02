"""
Sistema de Chat WhatsApp com Fluxo de 3 Etapas
ESPERA → ATRIBUÍDO → AUTOMAÇÃO

SEMANA 1: Integração de criptografia
"""
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import structlog
from dataclasses import dataclass
import base64

# SEMANA 1 - Importar módulo de criptografia
try:
    from app.core.encryption import encryption_manager
    ENCRYPTION_ENABLED = True
except ImportError:
    ENCRYPTION_ENABLED = False

logger = structlog.get_logger(__name__)


class ConversationStatus(str, Enum):
    """Status das conversas no fluxo"""
    ESPERA = "waiting"        # Aguardando atribuição
    ATRIBUIDO = "assigned"    # Atribuído a um atendente
    AUTOMACAO = "automation"  # Em automação (bot)
    ENCERRADO = "closed"      # Conversa encerrada


class MessageType(str, Enum):
    """Tipos de mensagem"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"


class SenderType(str, Enum):
    """Tipos de remetente"""
    CUSTOMER = "customer"
    AGENT = "agent"
    BOT = "bot"
    SYSTEM = "system"


@dataclass
class WhatsAppMessage:
    """Estrutura de mensagem WhatsApp"""
    id: str
    conversation_id: str
    sender_type: SenderType
    sender_id: str
    content: str
    message_type: MessageType
    timestamp: datetime
    whatsapp_message_id: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class WhatsAppConversation:
    """Estrutura de conversa WhatsApp"""
    id: str
    customer_name: str
    customer_phone: str
    status: ConversationStatus
    assigned_agent_id: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    last_message: Optional[str] = None
    messages_count: int = 0
    priority: int = 0  # 0=normal, 1=alta, 2=urgente
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class WhatsAppChatFlow:
    """Gerenciador do fluxo de chat WhatsApp"""
    
    def __init__(self):
        self.conversations: Dict[str, WhatsAppConversation] = {}
        self.messages: Dict[str, List[WhatsAppMessage]] = {}
        self.agents: Dict[str, Dict] = {}
        self.automation_rules: List[Dict] = []
        self.stats = {
            "total_conversations": 0,
            "by_status": {status.value: 0 for status in ConversationStatus},
            "messages_today": 0,
            "avg_response_time": 0
        }
        
        # Configurar regras de automação padrão
        self._setup_automation_rules()
    
    def _setup_automation_rules(self):
        """Configurar regras de automação"""
        self.automation_rules = [
            {
                "trigger": "greeting",
                "keywords": ["oi", "olá", "bom dia", "boa tarde", "boa noite"],
                "response": "Olá! Bem-vindo ao atendimento da ISP. Como posso ajudá-lo hoje?",
                "next_action": "wait_for_response"
            },
            {
                "trigger": "internet_problem",
                "keywords": ["internet", "conexão", "lenta", "não funciona", "sem sinal"],
                "response": "Entendo que você está com problemas na internet. Vou verificar sua conexão. Qual seu endereço?",
                "next_action": "collect_address"
            },
            {
                "trigger": "billing",
                "keywords": ["fatura", "conta", "pagamento", "valor", "cobrança"],
                "response": "Vou ajudá-lo com questões de faturamento. Preciso do seu CPF para localizar sua conta.",
                "next_action": "collect_cpf"
            },
            {
                "trigger": "support",
                "keywords": ["suporte", "técnico", "ajuda", "problema"],
                "response": "Estou aqui para ajudar! Pode me descrever qual problema você está enfrentando?",
                "next_action": "collect_problem_details"
            }
        ]
    
    # Gerenciamento de Conversas
    async def create_conversation(
        self,
        customer_name: str,
        customer_phone: str,
        initial_message: str = None
    ) -> WhatsAppConversation:
        """Criar nova conversa (Status: ESPERA)"""
        conversation_id = f"conv_{len(self.conversations) + 1}_{int(datetime.now().timestamp())}"
        
        conversation = WhatsAppConversation(
            id=conversation_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            status=ConversationStatus.ESPERA,
            last_message=initial_message
        )
        
        self.conversations[conversation_id] = conversation
        self.messages[conversation_id] = []
        
        # Adicionar mensagem inicial se fornecida
        if initial_message:
            await self.add_message(
                conversation_id=conversation_id,
                sender_type=SenderType.CUSTOMER,
                sender_id=customer_phone,
                content=initial_message,
                message_type=MessageType.TEXT
            )
        
        # Atualizar estatísticas
        self.stats["total_conversations"] += 1
        self.stats["by_status"][ConversationStatus.ESPERA.value] += 1
        
        logger.info("Nova conversa criada", 
                   conversation_id=conversation_id,
                   customer=customer_name,
                   status=ConversationStatus.ESPERA.value)
        
        return conversation
    
    async def assign_conversation(
        self,
        conversation_id: str,
        agent_id: str
    ) -> bool:
        """Atribuir conversa a um agente (ESPERA → ATRIBUÍDO)"""
        if conversation_id not in self.conversations:
            return False
        
        conversation = self.conversations[conversation_id]
        
        if conversation.status != ConversationStatus.ESPERA:
            logger.warning("Tentativa de atribuir conversa em status inválido",
                         conversation_id=conversation_id,
                         current_status=conversation.status.value)
            return False
        
        # Atualizar status
        old_status = conversation.status
        conversation.status = ConversationStatus.ATRIBUIDO
        conversation.assigned_agent_id = agent_id
        conversation.updated_at = datetime.now()
        
        # Atualizar estatísticas
        self.stats["by_status"][old_status.value] -= 1
        self.stats["by_status"][ConversationStatus.ATRIBUIDO.value] += 1
        
        # Adicionar mensagem do sistema
        await self.add_message(
            conversation_id=conversation_id,
            sender_type=SenderType.SYSTEM,
            sender_id="system",
            content=f"Conversa atribuída ao agente {agent_id}",
            message_type=MessageType.TEXT
        )
        
        logger.info("Conversa atribuída",
                   conversation_id=conversation_id,
                   agent_id=agent_id,
                   status_change=f"{old_status.value} → {ConversationStatus.ATRIBUIDO.value}")
        
        return True
    
    async def start_automation(
        self,
        conversation_id: str
    ) -> bool:
        """Iniciar automação (ATRIBUÍDO → AUTOMAÇÃO)"""
        if conversation_id not in self.conversations:
            return False
        
        conversation = self.conversations[conversation_id]
        
        if conversation.status != ConversationStatus.ATRIBUIDO:
            logger.warning("Tentativa de automatizar conversa em status inválido",
                         conversation_id=conversation_id,
                         current_status=conversation.status.value)
            return False
        
        # Atualizar status
        old_status = conversation.status
        conversation.status = ConversationStatus.AUTOMACAO
        conversation.updated_at = datetime.now()
        
        # Atualizar estatísticas
        self.stats["by_status"][old_status.value] -= 1
        self.stats["by_status"][ConversationStatus.AUTOMACAO.value] += 1
        
        # Adicionar mensagem do sistema
        await self.add_message(
            conversation_id=conversation_id,
            sender_type=SenderType.SYSTEM,
            sender_id="system",
            content="Automação iniciada - Bot assumiu a conversa",
            message_type=MessageType.TEXT
        )
        
        # Enviar mensagem de boas-vindas do bot
        await self.send_bot_message(
            conversation_id,
            "Olá! Sou o assistente virtual da ISP. Como posso ajudá-lo hoje?"
        )
        
        logger.info("Automação iniciada",
                   conversation_id=conversation_id,
                   status_change=f"{old_status.value} → {ConversationStatus.AUTOMACAO.value}")
        
        return True
    
    async def takeover_conversation(
        self,
        conversation_id: str,
        agent_id: str
    ) -> bool:
        """Agente assume conversa da automação (AUTOMAÇÃO → ATRIBUÍDO)"""
        if conversation_id not in self.conversations:
            return False
        
        conversation = self.conversations[conversation_id]
        
        if conversation.status != ConversationStatus.AUTOMACAO:
            logger.warning("Tentativa de assumir conversa em status inválido",
                         conversation_id=conversation_id,
                         current_status=conversation.status.value)
            return False
        
        # Atualizar status
        old_status = conversation.status
        conversation.status = ConversationStatus.ATRIBUIDO
        conversation.assigned_agent_id = agent_id
        conversation.updated_at = datetime.now()
        
        # Atualizar estatísticas
        self.stats["by_status"][old_status.value] -= 1
        self.stats["by_status"][ConversationStatus.ATRIBUIDO.value] += 1
        
        # Adicionar mensagem do sistema
        await self.add_message(
            conversation_id=conversation_id,
            sender_type=SenderType.SYSTEM,
            sender_id="system",
            content=f"Agente {agent_id} assumiu a conversa",
            message_type=MessageType.TEXT
        )
        
        logger.info("Conversa assumida por agente",
                   conversation_id=conversation_id,
                   agent_id=agent_id,
                   status_change=f"{old_status.value} → {ConversationStatus.ATRIBUIDO.value}")
        
        return True
    
    async def close_conversation(
        self,
        conversation_id: str,
        reason: str = "Resolvido"
    ) -> bool:
        """Encerrar conversa (qualquer status → ENCERRADO)"""
        if conversation_id not in self.conversations:
            return False
        
        conversation = self.conversations[conversation_id]
        old_status = conversation.status
        
        # Atualizar status
        conversation.status = ConversationStatus.ENCERRADO
        conversation.updated_at = datetime.now()
        conversation.metadata["closed_reason"] = reason
        conversation.metadata["closed_at"] = datetime.now().isoformat()
        
        # Atualizar estatísticas
        self.stats["by_status"][old_status.value] -= 1
        self.stats["by_status"][ConversationStatus.ENCERRADO.value] += 1
        
        # Adicionar mensagem do sistema
        await self.add_message(
            conversation_id=conversation_id,
            sender_type=SenderType.SYSTEM,
            sender_id="system",
            content=f"Conversa encerrada: {reason}",
            message_type=MessageType.TEXT
        )
        
        logger.info("Conversa encerrada",
                   conversation_id=conversation_id,
                   reason=reason,
                   status_change=f"{old_status.value} → {ConversationStatus.ENCERRADO.value}")
        
        return True
    
    # Gerenciamento de Mensagens
    async def add_message(
        self,
        conversation_id: str,
        sender_type: SenderType,
        sender_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        whatsapp_message_id: str = None
    ) -> WhatsAppMessage:
        """Adicionar mensagem à conversa"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversa {conversation_id} não encontrada")
        
        message_id = f"msg_{len(self.messages.get(conversation_id, []))}_{int(datetime.now().timestamp())}"
        
        message = WhatsAppMessage(
            id=message_id,
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            whatsapp_message_id=whatsapp_message_id
        )
        
        # Adicionar à lista de mensagens
        if conversation_id not in self.messages:
            self.messages[conversation_id] = []
        
        self.messages[conversation_id].append(message)
        
        # Atualizar conversa
        conversation = self.conversations[conversation_id]
        conversation.last_message = content[:100] + "..." if len(content) > 100 else content
        conversation.messages_count += 1
        conversation.updated_at = datetime.now()
        
        # Atualizar estatísticas
        self.stats["messages_today"] += 1
        
        # Processar automação se necessário
        if (sender_type == SenderType.CUSTOMER and 
            conversation.status == ConversationStatus.AUTOMACAO):
            await self.process_automation(conversation_id, content)
        
        logger.debug("Mensagem adicionada",
                    conversation_id=conversation_id,
                    sender_type=sender_type.value,
                    message_type=message_type.value)
        
        return message
    
    async def send_bot_message(
        self,
        conversation_id: str,
        content: str
    ) -> WhatsAppMessage:
        """Enviar mensagem do bot"""
        return await self.add_message(
            conversation_id=conversation_id,
            sender_type=SenderType.BOT,
            sender_id="bot",
            content=content,
            message_type=MessageType.TEXT
        )
    
    # ========================================================================
    # SEMANA 1 - CRIPTOGRAFIA DE MENSAGENS
    # ========================================================================
    
    async def encrypt_message_content(
        self,
        customer_id: str,
        content: str
    ) -> Tuple[str, str]:
        """
        Criptografar conteúdo de mensagem
        
        Returns:
            (conteudo_criptografado_base64, iv_base64)
        """
        if not ENCRYPTION_ENABLED:
            logger.warning("Encryption module not available")
            return content, ""
        
        try:
            # Derivar chave para o cliente
            client_key = await encryption_manager.derive_client_key(customer_id)
            
            # Criptografar conteúdo
            encrypted_data, iv = encryption_manager.encrypt(
                plaintext=content,
                client_key=client_key
            )
            
            # Converter para base64
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            iv_b64 = base64.b64encode(iv).decode('utf-8')
            
            logger.debug("Message encrypted successfully", customer_id=customer_id)
            
            return encrypted_b64, iv_b64
            
        except Exception as e:
            logger.error("Failed to encrypt message", error=str(e), customer_id=customer_id)
            # Retornar plaintext em caso de erro
            return content, ""
    
    async def decrypt_message_content(
        self,
        customer_id: str,
        encrypted_content: str,
        iv: str
    ) -> str:
        """
        Descriptografar conteúdo de mensagem
        
        Args:
            customer_id: ID do cliente para derivar chave
            encrypted_content: Base64 do conteúdo criptografado
            iv: Base64 do initialization vector
        
        Returns:
            Conteúdo plaintext descriptografado
        """
        if not ENCRYPTION_ENABLED or not iv:
            logger.warning("Encryption not available or missing IV")
            return encrypted_content
        
        try:
            # Derivar chave para o cliente
            client_key = await encryption_manager.derive_client_key(customer_id)
            
            # Decodificar de base64
            encrypted_data = base64.b64decode(encrypted_content)
            iv_bytes = base64.b64decode(iv)
            
            # Descriptografar
            plaintext = encryption_manager.decrypt(
                ciphertext=encrypted_data,
                iv=iv_bytes,
                client_key=client_key
            )
            
            logger.debug("Message decrypted successfully", customer_id=customer_id)
            
            return plaintext
            
        except Exception as e:
            logger.error("Failed to decrypt message", error=str(e), customer_id=customer_id)
            # Retornar encrypted content em caso de erro
            return encrypted_content
    
    async def get_conversation_messages_decrypted(
        self,
        conversation_id: str,
        customer_id: str
    ) -> List[Dict]:
        """
        Obter todas as mensagens de uma conversa com conteúdo descriptografado
        """
        if conversation_id not in self.messages:
            return []
        
        messages = self.messages[conversation_id]
        decrypted_messages = []
        
        for msg in messages:
            msg_dict = {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_type": msg.sender_type.value,
                "sender_id": msg.sender_id,
                "content": msg.content,  # Conteúdo descriptografado
                "message_type": msg.message_type.value,
                "timestamp": msg.timestamp.isoformat(),
                "whatsapp_message_id": msg.whatsapp_message_id
            }
            
            # Se temos metadados de criptografia, descriptografar
            if msg.metadata and "encrypted" in msg.metadata:
                try:
                    decrypted = await self.decrypt_message_content(
                        customer_id=customer_id,
                        encrypted_content=msg.metadata.get("conteudo_criptografado"),
                        iv=msg.metadata.get("iv")
                    )
                    msg_dict["content"] = decrypted
                except Exception as e:
                    logger.warning(f"Could not decrypt message {msg.id}: {str(e)}")
            
            decrypted_messages.append(msg_dict)
        
        return decrypted_messages
    
    async def add_encrypted_message(
        self,
        conversation_id: str,
        sender_type: SenderType,
        sender_id: str,
        content: str,
        customer_id: str,
        message_type: MessageType = MessageType.TEXT,
        whatsapp_message_id: str = None
    ) -> WhatsAppMessage:
        """
        Adicionar mensagem com conteúdo criptografado
        
        SEMANA 1: Integração com encryption_manager
        """
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversa {conversation_id} não encontrada")
        
        # Criptografar conteúdo
        encrypted_content, iv = await self.encrypt_message_content(
            customer_id=customer_id,
            content=content
        )
        
        # Criar mensagem com metadados de criptografia
        message_id = f"msg_{len(self.messages.get(conversation_id, []))}_{int(datetime.now().timestamp())}"
        
        message = WhatsAppMessage(
            id=message_id,
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,  # Armazenar plaintext em memória
            message_type=message_type,
            timestamp=datetime.now(),
            whatsapp_message_id=whatsapp_message_id,
            metadata={
                "encrypted": True,
                "conteudo_criptografado": encrypted_content,
                "iv": iv,
                "encryption_type": "AES-256-CBC"
            }
        )
        
        # Adicionar à lista
        if conversation_id not in self.messages:
            self.messages[conversation_id] = []
        
        self.messages[conversation_id].append(message)
        
        # Atualizar conversa
        conversation = self.conversations[conversation_id]
        conversation.last_message = "[Encrypted message]"  # Não mostrar preview
        conversation.messages_count += 1
        conversation.updated_at = datetime.now()
        
        self.stats["messages_today"] += 1
        
        logger.info(
            "Encrypted message added",
            conversation_id=conversation_id,
            sender_type=sender_type.value,
            encryption_enabled=True
        )
        
        return message
    
    async def enable_conversation_encryption(
        self,
        conversation_id: str,
        customer_id: str
    ) -> bool:
        """
        Ativar criptografia para conversa
        
        Configura metadados de criptografia para todas as futuras mensagens
        """
        if conversation_id not in self.conversations:
            return False
        
        conversation = self.conversations[conversation_id]
        conversation.metadata["encryption_enabled"] = True
        conversation.metadata["customer_id"] = customer_id
        conversation.metadata["encryption_started_at"] = datetime.now().isoformat()
        
        logger.info(
            "Conversation encryption enabled",
            conversation_id=conversation_id,
            customer_id=customer_id
        )
        
        return True
    
    
            conversation_id=conversation_id,
            sender_type=SenderType.BOT,
            sender_id="bot",
            content=content,
            message_type=MessageType.TEXT
        )
    
    # Sistema de Automação
    async def process_automation(
        self,
        conversation_id: str,
        customer_message: str
    ):
        """Processar mensagem do cliente na automação"""
        message_lower = customer_message.lower()
        
        # Verificar regras de automação
        for rule in self.automation_rules:
            if any(keyword in message_lower for keyword in rule["keywords"]):
                # Enviar resposta automática
                await self.send_bot_message(conversation_id, rule["response"])
                
                # Executar próxima ação se definida
                if rule.get("next_action"):
                    await self.execute_automation_action(
                        conversation_id, 
                        rule["next_action"]
                    )
                
                logger.info("Regra de automação ativada",
                           conversation_id=conversation_id,
                           trigger=rule["trigger"])
                return
        
        # Se não encontrou regra específica, resposta genérica
        await self.send_bot_message(
            conversation_id,
            "Entendi. Um de nossos atendentes irá ajudá-lo em breve. "
            "Enquanto isso, você pode me contar mais detalhes sobre sua solicitação."
        )
    
    async def execute_automation_action(
        self,
        conversation_id: str,
        action: str
    ):
        """Executar ação de automação"""
        actions = {
            "wait_for_response": self._wait_for_response,
            "collect_address": self._collect_address,
            "collect_cpf": self._collect_cpf,
            "collect_problem_details": self._collect_problem_details
        }
        
        if action in actions:
            await actions[action](conversation_id)
    
    async def _wait_for_response(self, conversation_id: str):
        """Aguardar resposta do cliente"""
        # Implementar lógica de espera
        pass
    
    async def _collect_address(self, conversation_id: str):
        """Coletar endereço do cliente"""
        await asyncio.sleep(1)  # Simular delay
        await self.send_bot_message(
            conversation_id,
            "Por favor, me informe seu endereço completo para que eu possa verificar sua conexão."
        )
    
    async def _collect_cpf(self, conversation_id: str):
        """Coletar CPF do cliente"""
        await asyncio.sleep(1)
        await self.send_bot_message(
            conversation_id,
            "Por favor, me informe seu CPF (apenas números) para localizar sua conta."
        )
    
    async def _collect_problem_details(self, conversation_id: str):
        """Coletar detalhes do problema"""
        await asyncio.sleep(1)
        await self.send_bot_message(
            conversation_id,
            "Pode me descrever em detalhes o problema que você está enfrentando? "
            "Isso me ajudará a encontrar a melhor solução."
        )
    
    # Consultas e Relatórios
    def get_conversations_by_status(self, status: ConversationStatus) -> List[WhatsAppConversation]:
        """Obter conversas por status"""
        return [conv for conv in self.conversations.values() if conv.status == status]
    
    def get_conversation(self, conversation_id: str) -> Optional[WhatsAppConversation]:
        """Obter conversa específica"""
        return self.conversations.get(conversation_id)
    
    def get_messages(self, conversation_id: str) -> List[WhatsAppMessage]:
        """Obter mensagens de uma conversa"""
        return self.messages.get(conversation_id, [])
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do sistema"""
        return {
            **self.stats,
            "active_conversations": len([
                c for c in self.conversations.values() 
                if c.status != ConversationStatus.ENCERRADO
            ]),
            "agents_online": len(self.agents),
            "automation_rules": len(self.automation_rules)
        }
    
    def get_agent_workload(self, agent_id: str) -> Dict[str, Any]:
        """Obter carga de trabalho do agente"""
        assigned_conversations = [
            c for c in self.conversations.values()
            if c.assigned_agent_id == agent_id and c.status == ConversationStatus.ATRIBUIDO
        ]
        
        return {
            "agent_id": agent_id,
            "assigned_conversations": len(assigned_conversations),
            "conversations": [c.id for c in assigned_conversations]
        }


# Instância global
whatsapp_chat_flow = WhatsAppChatFlow()