/**
 * Serviço WhatsApp Web - CIANET PROVEDOR
 * Integração com whatsapp-web.js para gerenciar sessões do WhatsApp
 */

const express = require('express');
const cors = require('cors');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const qrcodeTerminal = require('qrcode-terminal');

const app = express();
app.use(cors());
app.use(express.json());

// Armazenar sessões ativas
const sessions = new Map();
const qrCodes = new Map();

// Configuração do cliente WhatsApp
function createWhatsAppClient(sessionId) {
    console.log(`[${sessionId}] Criando cliente WhatsApp...`);
    
    const client = new Client({
        authStrategy: new LocalAuth({
            clientId: sessionId,
            dataPath: './sessions'
        }),
        puppeteer: {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        }
    });

    // Evento: QR Code gerado
    client.on('qr', async (qr) => {
        console.log(`[${sessionId}] QR Code gerado`);
        qrcodeTerminal.generate(qr, { small: true });
        
        // Converter para base64 para enviar ao frontend
        const qrBase64 = await qrcode.toDataURL(qr, {
            width: 300,
            margin: 2,
            color: {
                dark: '#166534',
                light: '#ffffff'
            }
        });
        
        qrCodes.set(sessionId, {
            qr: qr,
            qrBase64: qrBase64,
            timestamp: Date.now(),
            status: 'pending'
        });
    });

    // Evento: Carregando
    client.on('loading_screen', (percent, message) => {
        console.log(`[${sessionId}] Carregando: ${percent}% - ${message}`);
    });

    // Evento: Autenticado
    client.on('authenticated', () => {
        console.log(`[${sessionId}] ✅ Autenticado!`);
        const qrData = qrCodes.get(sessionId);
        if (qrData) {
            qrData.status = 'authenticated';
            qrCodes.set(sessionId, qrData);
        }
    });

    // Evento: Pronto
    client.on('ready', () => {
        console.log(`[${sessionId}] ✅ WhatsApp pronto!`);
        const session = sessions.get(sessionId);
        if (session) {
            session.status = 'ready';
            session.info = client.info;
            sessions.set(sessionId, session);
        }
    });

    // Evento: Desconectado
    client.on('disconnected', (reason) => {
        console.log(`[${sessionId}] ❌ Desconectado: ${reason}`);
        sessions.delete(sessionId);
        qrCodes.delete(sessionId);
    });

    // Evento: Mensagem recebida
    client.on('message', async (msg) => {
        console.log(`[${sessionId}] 📩 Mensagem de ${msg.from}: ${msg.body}`);
        
        // Notificar o backend Python via webhook
        try {
            await fetch('http://localhost:8000/api/v1/whatsapp/webhook/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sessionId: sessionId,
                    from: msg.from,
                    body: msg.body,
                    timestamp: msg.timestamp,
                    type: msg.type,
                    isGroup: msg.from.includes('@g.us')
                })
            });
        } catch (e) {
            console.log(`[${sessionId}] Erro ao enviar webhook: ${e.message}`);
        }
    });

    // Evento: Erro de autenticação
    client.on('auth_failure', (msg) => {
        console.log(`[${sessionId}] ❌ Falha na autenticação: ${msg}`);
        const qrData = qrCodes.get(sessionId);
        if (qrData) {
            qrData.status = 'auth_failure';
            qrCodes.set(sessionId, qrData);
        }
    });

    return client;
}

// ========== ENDPOINTS ==========

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        service: 'whatsapp-web-service',
        activeSessions: sessions.size,
        timestamp: new Date().toISOString()
    });
});

// Criar nova sessão e obter QR Code
app.post('/session/create', async (req, res) => {
    try {
        const sessionId = req.body.sessionId || `session_${Date.now()}`;
        
        // Verificar se sessão já existe
        if (sessions.has(sessionId)) {
            const session = sessions.get(sessionId);
            if (session.status === 'ready') {
                return res.json({
                    success: true,
                    sessionId: sessionId,
                    status: 'already_connected',
                    info: session.info
                });
            }
        }
        
        // Criar novo cliente
        const client = createWhatsAppClient(sessionId);
        
        sessions.set(sessionId, {
            client: client,
            status: 'initializing',
            createdAt: Date.now()
        });
        
        // Inicializar cliente
        client.initialize();
        
        // Aguardar QR Code ser gerado (máximo 30 segundos)
        let attempts = 0;
        const maxAttempts = 30;
        
        while (!qrCodes.has(sessionId) && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
            
            // Verificar se já conectou (sessão existente)
            const session = sessions.get(sessionId);
            if (session && session.status === 'ready') {
                return res.json({
                    success: true,
                    sessionId: sessionId,
                    status: 'connected',
                    message: 'Sessão restaurada automaticamente'
                });
            }
        }
        
        if (qrCodes.has(sessionId)) {
            const qrData = qrCodes.get(sessionId);
            res.json({
                success: true,
                sessionId: sessionId,
                qrCode: qrData.qrBase64,
                status: 'qr_ready'
            });
        } else {
            res.status(408).json({
                success: false,
                error: 'Timeout ao gerar QR Code'
            });
        }
        
    } catch (error) {
        console.error('Erro ao criar sessão:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Obter QR Code atual
app.get('/session/:sessionId/qr', (req, res) => {
    const { sessionId } = req.params;
    
    if (qrCodes.has(sessionId)) {
        const qrData = qrCodes.get(sessionId);
        res.json({
            success: true,
            qrCode: qrData.qrBase64,
            status: qrData.status,
            timestamp: qrData.timestamp
        });
    } else {
        res.status(404).json({
            success: false,
            error: 'QR Code não encontrado'
        });
    }
});

// Verificar status da sessão
app.get('/session/:sessionId/status', (req, res) => {
    const { sessionId } = req.params;
    
    if (sessions.has(sessionId)) {
        const session = sessions.get(sessionId);
        const qrData = qrCodes.get(sessionId);
        
        res.json({
            success: true,
            sessionId: sessionId,
            status: session.status,
            qrStatus: qrData?.status || 'unknown',
            connected: session.status === 'ready',
            info: session.info || null
        });
    } else {
        res.json({
            success: false,
            sessionId: sessionId,
            status: 'not_found',
            connected: false
        });
    }
});

// Desconectar sessão
app.post('/session/:sessionId/disconnect', async (req, res) => {
    const { sessionId } = req.params;
    
    if (sessions.has(sessionId)) {
        const session = sessions.get(sessionId);
        try {
            await session.client.logout();
            await session.client.destroy();
            sessions.delete(sessionId);
            qrCodes.delete(sessionId);
            
            res.json({
                success: true,
                message: 'Sessão desconectada'
            });
        } catch (error) {
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    } else {
        res.status(404).json({
            success: false,
            error: 'Sessão não encontrada'
        });
    }
});

// Enviar mensagem
app.post('/session/:sessionId/send', async (req, res) => {
    const { sessionId } = req.params;
    const { to, message, type = 'text' } = req.body;
    
    if (!sessions.has(sessionId)) {
        return res.status(404).json({
            success: false,
            error: 'Sessão não encontrada'
        });
    }
    
    const session = sessions.get(sessionId);
    
    if (session.status !== 'ready') {
        return res.status(400).json({
            success: false,
            error: 'Sessão não está pronta'
        });
    }
    
    try {
        // Formatar número (adicionar @c.us se necessário)
        let chatId = to;
        if (!to.includes('@')) {
            chatId = `${to.replace(/\D/g, '')}@c.us`;
        }
        
        let result;
        if (type === 'text') {
            result = await session.client.sendMessage(chatId, message);
        }
        
        res.json({
            success: true,
            messageId: result.id._serialized,
            timestamp: result.timestamp
        });
        
    } catch (error) {
        console.error('Erro ao enviar mensagem:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Listar sessões ativas
app.get('/sessions', (req, res) => {
    const sessionList = [];
    
    sessions.forEach((session, sessionId) => {
        sessionList.push({
            sessionId: sessionId,
            status: session.status,
            createdAt: session.createdAt,
            info: session.info || null
        });
    });
    
    res.json({
        success: true,
        count: sessionList.length,
        sessions: sessionList
    });
});

// Obter foto de perfil de um contato
app.get('/session/:sessionId/profile-pic/:phoneNumber', async (req, res) => {
    const { sessionId, phoneNumber } = req.params;
    
    if (!sessions.has(sessionId)) {
        return res.status(404).json({
            success: false,
            error: 'Sessão não encontrada'
        });
    }
    
    const session = sessions.get(sessionId);
    
    if (session.status !== 'ready') {
        return res.status(400).json({
            success: false,
            error: 'Sessão não está pronta'
        });
    }
    
    try {
        // Formatar número
        let chatId = phoneNumber;
        if (!phoneNumber.includes('@')) {
            chatId = `${phoneNumber.replace(/\D/g, '')}@c.us`;
        }
        
        const profilePicUrl = await session.client.getProfilePicUrl(chatId);
        
        res.json({
            success: true,
            phoneNumber: phoneNumber,
            profilePicUrl: profilePicUrl || null
        });
        
    } catch (error) {
        console.error('Erro ao obter foto de perfil:', error);
        res.json({
            success: true,
            phoneNumber: phoneNumber,
            profilePicUrl: null
        });
    }
});

// Listar conversas/chats recentes
app.get('/session/:sessionId/chats', async (req, res) => {
    const { sessionId } = req.params;
    const limit = parseInt(req.query.limit) || 20;
    
    if (!sessions.has(sessionId)) {
        return res.status(404).json({
            success: false,
            error: 'Sessão não encontrada'
        });
    }
    
    const session = sessions.get(sessionId);
    
    if (session.status !== 'ready') {
        return res.status(400).json({
            success: false,
            error: 'Sessão não está pronta'
        });
    }
    
    try {
        const chats = await session.client.getChats();
        const chatList = [];
        
        for (let i = 0; i < Math.min(chats.length, limit); i++) {
            const chat = chats[i];
            
            // Ignorar grupos por enquanto
            if (chat.isGroup) continue;
            
            let profilePicUrl = null;
            try {
                profilePicUrl = await session.client.getProfilePicUrl(chat.id._serialized);
            } catch (e) {
                // Sem foto de perfil
            }
            
            chatList.push({
                id: chat.id._serialized,
                name: chat.name || chat.pushname || 'Desconhecido',
                phoneNumber: chat.id.user,
                lastMessage: chat.lastMessage?.body || '',
                timestamp: chat.lastMessage?.timestamp || 0,
                unreadCount: chat.unreadCount || 0,
                isOnline: chat.isOnline || false,
                profilePicUrl: profilePicUrl
            });
        }
        
        // Ordenar por timestamp (mais recentes primeiro)
        chatList.sort((a, b) => b.timestamp - a.timestamp);
        
        res.json({
            success: true,
            count: chatList.length,
            chats: chatList
        });
        
    } catch (error) {
        console.error('Erro ao listar chats:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Obter mensagens de um chat
app.get('/session/:sessionId/messages/:chatId', async (req, res) => {
    const { sessionId, chatId } = req.params;
    const limit = parseInt(req.query.limit) || 50;
    
    if (!sessions.has(sessionId)) {
        return res.status(404).json({
            success: false,
            error: 'Sessão não encontrada'
        });
    }
    
    const session = sessions.get(sessionId);
    
    if (session.status !== 'ready') {
        return res.status(400).json({
            success: false,
            error: 'Sessão não está pronta'
        });
    }
    
    try {
        // Formatar chatId
        let formattedChatId = chatId;
        if (!chatId.includes('@')) {
            formattedChatId = `${chatId.replace(/\D/g, '')}@c.us`;
        }
        
        const chat = await session.client.getChatById(formattedChatId);
        const messages = await chat.fetchMessages({ limit: limit });
        
        const messageList = messages.map(msg => ({
            id: msg.id._serialized,
            body: msg.body,
            from: msg.from,
            to: msg.to,
            fromMe: msg.fromMe,
            timestamp: msg.timestamp,
            type: msg.type,
            hasMedia: msg.hasMedia
        }));
        
        res.json({
            success: true,
            chatId: formattedChatId,
            count: messageList.length,
            messages: messageList
        });
        
    } catch (error) {
        console.error('Erro ao obter mensagens:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// ========== INICIAR SERVIDOR ==========
const PORT = process.env.PORT || 3001;

app.listen(PORT, () => {
    console.log('═══════════════════════════════════════════');
    console.log('   🟢 WhatsApp Web Service - CIANET');
    console.log('═══════════════════════════════════════════');
    console.log(`   📡 Servidor rodando na porta ${PORT}`);
    console.log(`   🔗 http://localhost:${PORT}`);
    console.log('═══════════════════════════════════════════');
});
