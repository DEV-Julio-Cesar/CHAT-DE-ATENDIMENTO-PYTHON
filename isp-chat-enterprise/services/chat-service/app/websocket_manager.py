#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket Manager para Chat em Tempo Real
Gerencia conexões WebSocket, salas de chat e broadcasting de mensagens
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """Informações de uma conexão WebSocket"""
    websocket: WebSocket
    conversation_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)

class WebSocketManager:
    """
    Gerenciador de conexões WebSocket para chat em tempo real
    
    Funcionalidades:
    - Gerenciamento de conexões por conversa
    - Broadcasting de mensagens
    - Eventos de presença (usuário online/offline)
    - Heartbeat para manter conexões vivas
    - Métricas de conexões ativas
    """
    
    def __init__(self):
        # Conexões ativas: {websocket: ConnectionInfo}
        self.active_connections: Dict[WebSocket, ConnectionInfo] = {}
        
        # Conexões por conversa: {conversation_id: {websocket1, websocket2, ...}}
        self.conversation_connections: Dict[str, Set[WebSocket]] = {}
        
        # Conexões por usuário: {user_id: {websocket1, websocket2, ...}}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        
        # Status de digitação: {conversation_id: {user_id: timestamp}}
        self.typing_status: Dict[str, Dict[str, datetime]] = {}
        
        # Task para limpeza periódica
        self.cleanup_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Configurações
        self.heartbeat_interval = 30  # segundos
        self.typing_timeout = 5  # segundos
        self.connection_timeout = 300  # 5 minutos
        
        self.is_running = False
    
    async def start(self):
        """Iniciar WebSocket manager"""
        logger.info("🚀 Iniciando WebSocket Manager...")
        
        # Iniciar tasks de manutenção
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        self.is_running = True
        logger.info("✅ WebSocket Manager iniciado")
    
    async def stop(self):
        """Parar WebSocket manager"""
        logger.info("🛑 Parando WebSocket Manager...")
        
        self.is_running = False
        
        # Cancelar tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        # Fechar todas as conexões
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar WebSocket: {e}")
        
        # Limpar estruturas
        self.active_connections.clear()
        self.conversation_connections.clear()
        self.user_connections.clear()
        self.typing_status.clear()
        
        logger.info("✅ WebSocket Manager parado")
    
    async def connect(
        self, 
        websocket: WebSocket, 
        conversation_id: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None
    ):
        """
        Conectar novo WebSocket
        
        Args:
            websocket: Conexão WebSocket
            conversation_id: ID da conversa
            user_id: ID do usuário (opcional)
            user_name: Nome do usuário (opcional)
        """
        try:
            # Aceitar conexão
            await websocket.accept()
            
            # Criar informações da conexão
            connection_info = ConnectionInfo(
                websocket=websocket,
                conversation_id=conversation_id,
                user_id=user_id,
                user_name=user_name
            )
            
            # Registrar conexão
            self.active_connections[websocket] = connection_info
            
            # Adicionar à conversa
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = set()
            self.conversation_connections[conversation_id].add(websocket)
            
            # Adicionar ao usuário se fornecido
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(websocket)
            
            logger.info(
                f"WebSocket conectado: conversa={conversation_id}, "
                f"usuário={user_name or user_id or 'anônimo'}, "
                f"total_conexões={len(self.active_connections)}"
            )
            
            # Notificar outros usuários da conversa
            await self.broadcast_to_conversation(
                conversation_id,
                {
                    "type": "user_joined",
                    "user_id": user_id,
                    "user_name": user_name,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_websocket=websocket
            )
            
            # Enviar mensagem de boas-vindas
            await self.send_to_websocket(websocket, {
                "type": "connection_established",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat(),
                "active_users": await self._get_conversation_users(conversation_id)
            })
            
        except Exception as e:
            logger.error(f"Erro ao conectar WebSocket: {e}")
            await self._cleanup_websocket(websocket)
    
    def disconnect(self, websocket: WebSocket, conversation_id: Optional[str] = None):
        """
        Desconectar WebSocket
        
        Args:
            websocket: Conexão WebSocket
            conversation_id: ID da conversa (opcional, será obtido automaticamente)
        """
        try:
            connection_info = self.active_connections.get(websocket)
            if not connection_info:
                return
            
            actual_conversation_id = connection_info.conversation_id
            user_id = connection_info.user_id
            user_name = connection_info.user_name
            
            # Remover das estruturas
            self._remove_websocket_from_structures(websocket)
            
            logger.info(
                f"WebSocket desconectado: conversa={actual_conversation_id}, "
                f"usuário={user_name or user_id or 'anônimo'}, "
                f"total_conexões={len(self.active_connections)}"
            )
            
            # Notificar outros usuários da conversa (async task para não bloquear)
            asyncio.create_task(self.broadcast_to_conversation(
                actual_conversation_id,
                {
                    "type": "user_left",
                    "user_id": user_id,
                    "user_name": user_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ))
            
        except Exception as e:
            logger.error(f"Erro ao desconectar WebSocket: {e}")
    
    async def send_to_websocket(self, websocket: WebSocket, data: Dict[str, Any]):
        """
        Enviar dados para um WebSocket específico
        
        Args:
            websocket: Conexão WebSocket
            data: Dados para enviar
        """
        try:
            await websocket.send_json(data)
            
            # Atualizar última atividade
            if websocket in self.active_connections:
                self.active_connections[websocket].last_activity = datetime.utcnow()
                
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Erro ao enviar dados via WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_conversation(
        self, 
        conversation_id: str, 
        data: Dict[str, Any],
        exclude_websocket: Optional[WebSocket] = None
    ):
        """
        Broadcast para todos os WebSockets de uma conversa
        
        Args:
            conversation_id: ID da conversa
            data: Dados para enviar
            exclude_websocket: WebSocket para excluir do broadcast
        """
        if conversation_id not in self.conversation_connections:
            return
        
        websockets = self.conversation_connections[conversation_id].copy()
        
        # Remover WebSocket excluído
        if exclude_websocket and exclude_websocket in websockets:
            websockets.remove(exclude_websocket)
        
        # Enviar para todos os WebSockets
        tasks = []
        for websocket in websockets:
            tasks.append(self.send_to_websocket(websocket, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_user(
        self, 
        user_id: str, 
        data: Dict[str, Any]
    ):
        """
        Broadcast para todos os WebSockets de um usuário
        
        Args:
            user_id: ID do usuário
            data: Dados para enviar
        """
        if user_id not in self.user_connections:
            return
        
        websockets = self.user_connections[user_id].copy()
        
        # Enviar para todos os WebSockets do usuário
        tasks = []
        for websocket in websockets:
            tasks.append(self.send_to_websocket(websocket, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def set_typing_status(
        self, 
        conversation_id: str, 
        user_id: str, 
        is_typing: bool = True
    ):
        """
        Definir status de digitação
        
        Args:
            conversation_id: ID da conversa
            user_id: ID do usuário
            is_typing: Se está digitando
        """
        try:
            if conversation_id not in self.typing_status:
                self.typing_status[conversation_id] = {}
            
            if is_typing:
                self.typing_status[conversation_id][user_id] = datetime.utcnow()
            else:
                self.typing_status[conversation_id].pop(user_id, None)
            
            # Broadcast status de digitação
            await self.broadcast_to_conversation(
                conversation_id,
                {
                    "type": "typing_status",
                    "user_id": user_id,
                    "is_typing": is_typing,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao definir status de digitação: {e}")
    
    def get_conversation_connections(self, conversation_id: str) -> int:
        """Obter número de conexões ativas em uma conversa"""
        return len(self.conversation_connections.get(conversation_id, set()))
    
    def get_user_connections(self, user_id: str) -> int:
        """Obter número de conexões ativas de um usuário"""
        return len(self.user_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Obter número total de conexões ativas"""
        return len(self.active_connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do WebSocket manager"""
        return {
            "total_connections": len(self.active_connections),
            "conversations_with_connections": len(self.conversation_connections),
            "users_connected": len(self.user_connections),
            "typing_conversations": len(self.typing_status),
            "is_running": self.is_running,
            "uptime_seconds": (datetime.utcnow() - datetime.utcnow()).total_seconds() if self.is_running else 0
        }
    
    # === MÉTODOS PRIVADOS ===
    
    async def _get_conversation_users(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Obter lista de usuários ativos na conversa"""
        users = []
        
        if conversation_id in self.conversation_connections:
            for websocket in self.conversation_connections[conversation_id]:
                connection_info = self.active_connections.get(websocket)
                if connection_info and connection_info.user_id:
                    users.append({
                        "user_id": connection_info.user_id,
                        "user_name": connection_info.user_name,
                        "connected_at": connection_info.connected_at.isoformat()
                    })
        
        return users
    
    def _remove_websocket_from_structures(self, websocket: WebSocket):
        """Remover WebSocket de todas as estruturas de dados"""
        connection_info = self.active_connections.pop(websocket, None)
        
        if not connection_info:
            return
        
        # Remover da conversa
        conversation_id = connection_info.conversation_id
        if conversation_id in self.conversation_connections:
            self.conversation_connections[conversation_id].discard(websocket)
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]
        
        # Remover do usuário
        user_id = connection_info.user_id
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def _cleanup_websocket(self, websocket: WebSocket):
        """Limpar WebSocket com erro"""
        try:
            await websocket.close()
        except:
            pass
        finally:
            self.disconnect(websocket)
    
    async def _cleanup_loop(self):
        """Loop de limpeza periódica"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Executar a cada minuto
                await self._cleanup_inactive_connections()
                await self._cleanup_typing_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop de limpeza: {e}")
    
    async def _heartbeat_loop(self):
        """Loop de heartbeat para manter conexões vivas"""
        while self.is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop de heartbeat: {e}")
    
    async def _cleanup_inactive_connections(self):
        """Limpar conexões inativas"""
        now = datetime.utcnow()
        inactive_websockets = []
        
        for websocket, connection_info in self.active_connections.items():
            if (now - connection_info.last_activity).total_seconds() > self.connection_timeout:
                inactive_websockets.append(websocket)
        
        for websocket in inactive_websockets:
            logger.info("Removendo conexão inativa")
            await self._cleanup_websocket(websocket)
    
    async def _cleanup_typing_status(self):
        """Limpar status de digitação expirados"""
        now = datetime.utcnow()
        
        for conversation_id in list(self.typing_status.keys()):
            expired_users = []
            
            for user_id, timestamp in self.typing_status[conversation_id].items():
                if (now - timestamp).total_seconds() > self.typing_timeout:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.typing_status[conversation_id][user_id]
                
                # Notificar que parou de digitar
                await self.broadcast_to_conversation(
                    conversation_id,
                    {
                        "type": "typing_status",
                        "user_id": user_id,
                        "is_typing": False,
                        "timestamp": now.isoformat()
                    }
                )
            
            # Remover conversa se não há mais usuários digitando
            if not self.typing_status[conversation_id]:
                del self.typing_status[conversation_id]
    
    async def _send_heartbeat(self):
        """Enviar heartbeat para todas as conexões"""
        heartbeat_data = {
            "type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        tasks = []
        for websocket in list(self.active_connections.keys()):
            tasks.append(self.send_to_websocket(websocket, heartbeat_data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

# Instância global do WebSocket manager
websocket_manager = WebSocketManager()