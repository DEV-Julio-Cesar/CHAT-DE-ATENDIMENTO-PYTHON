"""
Servidor WebSocket para comunicação em tempo real
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.routing import APIRouter
import json
import structlog
from typing import Dict, List, Set, Optional, Any
import asyncio
from datetime import datetime
import uuid

from app.core.security import security_manager
from app.core.redis_client import redis_manager, CacheKeys
from app.models.database import UserRole

logger = structlog.get_logger(__name__)

# Router para WebSocket
websocket_router = APIRouter()


class ConnectionManager:
    """Gerenciador de conexões WebSocket"""
    
    def __init__(self):
        # Conexões ativas: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Salas de chat: {room_id: {user_ids}}
        self.chat_rooms: Dict[str, Set[str]] = {}
        # Conexões por role: {role: {user_ids}}
        self.connections_by_role: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str) -> str:
        """Conectar usuário"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        
        # Adicionar à lista de conexões ativas
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][connection_id] = websocket
        
        # Adicionar por role
        if user_role not in self.connections_by_role:
            self.connections_by_role[user_role] = set()
        self.connections_by_role[user_role].add(user_id)
        
        logger.info(
            "WebSocket connection established",
            user_id=user_id,
            connection_id=connection_id,
            role=user_role,
            total_connections=self.get_total_connections()
        )
        
        # Notificar outros usuários sobre nova conexão (apenas admins/supervisores)
        if user_role in [UserRole.ADMIN.value, UserRole.SUPERVISOR.value]:
            await self.broadcast_to_role(
                [UserRole.ADMIN.value, UserRole.SUPERVISOR.value],
                {
                    "type": "user_connected",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user=user_id
            )
        
        return connection_id
    
    async def disconnect(self, user_id: str, connection_id: str, user_role: str):
        """Desconectar usuário"""
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]
                
                # Se não há mais conexões do usuário, remover completamente
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    
                    # Remover das conexões por role
                    if user_role in self.connections_by_role:
                        self.connections_by_role[user_role].discard(user_id)
        
        # Remover de todas as salas de chat
        rooms_to_remove = []
        for room_id, users in self.chat_rooms.items():
            users.discard(user_id)
            if not users:  # Sala vazia
                rooms_to_remove.append(room_id)
        
        for room_id in rooms_to_remove:
            del self.chat_rooms[room_id]
        
        logger.info(
            "WebSocket connection closed",
            user_id=user_id,
            connection_id=connection_id,
            role=user_role,
            total_connections=self.get_total_connections()
        )
        
        # Notificar outros usuários sobre desconexão
        if user_role in [UserRole.ADMIN.value, UserRole.SUPERVISOR.value]:
            await self.broadcast_to_role(
                [UserRole.ADMIN.value, UserRole.SUPERVISOR.value],
                {
                    "type": "user_disconnected",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user=user_id
            )
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Enviar mensagem para usuário específico"""
        if user_id in self.active_connections:
            # Enviar para todas as conexões do usuário
            disconnected_connections = []
            
            for connection_id, websocket in self.active_connections[user_id].items():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(
                        "Failed to send message to connection",
                        user_id=user_id,
                        connection_id=connection_id,
                        error=str(e)
                    )
                    disconnected_connections.append(connection_id)
            
            # Remover conexões mortas
            for connection_id in disconnected_connections:
                if connection_id in self.active_connections[user_id]:
                    del self.active_connections[user_id][connection_id]
    
    async def broadcast_to_role(
        self, 
        roles: List[str], 
        message: dict, 
        exclude_user: Optional[str] = None
    ):
        """Broadcast para usuários com roles específicas"""
        target_users = set()
        
        for role in roles:
            if role in self.connections_by_role:
                target_users.update(self.connections_by_role[role])
        
        if exclude_user:
            target_users.discard(exclude_user)
        
        # Enviar mensagem para todos os usuários alvo
        for user_id in target_users:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_user: Optional[str] = None):
        """Broadcast para sala de chat específica"""
        if room_id in self.chat_rooms:
            users = self.chat_rooms[room_id].copy()
            if exclude_user:
                users.discard(exclude_user)
            
            for user_id in users:
                await self.send_personal_message(message, user_id)
    
    async def join_room(self, room_id: str, user_id: str):
        """Adicionar usuário à sala"""
        if room_id not in self.chat_rooms:
            self.chat_rooms[room_id] = set()
        
        self.chat_rooms[room_id].add(user_id)
        
        # Notificar outros usuários da sala
        await self.broadcast_to_room(
            room_id,
            {
                "type": "user_joined_room",
                "room_id": room_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            exclude_user=user_id
        )
    
    async def leave_room(self, room_id: str, user_id: str):
        """Remover usuário da sala"""
        if room_id in self.chat_rooms:
            self.chat_rooms[room_id].discard(user_id)
            
            # Notificar outros usuários da sala
            await self.broadcast_to_room(
                room_id,
                {
                    "type": "user_left_room",
                    "room_id": room_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user=user_id
            )
            
            # Remover sala se vazia
            if not self.chat_rooms[room_id]:
                del self.chat_rooms[room_id]
    
    def get_total_connections(self) -> int:
        """Obter total de conexões ativas"""
        total = 0
        for user_connections in self.active_connections.values():
            total += len(user_connections)
        return total
    
    def get_online_users(self) -> List[str]:
        """Obter lista de usuários online"""
        return list(self.active_connections.keys())
    
    def get_room_users(self, room_id: str) -> List[str]:
        """Obter usuários de uma sala"""
        if room_id in self.chat_rooms:
            return list(self.chat_rooms[room_id])
        return []


# Instância global do gerenciador
manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[dict]:
    """Autenticar conexão WebSocket"""
    try:
        # Verificar token
        payload = security_manager.verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        # Buscar dados do usuário no cache
        cache_key = CacheKeys.format_key(CacheKeys.USER_SESSION, user_id=user_id)
        user_data = await redis_manager.get_json(cache_key)
        
        if not user_data or not user_data.get("ativo", False):
            return None
        
        return user_data
        
    except Exception as e:
        logger.warning("WebSocket authentication failed", error=str(e))
        return None


@websocket_router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """Endpoint principal do WebSocket"""
    
    # Autenticar usuário
    user_data = await authenticate_websocket(websocket, token)
    if not user_data:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = user_data["id"]
    user_role = user_data["role"]
    connection_id = None
    
    try:
        # Conectar usuário
        connection_id = await manager.connect(websocket, user_id, user_role)
        
        # Enviar mensagem de boas-vindas
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "message": "Connected successfully",
            "user_id": user_id,
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Loop principal de mensagens
        while True:
            try:
                # Receber mensagem
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Processar mensagem
                await handle_websocket_message(websocket, user_data, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception as e:
                logger.error("WebSocket message handling error", error=str(e), user_id=user_id)
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e), user_id=user_id)
    finally:
        # Desconectar usuário
        if connection_id:
            await manager.disconnect(user_id, connection_id, user_role)


async def handle_websocket_message(websocket: WebSocket, user_data: dict, message: dict):
    """Processar mensagem recebida via WebSocket"""
    
    message_type = message.get("type")
    user_id = user_data["id"]
    user_role = user_data["role"]
    
    try:
        if message_type == "ping":
            # Responder pong para keep-alive
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }))
        
        elif message_type == "join_room":
            # Entrar em sala de chat
            room_id = message.get("room_id")
            if room_id:
                await manager.join_room(room_id, user_id)
                await websocket.send_text(json.dumps({
                    "type": "room_joined",
                    "room_id": room_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        elif message_type == "leave_room":
            # Sair de sala de chat
            room_id = message.get("room_id")
            if room_id:
                await manager.leave_room(room_id, user_id)
                await websocket.send_text(json.dumps({
                    "type": "room_left",
                    "room_id": room_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        elif message_type == "chat_message":
            # Mensagem de chat
            room_id = message.get("room_id")
            content = message.get("content")
            
            if room_id and content:
                chat_message = {
                    "type": "chat_message",
                    "room_id": room_id,
                    "user_id": user_id,
                    "username": user_data["username"],
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Broadcast para a sala
                await manager.broadcast_to_room(room_id, chat_message, exclude_user=user_id)
                
                # Confirmar envio
                await websocket.send_text(json.dumps({
                    "type": "message_sent",
                    "room_id": room_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        elif message_type == "private_message":
            # Mensagem privada
            target_user_id = message.get("target_user_id")
            content = message.get("content")
            
            if target_user_id and content:
                private_message = {
                    "type": "private_message",
                    "from_user_id": user_id,
                    "from_username": user_data["username"],
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Enviar para usuário alvo
                await manager.send_personal_message(private_message, target_user_id)
                
                # Confirmar envio
                await websocket.send_text(json.dumps({
                    "type": "private_message_sent",
                    "target_user_id": target_user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        elif message_type == "get_online_users":
            # Obter usuários online (apenas para admins/supervisores)
            if user_role in [UserRole.ADMIN.value, UserRole.SUPERVISOR.value]:
                online_users = manager.get_online_users()
                await websocket.send_text(json.dumps({
                    "type": "online_users",
                    "users": online_users,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        elif message_type == "get_room_users":
            # Obter usuários de uma sala
            room_id = message.get("room_id")
            if room_id:
                room_users = manager.get_room_users(room_id)
                await websocket.send_text(json.dumps({
                    "type": "room_users",
                    "room_id": room_id,
                    "users": room_users,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        elif message_type == "broadcast_notification":
            # Broadcast de notificação (apenas para admins)
            if user_role == UserRole.ADMIN.value:
                notification_message = message.get("message")
                target_roles = message.get("target_roles", [])
                
                if notification_message:
                    notification = {
                        "type": "notification",
                        "message": notification_message,
                        "from_user": user_data["username"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    if target_roles:
                        await manager.broadcast_to_role(target_roles, notification)
                    else:
                        # Broadcast para todos
                        for role in manager.connections_by_role.keys():
                            await manager.broadcast_to_role([role], notification)
        
        else:
            # Tipo de mensagem desconhecido
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    except Exception as e:
        logger.error("Message handling error", error=str(e), user_id=user_id, message_type=message_type)
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process message",
            "timestamp": datetime.utcnow().isoformat()
        }))


# Funções utilitárias para envio de notificações
async def send_notification_to_user(user_id: str, notification: dict):
    """Enviar notificação para usuário específico"""
    await manager.send_personal_message({
        "type": "notification",
        **notification,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)


async def send_notification_to_role(roles: List[str], notification: dict):
    """Enviar notificação para usuários com roles específicas"""
    await manager.broadcast_to_role(roles, {
        "type": "notification",
        **notification,
        "timestamp": datetime.utcnow().isoformat()
    })


async def send_system_alert(message: str, priority: str = "normal"):
    """Enviar alerta do sistema para todos os usuários online"""
    alert = {
        "type": "system_alert",
        "message": message,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Enviar para todos os roles
    for role in manager.connections_by_role.keys():
        await manager.broadcast_to_role([role], alert)


# Endpoint para estatísticas WebSocket (apenas para admins)
@websocket_router.get("/stats")
async def websocket_stats():
    """Obter estatísticas das conexões WebSocket"""
    return {
        "total_connections": manager.get_total_connections(),
        "online_users": len(manager.get_online_users()),
        "active_rooms": len(manager.chat_rooms),
        "connections_by_role": {
            role: len(users) for role, users in manager.connections_by_role.items()
        }
    }