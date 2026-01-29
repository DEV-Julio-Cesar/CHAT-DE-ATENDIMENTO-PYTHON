#!/usr/bin/env node
// =========================================================================
// SERVIDOR WEB - VERSÃO WEB DO SISTEMA DE ATENDIMENTO WHATSAPP
// =========================================================================

const express = require('express');
const path = require('path');
const cors = require('cors');
const fs = require('fs-extra');
const WebSocket = require('ws');
const http = require('http');

// Importar módulos do sistema
const logger = require('./src/infraestrutura/logger');
const { validarCredenciais, obterNivelPermissao, obterDadosUsuario } = require('./src/aplicacao/validacao-credenciais');
const gerenciadorUsuarios = require('./src/aplicacao/gerenciador-usuarios');
const GerenciadorPoolWhatsApp = require('./src/services/GerenciadorPoolWhatsApp');
const gerenciadorMensagens = require('./src/aplicacao/gerenciador-mensagens');
const campanhas = require('./src/aplicacao/campanhas');
const chatbot = require('./src/aplicacao/chatbot');
const metricas = require('./src/aplicacao/metricas');
const automacaoConfig = require('./src/aplicacao/automacao-config');
const backups = require('./src/aplicacao/backup');

console.log('🌐 INICIANDO SERVIDOR WEB...\n');

// =========================================================================
// CONFIGURAÇÕES
// =========================================================================
const PORT = process.env.PORT || 3000;

// =========================================================================
// CRIAR APLICAÇÃO EXPRESS
// =========================================================================
const app = express();
const server = http.createServer(app);

// Middleware
app.use(cors({
    origin: true,
    credentials: true
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Servir arquivos estáticos
app.use(express.static(path.join(__dirname, 'src/interfaces')));
app.use('/dados', express.static(path.join(__dirname, 'dados')));

// =========================================================================
// INICIALIZAR POOL WHATSAPP
// =========================================================================
let poolWhatsApp = null;

async function inicializarPoolWhatsApp() {
    try {
        poolWhatsApp = new GerenciadorPoolWhatsApp({
            sessionPath: path.join(__dirname, '.wwebjs_auth'),
            onQR: (clientId, qrDataURL) => {
                // Enviar QR via SSE e WebSocket
                broadcastToAllClients('qr-generated', { clientId, qrDataURL });
                logger.info(`[QR] QR Code gerado para ${clientId}`);
            },
            onReady: (clientId) => {
                logger.sucesso(`[Pool] Cliente ${clientId} pronto`);
                broadcastToAllClients('client-ready', { clientId });
            },
            onMessage: (clientId, message) => {
                // Processar mensagem recebida
                processarMensagemRecebida(clientId, message);
            }
        });
        
        // Restaurar sessões persistidas
        await poolWhatsApp.restorePersistedSessions();
        logger.sucesso('[Pool] WhatsApp Pool inicializado');
    } catch (erro) {
        logger.erro('[Pool] Erro ao inicializar:', erro.message);
    }
}

// =========================================================================
// SERVER-SENT EVENTS PARA COMUNICAÇÃO EM TEMPO REAL (SUBSTITUI WEBSOCKETS)
// =========================================================================
app.get('/api/events', (req, res) => {
    // Configurar SSE
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
    });

    // Adicionar cliente à lista
    const clientId = Date.now();
    sseClients.set(clientId, res);
    
    logger.info(`[SSE] Cliente ${clientId} conectado`);
    
    // Enviar evento de conexão
    res.write(`data: ${JSON.stringify({ type: 'connected', clientId })}\n\n`);
    
    // Cleanup quando cliente desconecta
    req.on('close', () => {
        sseClients.delete(clientId);
        logger.info(`[SSE] Cliente ${clientId} desconectado`);
    });
});

// Mapa para armazenar clientes SSE
const sseClients = new Map();

function broadcastToClients(type, data) {
    const message = `data: ${JSON.stringify({ type, data, timestamp: Date.now() })}\n\n`;
    
    sseClients.forEach((res, clientId) => {
        try {
            res.write(message);
        } catch (error) {
            logger.erro(`[SSE] Erro ao enviar para cliente ${clientId}:`, error.message);
            sseClients.delete(clientId);
        }
    });
    
    logger.info(`[SSE] Mensagem enviada para ${sseClients.size} clientes: ${type}`);
}

// =========================================================================
// WEBSOCKET PARA COMUNICAÇÃO EM TEMPO REAL (BACKUP)
// =========================================================================
const wss = new WebSocket.Server({ 
    server,
    path: '/ws'
});
const clients = new Set();

wss.on('connection', (ws, req) => {
    clients.add(ws);
    logger.info('[WebSocket] Cliente conectado');
    
    // Enviar mensagem de boas-vindas
    ws.send(JSON.stringify({ type: 'connected', timestamp: Date.now() }));
    
    ws.on('close', () => {
        clients.delete(ws);
        logger.info('[WebSocket] Cliente desconectado');
    });
    
    ws.on('error', (error) => {
        logger.erro('[WebSocket] Erro:', error.message);
        clients.delete(ws);
    });
    
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            logger.info('[WebSocket] Mensagem recebida:', data);
        } catch (error) {
            logger.erro('[WebSocket] Erro ao processar mensagem:', error.message);
        }
    });
});

// Função para broadcast que usa tanto SSE quanto WebSocket
function broadcastToAllClients(type, data) {
    // Enviar via SSE (principal)
    broadcastToClients(type, data);
    
    // Enviar via WebSocket (backup)
    const message = JSON.stringify({ type, data, timestamp: Date.now() });
    clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            try {
                client.send(message);
            } catch (error) {
                logger.erro('[WebSocket] Erro ao enviar:', error.message);
                clients.delete(client);
            }
        }
    });
}

// =========================================================================
// CHAT INTERNO VIA SSE
// =========================================================================
app.get('/api/chat-events', (req, res) => {
    // Configurar SSE para chat
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
    });

    const clientId = Date.now();
    chatSseClients.set(clientId, res);
    
    logger.info(`[Chat SSE] Cliente ${clientId} conectado`);
    
    req.on('close', () => {
        chatSseClients.delete(clientId);
        logger.info(`[Chat SSE] Cliente ${clientId} desconectado`);
    });
});

const chatSseClients = new Map();

// API para enviar mensagens de chat interno
app.post('/api/chat-message', (req, res) => {
    try {
        const { from, texto } = req.body;
        
        const message = {
            type: 'internal',
            from,
            texto,
            timestamp: Date.now()
        };
        
        const data = `data: ${JSON.stringify(message)}\n\n`;
        
        chatSseClients.forEach((clientRes, clientId) => {
            try {
                clientRes.write(data);
            } catch (error) {
                logger.erro(`[Chat SSE] Erro ao enviar para cliente ${clientId}:`, error.message);
                chatSseClients.delete(clientId);
            }
        });
        
        res.json({ success: true });
    } catch (error) {
        logger.erro('[Chat SSE] Erro ao processar mensagem:', error.message);
        res.status(500).json({ success: false, message: error.message });
    }
});

// =========================================================================
// ROTAS DA API
// =========================================================================

// Rota principal - servir index.html
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/login.html'));
});

// Rota para páginas específicas
app.get('/login', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/login.html'));
});

app.get('/principal', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/index.html'));
});

app.get('/chat-filas', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/chat-filas.html'));
});

app.get('/campanhas', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/campanhas.html'));
});

app.get('/usuarios', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/usuarios.html'));
});

app.get('/automacao', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/automacao.html'));
});

app.get('/dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/painel.html'));
});

// Rota para o gerenciador de pool
app.get('/pool-manager', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/gerenciador-pool.html'));
});

// Rota para validação WhatsApp
app.get('/validacao-whatsapp', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/validacao-whatsapp.html'));
});

// Rota para janela QR
app.get('/janela-qr', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/janela-qr.html'));
});

// Rota para conectar número
app.get('/conectar-numero', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/conectar-numero.html'));
});

// Rota para saúde do sistema
app.get('/saude', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/saude.html'));
});

// Rota para histórico
app.get('/historico', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/historico.html'));
});

// Rota para o web-adapter
app.get('/web-adapter.js', (req, res) => {
    res.sendFile(path.join(__dirname, 'src/interfaces/web-adapter.js'));
});

// =========================================================================
// API DE AUTENTICAÇÃO
// =========================================================================
app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        if (!username || !password) {
            return res.status(400).json({ 
                success: false, 
                message: 'Usuário e senha são obrigatórios' 
            });
        }
        
        const valido = await validarCredenciais(username, password);
        
        if (!valido) {
            return res.status(401).json({ 
                success: false, 
                message: 'Usuário ou senha inválidos' 
            });
        }
        
        const role = await obterNivelPermissao(username);
        const dados = await obterDadosUsuario(username);
        
        logger.sucesso(`[Login Web] ${username} autenticado com sucesso (${role})`);
        
        res.json({ 
            success: true, 
            user: { username, role, ...dados }
        });
        
    } catch (erro) {
        logger.erro('[Login Web] Erro:', erro.message);
        res.status(500).json({ 
            success: false, 
            message: 'Erro interno do servidor' 
        });
    }
});

// =========================================================================
// API DO WHATSAPP
// =========================================================================
app.get('/api/whatsapp/clients', async (req, res) => {
    try {
        if (!poolWhatsApp) {
            return res.json({ success: true, clients: [] });
        }
        
        const clients = Array.from(poolWhatsApp.clients.keys());
        const clientsStatus = {};
        
        for (const clientId of clients) {
            const client = poolWhatsApp.clients.get(clientId);
            clientsStatus[clientId] = {
                id: clientId,
                status: client?.status || 'unknown',
                ready: client?.status === 'ready'
            };
        }
        
        res.json({ success: true, clients: clientsStatus });
    } catch (erro) {
        logger.erro('[API WhatsApp] Erro ao listar clientes:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

app.post('/api/whatsapp/create-client', async (req, res) => {
    try {
        if (!poolWhatsApp) {
            return res.status(500).json({ 
                success: false, 
                message: 'Pool WhatsApp não inicializado' 
            });
        }
        
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const result = await poolWhatsApp.createAndInitialize(clientId);
        
        res.json(result);
    } catch (erro) {
        logger.erro('[API WhatsApp] Erro ao criar cliente:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

app.post('/api/whatsapp/send-message', async (req, res) => {
    try {
        const { clientId, chatId, message } = req.body;
        
        if (!poolWhatsApp) {
            return res.status(500).json({ 
                success: false, 
                message: 'Pool WhatsApp não inicializado' 
            });
        }
        
        const result = await poolWhatsApp.sendMessage(clientId, chatId, message);
        res.json({ success: true, result });
    } catch (erro) {
        logger.erro('[API WhatsApp] Erro ao enviar mensagem:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

// =========================================================================
// API DE USUÁRIOS
// =========================================================================
app.get('/api/users', async (req, res) => {
    try {
        const usuarios = await gerenciadorUsuarios.listarUsuarios();
        res.json({ success: true, users: usuarios });
    } catch (erro) {
        logger.erro('[API Users] Erro:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

app.post('/api/users', async (req, res) => {
    try {
        const resultado = await gerenciadorUsuarios.cadastrarUsuario(req.body);
        res.json(resultado);
    } catch (erro) {
        logger.erro('[API Users] Erro ao cadastrar:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

// =========================================================================
// API DE CAMPANHAS
// =========================================================================
app.get('/api/campaigns', async (req, res) => {
    try {
        const listaCampanhas = await campanhas.listarCampanhas();
        res.json({ success: true, campaigns: listaCampanhas });
    } catch (erro) {
        logger.erro('[API Campaigns] Erro:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

app.post('/api/campaigns', async (req, res) => {
    try {
        const resultado = await campanhas.criarCampanha(req.body);
        res.json(resultado);
    } catch (erro) {
        logger.erro('[API Campaigns] Erro ao criar:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

// =========================================================================
// API DE MÉTRICAS
// =========================================================================
app.get('/api/metrics', async (req, res) => {
    try {
        const dadosMetricas = await metricas.obterMetricas();
        res.json({ success: true, metrics: dadosMetricas });
    } catch (erro) {
        logger.erro('[API Metrics] Erro:', erro.message);
        res.status(500).json({ success: false, message: erro.message });
    }
});

// =========================================================================
// API DE STATUS
// =========================================================================
app.get('/api/status', (req, res) => {
    const status = {
        server: 'online',
        timestamp: new Date().toISOString(),
        whatsapp: {
            pool: poolWhatsApp ? 'initialized' : 'not_initialized',
            clients: poolWhatsApp ? poolWhatsApp.clients.size : 0
        },
        websockets: {
            main: clients.size,
            sse: sseClients.size
        }
    };
    
    res.json({ success: true, status });
});

// =========================================================================
// PROCESSAR MENSAGENS RECEBIDAS
// =========================================================================
async function processarMensagemRecebida(clientId, message) {
    try {
        // Broadcast da mensagem para todos os clientes conectados
        broadcastToAllClients('new-message', {
            clientId,
            message: {
                id: message.id._serialized,
                from: message.from,
                to: message.to,
                body: message.body,
                timestamp: message.timestamp,
                type: message.type
            }
        });
        
        // Processar com chatbot se necessário
        // Aqui você pode adicionar lógica de automação
        
    } catch (erro) {
        logger.erro('[Mensagem] Erro ao processar:', erro.message);
    }
}

// =========================================================================
// INICIALIZAÇÃO DO SERVIDOR
// =========================================================================
async function iniciarServidor() {
    try {
        // Garantir que as pastas existem
        await fs.ensureDir('dados');
        await fs.ensureDir('dados/logs');
        await fs.ensureDir('.wwebjs_auth');
        
        // Inicializar pool WhatsApp
        await inicializarPoolWhatsApp();
        
        // Iniciar servidor HTTP
        server.listen(PORT, () => {
            console.log('🎉 SERVIDOR WEB INICIADO COM SUCESSO!\n');
            console.log(`📱 Aplicação Web: http://localhost:${PORT}`);
            console.log(`🔌 WebSocket Principal: ws://localhost:${PORT}/ws`);
            console.log(`💬 WebSocket Chat: ws://localhost:${PORT}/chat-ws`);
            console.log('\n💡 Acesse http://localhost:' + PORT + ' no seu navegador');
            console.log('👤 Login padrão: admin / admin\n');
            
            logger.sucesso(`[Servidor Web] Iniciado na porta ${PORT}`);
            logger.sucesso(`[WebSocket] Principal em ${PORT}/ws`);
            logger.sucesso(`[WebSocket] Chat em ${PORT}/chat-ws`);
        });
        
    } catch (erro) {
        console.error('❌ ERRO AO INICIAR SERVIDOR:', erro.message);
        process.exit(1);
    }
}

// =========================================================================
// TRATAMENTO DE SINAIS
// =========================================================================
process.on('SIGINT', async () => {
    console.log('\n🛑 Encerrando servidor...');
    
    if (poolWhatsApp) {
        await poolWhatsApp.destroyAll();
    }
    
    server.close(() => {
        console.log('✅ Servidor encerrado com sucesso');
        process.exit(0);
    });
});

process.on('uncaughtException', (erro) => {
    logger.erro('[Servidor] Erro não capturado:', erro.message);
});

process.on('unhandledRejection', (erro) => {
    logger.erro('[Servidor] Promise rejeitada:', erro.message);
});

// =========================================================================
// INICIAR
// =========================================================================
iniciarServidor();