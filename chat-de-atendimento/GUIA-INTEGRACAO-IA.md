# 🔗 GUIA DE INTEGRAÇÃO - IA Humanizada

Instruções específicas para integrar em diferentes partes da sua aplicação.

## 🎯 INTEGRAÇÃO POR CONTEXTO

### 1️⃣ INTEGRAÇÃO COM WhatsApp (Mais Comum)

Se você usar `whatsapp-web.js`:

```javascript
// Em src/whatsapp/seu-arquivo-principal.js

const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');
const client = require('whatsapp-web.js').Client;

// Instanciar serviço
const servicoIA = new ServicoIAHumanizada({
    servico: 'Chat WhatsApp',
    empresa: 'Seu Negócio'
});

// Quando receber mensagem
client.on('message', async (msg) => {
    try {
        // Extrair ID do cliente (remover @c.us)
        const idCliente = msg.from.split('@')[0];
        const nomeCliente = msg.author || msg.from;
        
        // Detectar tipo de mensagem (opcional)
        let tipoSolicitacao = 'duvida';
        if (msg.body.toLowerCase().includes('problema')) tipoSolicitacao = 'problema';
        if (msg.body.toLowerCase().includes('oi')) tipoSolicitacao = 'saudacao';
        
        // Processar com IA
        const resultado = await servicoIA.procesarMensagemCliente(
            msg.body,
            idCliente,
            tipoSolicitacao,
            { nome: nomeCliente }
        );
        
        // Responder cliente
        if (resultado.success) {
            await msg.reply(resultado.resposta);
        } else {
            // Fallback
            await msg.reply('Um atendente irá ajudá-lo em breve!');
        }
        
    } catch (erro) {
        console.error('Erro ao processar mensagem WhatsApp:', erro);
        msg.reply('Desculpe, ocorreu um erro. Tentaremos novamente em breve.');
    }
});
```

---

### 2️⃣ INTEGRAÇÃO COM EXPRESS/API REST

Use a rota pronta que já criei:

```javascript
// Em main.js ou app.js

const express = require('express');
const app = express();

// Middleware
app.use(express.json());

// Importar rota IA
const rotasChat = require('./src/rotas/chat-ia-integracao');

// Registrar rotas
app.use('/api', rotasChat);

// Iniciar servidor
app.listen(3000, () => {
    console.log('Servidor rodando em http://localhost:3000');
    console.log('Chat API em http://localhost:3000/api/chat/saude');
});
```

Agora você tem estes endpoints:

```
POST   /api/chat/mensagem
POST   /api/chat/problema
POST   /api/chat/insatisfacao
POST   /api/chat/pergunta-diagnostica
POST   /api/chat/feedback
GET    /api/chat/:idCliente/info
DELETE /api/chat/:idCliente/limpar
```

---

### 3️⃣ INTEGRAÇÃO COM FRONTEND (JavaScript)

Para usar em página web:

```javascript
// Em seu arquivo HTML/JS

async function enviarMensagem(texto, nomeCliente) {
    const idCliente = localStorage.getItem('clienteId') || 'anonimo_' + Date.now();
    
    try {
        const resposta = await fetch('http://localhost:3000/api/chat/mensagem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mensagem: texto,
                idCliente: idCliente,
                nomeCliente: nomeCliente,
                tipoSolicitacao: 'duvida'
            })
        });
        
        const dados = await resposta.json();
        
        if (dados.success) {
            exibirMensagem(dados.resposta, 'bot');
            salvarClienteId(idCliente);
        } else {
            exibirMensagem(
                'Desculpe, houve um erro. Tentaremos novamente.',
                'bot'
            );
        }
        
    } catch (erro) {
        console.error('Erro:', erro);
        exibirMensagem('Erro de conexão com o servidor.', 'bot');
    }
}

function salvarClienteId(id) {
    localStorage.setItem('clienteId', id);
}

function exibirMensagem(texto, origem) {
    const chat = document.getElementById('chat');
    const div = document.createElement('div');
    div.className = 'mensagem ' + origem;
    div.textContent = texto;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}
```

---

### 4️⃣ INTEGRAÇÃO COM SERVIDOR WEBSOCKET

Para chat em tempo real:

```javascript
// Em src/whatsapp/servidor-websocket.js

const WebSocket = require('ws');
const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');

const wss = new WebSocket.Server({ port: 8080 });
const servicoIA = new ServicoIAHumanizada();

wss.on('connection', (ws) => {
    console.log('Cliente conectado');
    
    ws.on('message', async (mensagem) => {
        try {
            const dados = JSON.parse(mensagem);
            
            const resultado = await servicoIA.procesarMensagemCliente(
                dados.texto,
                dados.idCliente,
                dados.tipo || 'duvida',
                { nome: dados.nome }
            );
            
            // Enviar resposta ao cliente
            ws.send(JSON.stringify({
                tipo: 'resposta',
                resposta: resultado.resposta,
                sucesso: resultado.success
            }));
            
        } catch (erro) {
            ws.send(JSON.stringify({
                tipo: 'erro',
                mensagem: 'Erro ao processar mensagem'
            }));
        }
    });
    
    ws.on('close', () => {
        console.log('Cliente desconectado');
    });
});

console.log('WebSocket server rodando em ws://localhost:8080');
```

Cliente WebSocket:

```javascript
// Frontend
const ws = new WebSocket('ws://localhost:8080');

function enviarPeloWebSocket(texto, idCliente, nome) {
    ws.send(JSON.stringify({
        texto: texto,
        idCliente: idCliente,
        nome: nome,
        tipo: 'duvida'
    }));
}

ws.onmessage = (evento) => {
    const dados = JSON.parse(evento.data);
    if (dados.tipo === 'resposta') {
        exibirResposta(dados.resposta);
    }
};
```

---

### 5️⃣ INTEGRAÇÃO COM BANCO DE DADOS

Para persistir conversas:

```javascript
// Em seu controller de chat

const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');
const Conversa = require('../models/Conversa'); // seu modelo

const servicoIA = new ServicoIAHumanizada();

async function processarMensagemComBD(mensagem, idCliente, idUsuario) {
    // Processar com IA
    const resultado = await servicoIA.procesarMensagemCliente(
        mensagem,
        idCliente,
        'duvida',
        { nome: idUsuario }
    );
    
    // Salvar em BD
    await Conversa.create({
        idCliente: idCliente,
        idUsuario: idUsuario,
        mensagemCliente: mensagem,
        respostaBot: resultado.resposta,
        tipo: resultado.tipo,
        sucesso: resultado.success,
        timestamp: new Date()
    });
    
    return resultado;
}

// Depois recuperar histórico
async function obterHistoricoCliente(idCliente) {
    const conversas = await Conversa.find({ idCliente })
        .sort({ timestamp: 1 });
    
    return conversas.map(c => ({
        role: 'user',
        mensagem: c.mensagemCliente,
        timestamp: c.timestamp
    }, {
        role: 'bot',
        mensagem: c.respostaBot,
        timestamp: c.timestamp
    }));
}
```

---

### 6️⃣ INTEGRAÇÃO COM MULHER HANDLERS (Múltiplas Fontes)

Para atender cliente via múltiplos canais:

```javascript
// Em um arquivo centralizador

const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');

class GerenciadorCanaisMultiplos {
    constructor() {
        this.servicoIA = new ServicoIAHumanizada();
    }
    
    // WhatsApp
    async procesarWhatsApp(msg) {
        const idCliente = msg.from.split('@')[0];
        const resultado = await this.servicoIA.procesarMensagemCliente(
            msg.body,
            idCliente,
            this._detectarTipo(msg.body),
            { canal: 'whatsapp', nome: msg.author }
        );
        return resultado;
    }
    
    // Email
    async procesarEmail(email) {
        const resultado = await this.servicoIA.procesarMensagemCliente(
            email.corpo,
            email.de,
            'duvida',
            { canal: 'email', nome: email.remetente }
        );
        return resultado;
    }
    
    // Chat Web
    async procesarChat(msg, idCliente, nome) {
        const resultado = await this.servicoIA.procesarMensagemCliente(
            msg,
            idCliente,
            'duvida',
            { canal: 'web', nome: nome }
        );
        return resultado;
    }
    
    // Telegram
    async procesarTelegram(msg, userId) {
        const resultado = await this.servicoIA.procesarMensagemCliente(
            msg.text,
            'tg_' + userId,
            this._detectarTipo(msg.text),
            { canal: 'telegram' }
        );
        return resultado;
    }
    
    _detectarTipo(texto) {
        if (texto.includes('problema')) return 'problema';
        if (texto.includes('oi') || texto.includes('ola')) return 'saudacao';
        if (texto.includes('obrigado')) return 'feedback';
        return 'duvida';
    }
}

// Usar
const gerenciador = new GerenciadorCanaisMultiplos();

// WhatsApp
client.on('message', async (msg) => {
    const resultado = await gerenciador.procesarWhatsApp(msg);
    msg.reply(resultado.resposta);
});

// Web
app.post('/chat', async (req, res) => {
    const resultado = await gerenciador.procesarChat(
        req.body.mensagem,
        req.body.idCliente,
        req.body.nome
    );
    res.json({ resposta: resultado.resposta });
});
```

---

### 7️⃣ INTEGRAÇÃO COM LOGGING/MONITORAMENTO

Para rastrear e analisar:

```javascript
// Em um middleware ou serviço

const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');
const logger = require('../infraestrutura/logger');

class ServicoIAComMonitoramento {
    constructor() {
        this.servicoIA = new ServicoIAHumanizada();
    }
    
    async procesarComMonitoramento(mensagem, idCliente, tipo, info) {
        const inicio = Date.now();
        
        try {
            const resultado = await this.servicoIA.procesarMensagemCliente(
                mensagem,
                idCliente,
                tipo,
                info
            );
            
            const duracao = Date.now() - inicio;
            
            // Log de sucesso
            logger.info('[IA] Resposta gerada', {
                idCliente,
                tipo,
                duracao: duracao + 'ms',
                tamanhoResposta: resultado.resposta.length,
                sucesso: true
            });
            
            // Métricas
            this._registrarMetrica({
                tipo: 'ia_resposta',
                duracao: duracao,
                sucesso: true,
                cliente: idCliente
            });
            
            return resultado;
            
        } catch (erro) {
            const duracao = Date.now() - inicio;
            
            logger.erro('[IA] Erro ao gerar resposta', {
                idCliente,
                tipo,
                duracao: duracao + 'ms',
                erro: erro.message
            });
            
            this._registrarMetrica({
                tipo: 'ia_erro',
                duracao: duracao,
                sucesso: false,
                cliente: idCliente,
                erro: erro.message
            });
            
            throw erro;
        }
    }
    
    _registrarMetrica(dados) {
        // Enviar para seu sistema de métricas (Prometheus, DataDog, etc)
        console.log('[Métrica]', dados);
    }
}

module.exports = ServicoIAComMonitoramento;
```

---

### 8️⃣ INTEGRAÇÃO COM AUTENTICAÇÃO

Para proteger endpoints:

```javascript
// Em seu middleware de autenticação

const express = require('express');
const jwt = require('jsonwebtoken');
const rotasChat = require('./src/rotas/chat-ia-integracao');

const app = express();

// Middleware de autenticação
const verificarToken = (req, res, next) => {
    const token = req.headers['authorization']?.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({ error: 'Token não fornecido' });
    }
    
    try {
        const decoded = jwt.verify(token, 'sua-chave-secreta');
        req.usuario = decoded;
        next();
    } catch (erro) {
        res.status(401).json({ error: 'Token inválido' });
    }
};

// Rotas protegidas
app.use('/api/chat', verificarToken);
app.use('/api', rotasChat);

// Ou proteger endpoint específico
app.post('/api/chat/mensagem', verificarToken, async (req, res) => {
    // ... lógica
});
```

---

### 9️⃣ INTEGRAÇÃO COM TRATAMENTO DE ERROS GLOBAL

```javascript
// Middleware de erro centralizado

const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');

app.use((err, req, res, next) => {
    // Se erro for da IA
    if (err instanceof ServicoIAHumanizada) {
        logger.erro('Erro de IA:', err);
        return res.status(500).json({
            error: 'Erro ao processar com IA',
            resposta: 'Um atendente irá ajudá-lo em breve!'
        });
    }
    
    // Outros erros
    logger.erro('Erro geral:', err);
    res.status(500).json({ error: 'Erro interno' });
});
```

---

### 🔟 INTEGRAÇÃO COM CACHE

Para otimizar:

```javascript
// Em um arquivo de cache

const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');
const NodeCache = require('node-cache');

class ServicoIAComCache {
    constructor() {
        this.servicoIA = new ServicoIAHumanizada();
        this.cache = new NodeCache({ stdTTL: 3600 }); // 1 hora
    }
    
    async procesarComCache(mensagem, idCliente, tipo) {
        const chaveCache = `ia_${idCliente}_${mensagem.substring(0, 50)}`;
        
        // Verificar cache
        const cached = this.cache.get(chaveCache);
        if (cached) {
            console.log('[Cache] Hit');
            return cached;
        }
        
        // Processar
        const resultado = await this.servicoIA.procesarMensagemCliente(
            mensagem,
            idCliente,
            tipo
        );
        
        // Salvar em cache
        this.cache.set(chaveCache, resultado);
        console.log('[Cache] Saved');
        
        return resultado;
    }
}

module.exports = ServicoIAComCache;
```

---

## 📋 CHECKLIST DE INTEGRAÇÃO

- [ ] Arquivo de configuração criado
- [ ] API Key do Gemini configurada
- [ ] Serviço importado no arquivo principal
- [ ] Rotas REST integradas (ou serviço direto)
- [ ] Tratamento de erros implementado
- [ ] Logging configurado
- [ ] Testes executados com sucesso
- [ ] Documentação lida
- [ ] Variáveis de ambiente configuradas
- [ ] Pronto para produção

---

**Qual integração você precisa? Escolha acima e siga as instruções!** 🚀
