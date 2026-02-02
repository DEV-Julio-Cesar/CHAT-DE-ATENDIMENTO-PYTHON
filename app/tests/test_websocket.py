"""
Testes para WebSocket Enterprise
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.websocket.main import (
    ConnectionManager,
    WebSocketMessage,
    ConnectedUser,
    EventType,
    UserRole,
    ConnectionStatus,
    manager as global_manager
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def connection_manager():
    """Connection manager para testes"""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Mock de WebSocket"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_message():
    """Mensagem de exemplo"""
    return WebSocketMessage(
        event=EventType.MESSAGE,
        data={
            "room_id": "room_123",
            "content": "Olá, preciso de ajuda!",
            "type": "text"
        }
    )


# =============================================================================
# TESTES DE WebSocketMessage
# =============================================================================

class TestWebSocketMessage:
    """Testes para WebSocketMessage"""
    
    def test_create_message(self):
        """Criar mensagem básica"""
        msg = WebSocketMessage(
            event=EventType.MESSAGE,
            data={"content": "Teste"}
        )
        
        assert msg.event == EventType.MESSAGE
        assert msg.data["content"] == "Teste"
        assert msg.timestamp is not None
        assert msg.message_id is not None
    
    def test_message_to_json(self):
        """Serializar mensagem para JSON"""
        msg = WebSocketMessage(
            event=EventType.MESSAGE,
            data={"content": "Teste"}
        )
        
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["event"] == "message"
        assert parsed["data"]["content"] == "Teste"
        assert "timestamp" in parsed
        assert "message_id" in parsed
    
    def test_message_from_json(self):
        """Deserializar mensagem de JSON"""
        json_str = json.dumps({
            "event": "message",
            "data": {"content": "Teste"},
            "timestamp": "2024-01-01T12:00:00Z",
            "message_id": "test-123"
        })
        
        msg = WebSocketMessage.from_json(json_str)
        
        assert msg.event == EventType.MESSAGE
        assert msg.data["content"] == "Teste"
        assert msg.message_id == "test-123"
    
    def test_message_from_invalid_json(self):
        """Erro ao deserializar JSON inválido"""
        with pytest.raises(json.JSONDecodeError):
            WebSocketMessage.from_json("invalid json")


# =============================================================================
# TESTES DE ConnectedUser
# =============================================================================

class TestConnectedUser:
    """Testes para ConnectedUser"""
    
    def test_create_connected_user(self, mock_websocket):
        """Criar usuário conectado"""
        user = ConnectedUser(
            user_id="user_123",
            role=UserRole.CLIENTE,
            websocket=mock_websocket
        )
        
        assert user.user_id == "user_123"
        assert user.role == UserRole.CLIENTE
        assert user.status == ConnectionStatus.ONLINE
        assert user.current_conversation is None
        assert user.connection_id is not None
    
    def test_connected_user_to_dict(self, mock_websocket):
        """Converter usuário para dicionário"""
        user = ConnectedUser(
            user_id="user_123",
            role=UserRole.ATENDENTE,
            websocket=mock_websocket,
            metadata={"nome": "João"}
        )
        
        data = user.to_dict()
        
        assert data["user_id"] == "user_123"
        assert data["role"] == "atendente"
        assert data["metadata"]["nome"] == "João"
        assert "websocket" not in data  # Não deve incluir websocket


# =============================================================================
# TESTES DE ConnectionManager
# =============================================================================

class TestConnectionManager:
    """Testes para ConnectionManager"""
    
    @pytest.mark.asyncio
    async def test_connect_user(self, connection_manager, mock_websocket):
        """Conectar usuário"""
        user = await connection_manager.connect(
            websocket=mock_websocket,
            user_id="user_123",
            role=UserRole.CLIENTE
        )
        
        assert user.user_id == "user_123"
        assert "user_123" in connection_manager.active_connections
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_agent(self, connection_manager, mock_websocket):
        """Conectar atendente - deve adicionar aos disponíveis"""
        await connection_manager.connect(
            websocket=mock_websocket,
            user_id="agent_123",
            role=UserRole.ATENDENTE
        )
        
        assert "agent_123" in connection_manager.available_agents
    
    @pytest.mark.asyncio
    async def test_disconnect_user(self, connection_manager, mock_websocket):
        """Desconectar usuário"""
        await connection_manager.connect(
            websocket=mock_websocket,
            user_id="user_123",
            role=UserRole.CLIENTE
        )
        
        await connection_manager.disconnect("user_123")
        
        assert "user_123" not in connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_join_room(self, connection_manager, mock_websocket):
        """Entrar em sala"""
        await connection_manager.connect(
            websocket=mock_websocket,
            user_id="user_123",
            role=UserRole.CLIENTE
        )
        
        await connection_manager.join_room("user_123", "room_456")
        
        assert "room_456" in connection_manager.rooms
        assert "user_123" in connection_manager.rooms["room_456"]
        assert connection_manager.active_connections["user_123"].current_conversation == "room_456"
    
    @pytest.mark.asyncio
    async def test_leave_room(self, connection_manager, mock_websocket):
        """Sair de sala"""
        await connection_manager.connect(
            websocket=mock_websocket,
            user_id="user_123",
            role=UserRole.CLIENTE
        )
        await connection_manager.join_room("user_123", "room_456")
        
        await connection_manager.leave_room("user_123", "room_456")
        
        assert "room_456" not in connection_manager.rooms  # Sala vazia é removida
    
    @pytest.mark.asyncio
    async def test_send_personal(self, connection_manager, mock_websocket):
        """Enviar mensagem pessoal"""
        await connection_manager.connect(
            websocket=mock_websocket,
            user_id="user_123",
            role=UserRole.CLIENTE
        )
        
        msg = WebSocketMessage(event=EventType.MESSAGE, data={"content": "Teste"})
        result = await connection_manager.send_personal("user_123", msg)
        
        assert result is True
        mock_websocket.send_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, connection_manager, mock_websocket):
        """Broadcast para sala"""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        await connection_manager.connect(ws1, "user_1", UserRole.CLIENTE)
        await connection_manager.connect(ws2, "user_2", UserRole.ATENDENTE)
        await connection_manager.join_room("user_1", "room_123")
        await connection_manager.join_room("user_2", "room_123")
        
        msg = WebSocketMessage(event=EventType.MESSAGE, data={"content": "Olá"})
        await connection_manager.broadcast_to_room("room_123", msg, exclude={"user_1"})
        
        # user_2 deve receber, user_1 não (excluído)
        ws2.send_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_available_agent(self, connection_manager, mock_websocket):
        """Obter atendente disponível"""
        await connection_manager.connect(
            websocket=mock_websocket,
            user_id="agent_123",
            role=UserRole.ATENDENTE
        )
        
        agent = connection_manager.get_available_agent()
        assert agent == "agent_123"
    
    @pytest.mark.asyncio
    async def test_add_to_queue(self, connection_manager, mock_websocket):
        """Adicionar à fila de espera"""
        await connection_manager.connect(
            websocket=mock_websocket,
            user_id="agent_123",
            role=UserRole.ATENDENTE
        )
        
        await connection_manager.add_to_queue("conv_123")
        
        assert "conv_123" in connection_manager.waiting_queue
        assert connection_manager.get_queue_position("conv_123") == 1
    
    @pytest.mark.asyncio
    async def test_remove_from_queue(self, connection_manager):
        """Remover da fila"""
        connection_manager.waiting_queue.append("conv_123")
        
        await connection_manager.remove_from_queue("conv_123")
        
        assert "conv_123" not in connection_manager.waiting_queue
    
    def test_get_stats(self, connection_manager):
        """Obter estatísticas"""
        stats = connection_manager.get_stats()
        
        assert "total_connections" in stats
        assert "current_connections" in stats
        assert "active_rooms" in stats
        assert "available_agents" in stats
        assert "queue_size" in stats
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, connection_manager, mock_websocket):
        """Rastrear métricas"""
        initial_total = connection_manager.metrics["total_connections"]
        
        await connection_manager.connect(mock_websocket, "user_1", UserRole.CLIENTE)
        
        assert connection_manager.metrics["total_connections"] == initial_total + 1
        assert connection_manager.metrics["current_connections"] == 1


# =============================================================================
# TESTES DE EVENTOS
# =============================================================================

class TestEventTypes:
    """Testes para tipos de eventos"""
    
    def test_event_type_values(self):
        """Verificar valores de EventType"""
        assert EventType.MESSAGE.value == "message"
        assert EventType.TYPING_START.value == "typing_start"
        assert EventType.CONNECTED.value == "connected"
    
    def test_user_role_values(self):
        """Verificar valores de UserRole"""
        assert UserRole.CLIENTE.value == "cliente"
        assert UserRole.ATENDENTE.value == "atendente"
        assert UserRole.SUPERVISOR.value == "supervisor"
    
    def test_connection_status_values(self):
        """Verificar valores de ConnectionStatus"""
        assert ConnectionStatus.ONLINE.value == "online"
        assert ConnectionStatus.AWAY.value == "away"
        assert ConnectionStatus.BUSY.value == "busy"


# =============================================================================
# TESTES DE INTEGRAÇÃO
# =============================================================================

class TestIntegration:
    """Testes de integração"""
    
    @pytest.mark.asyncio
    async def test_complete_chat_flow(self, connection_manager):
        """Fluxo completo de chat"""
        ws_client = AsyncMock()
        ws_agent = AsyncMock()
        
        # Cliente conecta
        client = await connection_manager.connect(ws_client, "client_1", UserRole.CLIENTE)
        
        # Atendente conecta
        agent = await connection_manager.connect(ws_agent, "agent_1", UserRole.ATENDENTE)
        
        # Cliente entra na sala
        await connection_manager.join_room("client_1", "conv_123")
        
        # Atendente entra na sala
        await connection_manager.join_room("agent_1", "conv_123")
        
        # Verificar sala
        members = connection_manager.get_room_members("conv_123")
        assert "client_1" in members
        assert "agent_1" in members
        
        # Enviar mensagem para sala
        msg = WebSocketMessage(
            event=EventType.MESSAGE,
            data={"content": "Olá, preciso de ajuda!"}
        )
        await connection_manager.broadcast_to_room("conv_123", msg)
        
        # Ambos devem receber
        ws_client.send_text.assert_called()
        ws_agent.send_text.assert_called()
        
        # Cliente sai
        await connection_manager.leave_room("client_1", "conv_123")
        await connection_manager.disconnect("client_1")
        
        # Verificar cleanup
        assert "client_1" not in connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_queue_and_assignment(self, connection_manager):
        """Fila e atribuição de atendente"""
        ws_client = AsyncMock()
        ws_agent = AsyncMock()
        
        # Cliente sem atendente disponível
        await connection_manager.connect(ws_client, "client_1", UserRole.CLIENTE)
        await connection_manager.add_to_queue("conv_123")
        
        assert connection_manager.get_queue_position("conv_123") == 1
        
        # Atendente conecta
        await connection_manager.connect(ws_agent, "agent_1", UserRole.ATENDENTE)
        
        # Verificar atendente disponível
        available = connection_manager.get_available_agent()
        assert available == "agent_1"
        
        # Atribuir e remover da fila
        await connection_manager.join_room("agent_1", "conv_123")
        await connection_manager.remove_from_queue("conv_123")
        
        assert "conv_123" not in connection_manager.waiting_queue


# =============================================================================
# EXECUTAR TESTES
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
