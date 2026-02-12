# 📱 Configuração WhatsApp Web - CIANET

Este guia explica como configurar o WhatsApp Web REAL no sistema CIANET.

## 🎯 Visão Geral

O sistema usa **whatsapp-web.js** (Node.js) para gerar QR Codes VÁLIDOS do WhatsApp Web.

**Arquitetura:**
```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Frontend HTML  │ ───> │  Backend Python  │ ───> │ Service Node.js │
│  (Navegador)    │      │  (FastAPI)       │      │ (whatsapp-web)  │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                                            │
                                                            ▼
                                                    ┌─────────────────┐
                                                    │  WhatsApp Web   │
                                                    └─────────────────┘
```

## 📋 Pré-requisitos

### 1. Node.js
Baixe e instale o Node.js (versão 16 ou superior):
- **Windows**: https://nodejs.org/
- Verifique a instalação: `node --version`

### 2. Python (já instalado)
- Python 3.8+ com FastAPI

## 🚀 Instalação

### Passo 1: Instalar Dependências Node.js

```bash
cd whatsapp-service
npm install
```

Isso instalará:
- `whatsapp-web.js` - Cliente WhatsApp Web
- `qrcode` - Gerador de QR Code
- `express` - Servidor HTTP
- `cors` - Suporte CORS

### Passo 2: Instalar Dependência Python

```bash
pip install httpx
```

## ▶️ Executar

### Opção 1: Script Automático (Windows)

```bash
start_whatsapp_service.bat
```

### Opção 2: Manual

```bash
cd whatsapp-service
npm start
```

O serviço estará disponível em: **http://localhost:3001**

## 🔧 Como Usar

### 1. Iniciar o Serviço WhatsApp

Execute o serviço Node.js (porta 3001):
```bash
npm start
```

Você verá:
```
🚀 WhatsApp Service rodando na porta 3001
📡 API disponível em http://localhost:3001
🚀 Inicializando cliente WhatsApp...
📱 QR Code gerado!
```

### 2. Iniciar o Backend Python

Em outro terminal:
```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Acessar a Interface Web

Abra o navegador:
```
http://localhost:8000/whatsapp
```

### 4. Escanear QR Code

1. O QR Code será gerado automaticamente na página
2. Abra o WhatsApp no celular
3. Vá em **Mais opções (⋮)** > **Aparelhos conectados**
4. Toque em **Conectar um aparelho**
5. Escaneie o QR Code da tela

### 5. Aguardar Conexão

Quando conectado, você verá:
```
✅ Cliente autenticado!
✅ Cliente WhatsApp pronto!
📞 Conectado como: [seu número]
```

## 🔌 Endpoints da API

### Node.js Service (porta 3001)

#### GET /status
Verifica status do serviço
```json
{
  "success": true,
  "status": "connected",
  "clientInfo": {
    "number": "5511999999999",
    "name": "Nome"
  }
}
```

#### GET /qr-code
Obtém QR Code para conectar
```json
{
  "success": true,
  "qr_code": "data:image/png;base64,..."
}
```

#### POST /send-message
Envia mensagem
```json
{
  "phone": "5511999999999",
  "message": "Olá!"
}
```

### Python Backend (porta 8000)

#### GET /api/v1/whatsapp/qr-code
Proxy para obter QR Code do serviço Node.js

#### POST /api/v1/whatsapp/send-message-web
Envia mensagem via WhatsApp Web

## 🐛 Troubleshooting

### Erro: "Serviço WhatsApp não está rodando"

**Solução:**
1. Verifique se o Node.js está instalado: `node --version`
2. Inicie o serviço: `cd whatsapp-service && npm start`
3. Verifique se está rodando na porta 3001

### Erro: "QR Code inválido"

**Causa:** Você estava usando o QR Code genérico (antigo)

**Solução:** 
1. Certifique-se de que o serviço Node.js está rodando
2. O novo QR Code é REAL e válido para WhatsApp
3. Recarregue a página `/whatsapp`

### Erro: "Cannot find module 'whatsapp-web.js'"

**Solução:**
```bash
cd whatsapp-service
npm install
```

### QR Code não aparece

**Solução:**
1. Abra o console do navegador (F12)
2. Verifique erros de conexão
3. Teste o endpoint: `http://localhost:3001/status`
4. Aguarde 5-10 segundos após iniciar o serviço

### WhatsApp desconecta sozinho

**Solução:**
1. Marque "Manter-me conectado" ao escanear o QR Code
2. Não feche o serviço Node.js
3. Mantenha o servidor rodando 24/7

## 📁 Estrutura de Arquivos

```
whatsapp-service/
├── server.js           # Servidor Node.js principal
├── package.json        # Dependências Node.js
├── README.md          # Documentação do serviço
└── .wwebjs_auth/      # Sessão salva (gerado automaticamente)

app/services/
└── whatsapp_web_qr.py # Cliente Python (proxy)

app/api/endpoints/
└── whatsapp_python.py # Endpoints REST
```

## 🔐 Segurança

- A sessão é salva em `.wwebjs_auth/` (não commitar no Git)
- Use HTTPS em produção
- Implemente autenticação nos endpoints
- Limite rate de envio de mensagens

## 🚀 Produção

### Deploy com PM2 (recomendado)

```bash
npm install -g pm2
cd whatsapp-service
pm2 start server.js --name whatsapp-service
pm2 save
pm2 startup
```

### Docker (opcional)

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY whatsapp-service/package*.json ./
RUN npm install
COPY whatsapp-service/ ./
CMD ["node", "server.js"]
```

## 📞 Suporte

- Documentação whatsapp-web.js: https://wwebjs.dev/
- Issues: https://github.com/pedroslopez/whatsapp-web.js/issues

## ✅ Checklist de Instalação

- [ ] Node.js instalado (v16+)
- [ ] Dependências instaladas (`npm install`)
- [ ] Serviço Node.js rodando (porta 3001)
- [ ] Backend Python rodando (porta 8000)
- [ ] QR Code aparecendo na página `/whatsapp`
- [ ] WhatsApp conectado com sucesso
- [ ] Teste de envio de mensagem funcionando

## 🎉 Pronto!

Agora você tem um WhatsApp Web REAL integrado ao sistema CIANET!
