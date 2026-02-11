const express = require('express');
const cors = require('cors');
const qrcode = require('qrcode');
const { Client, LocalAuth } = require('whatsapp-web.js');

const app = express();
const PORT = 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Estado do cliente WhatsApp
let client = null;
let qrCodeData = null;
let isReady = false;
let clientInfo = null;

// Inicializar cliente WhatsApp
function initializeWhatsAppClient() {
    console.log('🚀 Inicializando cliente WhatsApp...');
    
    client = new Client({
        authStrategy: new LocalAuth({
            clientId: 'cianet-whatsapp'
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
        console.log('📱 QR Code gerado!');
        try {
            qrCodeData = await qrcode.toDataURL(qr);
            console.log('✅ QR Code convertido para base64');
        } catch (err) {
            console.error('❌ Erro ao gerar QR Code:', err);
        }
    });

    // Evento: Cliente autenticado
    client.on('authenticated', () => {
        console.log('✅ Cliente autenticado!');
        qrCodeData = null;
    });

    // Evento: Autenticação falhou
    client.on('auth_failure', (msg) => {
        console.error('❌ Falha na autenticação:', msg);
        qrCodeData = null;
    });

    // Evento: Cliente pronto
    client.on('ready', async () => {
        console.log('✅ Cliente WhatsApp pronto!');
        isReady = true;
        qrCodeData = null;
        
        try {
            clientInfo = {
                number: client.info.wid.user,
                name: client.info.pushname,
                platform: client.info.platform
            };
            console.log('📞 Conectado como:', clientInfo);
        } catch (err) {
            console.error('Erro ao obter info do cliente:', err);
        }
    });

    // Evento: Cliente desconectado
    client.on('disconnected', (reason) => {
        console.log('⚠️ Cliente desconectado:', reason);
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
    });

    // Inicializar
    client.initialize().catch(err => {
        console.error('❌ Erro ao inicializar cliente:', err);
    });
}

// Rotas da API

// Status do serviço
app.get('/status', (req, res) => {
    res.json({
        success: true,
        service: 'WhatsApp Web Service',
        version: '1.0.0',
        status: isReady ? 'connected' : 'disconnected',
        hasQrCode: !!qrCodeData,
        clientInfo: clientInfo
    });
});

// Obter QR Code
app.get('/qr-code', (req, res) => {
    if (isReady) {
        return res.json({
            success: true,
            connected: true,
            message: 'WhatsApp já está conectado',
            clientInfo: clientInfo
        });
    }

    if (!qrCodeData) {
        return res.json({
            success: false,
            error: 'QR Code ainda não foi gerado. Aguarde alguns segundos e tente novamente.',
            message: 'Inicializando conexão com WhatsApp Web...'
        });
    }

    res.json({
        success: true,
        qr_code: qrCodeData,
        message: 'Escaneie o QR Code com seu WhatsApp'
    });
});

// Enviar mensagem
app.post('/send-message', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp não está conectado. Escaneie o QR Code primeiro.'
        });
    }

    const { phone, message } = req.body;

    if (!phone || !message) {
        return res.status(400).json({
            success: false,
            error: 'Campos "phone" e "message" são obrigatórios'
        });
    }

    try {
        // Formatar número (remover caracteres especiais)
        const cleanPhone = phone.replace(/\D/g, '');
        
        console.log(`📤 Tentando enviar mensagem para ${cleanPhone}`);
        
        // Tentar diferentes formatos de número
        const formats = [
            `${cleanPhone}@c.us`,           // Formato padrão
            `55${cleanPhone}@c.us`,         // Com código do Brasil
            `${cleanPhone}@s.whatsapp.net`  // Formato alternativo
        ];
        
        let sent = false;
        let lastError = null;
        
        for (const chatId of formats) {
            try {
                console.log(`   Tentando formato: ${chatId}`);
                
                // Tentar obter o número ID primeiro
                try {
                    const numberId = await client.getNumberId(chatId.replace('@c.us', '').replace('@s.whatsapp.net', ''));
                    if (numberId) {
                        console.log(`   ✅ Número encontrado: ${numberId._serialized}`);
                        await client.sendMessage(numberId._serialized, message);
                        sent = true;
                        console.log(`✅ Mensagem enviada com sucesso para ${cleanPhone}`);
                        break;
                    }
                } catch (e) {
                    // Se getNumberId falhar, tentar enviar diretamente
                    console.log(`   ⚠️ getNumberId falhou, tentando envio direto...`);
                    await client.sendMessage(chatId, message);
                    sent = true;
                    console.log(`✅ Mensagem enviada com sucesso para ${cleanPhone}`);
                    break;
                }
            } catch (error) {
                lastError = error;
                console.log(`   ❌ Falhou com formato ${chatId}: ${error.message}`);
                continue;
            }
        }
        
        if (!sent) {
            throw new Error(lastError?.message || 'Não foi possível enviar a mensagem em nenhum formato');
        }

        res.json({
            success: true,
            message: 'Mensagem enviada com sucesso',
            to: phone
        });
    } catch (error) {
        console.error('❌ Erro ao enviar mensagem:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro ao enviar mensagem: ' + error.message
        });
    }
});

// Listar chats/conversas
app.get('/chats', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp não está conectado'
        });
    }

    try {
        console.log('📋 Buscando lista de chats...');
        
        // Obter todos os chats
        const chats = await client.getChats();
        
        // Filtrar apenas chats individuais (não grupos)
        const individualChats = chats.filter(chat => !chat.isGroup);
        
        // Mapear para formato simplificado
        const chatList = await Promise.all(individualChats.slice(0, 50).map(async (chat) => {
            try {
                const contact = await chat.getContact();
                const lastMessage = chat.lastMessage;
                
                return {
                    id: chat.id._serialized,
                    name: contact.pushname || contact.name || chat.name || 'Sem nome',
                    phone: contact.number,
                    profilePic: contact.profilePicUrl || null,
                    lastMessage: lastMessage ? {
                        body: lastMessage.body,
                        timestamp: lastMessage.timestamp,
                        fromMe: lastMessage.fromMe
                    } : null,
                    unreadCount: chat.unreadCount,
                    timestamp: chat.timestamp
                };
            } catch (err) {
                console.error('Erro ao processar chat:', err);
                return null;
            }
        }));
        
        // Remover nulls e ordenar por timestamp
        const validChats = chatList
            .filter(chat => chat !== null)
            .sort((a, b) => b.timestamp - a.timestamp);
        
        console.log(`✅ ${validChats.length} chats encontrados`);
        
        res.json({
            success: true,
            chats: validChats,
            total: validChats.length
        });
    } catch (error) {
        console.error('❌ Erro ao buscar chats:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro ao buscar chats: ' + error.message
        });
    }
});

// Obter mensagens de um chat específico
app.get('/chats/:chatId/messages', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp não está conectado'
        });
    }

    const { chatId } = req.params;
    const limit = parseInt(req.query.limit) || 50;

    try {
        console.log(`📨 Buscando mensagens do chat: ${chatId}`);
        
        const chat = await client.getChatById(chatId);
        const messages = await chat.fetchMessages({ limit });
        
        const messageList = messages.map(msg => ({
            id: msg.id._serialized,
            body: msg.body,
            timestamp: msg.timestamp,
            fromMe: msg.fromMe,
            type: msg.type,
            hasMedia: msg.hasMedia,
            author: msg.author
        }));
        
        console.log(`✅ ${messageList.length} mensagens encontradas`);
        
        res.json({
            success: true,
            messages: messageList,
            total: messageList.length
        });
    } catch (error) {
        console.error('❌ Erro ao buscar mensagens:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro ao buscar mensagens: ' + error.message
        });
    }
});
app.post('/disconnect', async (req, res) => {
    if (!client) {
        return res.json({
            success: false,
            error: 'Cliente não está inicializado'
        });
    }

    try {
        await client.destroy();
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        
        res.json({
            success: true,
            message: 'WhatsApp desconectado com sucesso'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: 'Erro ao desconectar: ' + error.message
        });
    }
});

// Reconectar
app.post('/reconnect', async (req, res) => {
    try {
        if (client) {
            await client.destroy();
        }
        
        isReady = false;
        clientInfo = null;
        qrCodeData = null;
        
        initializeWhatsAppClient();
        
        res.json({
            success: true,
            message: 'Reconectando... Aguarde o QR Code ser gerado.'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: 'Erro ao reconectar: ' + error.message
        });
    }
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🚀 WhatsApp Service rodando na porta ${PORT}`);
    console.log(`📡 API disponível em http://localhost:${PORT}`);
    console.log('');
    initializeWhatsAppClient();
});

// Tratamento de erros
process.on('unhandledRejection', (err) => {
    console.error('❌ Unhandled Rejection:', err);
});

process.on('uncaughtException', (err) => {
    console.error('❌ Uncaught Exception:', err);
});
