# 📚 Documentação da API - Sistema de Chat de Atendimento

## Visão Geral

API RESTful para sistema de atendimento ao cliente via WhatsApp, desenvolvida para provedores de internet (ISP) com suporte a até 10.000+ clientes.

**Base URL:** `https://api.seudominio.com/api/v1`

**Versão:** 2.0.0

## 🔐 Autenticação

A API utiliza autenticação JWT (JSON Web Token). Para acessar endpoints protegidos, inclua o token no header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Obtendo Token

```bash
curl -X POST "https://api.seudominio.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@email.com", "password": "senha123"}'
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "email": "usuario@email.com",
    "nome": "João Silva",
    "role": "atendente"
  }
}
```

### Roles de Usuário

| Role | Descrição | Permissões |
|------|-----------|------------|
| `admin` | Administrador | Acesso total ao sistema |
| `atendente` | Atendente | Gerenciar conversas, responder mensagens |
| `supervisor` | Supervisor | Visualizar métricas, gerenciar atendentes |
| `user` | Usuário básico | Acesso limitado |

---

## 📋 Endpoints

### Autenticação (`/api/v1/auth`)

#### POST `/auth/login`
Autenticar usuário e obter token JWT.

**Request Body:**
```json
{
  "email": "usuario@email.com",
  "password": "senha123"
}
```

**Rate Limiting:** 5 tentativas / 15 minutos por IP

**Responses:**
- `200` - Login bem-sucedido
- `401` - Credenciais inválidas
- `429` - Rate limit excedido

---

#### POST `/auth/logout`
Revogar token atual.

**Headers:** `Authorization: Bearer <token>`

**Responses:**
- `200` - Logout bem-sucedido
- `401` - Token inválido

---

#### POST `/auth/refresh`
Renovar token JWT antes da expiração.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### Usuários (`/api/v1/users`)

#### GET `/users`
Listar todos os usuários (Admin only).

**Query Parameters:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| `page` | int | Página (default: 1) |
| `limit` | int | Itens por página (default: 20, max: 100) |
| `role` | string | Filtrar por role |
| `is_active` | bool | Filtrar por status |

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "email": "admin@empresa.com",
      "nome": "Admin",
      "role": "admin",
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "pages": 8
}
```

---

#### POST `/users`
Criar novo usuário (Admin only).

**Request Body:**
```json
{
  "email": "novo@email.com",
  "password": "SenhaSegura123!",
  "nome": "Novo Usuário",
  "role": "atendente"
}
```

**Validações de Senha:**
- Mínimo 8 caracteres
- Pelo menos 1 letra maiúscula
- Pelo menos 1 número
- Pelo menos 1 caractere especial

---

#### GET `/users/{user_id}`
Obter detalhes de um usuário.

---

#### PUT `/users/{user_id}`
Atualizar usuário.

---

#### DELETE `/users/{user_id}`
Desativar usuário (soft delete).

---

### Conversas (`/api/v1/conversations`)

#### GET `/conversations`
Listar conversas do atendente logado.

**Query Parameters:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| `status` | string | `queue`, `in_progress`, `resolved`, `closed` |
| `channel` | string | `whatsapp`, `web`, `api` |
| `assigned_to` | int | ID do atendente |
| `start_date` | datetime | Data inicial |
| `end_date` | datetime | Data final |

**Response:**
```json
{
  "conversations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "customer_phone": "+5511999999999",
      "customer_name": "Cliente Exemplo",
      "status": "in_progress",
      "channel": "whatsapp",
      "assigned_to": 1,
      "started_at": "2026-02-01T10:00:00Z",
      "last_message_at": "2026-02-01T10:30:00Z",
      "messages_count": 15
    }
  ],
  "total": 45
}
```

---

#### GET `/conversations/{conversation_id}`
Obter detalhes de uma conversa incluindo mensagens.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_phone": "+5511999999999",
  "customer_name": "Cliente Exemplo",
  "status": "in_progress",
  "messages": [
    {
      "id": "msg-001",
      "direction": "incoming",
      "content": "Olá, preciso de ajuda",
      "timestamp": "2026-02-01T10:00:00Z",
      "status": "delivered"
    },
    {
      "id": "msg-002",
      "direction": "outgoing",
      "content": "Olá! Como posso ajudar?",
      "timestamp": "2026-02-01T10:01:00Z",
      "status": "read",
      "sent_by": "bot"
    }
  ]
}
```

---

#### POST `/conversations/{conversation_id}/messages`
Enviar mensagem em uma conversa.

**Request Body:**
```json
{
  "content": "Sua internet será normalizada em breve.",
  "type": "text"
}
```

**Tipos de Mensagem:**
- `text` - Texto simples
- `image` - Imagem (URL ou base64)
- `document` - Documento
- `template` - Template pré-aprovado

---

#### POST `/conversations/{conversation_id}/transfer`
Transferir conversa para outro atendente.

**Request Body:**
```json
{
  "to_agent_id": 5,
  "reason": "Especialista em fibra óptica"
}
```

---

#### POST `/conversations/{conversation_id}/close`
Encerrar conversa.

**Request Body:**
```json
{
  "resolution": "resolved",
  "notes": "Problema resolvido - reset do modem"
}
```

---

### WhatsApp (`/api/v1/whatsapp`)

#### POST `/whatsapp/webhook`
Webhook para receber eventos do WhatsApp Business API.

**Headers:**
- `X-Hub-Signature-256` - Assinatura HMAC para validação

**Este endpoint é chamado automaticamente pela Meta.**

---

#### GET `/whatsapp/webhook`
Verificação do webhook (challenge).

**Query Parameters:**
- `hub.mode` - Deve ser `subscribe`
- `hub.verify_token` - Token de verificação configurado
- `hub.challenge` - Challenge a ser retornado

---

#### POST `/whatsapp/send`
Enviar mensagem WhatsApp.

**Request Body:**
```json
{
  "to": "+5511999999999",
  "type": "text",
  "content": "Olá! Esta é uma mensagem de teste."
}
```

---

#### POST `/whatsapp/send-template`
Enviar template pré-aprovado.

**Request Body:**
```json
{
  "to": "+5511999999999",
  "template_name": "boas_vindas",
  "language": "pt_BR",
  "components": [
    {
      "type": "body",
      "parameters": [
        {"type": "text", "text": "João"}
      ]
    }
  ]
}
```

---

### Chatbot (`/api/v1/chatbot`)

#### POST `/chatbot/message`
Processar mensagem com IA (Gemini).

**Request Body:**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Minha internet está lenta",
  "context": {
    "customer_name": "João",
    "customer_plan": "100 Mbps"
  }
}
```

**Response:**
```json
{
  "response": "Olá João! Vou verificar sua conexão. Você pode me informar se o problema é em todos os dispositivos ou apenas em um?",
  "intent": "suporte_tecnico",
  "confidence": 0.95,
  "should_transfer": false,
  "suggested_actions": ["verificar_modem", "testar_velocidade"]
}
```

---

#### POST `/chatbot/escalate`
Escalar conversa para atendente humano.

**Request Body:**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "reason": "Cliente solicitou atendente humano"
}
```

---

### Dashboard (`/api/v1/dashboard`)

#### GET `/dashboard/metrics`
Obter métricas em tempo real.

**Response:**
```json
{
  "conversations": {
    "active": 45,
    "in_queue": 12,
    "resolved_today": 156
  },
  "agents": {
    "online": 8,
    "busy": 6,
    "available": 2
  },
  "performance": {
    "avg_response_time_seconds": 45,
    "avg_resolution_time_minutes": 12,
    "satisfaction_rate": 4.5
  }
}
```

---

#### GET `/dashboard/agents`
Listar status dos atendentes.

**Response:**
```json
{
  "agents": [
    {
      "id": 1,
      "nome": "Maria Silva",
      "status": "online",
      "current_conversations": 3,
      "max_conversations": 5,
      "avg_response_time": 30
    }
  ]
}
```

---

#### GET `/dashboard/queue`
Visualizar fila de espera.

**Response:**
```json
{
  "queue": [
    {
      "position": 1,
      "customer_phone": "+5511999999999",
      "customer_name": "Cliente VIP",
      "waiting_since": "2026-02-01T10:00:00Z",
      "estimated_wait_minutes": 5,
      "priority": "high"
    }
  ],
  "total_in_queue": 12,
  "avg_wait_time_minutes": 8
}
```

---

### Health Check (`/health`)

#### GET `/health`
Verificar status da aplicação.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-02-01T10:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "sqlserver": "healthy",
    "whatsapp_api": "healthy"
  }
}
```

---

## 🔄 WebSocket

### Conexão

```javascript
const ws = new WebSocket('wss://api.seudominio.com/ws/chat?token=JWT_TOKEN');

ws.onopen = () => {
  console.log('Conectado!');
  
  // Entrar em uma sala de conversa
  ws.send(JSON.stringify({
    type: 'join_conversation',
    conversation_id: '550e8400-e29b-41d4-a716-446655440000'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Mensagem recebida:', data);
};
```

### Eventos

#### Cliente → Servidor

| Evento | Descrição |
|--------|-----------|
| `join_conversation` | Entrar em uma conversa |
| `leave_conversation` | Sair de uma conversa |
| `send_message` | Enviar mensagem |
| `typing_start` | Indicar que está digitando |
| `typing_stop` | Parar indicador de digitação |
| `ping` | Keep-alive |

#### Servidor → Cliente

| Evento | Descrição |
|--------|-----------|
| `new_message` | Nova mensagem recebida |
| `message_status` | Atualização de status (enviado/entregue/lido) |
| `agent_typing` | Atendente está digitando |
| `conversation_assigned` | Conversa foi atribuída |
| `conversation_closed` | Conversa foi encerrada |
| `queue_update` | Atualização da posição na fila |
| `pong` | Resposta ao ping |

### Formato das Mensagens

```json
{
  "type": "send_message",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Olá, como posso ajudar?",
  "message_type": "text"
}
```

---

## ⚠️ Códigos de Erro

| Código | Descrição |
|--------|-----------|
| `400` | Bad Request - Dados inválidos |
| `401` | Unauthorized - Token ausente ou inválido |
| `403` | Forbidden - Sem permissão para o recurso |
| `404` | Not Found - Recurso não encontrado |
| `429` | Too Many Requests - Rate limit excedido |
| `500` | Internal Server Error - Erro no servidor |

### Formato de Erro

```json
{
  "detail": "Mensagem de erro descritiva",
  "error_code": "VALIDATION_ERROR",
  "field": "email"
}
```

---

## 🔒 Rate Limiting

| Endpoint | Limite | Janela |
|----------|--------|--------|
| `POST /auth/login` | 5 req | 15 min |
| `POST /auth/register` | 3 req | 1 hora |
| `POST /whatsapp/send` | 100 req | 1 min |
| Outros endpoints | 100 req | 1 min |

**Headers de Rate Limit:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706788800
```

---

## 📊 Métricas (Prometheus)

Endpoint: `GET /metrics`

Métricas disponíveis:
- `http_requests_total` - Total de requisições HTTP
- `http_request_duration_seconds` - Latência das requisições
- `websocket_connections_active` - Conexões WebSocket ativas
- `conversations_active_total` - Conversas em andamento
- `messages_sent_total` - Mensagens enviadas
- `chatbot_responses_total` - Respostas do chatbot

---

## 🧪 Testando a API

### Com cURL

```bash
# Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@email.com", "password": "admin123"}' \
  | jq -r '.access_token')

# Listar conversas
curl -X GET "http://localhost:8000/api/v1/conversations" \
  -H "Authorization: Bearer $TOKEN"

# Enviar mensagem WhatsApp
curl -X POST "http://localhost:8000/api/v1/whatsapp/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to": "+5511999999999", "type": "text", "content": "Teste"}'
```

### Com Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "admin@email.com",
    "password": "admin123"
})
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Listar conversas
conversations = requests.get(f"{BASE_URL}/conversations", headers=headers)
print(conversations.json())

# Enviar mensagem
message = requests.post(
    f"{BASE_URL}/whatsapp/send",
    headers=headers,
    json={"to": "+5511999999999", "type": "text", "content": "Olá!"}
)
print(message.json())
```

---

## 📝 Changelog

### v2.0.0 (2026-02-01)
- ✅ Integração WhatsApp Business API (Meta Cloud)
- ✅ Chatbot com Google Gemini AI
- ✅ WebSocket para tempo real
- ✅ SQL Server para autenticação
- ✅ Rate limiting e proteção DDoS
- ✅ Security headers (HSTS, CSP, etc.)

### v1.0.0 (2025-12-01)
- Release inicial
