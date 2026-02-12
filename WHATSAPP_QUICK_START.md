# 🚀 WhatsApp - Guia Rápido

## ✅ Status Atual

O serviço WhatsApp está **RODANDO** e **CONECTADO**!

- 📱 Número: **+5584889868**
- 👤 Nome: **Anjo**
- 📲 Plataforma: **Android**
- ✅ Status: **Conectado e pronto para uso**

## 🎯 Como Usar

### 1. Acessar a Interface

Abra no navegador:
```
http://localhost:8000/whatsapp
```

### 2. Verificar Conexão

A página mostrará automaticamente:
- ✅ **Se conectado**: Ícone verde do WhatsApp com suas informações
- ⏳ **Se desconectado**: QR Code para escanear

### 3. Enviar Mensagens

#### Via Interface Web (em breve)
A interface de envio será adicionada na página `/whatsapp`

#### Via API REST

**Endpoint:** `POST /api/v1/whatsapp/send-message-web`

**Exemplo Python:**
```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/whatsapp/send-message-web',
    params={
        'phone': '5511999999999',  # Número com código do país
        'message': 'Olá! Esta é uma mensagem de teste.'
    }
)

print(response.json())
```

**Exemplo cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/whatsapp/send-message-web?phone=5511999999999&message=Olá!"
```

**Exemplo JavaScript:**
```javascript
fetch('/api/v1/whatsapp/send-message-web?phone=5511999999999&message=Olá!', {
    method: 'POST'
})
.then(r => r.json())
.then(data => console.log(data));
```

### 4. Gerenciar Conexão

**Desconectar:**
- Clique no botão "Desconectar" na página `/whatsapp`
- Ou via API: `POST /api/v1/whatsapp/disconnect`

**Reconectar:**
- Clique no botão "Atualizar Status"
- Ou via API: `POST /api/v1/whatsapp/reconnect`

## 🔧 Comandos Úteis

### Verificar se o serviço está rodando
```bash
curl http://localhost:3001/status
```

### Ver logs do serviço
O serviço está rodando em background. Para ver os logs, use o Kiro para verificar o processo.

### Parar o serviço
Use o Kiro para parar o processo do Node.js (processId: 6)

### Reiniciar o serviço
```bash
cd whatsapp-service
node server.js
```

## 📊 Endpoints Disponíveis

### Python Backend (porta 8000)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/whatsapp/qr-code` | Obter QR Code ou status |
| POST | `/api/v1/whatsapp/send-message-web` | Enviar mensagem |
| POST | `/api/v1/whatsapp/disconnect` | Desconectar WhatsApp |
| POST | `/api/v1/whatsapp/reconnect` | Reconectar WhatsApp |
| GET | `/api/v1/whatsapp/status` | Status do serviço |

### Node.js Service (porta 3001)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/status` | Status do serviço |
| GET | `/qr-code` | QR Code real do WhatsApp |
| POST | `/send-message` | Enviar mensagem (direto) |
| POST | `/disconnect` | Desconectar |
| POST | `/reconnect` | Reconectar |

## 🎉 Pronto para Usar!

Seu WhatsApp Web está conectado e funcionando. Você pode:

1. ✅ Enviar mensagens via API
2. ✅ Verificar status da conexão
3. ✅ Gerenciar a conexão (desconectar/reconectar)
4. ✅ Ver informações da conta conectada

## 💡 Dicas

- A sessão fica salva em `.wwebjs_auth/` - não precisa escanear QR Code toda vez
- Mantenha o serviço Node.js rodando para o WhatsApp funcionar
- Use "Manter-me conectado" ao escanear o QR Code
- Em produção, use PM2 para manter o serviço sempre ativo

## 🐛 Problemas?

**Erro: "Serviço WhatsApp não está rodando"**
- Execute: `cd whatsapp-service && node server.js`

**WhatsApp desconectou**
- Clique em "Reconectar" na página `/whatsapp`
- Escaneie o novo QR Code

**Mensagem não enviada**
- Verifique se o número está no formato correto: `5511999999999`
- Verifique se o número está registrado no WhatsApp
- Veja os logs do serviço Node.js

## 📞 Teste Rápido

```bash
# Testar envio de mensagem
curl -X POST "http://localhost:8000/api/v1/whatsapp/send-message-web?phone=SEU_NUMERO&message=Teste"
```

Substitua `SEU_NUMERO` pelo seu número com código do país (ex: 5584889868).
