// =========================================================================
// SISTEMA DE ATENDIMENTO WHATSAPP - ARQUIVO PRINCIPAL
// =========================================================================

// =========================================================================
// 1. IMPORTAÃ‡Ã•ES
// =========================================================================
const { app, BrowserWindow, ipcMain, Menu, dialog, Notification } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const axios = require('axios');
const WebSocket = require('ws');
const { MessageMedia } = require('whatsapp-web.js');

// ImportaÃ§Ãµes dos mÃ³dulos internos
const iaGemini = require('./src/aplicacao/ia-gemini');
// Handler IPC para Gemini
ipcMain.handle('ia:gemini:perguntar', async (_event, { mensagem, contexto }) => {
    return await iaGemini.enviarPerguntaGemini({ mensagem, contexto });
});
const { validarCredenciais, obterNivelPermissao, obterDadosUsuario } = require('./src/aplicacao/validacao-credenciais');
const gerenciadorUsuarios = require('./src/aplicacao/gerenciador-usuarios');
const logger = require('./src/infraestrutura/logger');
const GerenciadorPoolWhatsApp = require('./src/services/GerenciadorPoolWhatsApp');
const GerenciadorJanelas = require('./src/services/GerenciadorJanelas');
const gerenciadorMensagens = require('./src/aplicacao/gerenciador-mensagens');
const gerenciadorMidia = require('./src/aplicacao/gerenciador-midia');
const chatbot = require('./src/aplicacao/chatbot');
const metricas = require('./src/aplicacao/metricas');
const notificacoes = require('./src/aplicacao/notificacoes');
const backups = require('./src/aplicacao/backup');
const atend = require('./src/aplicacao/atendimentos');
const relatorios = require('./src/aplicacao/relatorios');
const tema = require('./src/aplicacao/tema');
const { startApi } = require('./src/infraestrutura/api');

// Core Infrastructure
const gerenciadorConfiguracoes = require('./src/core/gerenciador-configuracoes');
const tratadorErros = require('./src/core/tratador-erros');
const monitorDesempenho = require('./src/core/monitor-desempenho');
const sinalizadoresRecursos = require('./src/core/sinalizadores-recursos');

// =========================================================================
// 2. VARIÃVEIS GLOBAIS
// =========================================================================

// Window Manager (gerencia navegaÃ§Ã£o entre telas)
let gerenciadorJanelas = null;

// Pool Manager de Clientes WhatsApp
let poolWhatsApp = null;
const qrWindows = new Map();

// ConfiguraÃ§Ãµes da API Cloud (WhatsApp Business)
let WHATSAPP_TOKEN = '';
let PHONE_NUMBER_ID = '';
const API_VERSION = 'v19.0';

// WebSocket
const WS_SERVER_URL = 'ws://localhost:8080';
let ws = null;
let internalWS = null;
let internalChatHistory = [];

// UsuÃ¡rio logado
let usuarioLogado = null;

// =========================================================================
// 3. FUNÃ‡Ã•ES DE CONEXÃƒO WEBSOCKET
// =========================================================================

/**
 * Conecta ao servidor WebSocket externo
 */
function connectWebSocket() {
    logger.info(`[WS] Conectando a ${WS_SERVER_URL}...`);
    
    ws = new WebSocket(WS_SERVER_URL);
    
    ws.on('open', () => {
        logger.info('[WS] ConexÃ£o estabelecida');
    });
    
    ws.on('message', (data) => {
        try {
            const mensagem = JSON.parse(data.toString());
            if (mainWindow) {
                mainWindow.webContents.send('nova-mensagem-recebida', mensagem);
            }
        } catch (erro) {
            logger.erro('[WS] Erro ao processar mensagem:', erro.message);
        }
    });
    
    ws.on('close', () => {
        logger.info('[WS] ConexÃ£o fechada. Reconectando em 5s...');
        setTimeout(connectWebSocket, 5000);
    });
    
    ws.on('error', (erro) => {
        logger.erro('[WS] Erro:', erro.message);
    });
}

/**
 * Conecta ao servidor de chat interno
 */
function connectInternalChat() {
    try {
        internalWS = new WebSocket('ws://localhost:9090');
        
        internalWS.on('open', () => {
            logger.info('[ChatInterno] Conectado');
        });
        
        internalWS.on('message', (data) => {
            try {
                const msg = JSON.parse(data.toString());
                if (msg.type === 'internal') {
                    internalChatHistory.push(msg);
                    if (mainWindow) {
                        mainWindow.webContents.send('internal-chat-message', msg);
                    }
                }
            } catch (erro) {
                logger.erro('[ChatInterno] Erro ao processar:', erro.message);
            }
        });
        
        internalWS.on('close', () => {
            logger.info('[ChatInterno] Desconectado. Reconectando...');
            setTimeout(connectInternalChat, 4000);
        });
        
        internalWS.on('error', (erro) => {
            logger.erro('[ChatInterno] Erro:', erro.message);
        });
    } catch (erro) {
        logger.erro('[ChatInterno] Falha na conexÃ£o:', erro.message);
    }
}

/**
 * Envia mensagem para o chat interno
 */
function sendInternalChatMessage(from, texto) {
    if (!internalWS || internalWS.readyState !== WebSocket.OPEN) {
        return { sucesso: false, erro: 'WebSocket indisponÃ­vel' };
    }
    
    const payload = { type: 'internal', from, texto, timestamp: Date.now() };
    internalWS.send(JSON.stringify(payload));
    
    return { sucesso: true };
}

// =========================================================================
// 4. FUNÃ‡Ã•ES DE API WHATSAPP CLOUD
// =========================================================================

/**
 * Envia mensagem via WhatsApp Cloud API
 */
async function enviarMensagemWhatsApp(numeroDestino, mensagem) {
    if (!WHATSAPP_TOKEN || !PHONE_NUMBER_ID) {
        throw new Error('Credenciais da API nÃ£o configuradas');
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
    } catch (erro) {
        const mensagemErro = erro.response?.data?.error?.message || erro.message;
        logger.erro('[API WhatsApp] Erro:', mensagemErro);
        throw new Error(`Falha na API: ${mensagemErro}`);
    }
}

// =========================================================================
// 5. FUNÃ‡Ã•ES DE CRIAÃ‡ÃƒO DE JANELAS
// =========================================================================

/**
 * Cria janela de login
 */
function createLoginWindow() {
    loginWindow = new BrowserWindow({
        width: 450,
        height: 600,
        resizable: false,
        frame: true,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-login.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    loginWindow.loadFile('src/interfaces/login.html');
    
    // Abrir DevTools automaticamente em desenvolvimento
    loginWindow.webContents.openDevTools();
    
    // Capturar erros do console
    loginWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
        const levels = ['log', 'warn', 'error', 'debug'];
        logger.info(`[Browser Console ${levels[level]}] ${message}`);
    });
    
    loginWindow.on('closed', () => {
        loginWindow = null;
        // Se fechar login sem autenticar, sai do app
        if (!mainWindow) {
            app.quit();
        }
    });
}

/**
 * Cria janela principal
 */
function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    mainWindow.loadFile('src/interfaces/index.html');
    
    // Envia dados do usuÃ¡rio logado
    mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.send('usuario-logado', usuarioLogado);
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

/**
 * Cria janela de histÃ³rico
 */
function createHistoryWindow() {
    if (historyWindow) {
        historyWindow.focus();
        return;
    }
    
    historyWindow = new BrowserWindow({
        width: 800,
        height: 700,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-historico.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    
    historyWindow.loadFile('src/interfaces/historico.html');
    historyWindow.on('closed', () => {
        historyWindow = null;
    });
}

/**
 * Cria janela de cadastro
 */
function createCadastroWindow() {
    const win = new BrowserWindow({
        width: 500,
        height: 650,
        resizable: false,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-cadastro.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    win.loadFile('src/interfaces/cadastro.html');
}

/**
 * Cria janela de QR Code para cliente especÃ­fico
 */
function createQRWindow(clientId) {
    if (qrWindows.has(clientId)) {
        qrWindows.get(clientId).focus();
        return;
    }
    
    const qrWindow = new BrowserWindow({
        width: 500,
        height: 650,
        title: `WhatsApp - ${clientId}`,
        resizable: false,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-qr.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    
    qrWindow.loadFile('src/interfaces/janela-qr.html');
    qrWindows.set(clientId, qrWindow);
    
    qrWindow.webContents.once('did-finish-load', () => {
        qrWindow.webContents.send('set-client-id', clientId);
    });
    
    qrWindow.on('closed', () => {
        qrWindows.delete(clientId);
    });
}

/**
 * Cria janela de gerenciamento de mÃºltiplos clientes WhatsApp
 */
function createPoolManagerWindow() {
    const win = new BrowserWindow({
        width: 1200,
        height: 800,
        title: 'Gerenciador de ConexÃµes WhatsApp',
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-gerenciador-pool.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    win.loadFile('src/interfaces/gerenciador-pool.html');
}

/**
 * Cria janela de usuÃ¡rios
 */
function createUsuariosWindow() {
    const win = new BrowserWindow({
        width: 900,
        height: 650,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-usuarios.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    win.loadFile('src/interfaces/usuarios.html');
}

/**
 * Cria janela de chat
 */
function createChatWindow(clientId) {
    const win = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-chat.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    win.loadFile('src/interfaces/chat.html');
    
    win.webContents.on('did-finish-load', () => {
        win.webContents.send('set-client-id', clientId);
    });
}

/**
 * Cria janela do dashboard
 */
function createDashboardWindow() {
    const win = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-painel.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    win.loadFile('src/interfaces/painel.html');
}

/**
 * Cria janela do chatbot
 */
function createChatbotWindow() {
    const win = new BrowserWindow({
        width: 900,
        height: 700,
        webPreferences: {
            preload: path.join(__dirname, 'src/interfaces/pre-carregamento-chatbot.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    win.loadFile('src/interfaces/chatbot.html');
}

// =========================================================================
// 6. CONFIGURAÃ‡ÃƒO DE MENU
// =========================================================================

function criarMenuPrincipal() {
    const menuTemplate = [
        {
            label: 'Arquivo',
            submenu: [
                {
                    label: 'Recarregar',
                    accelerator: 'Ctrl+R',
                    click: () => {
                        if (mainWindow) mainWindow.reload();
                    }
                },
                { type: 'separator' },
                {
                    label: 'Sair',
                    accelerator: 'Ctrl+Q',
                    click: () => {
                        app.quit();
                    }
                }
            ]
        },
        {
            label: 'NavegaÃ§Ã£o',
            submenu: [
                {
                    label: 'Voltar',
                    accelerator: 'Alt+Left',
                    click: () => {
                        if (mainWindow) mainWindow.webContents.goBack();
                    }
                },
                {
                    label: 'AvanÃ§ar',
                    accelerator: 'Alt+Right',
                    click: () => {
                        if (mainWindow) mainWindow.webContents.goForward();
                    }
                }
            ]
        },
        {
            label: 'Visualizar',
            submenu: [
                {
                    label: 'Tela Cheia',
                    accelerator: 'F11',
                    click: (item, focusedWindow) => {
                        if (focusedWindow) {
                            focusedWindow.setFullScreen(!focusedWindow.isFullScreen());
                        }
                    }
                }
            ]
        },
        {
            label: 'Ajuda',
            submenu: [
                {
                    label: 'Sobre',
                    click: () => {
                        dialog.showMessageBox(mainWindow, {
                            type: 'info',
                            title: 'Sobre',
                            message: 'Sistema de Atendimento WhatsApp',
                            detail: 'VersÃ£o 1.0\nDesenvolvido com Electron e whatsapp-web.js'
                        });
                        
                        if (Notification.isSupported()) {
                            new Notification({
                                title: 'InformaÃ§Ã£o',
                                body: 'VocÃª estÃ¡ usando a versÃ£o 1.0'
                            }).show();
                        }
                    }
                }
            ]
        }
    ];
    
    const menu = Menu.buildFromTemplate(menuTemplate);
    Menu.setApplicationMenu(menu);
}

// =========================================================================
// 7. GERENCIAMENTO DE CLIENTES WHATSAPP
// =========================================================================

/**
 * Inicializa cliente WhatsApp com QR Code
 */
/**
 * Inicializa um cliente WhatsApp atravÃ©s do Pool Manager
 * @deprecated Use poolWhatsApp.createAndInitialize() diretamente
 */
async function inicializarClienteWhatsApp(clientId) {
    try {
        logger.info(`[${clientId}] Criando cliente no pool...`);
        return await poolWhatsApp.createAndInitialize(clientId);
    } catch (erro) {
        logger.erro(`[${clientId}] Erro ao inicializar:`, erro.message);
        return { success: false, message: erro.message };
    }
}

// =========================================================================
// 8. MANIPULADORES IPC
// =========================================================================

function configurarManipuladoresIPC() {
    // Login
    ipcMain.handle('login-attempt', async (_event, { username, password }) => {
        try {
            const valido = await validarCredenciais(username, password);
            
            if (!valido) {
                return { success: false, message: 'UsuÃ¡rio ou senha invÃ¡lidos' };
            }
            
            const role = await obterNivelPermissao(username);
            const dados = await obterDadosUsuario(username);
            
            usuarioLogado = { username, role, ...dados };
            
            logger.sucesso(`[Login] ${username} autenticado com sucesso (${role})`);
            // Auditoria de login
            try { require('./src/infraestrutura/auditoria').logAudit('login.success', { user: username, details: { role } }); } catch(e) {}
            
            // Registra atendente no sistema
            await atend.registrarAtendente(username);
            
            return { success: true, role, dados };
            
        } catch (erro) {
            logger.erro('[Login] Erro:', erro.message);
            try { require('./src/infraestrutura/auditoria').logAudit('login.error', { user: username, details: { erro: erro.message } }); } catch(e) {}
            return { success: false, message: 'Erro ao processar login: ' + erro.message };
        }
    });

    ipcMain.on('close-login-window', () => {
        // ApÃ³s login bem sucedido definimos 'principal' como raiz
        if (gerenciadorJanelas) {
            gerenciadorJanelas.resetHistory('principal');
        } else {
            gerenciadorJanelas.navigate('principal');
        }
    });

    ipcMain.on('open-register-window', () => {
        gerenciadorJanelas.navigate('cadastro');
    });

    // abrir lista de usuÃ¡rios
    // NavegaÃ§Ã£o simplificada (mantÃ©m compatibilidade)
    ipcMain.on('open-users-window', () => {
        gerenciadorJanelas.navigate('usuarios');
    });

    // abrir gerenciador de pool de clientes
    ipcMain.on('open-pool-manager', () => {
        gerenciadorJanelas.navigate('pool-manager');
    });

    // abrir janela de chat
    ipcMain.on('open-chat-window', (_event, clientId) => {
        gerenciadorJanelas.navigate('chat', { clientId });
    });

    // abrir dashboard
    ipcMain.on('open-dashboard', () => {
        gerenciadorJanelas.navigate('dashboard');
    });

    // abrir chatbot
    ipcMain.on('open-chatbot', () => {
        gerenciadorJanelas.navigate('chatbot');
    });
    
    // Restaurar sessÃµes persistidas
    ipcMain.handle('restore-persisted-sessions', async () => {
        return await poolWhatsApp.restorePersistedSessions();
    });

    // API de cadastro
    ipcMain.handle('register-new-user', async (event, newUser) => {
        try {
            const res = await gerenciadorUsuarios.cadastrarUsuario(newUser);
            return res;
        } catch (erro) {
            logger.erro('[Cadastro] Erro:', erro.message);
            return { success: false, message: 'Falha ao cadastrar usuÃ¡rio: ' + erro.message };
        }
    });

    ipcMain.handle('register-user', async (_event, dados) => {
        try {
            const result = await gerenciadorUsuarios.cadastrarUsuario(dados);
            return result;
        } catch (erro) {
            return { success: false, message: erro.message };
        }
    });

    // MÃ©tricas
    ipcMain.handle('get-metrics', async () => {
        return await metricas.obterMetricas();
    });

    ipcMain.handle('reset-metrics', async () => {
        return await metricas.resetarMetricas();
    });

    // APIs de usuÃ¡rios
    ipcMain.handle('list-users', async () => {
        try {
            const users = await gerenciadorUsuarios.listarUsuarios();
            return { success: true, users };
        } catch (erro) {
            logger.erro('[Listar UsuÃ¡rios] Erro:', erro.message);
            return { success: false, users: [], message: erro.message };
        }
    });

    ipcMain.handle('get-user-stats', async () => {
        try {
            const stats = await gerenciadorUsuarios.obterEstatisticas();
            return { success: true, stats };
        } catch (erro) {
            logger.erro('[EstatÃ­sticas] Erro:', erro.message);
            return { success: false, stats: {}, message: erro.message };
        }
    });

    ipcMain.handle('remove-user', async (_e, username) => {
        try {
            const res = await gerenciadorUsuarios.removerUsuario(username);
            return res;
        } catch (erro) {
            logger.erro('[Remover UsuÃ¡rio] Erro:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('set-user-active', async (_e, { username, ativo }) => {
        try {
            const res = await gerenciadorUsuarios.definirAtivo(username, ativo);
            return res;
        } catch (erro) {
            logger.erro('[Ativar/Desativar UsuÃ¡rio] Erro:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    // --- ENVIO DE MENSAGENS ---
    
    ipcMain.handle('send-whatsapp-message', async (event, { numero, mensagem, clientId, chatId, message }) => {
        try {
            // Formato novo (chat.html): { clientId, chatId, message }
            if (clientId && chatId && message) {
                const result = await poolWhatsApp.sendMessage(clientId, chatId, message);
                if (!result.success) {
                    return result;
                }
                
                // Registra mÃ©trica
                await metricas.registrarMensagemEnviada();
                // Auditoria
                try { require('./src/infraestrutura/auditoria').logAudit('message.send', { user: usuarioLogado?.username, details: { clientId, chatId }}); } catch(e) {}
                
                await gerenciadorMensagens.salvarMensagem(clientId, chatId, {
                    id: { id: result.messageId || Date.now() },
                    timestamp: Date.now(),
                    from: 'me',
                    to: chatId,
                    body: message,
                    type: 'chat',
                    fromMe: true,
                    hasMedia: false
                });

                logger.sucesso(`[${clientId}] Mensagem enviada para ${chatId}`);
                return { success: true };
            }
            
            // Formato antigo (index.html): { numero, mensagem, clientId }
            if (numero && mensagem) {
                // Se tem clientId, usa cliente especÃ­fico
                if (clientId && whatsappClients.has(clientId)) {
                    const client = whatsappClients.get(clientId);
                    if (client.info) {
                        await client.sendMessage(`${numero}@c.us`, mensagem);
                        try { require('./src/infraestrutura/auditoria').logAudit('message.send', { user: usuarioLogado?.username, details: { numero }}); } catch(e) {}
                        return { sucesso: true, dados: { status: 'enviado', clientId } };
                    }
                }
                
                // Caso contrÃ¡rio, tenta API Cloud
                if (WHATSAPP_TOKEN && !WHATSAPP_TOKEN.startsWith('TOKEN_DE_TESTE_')) {
                    const resultado = await enviarMensagemWhatsApp(numero, mensagem);
                    return { sucesso: true, dados: resultado };
                }
                
                return { sucesso: false, erro: 'Nenhum cliente disponÃ­vel' };
            }
            
            return { success: false, message: 'ParÃ¢metros invÃ¡lidos' };
            
        } catch (erro) {
            logger.erro('[Enviar Mensagem] Erro:', erro.message);
            return { success: false, sucesso: false, message: erro.message, erro: erro.message };
        }
    });
    
    // Enviar mensagem com mÃ­dia
    ipcMain.handle('send-whatsapp-media', async (_event, { clientId, chatId, filePath, caption }) => {
        try {
            const client = whatsappClients.get(clientId);
            if (!client) {
                return { success: false, message: 'Cliente nÃ£o conectado' };
            }

            const media = MessageMedia.fromFilePath(filePath);
            await client.sendMessage(chatId, media, { caption: caption || '' });

            logger.sucesso(`[${clientId}] MÃ­dia enviada para ${chatId}`);
            return { success: true };

        } catch (erro) {
            logger.erro('[Enviar MÃ­dia] Erro:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    // Download de mÃ­dia recebida
    ipcMain.handle('download-whatsapp-media', async (_event, { clientId, messageId }) => {
        try {
            const client = whatsappClients.get(clientId);
            if (!client) {
                return { success: false, message: 'Cliente nÃ£o conectado' };
            }

            // Implemente a lÃ³gica de download conforme necessÃ¡rio
            return { success: true };

        } catch (erro) {
            logger.erro('[Download MÃ­dia] Erro:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    // --- CHATS E HISTÃ“RICO ---
    
    ipcMain.handle('list-whatsapp-chats', async (_event, clientId) => {
        try {
            const client = whatsappClients.get(clientId);
            if (!client) {
                return { success: false, message: 'Cliente nÃ£o conectado', chats: [] };
            }

            const chats = await client.getChats();
            
            const chatList = chats.map(chat => ({
                id: chat.id._serialized,
                name: chat.name || chat.id.user,
                isGroup: chat.isGroup,
                unreadCount: chat.unreadCount,
                timestamp: chat.timestamp || 0
            }));

            // Ordena por timestamp (mais recente primeiro)
            chatList.sort((a, b) => b.timestamp - a.timestamp);

            return { success: true, chats: chatList };

        } catch (erro) {
            logger.erro('[Listar Chats] Erro:', erro.message);
            return { success: false, chats: [], message: erro.message };
        }
    });

    // Carregar histÃ³rico de mensagens
    ipcMain.handle('load-chat-history', async (_event, { clientId, chatId }) => {
        try {
            const result = await gerenciadorMensagens.carregarHistorico(clientId, chatId);
            return result;
        } catch (erro) {
            logger.erro('[Carregar HistÃ³rico] Erro:', erro.message);
            return { success: false, mensagens: [], message: erro.message };
        }
    });

    // --- MENSAGENS RÃPIDAS ---
    const mensagensRapidas = require('./src/aplicacao/mensagens-rapidas');
    ipcMain.handle('quick-messages-list', async () => {
        return { success: true, mensagens: await mensagensRapidas.carregarTodas() };
    });
    ipcMain.handle('quick-messages-get', async (_e, codigo) => {
        const msg = await mensagensRapidas.obterPorCodigo(codigo);
        return msg ? { success: true, mensagem: msg } : { success: false, message: 'NÃ£o encontrada' };
    });
    ipcMain.handle('quick-messages-add', async (_e, { codigo, texto }) => {
        return await mensagensRapidas.adicionarMensagem(codigo, texto);
    });
    ipcMain.handle('quick-messages-remove', async (_e, codigo) => {
        return await mensagensRapidas.removerMensagem(codigo);
    });
    ipcMain.handle('quick-messages-metrics', async () => {
        return await mensagensRapidas.obterMetricas();
    });
    ipcMain.handle('quick-messages-metrics-reset', async () => {
        return await mensagensRapidas.resetMetricas();
    });
    ipcMain.handle('quick-messages-registrar-uso', async (_e, codigo) => {
        return await mensagensRapidas.registrarUso(codigo);
    });
    
    ipcMain.handle('fetch-whatsapp-chats', async (event, clientId) => {
        const client = clientId ? whatsappClients.get(clientId) : Array.from(whatsappClients.values())[0];
        
        if (!client || !client.info) {
            return { sucesso: false, erro: 'Cliente nÃ£o conectado' };
        }
        
        try {
            const chats = await client.getChats();
            const conversasFormatadas = await Promise.all(
                chats.map(async (chat) => {
                    const number = chat.id.user || 'unknown';
                    let contact = null;
                    let profilePicUrl = '';
                    
                    try {
                        contact = await chat.getContact();
                        if (contact && typeof contact.getProfilePicUrl === 'function') {
                            profilePicUrl = await contact.getProfilePicUrl();
                        }
                    } catch (err) {
                        // Ignora erros de perfil
                    }
                    
                    const name = contact?.name || contact?.pushname || chat.name || number;
                    
                    return {
                        id: chat.id._serialized,
                        name,
                        number,
                        isGroup: !!chat.isGroup,
                        lastMessage: chat.lastMessage?.body || '',
                        profilePicUrl: profilePicUrl || '',
                        unreadCount: chat.unreadCount || 0
                    };
                })
            );
            
            return { sucesso: true, chats: conversasFormatadas };
        } catch (erro) {
            return { sucesso: false, erro: erro.message };
        }
    });
    
    ipcMain.handle('fetch-chat-history', async (event, { number, clientId }) => {
        const client = clientId ? whatsappClients.get(clientId) : Array.from(whatsappClients.values())[0];
        
        if (!client || !client.info) {
            return { sucesso: false, erro: 'Cliente nÃ£o conectado' };
        }
        
        try {
            const chatId = `${number}@c.us`;
            const chat = await client.getChatById(chatId);
            
            if (!chat) {
                return { sucesso: false, erro: 'Chat nÃ£o encontrado' };
            }
            
            const messages = await chat.fetchMessages({ limit: 50 });
            const history = messages.map(msg => ({
                texto: msg.body,
                timestamp: new Date(msg.timestamp * 1000).toLocaleString('pt-BR'),
                sender: msg.fromMe ? 'Eu' : (msg.author?.split('@')[0] || 'Cliente'),
                fromMe: msg.fromMe,
                hasMedia: msg.hasMedia
            })).reverse();
            
            return { sucesso: true, history };
        } catch (erro) {
            return { sucesso: false, erro: erro.message };
        }
    });
    
    ipcMain.on('open-history-search-window', () => {
        createHistoryWindow();
    });
    
    ipcMain.handle('search-chat-history', async (event, filters) => {
        // ImplementaÃ§Ã£o futura com banco de dados
        return { 
            sucesso: false, 
            erro: 'Busca de histÃ³rico requer banco de dados' 
        };
    });
    
    // --- CONFIGURAÃ‡Ã•ES ---
    
    ipcMain.handle('config-whatsapp-credentials', (event, { token, id }) => {
        WHATSAPP_TOKEN = token;
        PHONE_NUMBER_ID = id;
        return { sucesso: true, status: 'Credenciais atualizadas' };
    });
    
    // --- CHAT INTERNO ---
    
    ipcMain.handle('internal-chat-send', (event, { from, texto }) => {
        return sendInternalChatMessage(from, texto);
    });
    
    ipcMain.handle('internal-chat-history', () => {
        return { 
            sucesso: true, 
            history: internalChatHistory.slice(-100) 
        };
    });
    
    // --- INTERFACE ---
    
    ipcMain.on('set-fullscreen', (event, flag) => {
        const win = BrowserWindow.getFocusedWindow();
        if (win) {
            win.setFullScreen(flag);
        }
    });

    // Controle de notificaÃ§Ãµes
    ipcMain.handle('toggle-notifications', async (_event, ativo) => {
        notificacoes.setAtivo(ativo);
        return { success: true, ativo };
    });

    // Backups
    ipcMain.handle('backup:run', async () => backups.runBackupNow());
    ipcMain.handle('backup:list', async () => ({ success: true, files: await backups.listBackups() }));

    // Atendimentos
    ipcMain.handle('attend:register', async (_e, username) => atend.registrarAtendente(username));
    ipcMain.handle('attend:set-status', async (_e, { username, status }) => atend.setStatus(username, status));
    ipcMain.handle('attend:claim', async (_e, { username, clientId, chatId }) => atend.assumirChat(username, clientId, chatId));
    ipcMain.handle('attend:release', async (_e, { username, clientId, chatId }) => atend.liberarChat(username, clientId, chatId));
    ipcMain.handle('attend:get', async (_e, { clientId, chatId }) => atend.obterAtendimento(clientId, chatId));
    ipcMain.handle('attend:list', async () => atend.listarAtendimentos());

    // RelatÃ³rios
    ipcMain.handle('report:export', async (_e, tipo) => relatorios.exportar(tipo));

    // Tema
    ipcMain.handle('theme:get', async () => ({ success: true, theme: await tema.getTheme() }));
    ipcMain.handle('theme:set', async (_e, themeName) => tema.setTheme(themeName));

    // Abrir nova janela QR
    ipcMain.handle('open-new-qr-window', async () => {
        const clientId = `client_${Date.now()}`;
        createQRWindow(clientId);
        return { success: true, clientId };
    });

    // Iniciar conexÃ£o WhatsApp
    ipcMain.handle('start-whatsapp-connection', async (_event, clientId) => {
        try {
            const result = await inicializarClienteWhatsApp(clientId);
            return result;
        } catch (erro) {
            logger.erro('[WhatsApp] Erro ao iniciar conexÃ£o:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    // Listar clientes conectados
    ipcMain.handle('list-connected-clients', async () => {
        return poolWhatsApp.getReadyClients();
    });

    // Listar todos os clientes com informaÃ§Ãµes detalhadas
    ipcMain.handle('list-all-clients-info', async () => {
        return poolWhatsApp.getAllClientsInfo();
    });

    // Obter estatÃ­sticas do pool
    ipcMain.handle('get-pool-stats', async () => {
        return poolWhatsApp.getStats();
    });

    // Desconectar cliente
    ipcMain.handle('disconnect-client', async (_event, clientId) => {
        return await poolWhatsApp.removeClient(clientId);
    });

    // Reconectar cliente
    ipcMain.handle('reconnect-client', async (_event, clientId) => {
        return await poolWhatsApp.reconnectClient(clientId);
    });

    // Fazer logout de cliente (remove sessÃ£o)
    ipcMain.handle('logout-client', async (_event, clientId) => {
        const client = poolWhatsApp.clients.get(clientId);
        if (!client) {
            return { success: false, message: 'Cliente nÃ£o encontrado' };
        }
        const result = await client.logout();
        if (result.success) {
            await poolWhatsApp.removeClient(clientId);
        }
        return result;
    });

    // Chatbot
    ipcMain.handle('get-chatbot-rules', async () => {
        try {
            const rules = await chatbot.carregarRegras();
            return { success: true, rules };
        } catch (erro) {
            logger.erro('[Chatbot] Erro ao carregar regras:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('save-chatbot-rules', async (_event, rules) => {
        try {
            const result = await chatbot.salvarRegras(rules);
            return result;
        } catch (erro) {
            logger.erro('[Chatbot] Erro ao salvar regras:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    // Health Status
    ipcMain.handle('health:get-status', async () => {
        try {
            const messageQueue = require('./src/core/fila-mensagens');
            const poolStats = poolWhatsApp.getStats();
            const memUsage = process.memoryUsage();
            const uptimeSec = process.uptime();
            const uptimeStr = uptimeSec < 60 ? `${Math.floor(uptimeSec)}s` : 
                              uptimeSec < 3600 ? `${Math.floor(uptimeSec / 60)}m` : 
                              `${Math.floor(uptimeSec / 3600)}h`;
            
            const clientsInfo = poolWhatsApp.getAllClientsInfo().map(c => ({
                clientId: c.clientId,
                status: c.status,
                phoneNumber: c.phoneNumber
            }));

            return {
                pool: {
                    totalClients: poolStats.totalClients,
                    readyClients: poolStats.readyClients,
                    clients: clientsInfo
                },
                queue: {
                    size: messageQueue.size()
                },
                memory: {
                    usedMB: memUsage.heapUsed / 1024 / 1024
                },
                uptime: uptimeStr
            };
        } catch (erro) {
            logger.erro('[Health] Erro:', erro.message);
            return { error: erro.message };
        }
    });
}

// =========================================================================
// 9. HANDLERS DE NAVEGAÃ‡ÃƒO
// =========================================================================

function setupNavigationHandlers() {
    // Navegar para uma rota
    ipcMain.handle('navigate-to', async (_event, route, params = {}) => {
        logger.info(`[Navigation] Navegando para: ${route}`);
        gerenciadorJanelas.navigate(route, params);
        return { success: true };
    });

    // Voltar
    ipcMain.handle('navigate-back', async () => {
        const success = gerenciadorJanelas.goBack();
        return { success };
    });

    // AvanÃ§ar
    ipcMain.handle('navigate-forward', async () => {
        const success = gerenciadorJanelas.goForward();
        return { success };
    });

    // Obter estado de navegaÃ§Ã£o
    ipcMain.handle('navigation-get-state', async () => {
        return {
            canGoBack: gerenciadorJanelas.canGoBack(),
            canGoForward: gerenciadorJanelas.canGoForward(),
            currentRoute: gerenciadorJanelas.getCurrentRoute()
        };
    });

    logger.info('[Navigation] Handlers configurados');
}

// =========================================================================
// 10. INICIALIZAÃ‡ÃƒO DO APLICATIVO
// =========================================================================

app.whenReady().then(async () => {
    // ========================================
    // CORE INFRASTRUCTURE SETUP
    // ========================================
    
    // 1. Carregar configuraÃ§Ã£o
    try {
        gerenciadorConfiguracoes.load();
        logger.sucesso('[Config] ConfiguraÃ§Ã£o carregada com sucesso');
    } catch (error) {
        logger.erro('[Config] Falha ao carregar configuraÃ§Ã£o:', error.message);
    }

    // 2. Configurar error handler global
    try {
        tratadorErros.setupGlobalHandlers();
        logger.sucesso('[tratadorErros] Handlers globais configurados');
    } catch (error) {
        logger.erro('[tratadorErros] Falha na configuraÃ§Ã£o:', error.message);
    }

    // 3. Iniciar performance monitoring
    try {
        if (gerenciadorConfiguracoes.get('monitoring.monitorDesempenhoing', true)) {
            monitorDesempenho.startEventLoopMonitoring();
            logger.sucesso('[PerfMonitor] Monitoramento de performance iniciado');
        }
    } catch (error) {
        logger.erro('[PerfMonitor] Falha na inicializaÃ§Ã£o:', error.message);
    }

    // 4. Carregar feature flags
    try {
        const enabledFlags = sinalizadoresRecursos.getAllFlags()
            .filter(f => f.enabled)
            .map(f => f.name);
        logger.info(`[sinalizadoresRecursos] ${enabledFlags.length} flags habilitadas`);
        
        if (sinalizadoresRecursos.hasExperimentalEnabled()) {
            logger.alerta('[sinalizadoresRecursos] âš ï¸ Features experimentais ativadas');
        }
    } catch (error) {
        logger.erro('[sinalizadoresRecursos] Falha ao carregar flags:', error.message);
    }

    // ========================================
    // APPLICATION SETUP
    // ========================================
    
    // Inicializar Window Manager
    gerenciadorJanelas = new GerenciadorJanelas();
    logger.info('[App] Window Manager inicializado');
    
    // Registrar logger e gerenciadorJanelas no DI
    try {
        const di = require('./src/core/injecao-dependencias');
        di.register('logger', logger);
        di.register('gerenciadorJanelas', gerenciadorJanelas);
        di.register('gerenciadorConfiguracoes', gerenciadorConfiguracoes);
        di.register('tratadorErros', tratadorErros);
        di.register('monitorDesempenho', monitorDesempenho);
        di.register('sinalizadoresRecursos', sinalizadoresRecursos);
        logger.sucesso('[DI] Core modules registrados no DI Container');
    } catch(e) {
        logger.erro('[DI] Falha ao registrar modules:', e.message);
    }
    
    // Inicializar Pool Manager de WhatsApp
    const whatsappConfig = gerenciadorConfiguracoes.get('whatsapp', {});
    poolWhatsApp = new GerenciadorPoolWhatsApp({
        maxClients: whatsappConfig.maxClients || 10,
        sessionPath: path.join(__dirname, whatsappConfig.sessionPath || '.wwebjs_auth'),
        persistencePath: path.join(__dirname, 'dados', 'whatsapp-sessions.json'),
        autoReconnect: sinalizadoresRecursos.isEnabled('whatsapp.auto-reconnect'),
        reconnectDelay: 5000,
        healthCheckInterval: 60000,
        
        // Callbacks globais
        onQR: (clientId, qrDataURL) => {
            const qrWindow = qrWindows.get(clientId);
            if (qrWindow && !qrWindow.isDestroyed()) {
                qrWindow.webContents.send('qr-code-data', qrDataURL);
            }
        },
        
        onReady: (clientId, phoneNumber) => {
            logger.sucesso(`[Pool] Cliente ${clientId} pronto - Telefone: ${phoneNumber || 'N/A'}`);
            
            // NotificaÃ§Ã£o
            notificacoes.notificarClienteConectado(clientId);
            
            // Notifica janela QR especÃ­fica
            const qrWindow = qrWindows.get(clientId);
            if (qrWindow && !qrWindow.isDestroyed()) {
                qrWindow.webContents.send('whatsapp-ready', clientId);
            }
            
            // Notifica todas as janelas
            BrowserWindow.getAllWindows().forEach(win => {
                if (!win.isDestroyed()) {
                    win.webContents.send('new-client-ready', { clientId, phoneNumber, timestamp: Date.now() });
                }
            });
        },
        
        onMessage: async (clientId, message) => {
            if (message.fromMe || message.from.includes('@g.us')) return;
            
            logger.info(`[${clientId}] Nova mensagem de ${message.from}: ${message.body}`);
            
            // NotificaÃ§Ã£o
            const chat = await message.getChat();
            notificacoes.notificarNovaMensagem(chat.name || message.from, message.body);
            
            // Salva no histÃ³rico
            await gerenciadorMensagens.salvarMensagem(clientId, message.from, {
                id: message.id,
                timestamp: message.timestamp * 1000,
                from: message.from,
                to: message.to,
                body: message.body,
                type: message.type,
                fromMe: message.fromMe,
                hasMedia: message.hasMedia
            });
            

            // Processa com chatbot
            const resposta = await chatbot.processarMensagem(message.body, message.from, clientId);
            if (resposta.devResponder) {
                await poolWhatsApp.sendMessage(clientId, message.from, resposta.resposta);
                logger.info(`[${clientId}] Chatbot respondeu: ${resposta.resposta}`);
            } else {
                // Se chatbot nÃ£o souber, aciona Gemini
                const prompt = `VocÃª Ã© um agente virtual de atendimento de provedor de internet. Responda de forma clara, cordial e objetiva. Mensagem do cliente: "${message.body}"`;
                try {
                    const iaResp = await iaGemini.enviarPerguntaGemini({ mensagem: prompt });
                    if (iaResp.success && iaResp.resposta) {
                        await poolWhatsApp.sendMessage(clientId, message.from, iaResp.resposta);
                        logger.info(`[${clientId}] Gemini respondeu: ${iaResp.resposta}`);
                    } else {
                        logger.info(`[${clientId}] Gemini nÃ£o respondeu: ${iaResp.message}`);
                    }
                } catch (e) {
                    logger.erro(`[${clientId}] Erro ao acionar Gemini:`, e.message);
                }
            }
            
            // Registra mÃ©trica
            await metricas.registrarMensagemRecebida();
            
            // Notifica todas as janelas
            BrowserWindow.getAllWindows().forEach(win => {
                if (!win.isDestroyed()) {
                    win.webContents.send('nova-mensagem-recebida', {
                        clientId,
                        chatId: message.from,
                        mensagem: {
                            id: message.id.id,
                            body: message.body,
                            timestamp: message.timestamp * 1000,
                            fromMe: message.fromMe
                        }
                    });
                }
            });
        },
        
        onDisconnected: (clientId, reason) => {
            logger.aviso(`[Pool] Cliente ${clientId} desconectado: ${reason}`);
            notificacoes.notificarClienteDesconectado(clientId);
        },
        
        onAuthFailure: (clientId, message) => {
            logger.erro(`[Pool] Falha de autenticaÃ§Ã£o ${clientId}: ${message}`);
        }
    });
    // Registrar pool no DI
    try {
        const di = require('./src/core/injecao-dependencias');
        di.register('poolWhatsApp', poolWhatsApp);
    } catch(e) {
        logger.erro('[DI] Falha ao registrar poolWhatsApp:', e.message);
    }
    
    // Iniciar health check periÃ³dico
    poolWhatsApp.startHealthCheck();
    
    logger.info('[Pool] WhatsApp Pool Manager inicializado');
    
    configurarManipuladoresIPC();
    criarMenuPrincipal();
    
    // Inicia com tela de login
    createLoginWindow();
    
    // Configura backups e API
    if (sinalizadoresRecursos.isEnabled('backup.auto')) {
        backups.scheduleBackups();
        logger.info('[Backup] Backup automÃ¡tico agendado');
    }
    
    const apiConfig = gerenciadorConfiguracoes.get('api', {});
    if (apiConfig.enabled !== false && sinalizadoresRecursos.isEnabled('monitoring.metrics')) {
        startApi({
        getClients: () => poolWhatsApp.getReadyClients(),
        getStats: () => poolWhatsApp.getStats(),
        getAllClientsInfo: () => poolWhatsApp.getAllClientsInfo(),
        listChats: async (clientId) => {
            try {
                const clientInfo = poolWhatsApp.getClientInfo(clientId);
                if (!clientInfo || clientInfo.status !== 'ready') {
                    return { success: false, chats: [], message: 'Cliente nÃ£o conectado' };
                }
                
                const client = poolWhatsApp.clients.get(clientId).client;
                const chats = await client.getChats();
                return {
                    success: true,
                    chats: chats.map(c => ({ id: c.id._serialized, name: c.name || c.id.user, isGroup: c.isGroup }))
                };
            } catch (e) {
                return { success: false, chats: [], message: e.message };
            }
        },
        sendMessage: async ({ clientId, chatId, message }) => {
            return await poolWhatsApp.sendMessage(clientId, chatId, message);
        }
        });
        logger.sucesso(`[API] Servidor iniciado na porta ${apiConfig.port || 3333}`);
    } else {
        logger.info('[API] API desabilitada por configuraÃ§Ã£o');
    }
    
    // Configurar handlers de navegaÃ§Ã£o
    setupNavigationHandlers();
    
    // Iniciar com tela de login
    gerenciadorJanelas.navigate('login');
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        gerenciadorJanelas.navigate('login');
    }
});

app.on('before-quit', async () => {
    logger.info('=== Encerrando Aplicativo ===');
    
    // Performance report
    try {
        if (gerenciadorConfiguracoes.get('monitoring.monitorDesempenhoing', true)) {
            monitorDesempenho.report();
        }
    } catch (error) {
        logger.erro('[PerfMonitor] Erro ao gerar relatÃ³rio:', error.message);
    }
    
    // Salvar configuraÃ§Ã£o
    try {
        gerenciadorConfiguracoes.save();
        logger.info('[Config] ConfiguraÃ§Ã£o salva');
    } catch (error) {
        logger.erro('[Config] Erro ao salvar:', error.message);
    }
    
    // Shutdown gracioso do pool
    if (poolWhatsApp) {
        await poolWhatsApp.shutdown();
    }
    
    // NotificaÃ§Ã£o de saÃ­da
    if (Notification.isSupported()) {
        new Notification({
            title: 'Encerrando...',
            body: 'Salvando dados. AtÃ© logo!',
            silent: true
        }).show();
    }
    
    // Fecha WebSockets
    if (ws) ws.close();
    if (internalWS) internalWS.close();
});

// =========================================================================
// FIM DO ARQUIVO
// =========================================================================

