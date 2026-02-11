# 🌐 URLs DO SISTEMA - GUIA COMPLETO

## Sistema Rodando em: http://127.0.0.1:8000

---

## 📱 PÁGINAS WEB

### Autenticação
- **Login:** http://127.0.0.1:8000/login
- **Login (Legado):** http://127.0.0.1:8000/login-legacy

### Dashboard e Gestão
- **Dashboard Principal:** http://127.0.0.1:8000/dashboard
- **Chat/Atendimento:** http://127.0.0.1:8000/chat
- **Clientes:** http://127.0.0.1:8000/customers
- **Usuários:** http://127.0.0.1:8000/users
- **Configurações:** http://127.0.0.1:8000/settings

### WhatsApp
- **Configuração WhatsApp:** http://127.0.0.1:8000/whatsapp
- **Campanhas:** http://127.0.0.1:8000/campaigns

### Chatbot
- **Admin Chatbot:** http://127.0.0.1:8000/chatbot-admin

### Mobile PWA
- **App Mobile:** http://127.0.0.1:8000/mobile
- **Offline:** http://127.0.0.1:8000/offline

---

## 📚 DOCUMENTAÇÃO DA API

### Documentação Interativa
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **OpenAPI JSON:** http://127.0.0.1:8000/openapi.json

---

## 🔧 ENDPOINTS DE SISTEMA

### Health & Info
- **Health Check:** http://127.0.0.1:8000/health
- **Info da Aplicação:** http://127.0.0.1:8000/info
- **Raiz:** http://127.0.0.1:8000/

### Métricas
- **Prometheus Metrics:** http://127.0.0.1:8000/metrics
- **Cache Stats:** http://127.0.0.1:8000/cache/stats
- **Compression Stats:** http://127.0.0.1:8000/compression/stats
- **Performance Dashboard:** http://127.0.0.1:8000/performance/dashboard
- **Circuit Breakers:** http://127.0.0.1:8000/circuit-breakers

---

## 🔐 ENDPOINTS DE SEGURANÇA

### Autenticação (API v1)
- **POST** `/api/v1/auth/login` - Login
- **POST** `/api/v1/auth/logout` - Logout
- **POST** `/api/v1/auth/refresh` - Refresh Token
- **GET** `/api/v1/auth/me` - Usuário Atual

### Two-Factor Authentication (2FA)
- **POST** `/api/v1/2fa/setup` - Configurar 2FA
- **POST** `/api/v1/2fa/verify` - Verificar Código
- **POST** `/api/v1/2fa/enable` - Habilitar 2FA
- **POST** `/api/v1/2fa/disable` - Desabilitar 2FA
- **GET** `/api/v1/2fa/status` - Status do 2FA
- **POST** `/api/v1/2fa/regenerate-backup-codes` - Regenerar Códigos

---

## 💬 ENDPOINTS DE CHAT

### Conversas
- **GET** `/api/v1/conversations` - Listar Conversas
- **GET** `/api/v1/conversations/{id}` - Detalhes da Conversa
- **POST** `/api/v1/conversations` - Criar Conversa
- **PUT** `/api/v1/conversations/{id}` - Atualizar Conversa
- **DELETE** `/api/v1/conversations/{id}` - Deletar Conversa

### Mensagens
- **GET** `/api/v1/conversations/{id}/messages` - Mensagens da Conversa
- **POST** `/api/v1/conversations/{id}/messages` - Enviar Mensagem

---

## 📱 ENDPOINTS DE WHATSAPP

### WhatsApp Business API
- **POST** `/api/v1/whatsapp/webhook` - Webhook (receber mensagens)
- **GET** `/api/v1/whatsapp/webhook` - Verificação do Webhook
- **POST** `/api/v1/whatsapp/send` - Enviar Mensagem
- **POST** `/api/v1/whatsapp/send-template` - Enviar Template
- **GET** `/api/v1/whatsapp/templates` - Listar Templates

---

## 🤖 ENDPOINTS DE CHATBOT

### Chatbot AI
- **POST** `/api/v1/chatbot/message` - Enviar Mensagem ao Bot
- **POST** `/api/v1/chatbot/whatsapp/process` - Processar WhatsApp
- **GET** `/api/v1/chatbot/metrics` - Métricas do Bot
- **GET** `/api/v1/chatbot/conversation/{id}` - Histórico
- **DELETE** `/api/v1/chatbot/conversation/{id}` - Limpar Conversa
- **GET** `/api/v1/chatbot/intents` - Listar Intenções
- **GET** `/api/v1/chatbot/quick-replies/{intent}` - Respostas Rápidas

---

## 👥 ENDPOINTS DE USUÁRIOS

### Gestão de Usuários
- **GET** `/api/v1/users` - Listar Usuários
- **GET** `/api/v1/users/{id}` - Detalhes do Usuário
- **POST** `/api/v1/users` - Criar Usuário
- **PUT** `/api/v1/users/{id}` - Atualizar Usuário
- **DELETE** `/api/v1/users/{id}` - Deletar Usuário

---

## 📊 ENDPOINTS DE DASHBOARD

### Analytics
- **GET** `/api/v1/dashboard/stats` - Estatísticas Gerais
- **GET** `/api/v1/dashboard/metrics` - Métricas em Tempo Real
- **GET** `/api/v1/dashboard/reports` - Relatórios

---

## 📢 ENDPOINTS DE CAMPANHAS

### Campanhas de Marketing
- **GET** `/api/v1/campaigns` - Listar Campanhas
- **GET** `/api/v1/campaigns/{id}` - Detalhes da Campanha
- **POST** `/api/v1/campaigns` - Criar Campanha
- **PUT** `/api/v1/campaigns/{id}` - Atualizar Campanha
- **DELETE** `/api/v1/campaigns/{id}` - Deletar Campanha
- **POST** `/api/v1/campaigns/{id}/send` - Enviar Campanha

---

## 🔌 WEBSOCKET

### Comunicação em Tempo Real
- **WS** `/ws/chat/{conversation_id}` - WebSocket de Chat

---

## 📁 ARQUIVOS ESTÁTICOS

### CSS
- `/static/css/style.css` - Estilos principais
- `/static/css/design-system.css` - Design system
- `/static/css/mobile.css` - Estilos mobile

### JavaScript
- `/static/js/chat.js` - Chat JavaScript
- `/static/js/mobile-app.js` - Mobile app

### PWA
- `/static/manifest.json` - Manifest do PWA
- `/static/sw.js` - Service Worker
- `/static/icons/icon-192x192.png` - Ícone 192x192
- `/static/icons/icon-512x512.png` - Ícone 512x512

---

## 🧪 TESTANDO OS ENDPOINTS

### Usando cURL (PowerShell)

```powershell
# Health Check
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing

# Login
$body = @{
    username = "admin@example.com"
    password = "senha123"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://127.0.0.1:8000/api/v1/auth/login `
    -Method POST `
    -Body $body `
    -ContentType "application/json" `
    -UseBasicParsing

# Com Token
$token = "seu-token-aqui"
$headers = @{
    "Authorization" = "Bearer $token"
}

Invoke-WebRequest -Uri http://127.0.0.1:8000/api/v1/auth/me `
    -Headers $headers `
    -UseBasicParsing
```

### Usando Python

```python
import requests

# Health Check
response = requests.get("http://127.0.0.1:8000/health")
print(response.json())

# Login
response = requests.post(
    "http://127.0.0.1:8000/api/v1/auth/login",
    json={
        "username": "admin@example.com",
        "password": "senha123"
    }
)
token = response.json()["access_token"]

# Com Token
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://127.0.0.1:8000/api/v1/auth/me",
    headers=headers
)
print(response.json())
```

---

## 🎯 ATALHOS RÁPIDOS

### Desenvolvimento
```bash
# Iniciar servidor
python -m uvicorn app.main:app --reload

# Testar segurança
python test_all_security_features.py

# Demonstração
python demo_security_features.py

# Gerar chaves
python generate_secrets.py
```

### Abrir no Navegador
```powershell
# Login
Start-Process "http://127.0.0.1:8000/login"

# Dashboard
Start-Process "http://127.0.0.1:8000/dashboard"

# Documentação
Start-Process "http://127.0.0.1:8000/docs"

# Chatbot Admin
Start-Process "http://127.0.0.1:8000/chatbot-admin"
```

---

## 📝 NOTAS IMPORTANTES

1. **Autenticação:** A maioria dos endpoints requer token JWT no header `Authorization: Bearer TOKEN`

2. **CORS:** Configurado para aceitar requisições de:
   - http://localhost:3000
   - http://localhost:8000
   - http://127.0.0.1:8000

3. **Rate Limiting:** 
   - Login: 5 tentativas em 15 minutos
   - API Geral: 100 requisições por minuto

4. **Security Headers:** Todos os endpoints incluem headers de segurança (CSP, X-Frame-Options, etc)

5. **2FA:** Quando habilitado, login requer código adicional de 6 dígitos

---

**Última Atualização:** 10/02/2026  
**Versão:** 2.0.0  
**Status:** ✅ PRODUÇÃO READY
