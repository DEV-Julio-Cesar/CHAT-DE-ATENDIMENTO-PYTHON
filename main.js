// =========================================================================
// 1. IMPORTAÇÕES
// =========================================================================
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const axios = require('axios');
const WebSocket = require('ws');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const fs = require('fs-extra');
const { validateCredentials } = require('./auth'); // Importa a função de login

// =========================================================================
// 2. VARIÁVEIS GLOBAIS
// =========================================================================
let WHATSAPP_TOKEN = '';
let PHONE_NUMBER_ID = '';
let API_VERSION = 'v19.0';
let mainWindow = null;
let loginWindow = null; 
let historyWindow = null; // Para a janela de histórico
let whatsappClient = null;
const WS_SERVER_URL = 'ws://localhost:8080';
let ws = null;

// =========================================================================
// 3. DEFINIÇÕES DE FUNÇÕES (Todas antes de 'app.whenReady')
// =========================================================================

// --- FUNÇÃO WEBSOCKET (Sua lógica) ---
function connectWebSocket() {
    console.log(`[WS] Tentando conectar ao servidor em ${WS_SERVER_URL}...`);
    ws = new WebSocket(WS_SERVER_URL);
    ws.on('open', () => console.log('[WS] Conexão WebSocket estabelecida!'));
    ws.on('message', (data) => {
        try {
            const mensagem = JSON.parse(data.toString());
            if (mainWindow) {
                mainWindow.webContents.send('nova-mensagem-recebida', mensagem);
            }
        } catch (e) { console.error('[WS] Erro ao processar mensagem JSON:', e.message); }
    });
    ws.on('close', () => setTimeout(connectWebSocket, 5000));
    ws.on('error', (err) => console.error('[WS] Erro no WebSocket:', err.message));
}

// --- FUNÇÃO CLOUD API (Sua lógica) ---
async function enviarMensagemWhatsApp(numeroDestino, mensagem) {
    if (!WHATSAPP_TOKEN || !PHONE_NUMBER_ID) {
        throw new Error('As credenciais da API do WhatsApp não estão configuradas.');
    }
    const WHATSAPP_API_URL = `https://graph.facebook.com/${API_VERSION}/${PHONE_NUMBER_ID}/messages`;
    const payload = {
        messaging_product: 'whatsapp',
        to: numeroDestino,
        type: 'text',
        text: { body: mensagem }
    };
    try {
        const response = await axios.post(WHATSAPP_API_URL, payload, {
            headers: {
                'Authorization': `Bearer ${WHATSAPP_TOKEN}`,
                'Content-Type': 'application/json'
            }
        });
        return response.data;
    } catch (error) {
        console.error('ERRO ao enviar mensagem via API do WhatsApp:', error.response ? error.response.data : error.message);
        throw new Error(`Falha na API do WhatsApp: ${error.response ? (error.response.data?.error?.message || 'Erro desconhecido') : error.message}`);
    }
}

// --- FUNÇÕES DE JANELA ---

function createLoginWindow() {
    loginWindow = new BrowserWindow({
        width: 450,
        height: 550,
        resizable: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload-login.js'), // Preload do Login
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    loginWindow.loadFile('login.html');
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'), // Preload Principal
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    mainWindow.loadFile('index.html');
    
    if (loginWindow) {
        loginWindow.close();
        loginWindow = null;
    }
}

function createHistoryWindow() {
    if (historyWindow) {
        historyWindow.focus();
        return;
    }
    historyWindow = new BrowserWindow({
        width: 800,
        height: 700,
        webPreferences: {
            preload: path.join(__dirname, 'preload-history.js'), // Preload do Histórico
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    historyWindow.loadFile('history.html');
    historyWindow.on('closed', () => {
        historyWindow = null;
    });
}

// =========================================================================
// 4. INICIALIZAÇÃO DO ELECTRON (O Bloco Principal)
// =========================================================================
app.whenReady().then(() => {
    
    createLoginWindow(); // Inicia com a tela de login
    connectWebSocket();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createLoginWindow(); 
        }
    });

    // --- MANIPULADORES IPC (Todos aqui dentro) ---

    // 1) Login
    ipcMain.handle('login-attempt', async (event, { username, password }) => {
        const isAuthenticated = validateCredentials(username, password);
        if (isAuthenticated) {
            createMainWindow(); 
            return true;
        }
        return false;
    });

    // 2) Abrir Janela de Histórico
    ipcMain.on('open-history-search-window', () => {
        createHistoryWindow();
    });

    // 3) Pesquisar Histórico (Simulação)
    ipcMain.handle('search-chat-history', async (event, filters) => {
        console.log('[History Search] Recebido filtro:', filters);
        if (filters.number.startsWith('55')) { 
            const mockHistory = [
                { texto: 'Olá, qual o status?', sender: 'Cliente', timestamp: new Date('2025-11-01T10:00:00').getTime() },
                { texto: 'Em processamento.', sender: 'Eu', timestamp: new Date('2025-11-01T10:05:00').getTime() },
            ];
            const startTime = new Date(filters.dateStart).getTime();
            const endTime = new Date(filters.dateEnd).getTime();
            const filtered = mockHistory.filter(msg => msg.timestamp >= startTime && msg.timestamp <= endTime);
            return { sucesso: true, history: filtered };
        }
        return { sucesso: false, erro: 'A consulta de histórico completo requer um banco de dados local.' };
    });

    // 4) Fluxo de QR Code (Sua lógica)
    ipcMain.handle('iniciar-qr-code-flow', async () => {
        if (whatsappClient) {
            try { await whatsappClient.destroy(); } catch (e) { console.warn(e.message); }
            whatsappClient = null;
        }

        const sessionPath = path.join(app.getPath('userData'), '.wwebjs_auth', 'session-electron-app-session');
        try {
            if (fs.existsSync(sessionPath)) {
                await fs.remove(sessionPath);
            }
        } catch (e) { console.error('[QR] Erro ao remover pasta de sessão:', e.message); }

        const browserExecutablePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
        whatsappClient = new Client({
            authStrategy: new LocalAuth({ clientId: 'electron-app-session' }),
            puppeteer: {
                executablePath: browserExecutablePath,
                headless: false, 
                args: ['--no-sandbox', '--disable-setuid-sandbox'],
            }
        });

        whatsappClient.on('qr', async (qr) => {
            try {
                const qrDataURL = await qrcode.toDataURL(qr);
                if (mainWindow) mainWindow.webContents.send('qr-code-data', qrDataURL);
            } catch (error) { console.error('[QR] Erro ao gerar DataURL:', error.message); }
        });
        whatsappClient.on('ready', () => {
            if (mainWindow) mainWindow.webContents.send('whatsapp-ready');
        });
        whatsappClient.on('message', async msg => {
            const contact = await msg.getContact(); 
            const number = msg.from.split('@')[0];
            if (mainWindow) {
                mainWindow.webContents.send('nova-mensagem-recebida', {
                    texto: msg.body,
                    name: contact.name || contact.pushname || number,
                    number: number
                });
            }
        });

        whatsappClient.initialize().catch(e => console.error('[QR] Erro de inicialização:', e.message));
        return { sucesso: true, status: 'Fluxo de QR Code iniciado' };
    });

    // 5) Enviar Mensagem (Sua lógica)
    ipcMain.handle('send-whatsapp-message', async (event, { numero, mensagem }) => {
        try {
            if (WHATSAPP_TOKEN && WHATSAPP_TOKEN.startsWith('TOKEN_DE_TESTE_')) {
                return { sucesso: true, dados: { status: 'simulado' } };
            }
            if (whatsappClient && whatsappClient.info) {
                await whatsappClient.sendMessage(`${numero}@c.us`, mensagem);
                return { sucesso: true, dados: { status: 'enviado-qr' } };
            }
            const resultado = await enviarMensagemWhatsApp(numero, mensagem);
            return { sucesso: true, dados: resultado };
        } catch (erro) {
            return { sucesso: false, erro: erro.message };
        }
    });

    // 6) Buscar Chats (Sua lógica - Cole seu código de 'chats.map' aqui)
    ipcMain.handle('fetch-whatsapp-chats', async () => {
        if (!whatsappClient || !whatsappClient.info) {
            return { sucesso: false, erro: 'Cliente WhatsApp desconectado.' };
        }
        try {
            const chats = await whatsappClient.getChats();
            const conversasFormatadas = await Promise.all(chats.map(async (chat) => {
                const idObj = chat.id || {};
                const number = idObj.user || 'unknown';
                let contact = null;
                try { contact = await chat.getContact(); } catch (err) { /* ignore */ }
                let profilePicUrl = '';
                try {
                    if (contact && typeof contact.getProfilePicUrl === 'function') {
                        profilePicUrl = await contact.getProfilePicUrl();
                    }
                } catch (err) { /* ignore */ }
                const name = (contact && (contact.name || contact.pushname)) || (chat.name || number);
                return {
                    id: idObj._serialized || number, name, number,
                    isGroup: !!chat.isGroup,
                    lastMessage: chat.lastMessage ? (chat.lastMessage.body || '') : '',
                    profilePicUrl: profilePicUrl || ''
                };
            }));
            return { sucesso: true, chats: conversasFormatadas };
        } catch (e) {
            return { sucesso: false, erro: e && e.message ? e.message : String(e) };
        }
    });

    // 7) Buscar Histórico Recente (Sua lógica)
    ipcMain.handle('fetch-chat-history', async (event, number) => {
        if (!whatsappClient || !whatsappClient.info) {
            return { sucesso: false, erro: 'Cliente WhatsApp desconectado.' };
        }
        try {
            const chatId = `${number}@c.us`; 
            const chat = await whatsappClient.getChatById(chatId);
            if (!chat) return { sucesso: false, erro: 'Chat não encontrado.' };
            
            const messages = await chat.fetchMessages({ limit: 20 });
            const history = messages.map(msg => ({
                texto: msg.body,
                timestamp: new Date(msg.timestamp * 1000).toLocaleTimeString(),
                sender: msg.fromMe ? 'Eu' : (msg.author ? msg.author.split('@')[0] : 'Cliente')
            })).reverse();
            
            return { sucesso: true, history: history };
        } catch (e) {
            return { sucesso: false, erro: e.message || String(e) };
        }
    });

    // 8) Configurar Credenciais (Sua lógica)
    ipcMain.handle('config-whatsapp-credentials', (event, { token, id }) => {
        WHATSAPP_TOKEN = token;
        PHONE_NUMBER_ID = id;
        return { sucesso: true, status: 'Credenciais atualizadas' };
    });

}); // <-- FIM DO BLOCO app.whenReady().then()

// =========================================================================
// 5. EVENTOS GLOBAIS (FORA DO 'whenReady')
// =========================================================================
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});