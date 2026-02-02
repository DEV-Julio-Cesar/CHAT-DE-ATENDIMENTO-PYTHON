# 🔌 WebSocket Real-Time Chat - Documentação

## Visão Geral

Sistema de chat em tempo real utilizando WebSocket para comunicação bidirecional entre clientes, atendentes e o chatbot AI.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Web/Mobile)                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                    WebSocket (ws://...)
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI WebSocket Server                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Connection Manager                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │ Connections │ │   Rooms     │ │   Queue     │       │   │
│  │  │  (users)    │ │ (conversas) │ │  (espera)   │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Event Handlers                              │   │
│  │  • Message    • Typing     • Heartbeat    • Assignment  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Integrations                                │   │
│  │  • Chatbot AI    • Redis Pub/Sub    • Database          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Endpoints WebSocket

### Conexão Principal

```
WS /ws/chat/{user_id}?role={role}&token={token}
```

**Parâmetros:**
- `user_id`: ID único do usuário
- `role`: `cliente`, `atendente`, `supervisor`
- `token`: Token JWT (opcional, para autenticação)

### Endpoints HTTP Auxiliares

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/ws/status` | GET | Status do servidor WebSocket |
| `/ws/rooms` | GET | Listar salas ativas |
| `/ws/queue` | GET | Ver fila de espera |
| `/ws/agents` | GET | Listar atendentes disponíveis |
| `/ws/broadcast` | POST | Enviar mensagem broadcast |
| `/ws/assign/{conv}/{agent}` | POST | Atribuir conversa a atendente |

## Tipos de Eventos

### Eventos de Conexão

```json
// Conexão estabelecida
{
    "event": "connected",
    "data": {
        "connection_id": "uuid",
        "user_id": "user_123",
        "role": "cliente",
        "server_time": "2024-01-01T12:00:00Z"
    }
}

// Desconexão
{
    "event": "disconnected",
    "data": {"user_id": "user_123"}
}
```

### Eventos de Mensagem

```json
// Enviar mensagem
{
    "event": "message",
    "data": {
        "room_id": "conv_123",
        "content": "Olá, preciso de ajuda!",
        "type": "text"
    }
}

// Mensagem recebida
{
    "event": "message",
    "data": {
        "id": "msg_uuid",
        "room_id": "conv_123",
        "sender_id": "user_123",
        "sender_role": "cliente",
        "content": "Olá, preciso de ajuda!",
        "type": "text",
        "timestamp": "2024-01-01T12:00:00Z"
    }
}

// Resposta do Bot
{
    "event": "bot_response",
    "data": {
        "id": "msg_uuid",
        "content": "Olá! Sou a assistente virtual...",
        "metadata": {
            "intent": "saudacao",
            "sentiment": "neutro",
            "confidence": 0.95,
            "quick_replies": ["Ver minha conta", "Falar com atendente"]
        }
    }
}
```

### Eventos de Status

```json
// Começou a digitar
{
    "event": "typing_start",
    "data": {"user_id": "user_123", "room_id": "conv_123"}
}

// Parou de digitar
{
    "event": "typing_stop",
    "data": {"user_id": "user_123", "room_id": "conv_123"}
}

// Heartbeat
{
    "event": "heartbeat",
    "data": {"status": "alive", "server_time": "..."}
}
```

### Eventos de Atendimento

```json
// Conversa atribuída a atendente
{
    "event": "conversation_assigned",
    "data": {
        "room_id": "conv_123",
        "agent_id": "agent_456",
        "client_name": "João"
    }
}

// Posição na fila
{
    "event": "queue_position",
    "data": {
        "position": 3,
        "estimated_wait": "6-15 minutos"
    }
}

// Atualização da fila (para atendentes)
{
    "event": "queue_update",
    "data": {
        "queue_size": 5,
        "new_conversation": "conv_789"
    }
}
```

## Uso no Frontend

### JavaScript/TypeScript

```javascript
// Conectar
const ws = new WebSocket('ws://localhost:8000/ws/chat/user123?role=cliente');

ws.onopen = () => {
    console.log('Conectado!');
    
    // Entrar em uma sala
    ws.send(JSON.stringify({
        event: 'join_room',
        data: { room_id: 'conv_123' }
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch (message.event) {
        case 'message':
            displayMessage(message.data);
            break;
        case 'bot_response':
            displayBotMessage(message.data);
            break;
        case 'typing_start':
            showTypingIndicator(message.data.user_id);
            break;
        // ...
    }
};

// Enviar mensagem
function sendMessage(content) {
    ws.send(JSON.stringify({
        event: 'message',
        data: {
            room_id: 'conv_123',
            content: content,
            type: 'text'
        }
    }));
}

// Indicador de digitação
let typingTimeout;
function handleTyping() {
    ws.send(JSON.stringify({
        event: 'typing_start',
        data: { room_id: 'conv_123' }
    }));
    
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        ws.send(JSON.stringify({
            event: 'typing_stop',
            data: { room_id: 'conv_123' }
        }));
    }, 2000);
}
```

### React Hook

```typescript
import { useEffect, useState, useCallback } from 'react';

interface ChatMessage {
    id: string;
    content: string;
    sender_id: string;
    timestamp: string;
}

export function useWebSocketChat(userId: string, role: string) {
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [connected, setConnected] = useState(false);
    const [typing, setTyping] = useState<string | null>(null);

    useEffect(() => {
        const socket = new WebSocket(
            `ws://localhost:8000/ws/chat/${userId}?role=${role}`
        );

        socket.onopen = () => setConnected(true);
        socket.onclose = () => setConnected(false);
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.event === 'message' || data.event === 'bot_response') {
                setMessages(prev => [...prev, data.data]);
            }
            
            if (data.event === 'typing_start') {
                setTyping(data.data.user_id);
            }
            
            if (data.event === 'typing_stop') {
                setTyping(null);
            }
        };

        setWs(socket);
        return () => socket.close();
    }, [userId, role]);

    const sendMessage = useCallback((content: string, roomId: string) => {
        ws?.send(JSON.stringify({
            event: 'message',
            data: { room_id: roomId, content, type: 'text' }
        }));
    }, [ws]);

    return { connected, messages, typing, sendMessage };
}
```

## Fluxo de Atendimento

```
1. Cliente conecta via WebSocket
   └─> Recebe evento "connected"

2. Cliente entra em sala (conversa)
   └─> ws.send({ event: 'join_room', data: { room_id: 'conv_123' } })

3. Cliente envia mensagem
   └─> Se não há atendente na sala:
       └─> Chatbot AI responde automaticamente
       └─> Se chatbot detecta necessidade de escalação:
           └─> Busca atendente disponível
           └─> Se disponível: atribui e notifica ambos
           └─> Se não: adiciona à fila de espera

4. Atendente conecta e é notificado de nova conversa na fila
   └─> Recebe evento "queue_update"

5. Atendente assume conversa
   └─> POST /ws/assign/{conversation_id}/{agent_id}
   └─> Cliente recebe "conversation_assigned"
   └─> Atendente entra na sala

6. Comunicação em tempo real entre cliente e atendente
   └─> Mensagens, indicadores de digitação, etc.

7. Conversa encerrada
   └─> Ambos saem da sala
   └─> Sala é limpa automaticamente
```

## Escalabilidade

### Múltiplos Servidores

Para rodar em múltiplos servidores, o sistema usa Redis Pub/Sub para sincronizar eventos:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Server 1   │     │  Server 2   │     │  Server 3   │
│  (WS conn)  │     │  (WS conn)  │     │  (WS conn)  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │    Redis    │
                    │   Pub/Sub   │
                    └─────────────┘
```

### Configuração para Produção

```python
# config.py
class Settings:
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # segundos
    WS_MAX_CONNECTIONS_PER_USER: int = 3
    WS_MESSAGE_MAX_SIZE: int = 65536  # 64KB
    
    # Redis Pub/Sub
    REDIS_PUBSUB_CHANNELS: list = [
        "presence",      # Status online/offline
        "messages",      # Mensagens entre servidores
        "notifications"  # Notificações do sistema
    ]
```

## Testes

### Executar Testes

```bash
# Testes unitários
pytest app/tests/test_websocket.py -v

# Com cobertura
pytest app/tests/test_websocket.py --cov=app/websocket
```

### Demo Interativo

```bash
# Terminal 1 - Servidor
python run-local.py

# Terminal 2 - Cliente
python demo_websocket.py --user-id cliente1 --role cliente

# Terminal 3 - Atendente
python demo_websocket.py --user-id atendente1 --role atendente
```

### Interface Web

Abra `app/web/websocket_chat.html` no navegador para testar visualmente.

## Métricas

O sistema expõe métricas via endpoint `/ws/status`:

```json
{
    "status": "ready",
    "stats": {
        "total_connections": 1250,
        "current_connections": 45,
        "peak_connections": 127,
        "total_messages": 15420,
        "active_rooms": 23,
        "available_agents": 5,
        "queue_size": 3,
        "connections_by_role": {
            "cliente": 35,
            "atendente": 8,
            "supervisor": 2,
            "system": 0
        }
    }
}
```

## Segurança

### Autenticação JWT

```python
# No endpoint WebSocket
@websocket_router.websocket("/ws/chat/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(default=None)
):
    # Validar token
    if token:
        try:
            payload = verify_token(token)
            if payload["sub"] != user_id:
                await websocket.close(code=4003, reason="Token mismatch")
                return
        except:
            await websocket.close(code=4002, reason="Invalid token")
            return
```

### Rate Limiting

```python
# Limitar mensagens por usuário
MAX_MESSAGES_PER_MINUTE = 60

async def check_rate_limit(user_id: str) -> bool:
    key = f"ws_rate:{user_id}"
    count = await redis_manager.incr(key)
    if count == 1:
        await redis_manager.expire(key, 60)
    return count <= MAX_MESSAGES_PER_MINUTE
```

## Troubleshooting

### Conexão recusada

```bash
# Verificar se o servidor está rodando
curl http://localhost:8000/ws/status

# Verificar Redis
redis-cli ping
```

### Mensagens não chegam

1. Verificar se o usuário está na sala correta
2. Verificar logs do servidor para erros
3. Verificar conexão WebSocket no DevTools do navegador

### Performance lenta

1. Verificar latência do Redis
2. Verificar número de conexões ativas
3. Considerar escalar horizontalmente com mais servidores
