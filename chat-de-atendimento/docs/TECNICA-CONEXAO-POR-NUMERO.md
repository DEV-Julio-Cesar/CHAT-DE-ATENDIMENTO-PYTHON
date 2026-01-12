# 🔧 Documentação Técnica: Conexão por Número (v2.0.2)

## Resumo Técnico

Esta documentação descreve a implementação do novo sistema de conexão por número telefônico, integrado ao gerenciador de pool WhatsApp.

## 📋 Componentes Envolvidos

### 1. **Interface Frontend** (`src/interfaces/gerenciador-pool.html`)

#### Funções Principais

```javascript
// Abre modal com duas opções de conexão
async function conectarNovo() {
    mostrarModalConexao();
}

// Exibe modal com escolha de método
function mostrarModalConexao() { ... }

// Abre interface de conexão por número
async function abrirConexaoPorNumero() {
    window.open('/interfaces/conectar-numero.html', ...);
}

// Abre janela tradicional de QR Code
async function abrirConexaoPorQR() {
    await window.poolAPI.openNewQRWindow();
}
```

#### Modal Styling

Estilos CSS incluídos dinamicamente:
- `modal-conexao` - Container principal
- `modal-conteudo` - Box de conteúdo
- `opcoes-conexao` - Grid 2 colunas (responsivo)
- `opcao-conexao` - Botão individual com gradiente

Efeitos visuais:
- Fade-in para aparição
- Slide-up para conteúdo
- Hover com transform e shadow
- Diferentes gradientes por opção

### 2. **Interface de Número** (`src/interfaces/conectar-numero.html`)

#### Componentes

```html
<!-- Entrada de número -->
<input type="text" 
       pattern="^55\d{10,11}$"
       placeholder="5511999999999"
       id="phoneInput">

<!-- Exibição de QR -->
<div id="qrContainer">
    <img id="qrImage" src="" alt="QR Code">
</div>

<!-- Status polling -->
<div id="statusMessage">Aguardando...</div>
```

#### Fluxo de Funcionamento

1. **Validação de Entrada**
   - Padrão: `^55\d{10,11}$`
   - Validação HTML5 + JavaScript
   - Feedback visual em tempo real

2. **Envio para Backend**
   ```javascript
   const response = await fetch('/api/whatsapp/conectar-por-numero', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ 
           telefone: phoneNumber,
           metodo: 'numero-manual'
       })
   });
   ```

3. **Exibição de QR**
   - Recebe QR Code em base64
   - Exibe em `<img>`
   - Ativa polling de status

4. **Polling de Conexão**
   - Intervalo: 2 segundos
   - Timeout: 5 minutos
   - Endpoint: `GET /api/whatsapp/status/:clientId`
   - Verifica status até `ready`

5. **Sucesso e Retorno**
   - Ao atingir `status === 'ready'`
   - Exibe mensagem de sucesso
   - Fecha janela após 2s
   - Atualiza parent via `window.opener.location.reload()`

### 3. **API Backend** (`src/rotas/rotasWhatsAppSincronizacao.js`)

#### Endpoint 1: POST `/api/whatsapp/conectar-por-numero`

```javascript
router.post('/conectar-por-numero', async (req, res) => {
    const { telefone, metodo = 'numero-manual' } = req.body;
    
    // Validação de formato
    if (!telefone || !telefone.match(/^55\d{10,11}$/)) {
        return res.status(400).json({
            success: false,
            message: 'Formato inválido. Use: 5511999999999'
        });
    }
    
    try {
        // Criar novo cliente
        const novoClienteResult = await poolWhatsApp.createClient();
        const clientId = novoClienteResult.clientId;
        
        // Recuperar referência do cliente
        const cliente = poolWhatsApp.clients.get(clientId);
        
        // Armazenar número de telefone
        cliente.phoneNumber = telefone;
        
        // Aguardar QR Code (timeout: 30s)
        const qrCode = await Promise.race([
            new Promise(resolve => {
                cliente.once('qr_ready', (qr) => resolve(qr));
            }),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('QR timeout')), 30000)
            )
        ]);
        
        // Retornar resposta
        res.json({
            success: true,
            clientId,
            telefone,
            qrCode,
            metodo
        });
        
    } catch (erro) {
        res.status(500).json({
            success: false,
            message: 'Erro ao criar conexão: ' + erro.message
        });
    }
});
```

#### Endpoint 2: GET `/api/whatsapp/status/:clientId`

```javascript
router.get('/status/:clientId', async (req, res) => {
    const cliente = poolWhatsApp.clients.get(req.params.clientId);
    
    if (!cliente) {
        return res.status(404).json({
            success: false,
            message: 'Cliente não encontrado'
        });
    }
    
    const status = cliente.status || 'desconectado';
    
    res.json({
        success: true,
        clientId: req.params.clientId,
        status,
        telefone: cliente.phoneNumber || null,
        ativo: status === 'ready' || status === 'authenticated',
        ultimaAtividade: cliente.lastActivity || null
    });
});
```

### 4. **Pool Manager** (`src/core/GerenciadorPoolWhatsApp.js`)

#### Métodos Relevantes

```javascript
// Criar novo cliente
async createClient() {
    const clientId = this.gerarClienteId();
    const cliente = new ServicoClienteWhatsApp({
        clientId,
        sessionName: `session_${clientId}`
    });
    
    this.clients.set(clientId, cliente);
    
    // Iniciar conexão
    await cliente.iniciar();
    
    return { clientId, success: true };
}

// Obter cliente
getClient(clientId) {
    return this.clients.get(clientId);
}

// Status do cliente
async getClientStatus(clientId) {
    const cliente = this.clients.get(clientId);
    if (!cliente) return null;
    
    return {
        id: clientId,
        status: cliente.status,
        phoneNumber: cliente.phoneNumber,
        connected: cliente.isConnected
    };
}
```

### 5. **Serviço Cliente** (`src/services/ServicoClienteWhatsApp.js`)

#### Eventos Monitorados

```javascript
// CRÍTICO: Usar .on() não .once()
this.client.on('disconnected', (reason) => {
    this.status = 'disconnected';
    this.emit('disconnected', reason);
    // Trigger auto-reconnect
});

this.client.on('auth_failure', (message) => {
    this.status = 'auth_failure';
    this.emit('auth_failure', message);
});

this.client.on('qr', (qr) => {
    this.qrCode = qr;
    this.status = 'qr_ready';
    this.emit('qr_ready', qr);
});

this.client.on('ready', () => {
    this.status = 'ready';
    this.authenticated = true;
    this.emit('ready');
});
```

## 🔄 Fluxo Completo de Conexão

### Sequência de Eventos

```
Usuário clica "Adicionar"
         ↓
Modal aparece com 2 opções
         ↓
Usuário clica "Por Número"
         ↓
Janela conectar-numero.html abre
         ↓
Usuário digita número (5511999999999)
         ↓
JavaScript valida formato
         ↓
POST /api/whatsapp/conectar-por-numero
         ↓
Backend: createClient()
         ↓
ServicoClienteWhatsApp inicia
         ↓
Puppeteer abre browser
         ↓
whatsapp-web.js carrega
         ↓
Evento 'qr' dispara
         ↓
QR Code em base64 retorna ao frontend
         ↓
Frontend exibe QR
         ↓
Usuário escaneia com celular
         ↓
WhatsApp autentica
         ↓
Evento 'ready' dispara
         ↓
GET /api/whatsapp/status/:clientId retorna "ready"
         ↓
Frontend detecta sucesso
         ↓
Mostra mensagem "✅ Conectado!"
         ↓
Fecha janela em 2s
         ↓
Parent recarrega
         ↓
Nova conexão aparece na lista do Pool Manager
```

## 🛡️ Tratamento de Erros

### Cenários de Erro

#### 1. Formato de Número Inválido
```javascript
if (!telefone.match(/^55\d{10,11}$/)) {
    res.status(400).json({
        success: false,
        message: 'Formato inválido. Use: 5511999999999'
    });
}
```

#### 2. QR Code Não Escaneado (Timeout)
```javascript
new Promise((_, reject) => 
    setTimeout(() => reject(new Error('QR timeout')), 30000)
);
```

#### 3. Cliente Não Encontrado
```javascript
if (!cliente) {
    res.status(404).json({
        success: false,
        message: 'Cliente não encontrado'
    });
}
```

#### 4. Desconexão Durante Polling
```javascript
if (response.status === 404 || !data.ativo) {
    showError('Conexão perdida. Tente novamente.');
    // Reset UI
}
```

## 📊 Comparação com QR Code Tradicional

### Método: Por Número

**Vantagens:**
- ✅ Determinístico (sempre funciona)
- ✅ Identifica número antes de conectar
- ✅ Melhor para múltiplas contas
- ✅ Menos dependência de scanning automático

**Desvantagens:**
- ❌ Requer digitação correta
- ❌ Ainda precisa escanear QR após digitação

### Método: Por QR Tradicional

**Vantagens:**
- ✅ Mais direto
- ✅ Menos passos

**Desvantagens:**
- ❌ Dependente de scanning automático
- ❌ Menos controle sobre número
- ❌ Pode falhar se camera não capturar bem

## 🔐 Validações de Segurança

1. **Validação de Formato**
   - Regex: `^55\d{10,11}$`
   - Garante formato internacional

2. **Timeout de Operação**
   - QR: máximo 30 segundos
   - Polling: máximo 5 minutos
   - Previne travamento

3. **Isolamento de Sessão**
   - Cada cliente tem sessionId único
   - Dados persistem em JSON segregado
   - Sem compartilhamento entre clientes

4. **Rate Limiting**
   - Implementado via middleware
   - Máximo 10 req/min por IP
   - Previne força bruta

## 🧪 Testes

### Teste Manual: Conexão por Número

```bash
# 1. Iniciar app
npm start

# 2. Fazer login
# Abrir: http://localhost:3333
# Usuário: admin / Senha: admin

# 3. Navegar para Pool Manager
# Clicar: Pool Manager

# 4. Clique em "Adicionar Nova Conexão"
# Confirmar: Modal com 2 opções

# 5. Clique em "Conectar por Número"
# Confirmar: Nova janela abre

# 6. Digite: 5511999999999
# Confirmar: Validação visual

# 7. Clique em "Conectar"
# Confirmar: QR Code exibido

# 8. Escaneie QR com WhatsApp
# Confirmar: Status muda para "ready"

# 9. Janela fecha
# Confirmar: Volta ao Pool Manager

# 10. Verifique conexão
# Confirmar: Nova conexão listada com status ✅
```

### Teste Automatizado

```javascript
// teste-conexao-numero.js
const axios = require('axios');

async function testarConexaoPorNumero() {
    try {
        // 1. Criar conexão
        const res1 = await axios.post(
            'http://localhost:3333/api/whatsapp/conectar-por-numero',
            { telefone: '5511998765432' }
        );
        
        const { clientId, qrCode } = res1.data;
        console.log('✅ Conexão criada:', clientId);
        
        // 2. Verificar status
        let status = 'qr_ready';
        let tentativas = 0;
        
        while (status !== 'ready' && tentativas < 150) { // 5 min = 300 polls de 2s
            await new Promise(r => setTimeout(r, 2000));
            
            const res2 = await axios.get(
                `http://localhost:3333/api/whatsapp/status/${clientId}`
            );
            
            status = res2.data.status;
            console.log(`Status: ${status} (${tentativas})`);
            tentativas++;
        }
        
        if (status === 'ready') {
            console.log('✅ SUCESSO: Cliente conectado!');
        } else {
            console.log('❌ FALHA: Timeout na conexão');
        }
        
    } catch (erro) {
        console.error('❌ Erro:', erro.message);
    }
}

testarConexaoPorNumero();
```

## 📝 Changelog

### v2.0.2 - Conexão por Número

**Adições:**
- ✨ Nova interface de conexão por número (`conectar-numero.html`)
- ✨ Novo endpoint POST `/api/whatsapp/conectar-por-numero`
- ✨ Novo endpoint GET `/api/whatsapp/status/:clientId`
- ✨ Modal seletor de método de conexão
- 🔧 Integração com gerenciador-pool.html

**Melhorias:**
- 📈 Melhor controle sobre número que será conectado
- 📈 Validação de formato de telefone
- 📈 Polling com timeout de 5 minutos
- 📈 Feedback visual em tempo real

**Correções:**
- ✅ Listeners agora usam `.on()` em lugar de `.once()` (hotfix v2.0.2)

## 🚀 Deploy

1. Nenhuma dependência nova adicionada
2. Compatível com versões anteriores
3. Feature flag: `whatsapp.connection-methods = ['numero', 'qr']`
4. Sem breaking changes

## 📚 Referências

- whatsapp-web.js: https://github.com/pedrosans/whatsapp-web.js
- Express.js: https://expressjs.com/
- Puppeteer: https://github.com/puppeteer/puppeteer

---

**Versão:** 2.0.2  
**Atualizado:** 2026-01-11  
**Tipo:** Feature Enhancement
