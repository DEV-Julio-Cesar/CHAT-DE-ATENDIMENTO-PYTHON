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
const ExcelJS = require('exceljs');

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

// Instalar handler global de unhandledRejection para mitigar EBUSY originados por LocalAuth
try {
  const WhatsAppClientService = require('./src/services/WhatsAppClientService').default || require('./src/services/WhatsAppClientService');
  if (WhatsAppClientService && typeof WhatsAppClientService.ensureGlobalUnhandledRejectionHandler === 'function') {
    WhatsAppClientService.ensureGlobalUnhandledRejectionHandler();
  }
} catch (e) {
  // Se falhar, apenas logar e prosseguir — não deve impedir a inicialização do app
  try { const logger = require('./src/infraestrutura/logger'); logger.aviso('[BOOT] Não foi possível instalar handler global de unhandledRejection: ' + (e && e.message ? e.message : e)); } catch(_) { console.warn('[BOOT] Não foi possível instalar handler global de unhandledRejection:', e); }
}

const gerenciadorMensagens = require('./src/aplicacao/gerenciador-mensagens');
const gerenciadorMidia = require('./src/aplicacao/gerenciador-midia');
const chatbot = require('./src/aplicacao/chatbot');
const metricas = require('./src/aplicacao/metricas');
const notificacoes = require('./src/aplicacao/notificacoes');
const gerenciadorFilas = require('./src/aplicacao/gerenciador-filas');
const automacaoConfig = require('./src/aplicacao/automacao-config');
const campanhas = require('./src/aplicacao/campanhas');
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

function selecionarClienteWhatsAppParaCampanha(preferencialId) {
    if (!poolWhatsApp) {
        return { success: false, code: 'pool_not_ready', message: 'Pool WhatsApp não está inicializado.' };
    }

    if (preferencialId) {
        const preferencial = poolWhatsApp.clients.get(preferencialId);
        if (preferencial && preferencial.status === 'ready') {
            return { success: true, clientId: preferencialId, usouFallback: false };
        }
    }

    const prontos = typeof poolWhatsApp.getReadyClients === 'function' ? poolWhatsApp.getReadyClients() : [];
    if (Array.isArray(prontos) && prontos.length > 0) {
        return { success: true, clientId: prontos[0], usouFallback: Boolean(preferencialId && prontos[0] !== preferencialId) };
    }

    return { success: false, code: 'no_clients', message: 'Nenhuma sessão WhatsApp pronta para envio.' };
}

function construirChatIdWhatsApp(destinatario) {
    if (!destinatario) return null;
    const valor = String(destinatario).trim();
    if (!valor) return null;
    if (valor.endsWith('@c.us') || valor.endsWith('@g.us')) {
        return valor;
    }
    return `${valor}@c.us`;
}

async function gerarPromptIAParaCampanha(campanha) {
    if (!campanha?.usarAgenteIA) {
        return { success: false };
    }

    try {
        const destaques = [];
        if (campanha.nome) {
            destaques.push(`Campanha: ${campanha.nome}`);
        }
        if (campanha.finalidadeDescricao || campanha.finalidade) {
            destaques.push(`Finalidade: ${campanha.finalidadeDescricao || campanha.finalidade}`);
        }
        if (campanha.mensagemBase) {
            const previewMensagem = campanha.mensagemBase.length > 320
                ? `${campanha.mensagemBase.slice(0, 317)}...`
                : campanha.mensagemBase;
            destaques.push(`Mensagem base: ${previewMensagem}`);
        }

        const resposta = await automacaoConfig.gerarPromptPreview({
            instrucoesAdicionais: campanha.instrucoesIA,
            destaques
        });

        if (resposta?.success && resposta.prompt) {
            return { success: true, prompt: resposta.prompt, destaques, geradoEm: new Date().toISOString() };
        }
    } catch (erro) {
        logger.erro('[Campanhas] Erro ao gerar prompt IA:', erro.message);
    }

    return { success: false };
}

async function executarDisparoWhatsapp(campanha, destinatarios) {
    const selecaoCliente = selecionarClienteWhatsAppParaCampanha(campanha?.clientePreferencial);
    if (!selecaoCliente.success) {
        return {
            success: false,
            motivo: selecaoCliente.message,
            code: selecaoCliente.code || 'no_clients'
        };
    }

    const detalhes = [];
    let enviados = 0;
    let falhas = 0;

    for (const numero of destinatarios) {
        const chatId = construirChatIdWhatsApp(numero);
        if (!chatId) {
            falhas += 1;
            detalhes.push({ destinatario: numero, status: 'erro', erro: 'Número inválido' });
            continue;
        }

        try {
            const envio = await poolWhatsApp.sendMessage(selecaoCliente.clientId, chatId, campanha.mensagemBase);
            const messageId = (() => {
                if (!envio?.id) return null;
                if (typeof envio.id === 'string') return envio.id;
                if (typeof envio.id === 'object') {
                    return envio.id._serialized || envio.id.id || null;
                }
                return null;
            })();
            detalhes.push({
                destinatario: numero,
                chatId,
                status: 'enviado',
                messageId,
                timestamp: new Date().toISOString()
            });
            enviados += 1;
        } catch (erroEnvio) {
            logger.erro(`[Campanhas] Falha ao enviar mensagem de ${campanha?.id} para ${chatId}: ${erroEnvio.message}`);
            detalhes.push({
                destinatario: numero,
                chatId,
                status: 'erro',
                erro: erroEnvio.message || 'Falha ao enviar'
            });
            falhas += 1;
        }
    }

    return {
        success: enviados > 0,
        clientId: selecaoCliente.clientId,
        usouFallbackCliente: selecaoCliente.usouFallback,
        enviados,
        falhas,
        detalhes
    };
}

function textoDaCelula(valor) {
    if (valor === undefined || valor === null) return '';
    if (typeof valor === 'string') return valor.trim();
    return String(valor).trim();
}

function extrairDigitos(valor) {
    return String(valor || '').replace(/[^0-9]/g, '');
}

function detectarCabecalhoPlanilha(valores = []) {
    const mapa = {};
    valores.forEach((valor, index) => {
        const texto = textoDaCelula(valor).toLowerCase();
        if (!texto) return;
        if (mapa.nome === undefined && texto.includes('nome')) {
            mapa.nome = index;
        }
        if (mapa.telefone === undefined && (texto.includes('tel') || texto.includes('fone') || texto.includes('cel'))) {
            mapa.telefone = index;
        }
        if (mapa.cpf === undefined && texto.includes('cpf')) {
            mapa.cpf = index;
        }
    });
    if (mapa.nome !== undefined && mapa.telefone !== undefined && mapa.cpf !== undefined) {
        return mapa;
    }
    return null;
}

async function importarContatosDePlanilha(filePath) {
    if (!filePath) {
        throw new Error('Informe um arquivo para importar.');
    }

    const extensao = path.extname(filePath).toLowerCase();
    if (!['.xlsx', '.csv'].includes(extensao)) {
        throw new Error('Formato não suportado. Utilize arquivos .xlsx ou .csv.');
    }

    const workbook = new ExcelJS.Workbook();
    let worksheet;

    if (extensao === '.csv') {
        await workbook.csv.readFile(filePath);
        worksheet = workbook.worksheets[0];
    } else {
        await workbook.xlsx.readFile(filePath);
        worksheet = workbook.worksheets[0];
    }

    if (!worksheet) {
        throw new Error('Não encontramos dados na planilha.');
    }

    let cabecalho = null;
    const contatos = [];
    const vistos = new Set();

    worksheet.eachRow({ includeEmpty: false }, (row) => {
        const valores = row.values.slice(1);
        const possuiDados = valores.some((valor) => textoDaCelula(valor));
        if (!possuiDados) {
            return;
        }

        if (!cabecalho) {
            const possivelCabecalho = detectarCabecalhoPlanilha(valores);
            if (possivelCabecalho) {
                cabecalho = possivelCabecalho;
                return;
            }
            cabecalho = { nome: 0, telefone: 1, cpf: 2 };
        }

        const indiceNome = cabecalho.nome ?? 0;
        const indiceTelefone = cabecalho.telefone ?? 1;
        const indiceCpf = cabecalho.cpf ?? 2;

        const nome = textoDaCelula(valores[indiceNome]);
        const telefoneOriginal = textoDaCelula(valores[indiceTelefone]);
        const telefoneSanitizado = extrairDigitos(telefoneOriginal);
        if (!telefoneSanitizado || telefoneSanitizado.length < 8 || vistos.has(telefoneSanitizado)) {
            return;
        }

        vistos.add(telefoneSanitizado);

        const cpfOriginal = textoDaCelula(valores[indiceCpf]);
        const cpfSanitizado = extrairDigitos(cpfOriginal);

        contatos.push({
            nome: nome || null,
            telefone: telefoneSanitizado,
            telefoneOriginal: telefoneOriginal || telefoneSanitizado,
            cpf: cpfSanitizado || null,
            cpfOriginal: cpfOriginal || null
        });
    });

    if (contatos.length === 0) {
        throw new Error('Não encontramos contatos válidos na planilha.');
    }

    return {
        success: true,
        total: contatos.length,
        destinatarios: contatos.map((c) => c.telefone),
        contatos
    };
}

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
    // DESABILITADO - QR exibido via modal inline na janela principal
    logger.info(`[QR] createQRWindow DESABILITADO - usando modal inline para ${clientId}`);
    return;
    
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

    // abrir janela de chat (usa tela de filas como única UI)
    ipcMain.on('open-chat-window', (_event, payload) => {
        const params = (typeof payload === 'object' && payload !== null)
            ? payload
            : { clientId: payload };
        const usuarioInfo = usuarioLogado
            ? { usuario: usuarioLogado.username, role: usuarioLogado.role }
            : {};

        gerenciadorJanelas.navigate('chat-filas', {
            ...params,
            ...usuarioInfo
        });
    });

    // abrir dashboard
    ipcMain.on('open-dashboard', () => {
        gerenciadorJanelas.navigate('dashboard');
    });

    // abrir chatbot
    ipcMain.on('open-chatbot', () => {
        gerenciadorJanelas.navigate('chatbot');
    });
    
    ipcMain.on('open-automacao', () => {
        gerenciadorJanelas.navigate('automacao');
    });

    ipcMain.on('open-campanhas', () => {
        gerenciadorJanelas.navigate('campanhas');
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

    ipcMain.handle('whatsapp:get-contact-info', async (_event, { clientId, chatId } = {}) => {
        try {
            if (!clientId || !chatId) {
                return { success: false, message: 'clientId e chatId são obrigatórios' };
            }

            const client = whatsappClients.get(clientId);
            if (!client) {
                return { success: false, message: 'Cliente não conectado' };
            }

            let contact = null;
            try {
                contact = await client.getContactById(chatId);
            } catch (erroGetContact) {
                logger.aviso(`[Contato] Falha ao buscar contato ${chatId} via getContactById: ${erroGetContact.message}`);
            }

            if (!contact) {
                try {
                    const chat = await client.getChatById(chatId);
                    if (chat && typeof chat.getContact === 'function') {
                        contact = await chat.getContact();
                    }
                } catch (erroChat) {
                    logger.aviso(`[Contato] Não foi possível obter chat ${chatId}: ${erroChat.message}`);
                }
            }

            if (!contact) {
                return { success: false, message: 'Contato não encontrado' };
            }

            let profilePicUrl = '';
            try {
                if (typeof contact.getProfilePicUrl === 'function') {
                    profilePicUrl = await contact.getProfilePicUrl();
                }
            } catch (erroFoto) {
                logger.aviso(`[Contato] Não foi possível obter foto de ${chatId}: ${erroFoto.message}`);
            }

            const nomePreferencial = contact.verifiedName
                || contact.formattedName
                || contact.pushname
                || contact.name
                || contact.shortName
                || contact.number
                || chatId;

            return {
                success: true,
                contato: {
                    id: contact.id?._serialized || chatId,
                    numero: contact.id?.user || contact.number || '',
                    nome: nomePreferencial,
                    pushname: contact.pushname || '',
                    shortName: contact.shortName || '',
                    businessName: contact.verifiedName || '',
                    foto: profilePicUrl || ''
                }
            };
        } catch (erro) {
            logger.erro('[Contato WhatsApp] Erro ao obter informações:', erro.message);
            return { success: false, message: erro.message };
        }
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
    ipcMain.handle('attend:get-status', async (_e, username) => atend.obterStatusAtendente(username));

    // Filas de atendimento
    ipcMain.handle('filas:criar-conversa', async (_event, { clientId, chatId, metadata = {} } = {}) => {
        try {
            return await gerenciadorFilas.criarConversa(clientId, chatId, metadata || {});
        } catch (erro) {
            logger.erro('[Filas] Erro ao criar conversa:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:mover-espera', async (_event, { clientId, chatId, motivo } = {}) => {
        try {
            return await gerenciadorFilas.moverParaEspera(clientId, chatId, motivo);
        } catch (erro) {
            logger.erro('[Filas] Erro ao mover para espera:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:assumir', async (_event, { clientId, chatId, atendente } = {}) => {
        try {
            return await gerenciadorFilas.assumirConversa(clientId, chatId, atendente);
        } catch (erro) {
            logger.erro('[Filas] Erro ao assumir conversa:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:encerrar', async (_event, { clientId, chatId, atendente } = {}) => {
        try {
            return await gerenciadorFilas.encerrarConversa(clientId, chatId, atendente);
        } catch (erro) {
            logger.erro('[Filas] Erro ao encerrar conversa:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:listar-por-estado', async (_event, { estado, atendente } = {}) => {
        try {
            return await gerenciadorFilas.listarPorEstado(estado, atendente);
        } catch (erro) {
            logger.erro('[Filas] Erro ao listar por estado:', erro.message);
            return [];
        }
    });

    ipcMain.handle('filas:estatisticas', async () => {
        try {
            return await gerenciadorFilas.obterEstatisticas();
        } catch (erro) {
            logger.erro('[Filas] Erro ao obter estatísticas:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:atualizar-metadata', async (_event, { clientId, chatId, metadata = {} } = {}) => {
        try {
            return await gerenciadorFilas.atualizarMetadata(clientId, chatId, metadata || {});
        } catch (erro) {
            logger.erro('[Filas] Erro ao atualizar metadata:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:atribuir', async (_event, { clientId, chatId, atendente, atendenteOrigem } = {}) => {
        try {
            return await gerenciadorFilas.atribuirConversa(clientId, chatId, atendente, atendenteOrigem);
        } catch (erro) {
            logger.erro('[Filas] Erro ao atribuir conversa:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:transferir', async (_event, { clientId, chatId, atendenteDestino, atendenteOrigem } = {}) => {
        try {
            return await gerenciadorFilas.transferirConversa(clientId, chatId, atendenteDestino, atendenteOrigem);
        } catch (erro) {
            logger.erro('[Filas] Erro ao transferir conversa:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:atribuir-multiplos', async (_event, { conversasIds = [], atendente, atendenteOrigem } = {}) => {
        try {
            return await gerenciadorFilas.atribuirMultiplos(conversasIds, atendente, atendenteOrigem);
        } catch (erro) {
            logger.erro('[Filas] Erro ao atribuir múltiplas conversas:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:encerrar-multiplos', async (_event, { conversasIds = [], atendente } = {}) => {
        try {
            return await gerenciadorFilas.encerrarMultiplos(conversasIds, atendente);
        } catch (erro) {
            logger.erro('[Filas] Erro ao encerrar múltiplas conversas:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('filas:listar-atendentes', async () => {
        try {
            return await gerenciadorFilas.listarAtendentes();
        } catch (erro) {
            logger.erro('[Filas] Erro ao listar atendentes:', erro.message);
            return [];
        }
    });

    // RelatÃ³rios
    ipcMain.handle('report:export', async (_e, tipo) => relatorios.exportar(tipo));

    // Tema
    ipcMain.handle('theme:get', async () => ({ success: true, theme: await tema.getTheme() }));
    ipcMain.handle('theme:set', async (_e, themeName) => tema.setTheme(themeName));

    // Automação / Prompt Builder
    ipcMain.handle('automacao:obter-config', async () => {
        try {
            const config = await automacaoConfig.carregarConfiguracao();
            return { success: true, config };
        } catch (erro) {
            logger.erro('[Automacao] Erro ao carregar configuração:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('automacao:salvar-config', async (_event, configAtualizada) => {
        try {
            return await automacaoConfig.salvarConfiguracao(configAtualizada || {});
        } catch (erro) {
            logger.erro('[Automacao] Erro ao salvar configuração:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('automacao:gerar-prompt', async (_event, payload = {}) => {
        try {
            const resultado = await automacaoConfig.gerarPromptPreview(payload || {});
            return resultado;
        } catch (erro) {
            logger.erro('[Automacao] Erro ao gerar prompt:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('campanhas:listar', async () => {
        try {
            const campanhasRegistradas = await campanhas.listarCampanhas();
            return { success: true, campanhas: campanhasRegistradas };
        } catch (erro) {
            logger.erro('[Campanhas] Erro ao listar:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('campanhas:salvar', async (_event, campanha) => {
        try {
            return await campanhas.salvarCampanha(campanha || {});
        } catch (erro) {
            logger.erro('[Campanhas] Erro ao salvar:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('campanhas:remover', async (_event, idCampanha) => {
        try {
            return await campanhas.removerCampanha(idCampanha);
        } catch (erro) {
            logger.erro('[Campanhas] Erro ao remover:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('campanhas:importar-planilha', async (_event, payload = {}) => {
        try {
            const caminho = payload.filePath || payload.path;
            const resultado = await importarContatosDePlanilha(caminho);
            return resultado;
        } catch (erro) {
            logger.erro('[Campanhas] Erro ao importar planilha:', erro.message);
            return { success: false, message: erro.message };
        }
    });

    ipcMain.handle('campanhas:disparar', async (_event, payload = {}) => {
        const campanhaId = payload?.campanhaId || payload?.id;
        if (!campanhaId) {
            return { success: false, message: 'ID da campanha é obrigatório para disparo.' };
        }

        if (!poolWhatsApp) {
            return { success: false, message: 'Pool WhatsApp ainda não foi inicializado.' };
        }

        try {
            const campanha = await campanhas.obterCampanhaPorId(campanhaId);
            if (!campanha) {
                return { success: false, message: 'Campanha não encontrada.' };
            }

            const destinatarios = campanhas.sanitizarDestinatarios(campanha.destinatarios);
            if (destinatarios.length === 0) {
                return { success: false, message: 'Nenhum destinatário válido para disparo.' };
            }

            const canaisAtivos = Array.isArray(campanha.canais) && campanha.canais.length > 0
                ? [...new Set(campanha.canais)]
                : ['whatsapp'];

            const inicio = Date.now();
            const resultados = {};
            let totalEnviados = 0;
            let totalFalhas = 0;
            let clientUtilizado = null;
            let fallbackCliente = false;

            if (canaisAtivos.includes('whatsapp')) {
                const envioWhatsApp = await executarDisparoWhatsapp(campanha, destinatarios);
                if (envioWhatsApp.code === 'no_clients') {
                    return { success: false, message: envioWhatsApp.motivo || 'Nenhuma sessão WhatsApp pronta para envio.' };
                }

                resultados.whatsapp = {
                    enviados: envioWhatsApp.enviados,
                    falhas: envioWhatsApp.falhas,
                    detalhes: envioWhatsApp.detalhes,
                    clientId: envioWhatsApp.clientId
                };
                clientUtilizado = envioWhatsApp.clientId || null;
                fallbackCliente = Boolean(envioWhatsApp.usouFallbackCliente);
                totalEnviados += envioWhatsApp.enviados;
                totalFalhas += envioWhatsApp.falhas;
            }

            for (const canal of canaisAtivos) {
                if (canal === 'whatsapp') continue;
                resultados[canal] = {
                    status: 'pendente',
                    motivo: 'Integração ainda não disponível para este canal.',
                    totalPlanejado: destinatarios.length
                };
            }

            const duracaoMs = Date.now() - inicio;
            const statusFinal = totalEnviados > 0 && totalFalhas === 0
                ? 'executado'
                : totalEnviados > 0
                    ? 'parcial'
                    : 'erro';

            const promptIA = await gerarPromptIAParaCampanha(campanha);

            await campanhas.registrarHistoricoEnvio(campanhaId, {
                totalDestinatarios: destinatarios.length,
                canaisAtivos,
                resultados,
                clientId: clientUtilizado,
                mensagemUtilizada: campanha.mensagemBase,
                statusFinal,
                observacoes: totalFalhas ? `${totalFalhas} destinatário(s) falharam` : null,
                duracaoMs,
                iaAtivada: Boolean(campanha.usarAgenteIA),
                promptIA: promptIA?.prompt || null,
                instrucoesIA: campanha.instrucoesIA,
                destaquesIA: promptIA?.destaques || null,
                usouFallbackCliente: fallbackCliente
            });

            return {
                success: true,
                campanhaId,
                status: statusFinal,
                enviados: totalEnviados,
                falhas: totalFalhas,
                clientId: clientUtilizado,
                clientFallback: fallbackCliente,
                canais: canaisAtivos,
                ia: campanha.usarAgenteIA
                    ? {
                        ativa: true,
                        prompt: promptIA?.prompt || null,
                        geradoEm: promptIA?.geradoEm || null
                    }
                    : { ativa: false },
                resultados
            };
        } catch (erro) {
            logger.erro('[Campanhas] Erro ao disparar campanha:', erro);
            return { success: false, message: erro.message || 'Falha ao executar disparo.' };
        }
    });

    // Abrir nova conexão via QR (inline, sem nova janela)
    ipcMain.handle('open-new-qr-window', async () => {
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        logger.info(`[IPC] Iniciando conexão WhatsApp inline (sem nova janela) para ${clientId}`);

        const resultado = await poolWhatsApp.createAndInitialize(clientId);
        if (!resultado.success) {
            return { success: false, clientId, message: resultado.message };
        }

        return { success: true, clientId };
    });
    
    // Abrir janela de conexão por número
    ipcMain.handle('open-conexao-por-numero-window', async () => {
        createConexaoPorNumeroWindow();
        return { success: true };
    });
    
    // Iniciar nova conexão (cria cliente e inicia conexão WhatsApp)
    ipcMain.handle('iniciar-nova-conexao', async (_event) => {
        try {
            const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            logger.info(`[IPC] Iniciando nova conexão para ${clientId}`);
            
            const result = await poolWhatsApp.createAndInitialize(clientId);
            return result;
        } catch (erro) {
            logger.erro('[IPC] Erro ao iniciar nova conexão:', erro.message);
            return { success: false, message: erro.message };
        }
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
        const finalParams = { ...params };
        if (usuarioLogado) {
            if (!finalParams.usuario) {
                finalParams.usuario = usuarioLogado.username;
            }
            if (!finalParams.role) {
                finalParams.role = usuarioLogado.role;
            }
        }
        gerenciadorJanelas.navigate(route, finalParams);
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
    const autoReconnectFeatureEnabled = sinalizadoresRecursos.isEnabled('whatsapp.auto-reconnect');
    poolWhatsApp = new GerenciadorPoolWhatsApp({
        maxClients: whatsappConfig.maxClients || 10,
        sessionPath: path.join(__dirname, whatsappConfig.sessionPath || '.wwebjs_auth'),
        persistencePath: path.join(__dirname, 'dados', 'whatsapp-sessions.json'),
        autoReconnect: autoReconnectFeatureEnabled,
        reconnectDelay: 5000,
        healthCheckInterval: 60000,
        puppeteer: whatsappConfig.puppeteer,
        clientOptions: whatsappConfig.clientOptions,
        webVersionCache: whatsappConfig.webVersionCache,
        recovery: {
            ...(whatsappConfig.recovery || {}),
            autoReconnect: (whatsappConfig.recovery && typeof whatsappConfig.recovery.autoReconnect === 'boolean')
                ? whatsappConfig.recovery.autoReconnect
                : autoReconnectFeatureEnabled
        },
        keepAlive: whatsappConfig.keepAlive,
        
        // Callbacks globais
        onQR: (clientId, qrDataURL) => {
            const qrWindow = qrWindows.get(clientId);
            if (qrWindow && !qrWindow.isDestroyed()) {
                qrWindow.webContents.send('qr-code-data', qrDataURL);
            }
            
            // Enviar QR para todas as janelas (especialmente pool-manager)
            logger.info(`[QR] Enviando QR Code para todas as janelas - ${clientId}`);
            BrowserWindow.getAllWindows().forEach(win => {
                if (!win.isDestroyed()) {
                    win.webContents.send('qr-code-gerado', qrDataURL);
                }
            });
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
                    win.webContents.send('cliente-pronto-qr', clientId); // Fechar modal QR
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
            
            // Sincroniza conversa com o sistema de filas
            try {
                const contact = await message.getContact().catch(() => null);
                const nomeContato = contact?.pushname || contact?.name || chat.name || message.from;
                const corpoMensagem = message.body && message.body.trim().length > 0
                    ? message.body
                    : (message.hasMedia ? '[mídia]' : '[mensagem]');
                const metadata = {
                    nomeContato,
                    ultimaMensagem: corpoMensagem,
                    mensagensNaoLidas: chat.unreadCount || 0,
                    origem: 'whatsapp'
                };

                const conversaAtual = await gerenciadorFilas.buscarPorChatId(message.from);
                if (!conversaAtual) {
                    await gerenciadorFilas.criarConversa(clientId, message.from, metadata);
                } else {
                    await gerenciadorFilas.atualizarMetadata(clientId, message.from, metadata);
                }
            } catch (erroFilas) {
                logger.erro(`[Filas] Erro ao sincronizar conversa ${message.from}: ${erroFilas.message}`);
            }
            

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

