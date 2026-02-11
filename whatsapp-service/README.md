# WhatsApp Service - CIANET

Serviço Node.js para integração com WhatsApp Web usando `whatsapp-web.js`.

## Instalação

```bash
cd whatsapp-service
npm install
```

## Executar

```bash
npm start
```

Ou em modo desenvolvimento:

```bash
npm run dev
```

## Endpoints

### GET /status
Verifica o status do serviço

**Resposta:**
```json
{
  "success": true,
  "service": "WhatsApp Web Service",
  "status": "connected",
  "hasQrCode": false,
  "clientInfo": {
    "number": "5511999999999",
    "name": "Nome do Usuário",
    "platform": "android"
  }
}
```

### GET /qr-code
Obtém o QR Code para conectar ao WhatsApp

**Resposta (quando não conectado):**
```json
{
  "success": true,
  "qr_code": "data:image/png;base64,iVBORw0KG...",
  "message": "Escaneie o QR Code com seu WhatsApp"
}
```

**Resposta (quando já conectado):**
```json
{
  "success": true,
  "connected": true,
  "message": "WhatsApp já está conectado",
  "clientInfo": {...}
}
```

### POST /send-message
Envia uma mensagem via WhatsApp

**Body:**
```json
{
  "phone": "5511999999999",
  "message": "Olá! Esta é uma mensagem de teste."
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Mensagem enviada com sucesso",
  "to": "5511999999999"
}
```

### POST /disconnect
Desconecta o WhatsApp

### POST /reconnect
Reconecta o WhatsApp (gera novo QR Code)

## Porta

O serviço roda na porta **3001** por padrão.

## Integração com Python

O backend Python deve fazer requisições para `http://localhost:3001` para obter o QR Code e enviar mensagens.
