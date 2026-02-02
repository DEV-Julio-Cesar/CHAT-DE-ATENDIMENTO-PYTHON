"""
WebSocket Enterprise - Chat em Tempo Real
Sistema de comunicação bidirecional para atendimento

Features:
- Chat em tempo real entre clientes e atendentes
- Notificações instantâneas de novas mensagens
- Indicador de "digitando..."
- Gerenciamento de salas por conversa
- Broadcast de eventos do sistema
- Heartbeat para manter conexões ativas
- Reconexão automática
- Integração com Chatbot AI
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field, asdict
import json
import asyncio
import uuid
import structlog

from app.core.config import settings
from app.core.redis_client import redis_manager
from app.services.chatbot_ai import chatbot_ai, ChatResponse

logger = structlog.get_logger(__name__)

websocket_router = APIRouter()


# =============================================================================
# ENUMS E TIPOS
# =============================================================================

class EventType(str, Enum):
    """Tipos de eventos WebSocket"""
    # Conexão
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    
    # Mensagens
    MESSAGE = "message"
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_READ = "message_read"
    
    # Status
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    ONLINE_STATUS = "online_status"
    
    # Atendimento
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_ASSIGNED = "conversation_assigned"
    CONVERSATION_TRANSFERRED = "conversation_transferred"
    CONVERSATION_CLOSED = "conversation_closed"
    
    # Fila
    QUEUE_UPDATE = "queue_update"
    QUEUE_POSITION = "queue_position"
    
    # Sistema
    NOTIFICATION = "notification"
    SYSTEM_MESSAGE = "system_message"
    BOT_RESPONSE = "bot_response"


class UserRole(str, Enum):
    """Roles de usuário no WebSocket"""
    CLIENTE = "cliente"
    ATENDENTE = "atendente"
    SUPERVISOR = "supervisor"
    SYSTEM = "system"


class ConnectionStatus(str, Enum):
    """Status de conexão"""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class WebSocketMessage:
    """Mensagem WebSocket padronizada"""
    event: EventType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_json(self) -> str:
        return json.dumps({
            "event": self.event.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        })
    
    @classmethod
    def from_json(cls, data: str) -> "WebSocketMessage":
        parsed = json.loads(data)
        return cls(
            event=EventType(parsed.get("event", "message")),
            data=parsed.get("data", {}),
            timestamp=parsed.get("timestamp", datetime.now(timezone.utc).isoformat()),
            message_id=parsed.get("message_id", str(uuid.uuid4()))
        )


@dataclass
class ConnectedUser:
    """Usuário conectado"""
    user_id: str
    role: UserRole
    websocket: WebSocket
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ConnectionStatus = ConnectionStatus.ONLINE
    current_conversation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "connection_id": self.connection_id,
            "connected_at": self.connected_at.isoformat(),
            "status": self.status.value,
            "current_conversation": self.current_conversation,
            "metadata": self.metadata
        }


# =============================================================================
# CONNECTION MANAGER
# =============================================================================

class ConnectionManager:
    """
    Gerenciador de conexões WebSocket
    
    Mantém registro de todas as conexões ativas,
    organiza por salas (conversas) e permite
    broadcast de mensagens.
    """
    
    def __init__(self):
        # Conexões ativas por ID de usuário
        self.active_connections: Dict[str, ConnectedUser] = {}
        
        # Conexões por connection_id
        self.connections_by_id: Dict[str, ConnectedUser] = {}
        
        # Salas (conversas) com seus participantes
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of user_ids
        
        # Atendentes disponíveis
        self.available_agents: Set[str] = set()
        
        # Fila de espera
        self.waiting_queue: List[str] = []  # Lista de conversation_ids aguardando
        
        # Lock para operações thread-safe
        self._lock = asyncio.Lock()
        
        # Métricas
        self.metrics = {
            "total_connections": 0,
            "total_messages": 0,
            "current_connections": 0,
            "peak_connections": 0
        }
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        role: UserRole,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectedUser:
        """Aceitar nova conexão WebSocket"""
        await websocket.accept()
        
        async with self._lock:
            # Criar usuário conectado
            user = ConnectedUser(
                user_id=user_id,
                role=role,
                websocket=websocket,
                metadata=metadata or {}
            )
            
            # Registrar conexão
            self.active_connections[user_id] = user
            self.connections_by_id[user.connection_id] = user
            
            # Atualizar métricas
            self.metrics["total_connections"] += 1
            self.metrics["current_connections"] = len(self.active_connections)
            if self.metrics["current_connections"] > self.metrics["peak_connections"]:
                self.metrics["peak_connections"] = self.metrics["current_connections"]
            
            # Se for atendente, adicionar aos disponíveis
            if role in [UserRole.ATENDENTE, UserRole.SUPERVISOR]:
                self.available_agents.add(user_id)
            
            logger.info(
                "WebSocket connected",
                user_id=user_id,
                role=role.value,
                connection_id=user.connection_id
            )
            
            # Publicar no Redis para outros servidores
            await self._publish_presence(user_id, "online")
            
            return user
    
    async def disconnect(self, user_id: str):
        """Desconectar usuário"""
        async with self._lock:
            if user_id not in self.active_connections:
                return
            
            user = self.active_connections[user_id]
            
            # Remover de todas as salas
            for room_id in list(self.rooms.keys()):
                if user_id in self.rooms[room_id]:
                    self.rooms[room_id].discard(user_id)
                    # Notificar outros na sala
                    await self.broadcast_to_room(
                        room_id,
                        WebSocketMessage(
                            event=EventType.DISCONNECTED,
                            data={"user_id": user_id}
                        ),
                        exclude={user_id}
                    )
            
            # Remover das conexões
            del self.active_connections[user_id]
            if user.connection_id in self.connections_by_id:
                del self.connections_by_id[user.connection_id]
            
            # Remover de atendentes disponíveis
            self.available_agents.discard(user_id)
            
            # Atualizar métricas
            self.metrics["current_connections"] = len(self.active_connections)
            
            logger.info(
                "WebSocket disconnected",
                user_id=user_id,
                connection_id=user.connection_id
            )
            
            # Publicar no Redis
            await self._publish_presence(user_id, "offline")
    
    async def join_room(self, user_id: str, room_id: str):
        """Adicionar usuário a uma sala"""
        async with self._lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = set()
            
            self.rooms[room_id].add(user_id)
            
            # Atualizar conversa atual do usuário
            if user_id in self.active_connections:
                self.active_connections[user_id].current_conversation = room_id
            
            logger.info("User joined room", user_id=user_id, room_id=room_id)
            
            # Notificar outros na sala
            await self.broadcast_to_room(
                room_id,
                WebSocketMessage(
                    event=EventType.CONVERSATION_ASSIGNED,
                    data={"user_id": user_id, "room_id": room_id}
                ),
                exclude={user_id}
            )
    
    async def leave_room(self, user_id: str, room_id: str):
        """Remover usuário de uma sala"""
        async with self._lock:
            if room_id in self.rooms:
                self.rooms[room_id].discard(user_id)
                
                # Limpar sala vazia
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
            
            # Atualizar conversa atual
            if user_id in self.active_connections:
                if self.active_connections[user_id].current_conversation == room_id:
                    self.active_connections[user_id].current_conversation = None
            
            logger.info("User left room", user_id=user_id, room_id=room_id)
    
    async def send_personal(self, user_id: str, message: WebSocketMessage):
        """Enviar mensagem para um usuário específico"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].websocket.send_text(message.to_json())
                self.metrics["total_messages"] += 1
                return True
            except Exception as e:
                logger.error("Error sending personal message", user_id=user_id, error=str(e))
                await self.disconnect(user_id)
        return False
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude: Optional[Set[str]] = None
    ):
        """Enviar mensagem para todos em uma sala"""
        if room_id not in self.rooms:
            return
        
        exclude = exclude or set()
        tasks = []
        
        for user_id in self.rooms[room_id]:
            if user_id not in exclude and user_id in self.active_connections:
                tasks.append(self.send_personal(user_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_role(self, role: UserRole, message: WebSocketMessage):
        """Enviar mensagem para todos de um role"""
        tasks = []
        
        for user_id, user in self.active_connections.items():
            if user.role == role:
                tasks.append(self.send_personal(user_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_all(self, message: WebSocketMessage, exclude: Optional[Set[str]] = None):
        """Enviar mensagem para todos conectados"""
        exclude = exclude or set()
        tasks = []
        
        for user_id in self.active_connections:
            if user_id not in exclude:
                tasks.append(self.send_personal(user_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_user(self, user_id: str) -> Optional[ConnectedUser]:
        """Obter usuário conectado"""
        return self.active_connections.get(user_id)
    
    def get_room_members(self, room_id: str) -> List[str]:
        """Obter membros de uma sala"""
        return list(self.rooms.get(room_id, set()))
    
    def get_available_agent(self) -> Optional[str]:
        """Obter próximo atendente disponível"""
        for agent_id in self.available_agents:
            agent = self.active_connections.get(agent_id)
            if agent and agent.status == ConnectionStatus.ONLINE:
                return agent_id
        return None
    
    async def add_to_queue(self, conversation_id: str):
        """Adicionar conversa à fila de espera"""
        if conversation_id not in self.waiting_queue:
            self.waiting_queue.append(conversation_id)
            
            # Notificar atendentes sobre nova fila
            await self.broadcast_to_role(
                UserRole.ATENDENTE,
                WebSocketMessage(
                    event=EventType.QUEUE_UPDATE,
                    data={
                        "queue_size": len(self.waiting_queue),
                        "new_conversation": conversation_id
                    }
                )
            )
    
    async def remove_from_queue(self, conversation_id: str):
        """Remover conversa da fila"""
        if conversation_id in self.waiting_queue:
            self.waiting_queue.remove(conversation_id)
    
    def get_queue_position(self, conversation_id: str) -> int:
        """Obter posição na fila"""
        try:
            return self.waiting_queue.index(conversation_id) + 1
        except ValueError:
            return 0
    
    async def _publish_presence(self, user_id: str, status: str):
        """Publicar presença no Redis para outros servidores"""
        try:
            await redis_manager.publish(
                "presence",
                json.dumps({
                    "user_id": user_id,
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            )
        except Exception as e:
            logger.warning("Failed to publish presence", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do gerenciador"""
        return {
            **self.metrics,
            "active_rooms": len(self.rooms),
            "available_agents": len(self.available_agents),
            "queue_size": len(self.waiting_queue),
            "connections_by_role": {
                role.value: sum(1 for u in self.active_connections.values() if u.role == role)
                for role in UserRole
            }
        }


# Instância global
manager = ConnectionManager()


# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

@websocket_router.websocket("/ws/chat/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: str,
    role: str = Query(default="cliente"),
    token: Optional[str] = Query(default=None)
):
    """
    Endpoint principal de WebSocket para chat
    
    Parâmetros:
        user_id: ID único do usuário
        role: Role do usuário (cliente, atendente, supervisor)
        token: Token JWT para autenticação (opcional)
    
    Eventos suportados:
        - message: Enviar mensagem
        - typing_start/typing_stop: Indicador de digitação
        - join_room: Entrar em uma conversa
        - leave_room: Sair de uma conversa
        - heartbeat: Manter conexão ativa
    """
    # Validar role
    try:
        user_role = UserRole(role)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid role")
        return
    
    # TODO: Validar token JWT aqui se necessário
    # if token:
    #     try:
    #         payload = verify_token(token)
    #     except:
    #         await websocket.close(code=4002, reason="Invalid token")
    #         return
    
    # Conectar usuário
    user = await manager.connect(websocket, user_id, user_role)
    
    # Enviar confirmação de conexão
    await manager.send_personal(
        user_id,
        WebSocketMessage(
            event=EventType.CONNECTED,
            data={
                "connection_id": user.connection_id,
                "user_id": user_id,
                "role": user_role.value,
                "server_time": datetime.now(timezone.utc).isoformat()
            }
        )
    )
    
    try:
        # Loop principal de mensagens
        while True:
            # Receber mensagem
            data = await websocket.receive_text()
            
            try:
                message = WebSocketMessage.from_json(data)
            except (json.JSONDecodeError, ValueError) as e:
                await manager.send_personal(
                    user_id,
                    WebSocketMessage(
                        event=EventType.ERROR,
                        data={"error": "Invalid message format", "details": str(e)}
                    )
                )
                continue
            
            # Processar eventos
            await handle_websocket_event(user, message)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", user_id=user_id)
    except Exception as e:
        logger.error("WebSocket error", user_id=user_id, error=str(e))
    finally:
        await manager.disconnect(user_id)


async def handle_websocket_event(user: ConnectedUser, message: WebSocketMessage):
    """Processar evento WebSocket recebido"""
    event = message.event
    data = message.data
    
    try:
        if event == EventType.MESSAGE:
            await handle_message(user, data)
        
        elif event == EventType.TYPING_START:
            await handle_typing(user, data, is_typing=True)
        
        elif event == EventType.TYPING_STOP:
            await handle_typing(user, data, is_typing=False)
        
        elif event == EventType.HEARTBEAT:
            await handle_heartbeat(user)
        
        elif event == EventType.MESSAGE_READ:
            await handle_message_read(user, data)
        
        elif event.value.startswith("join_room"):
            room_id = data.get("room_id")
            if room_id:
                await manager.join_room(user.user_id, room_id)
        
        elif event.value.startswith("leave_room"):
            room_id = data.get("room_id")
            if room_id:
                await manager.leave_room(user.user_id, room_id)
        
        else:
            logger.warning("Unknown event type", event=event.value, user_id=user.user_id)
    
    except Exception as e:
        logger.error("Error handling event", event=event.value, error=str(e))
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.ERROR,
                data={"error": "Failed to process event", "event": event.value}
            )
        )


async def handle_message(user: ConnectedUser, data: Dict[str, Any]):
    """Processar mensagem de chat"""
    room_id = data.get("room_id") or user.current_conversation
    content = data.get("content", "")
    message_type = data.get("type", "text")
    
    if not room_id:
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.ERROR,
                data={"error": "No room specified"}
            )
        )
        return
    
    # Criar mensagem
    chat_message = {
        "id": str(uuid.uuid4()),
        "room_id": room_id,
        "sender_id": user.user_id,
        "sender_role": user.role.value,
        "content": content,
        "type": message_type,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Confirmar envio para o remetente
    await manager.send_personal(
        user.user_id,
        WebSocketMessage(
            event=EventType.MESSAGE_SENT,
            data={"message_id": chat_message["id"], "status": "sent"}
        )
    )
    
    # Se for cliente e não houver atendente na sala, usar chatbot
    room_members = manager.get_room_members(room_id)
    has_agent = any(
        manager.get_user(m) and manager.get_user(m).role in [UserRole.ATENDENTE, UserRole.SUPERVISOR]
        for m in room_members if m != user.user_id
    )
    
    if user.role == UserRole.CLIENTE and not has_agent:
        # Processar com chatbot
        await process_with_chatbot(user, room_id, content, chat_message)
    else:
        # Broadcast para a sala
        await manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event=EventType.MESSAGE,
                data=chat_message
            ),
            exclude={user.user_id}
        )
    
    # TODO: Salvar mensagem no banco de dados
    # await save_message_to_db(chat_message)
    
    logger.info(
        "Message sent",
        room_id=room_id,
        sender=user.user_id,
        has_agent=has_agent
    )


async def process_with_chatbot(
    user: ConnectedUser,
    room_id: str,
    content: str,
    original_message: Dict[str, Any]
):
    """Processar mensagem com chatbot AI"""
    try:
        # Broadcast da mensagem original
        await manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event=EventType.MESSAGE,
                data=original_message
            ),
            exclude={user.user_id}
        )
        
        # Indicador de digitação do bot
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.TYPING_START,
                data={"user_id": "bot", "room_id": room_id}
            )
        )
        
        # Gerar resposta do chatbot
        cliente_info = {
            "id": user.user_id,
            "nome": user.metadata.get("nome"),
            "telefone": user.metadata.get("telefone"),
            "plano": user.metadata.get("plano")
        }
        
        response: ChatResponse = await chatbot_ai.generate_response(
            conversation_id=room_id,
            user_message=content,
            cliente_info=cliente_info
        )
        
        # Parar indicador de digitação
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.TYPING_STOP,
                data={"user_id": "bot", "room_id": room_id}
            )
        )
        
        # Criar mensagem do bot
        bot_message = {
            "id": str(uuid.uuid4()),
            "room_id": room_id,
            "sender_id": "bot",
            "sender_role": "bot",
            "content": response.message,
            "type": "text",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "intent": response.intent.value,
                "sentiment": response.sentiment.value,
                "confidence": response.confidence,
                "quick_replies": response.quick_replies
            }
        }
        
        # Enviar resposta do bot
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.BOT_RESPONSE,
                data=bot_message
            )
        )
        
        # Se precisa escalar, notificar atendentes
        if response.should_escalate:
            await handle_escalation(user, room_id, response)
        
    except Exception as e:
        logger.error("Error processing with chatbot", error=str(e))
        
        # Mensagem de erro para o usuário
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.BOT_RESPONSE,
                data={
                    "id": str(uuid.uuid4()),
                    "room_id": room_id,
                    "sender_id": "bot",
                    "sender_role": "bot",
                    "content": "Desculpe, tive um problema técnico. Vou transferir você para um atendente.",
                    "type": "text",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        )
        
        # Escalar automaticamente em caso de erro
        await manager.add_to_queue(room_id)


async def handle_escalation(user: ConnectedUser, room_id: str, response: ChatResponse):
    """Processar escalação para atendente humano"""
    # Notificar usuário
    await manager.send_personal(
        user.user_id,
        WebSocketMessage(
            event=EventType.SYSTEM_MESSAGE,
            data={
                "message": "Estamos transferindo você para um atendente. Por favor, aguarde.",
                "type": "escalation"
            }
        )
    )
    
    # Tentar atribuir a um atendente disponível
    agent_id = manager.get_available_agent()
    
    if agent_id:
        # Atribuir ao atendente
        await manager.join_room(agent_id, room_id)
        
        # Notificar atendente
        await manager.send_personal(
            agent_id,
            WebSocketMessage(
                event=EventType.CONVERSATION_ASSIGNED,
                data={
                    "room_id": room_id,
                    "client_id": user.user_id,
                    "client_name": user.metadata.get("nome", "Cliente"),
                    "escalation_reason": response.escalation_reason,
                    "intent": response.intent.value,
                    "sentiment": response.sentiment.value,
                    "suggested_actions": response.suggested_actions
                }
            )
        )
        
        # Notificar cliente
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.CONVERSATION_ASSIGNED,
                data={
                    "message": "Você foi conectado a um atendente.",
                    "agent_id": agent_id
                }
            )
        )
        
        logger.info(
            "Conversation assigned to agent",
            room_id=room_id,
            agent_id=agent_id,
            reason=response.escalation_reason
        )
    else:
        # Adicionar à fila
        await manager.add_to_queue(room_id)
        position = manager.get_queue_position(room_id)
        
        await manager.send_personal(
            user.user_id,
            WebSocketMessage(
                event=EventType.QUEUE_POSITION,
                data={
                    "position": position,
                    "estimated_wait": f"{position * 2}-{position * 5} minutos"
                }
            )
        )
        
        logger.info(
            "Conversation added to queue",
            room_id=room_id,
            position=position
        )


async def handle_typing(user: ConnectedUser, data: Dict[str, Any], is_typing: bool):
    """Processar indicador de digitação"""
    room_id = data.get("room_id") or user.current_conversation
    
    if not room_id:
        return
    
    event = EventType.TYPING_START if is_typing else EventType.TYPING_STOP
    
    await manager.broadcast_to_room(
        room_id,
        WebSocketMessage(
            event=event,
            data={"user_id": user.user_id, "room_id": room_id}
        ),
        exclude={user.user_id}
    )


async def handle_heartbeat(user: ConnectedUser):
    """Processar heartbeat"""
    await manager.send_personal(
        user.user_id,
        WebSocketMessage(
            event=EventType.HEARTBEAT,
            data={
                "status": "alive",
                "server_time": datetime.now(timezone.utc).isoformat()
            }
        )
    )


async def handle_message_read(user: ConnectedUser, data: Dict[str, Any]):
    """Processar confirmação de leitura"""
    room_id = data.get("room_id")
    message_ids = data.get("message_ids", [])
    
    if not room_id or not message_ids:
        return
    
    await manager.broadcast_to_room(
        room_id,
        WebSocketMessage(
            event=EventType.MESSAGE_READ,
            data={
                "reader_id": user.user_id,
                "message_ids": message_ids,
                "read_at": datetime.now(timezone.utc).isoformat()
            }
        ),
        exclude={user.user_id}
    )


# =============================================================================
# HTTP ENDPOINTS
# =============================================================================

@websocket_router.get("/ws/status")
async def websocket_status():
    """Status do servidor WebSocket"""
    return {
        "status": "ready",
        "stats": manager.get_stats(),
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@websocket_router.get("/ws/rooms")
async def list_rooms():
    """Listar salas ativas"""
    rooms = []
    for room_id, members in manager.rooms.items():
        rooms.append({
            "room_id": room_id,
            "member_count": len(members),
            "members": [
                {
                    "user_id": m,
                    "role": manager.get_user(m).role.value if manager.get_user(m) else "unknown"
                }
                for m in members
            ]
        })
    return {"rooms": rooms}


@websocket_router.get("/ws/queue")
async def get_queue():
    """Obter fila de espera"""
    return {
        "queue": manager.waiting_queue,
        "size": len(manager.waiting_queue)
    }


@websocket_router.get("/ws/agents")
async def list_agents():
    """Listar atendentes disponíveis"""
    agents = []
    for agent_id in manager.available_agents:
        user = manager.get_user(agent_id)
        if user:
            agents.append({
                "user_id": agent_id,
                "status": user.status.value,
                "current_conversation": user.current_conversation
            })
    return {"agents": agents, "available": len(agents)}


@websocket_router.post("/ws/broadcast")
async def broadcast_message(
    message: str,
    room_id: Optional[str] = None,
    role: Optional[str] = None
):
    """
    Enviar mensagem broadcast via HTTP
    
    Útil para notificações do sistema.
    """
    ws_message = WebSocketMessage(
        event=EventType.SYSTEM_MESSAGE,
        data={"message": message, "type": "broadcast"}
    )
    
    if room_id:
        await manager.broadcast_to_room(room_id, ws_message)
    elif role:
        try:
            user_role = UserRole(role)
            await manager.broadcast_to_role(user_role, ws_message)
        except ValueError:
            return {"error": "Invalid role"}
    else:
        await manager.broadcast_all(ws_message)
    
    return {"success": True, "message": "Broadcast sent"}


@websocket_router.post("/ws/assign/{conversation_id}/{agent_id}")
async def assign_conversation(conversation_id: str, agent_id: str):
    """Atribuir conversa a um atendente"""
    agent = manager.get_user(agent_id)
    
    if not agent:
        return JSONResponse(
            status_code=404,
            content={"error": "Agent not connected"}
        )
    
    if agent.role not in [UserRole.ATENDENTE, UserRole.SUPERVISOR]:
        return JSONResponse(
            status_code=400,
            content={"error": "User is not an agent"}
        )
    
    # Adicionar atendente à sala
    await manager.join_room(agent_id, conversation_id)
    
    # Remover da fila
    await manager.remove_from_queue(conversation_id)
    
    return {"success": True, "message": f"Conversation assigned to {agent_id}"}