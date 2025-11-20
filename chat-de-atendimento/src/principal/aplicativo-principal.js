/**
 * =========================================================================
 * APLICATIVO PRINCIPAL - CHAT DE ATENDIMENTO WHATSAPP
 * =========================================================================
 * 
 * Este é o arquivo principal do aplicativo Electron que gerencia:
 * - Inicialização do aplicativo
 * - Criação de janelas (login, principal, cadastro, histórico)
 * - Comunicação IPC entre processos
 * - Integração com WhatsApp Web.js
 * - Servidores WebSocket internos
 * - Sistema de autenticação de usuários
 * 
 * Estrutura do Aplicativo:
 * - Login → Janela Principal → Chat WhatsApp
 * - Sistema de cadastro de usuários
 * - Histórico de conversas
 * - Chat interno entre atendentes
 * 
 * @author Sistema Chat Atendimento
 * @version 2.0.0
 * @since 2024
 */

// =========================================================================
// 1. IMPORTAÇÕES E DEPENDÊNCIAS
// =========================================================================
const { app, BrowserWindow, ipcMain, dialog, Notification, Menu } = require('electron');
const path = require('path');
const axios = require('axios');
const WebSocket = require('ws');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const fs = require('fs-extra');

// Importações locais do sistema
const { validarCredenciais } = require('../autenticacao/validador-credenciais');
const gerenciadorUsuarios = require('../autenticacao/gerenciador-usuarios');

// =========================================================================
// 2. VARIÁVEIS GLOBAIS E CONFIGURAÇÕES
// =========================================================================

/**
 * Configurações da API do WhatsApp Business
 */
let TOKEN_WHATSAPP = '';
let ID_NUMERO_TELEFONE = '';
let VERSAO_API = 'v19.0';

/**
 * Referências das janelas do aplicativo
 */
let janelaLogin = null;
let janelaPrincipal = null;
let janelaHistorico = null;
let janelasCadastro = new Map(); // Múltiplas janelas de cadastro

/**
 * Clientes WhatsApp e QR Code
 */
let clienteWhatsapp = null;
let clientesWhatsapp = {}; // Múltiplos clientes por usuário
let janelasQR = {}; // Janelas de QR Code por usuário

/**
 * Configurações de WebSocket
 */
const URL_SERVIDOR_WS = 'ws://localhost:8080';
let conexaoWS = null;
let conexaoWSInterna = null;
let historicoConversasInternas = [];

// =========================================================================
// 3. FUNÇÕES DE INICIALIZAÇÃO
// =========================================================================

/**
 * Conecta ao servidor de chat interno entre atendentes
 * @returns {void}
 */
function conectarChatInterno() {
    try {
        conexaoWSInterna = new WebSocket('ws://localhost:9090');
        
        conexaoWSInterna.on('open', () => {
            console.log('[ChatInterno] Conectado ao servidor interno');
        });
        
        conexaoWSInterna.on('message', dados => {
            let mensagem;
            try { 
                mensagem = JSON.parse(dados.toString()); 
            } catch { 
                return; 
            }
            
            if (mensagem.type === 'internal') {
                historicoConversasInternas.push(mensagem);
                if (janelaPrincipal) {
                    janelaPrincipal.webContents.send('mensagem-chat-interno', mensagem);
                }
            }
        });
        
        conexaoWSInterna.on('close', () => {
            console.log('[ChatInterno] Conexão fechada, tentando reconectar...');
            setTimeout(conectarChatInterno, 4000);
        });
        
        conexaoWSInterna.on('error', erro => {
            console.error('[ChatInterno] Erro na conexão:', erro.message);
        });
    } catch (erro) {
        console.error('[ChatInterno] Falha ao conectar:', erro.message);
    }
}

/**
 * Conecta ao servidor WebSocket principal
 * @returns {void}
 */
function conectarServidorWebSocket() {
    try {
        conexaoWS = new WebSocket(URL_SERVIDOR_WS);
        
        conexaoWS.on('open', () => {
            console.log('[WebSocket] Conectado ao servidor principal');
        });
        
        conexaoWS.on('message', dados => {
            try {
                const mensagem = JSON.parse(dados.toString());
                console.log('[WebSocket] Nova mensagem recebida:', mensagem);
                
                if (janelaPrincipal) {
                    janelaPrincipal.webContents.send('nova-mensagem-whatsapp', mensagem);
                }
            } catch (erro) {
                console.error('[WebSocket] Erro ao processar mensagem:', erro);
            }
        });
        
        conexaoWS.on('close', () => {
            console.log('[WebSocket] Conexão perdida, tentando reconectar...');
            setTimeout(conectarServidorWebSocket, 5000);
        });
        
        conexaoWS.on('error', erro => {
            console.error('[WebSocket] Erro na conexão:', erro.message);
        });
    } catch (erro) {
        console.error('[WebSocket] Falha ao conectar:', erro.message);
    }
}

// =========================================================================
// 4. GERENCIAMENTO DE JANELAS
// =========================================================================

/**
 * Cria e configura a janela de login
 * @returns {BrowserWindow} Janela de login criada
 */
function criarJanelaLogin() {
    janelaLogin = new BrowserWindow({
        width: 450,
        height: 600,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, '../interfaces/preload-login.js')
        },
        icon: path.join(__dirname, '../../assets/icon.png'),
        title: 'Login - Chat de Atendimento',
        show: false
    });

    janelaLogin.loadFile(path.join(__dirname, '../interfaces/login.html'));

    janelaLogin.once('ready-to-show', () => {
        janelaLogin.show();
    });

    janelaLogin.on('closed', () => {
        janelaLogin = null;
    });

    return janelaLogin;
}

/**
 * Cria e configura a janela principal do aplicativo
 * @returns {BrowserWindow} Janela principal criada
 */
function criarJanelaPrincipal() {
    janelaPrincipal = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, '../interfaces/preload-principal.js')
        },
        icon: path.join(__dirname, '../../assets/icon.png'),
        title: 'Chat de Atendimento WhatsApp',
        show: false
    });

    janelaPrincipal.loadFile(path.join(__dirname, '../interfaces/janela-principal.html'));

    janelaPrincipal.once('ready-to-show', () => {
        janelaPrincipal.show();
        conectarServidorWebSocket();
        conectarChatInterno();
    });

    janelaPrincipal.on('closed', () => {
        janelaPrincipal = null;
    });

    return janelaPrincipal;
}

/**
 * Cria janela de cadastro de usuários
 * @returns {BrowserWindow} Janela de cadastro
 */
function criarJanelaCadastro() {
    const janelaCadastro = new BrowserWindow({
        width: 500,
        height: 650,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, '../interfaces/preload-cadastro.js')
        },
        icon: path.join(__dirname, '../../assets/icon.png'),
        title: 'Cadastrar Novo Usuário',
        parent: janelaLogin || janelaPrincipal,
        modal: true,
        show: false
    });

    janelaCadastro.loadFile(path.join(__dirname, '../interfaces/cadastro.html'));

    janelaCadastro.once('ready-to-show', () => {
        janelaCadastro.show();
    });

    janelaCadastro.on('closed', () => {
        janelasCadastro.delete(janelaCadastro.id);
    });

    janelasCadastro.set(janelaCadastro.id, janelaCadastro);
    return janelaCadastro;
}

/**
 * Cria janela de histórico de conversas
 * @returns {BrowserWindow} Janela de histórico
 */
function criarJanelaHistorico() {
    if (janelaHistorico) {
        janelaHistorico.focus();
        return janelaHistorico;
    }

    janelaHistorico = new BrowserWindow({
        width: 1000,
        height: 700,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, '../interfaces/preload-historico.js')
        },
        icon: path.join(__dirname, '../../assets/icon.png'),
        title: 'Histórico de Conversas',
        show: false
    });

    janelaHistorico.loadFile(path.join(__dirname, '../interfaces/historico.html'));

    janelaHistorico.once('ready-to-show', () => {
        janelaHistorico.show();
    });

    janelaHistorico.on('closed', () => {
        janelaHistorico = null;
    });

    return janelaHistorico;
}

// =========================================================================
// 5. MANIPULADORES IPC (COMUNICAÇÃO ENTRE PROCESSOS)
// =========================================================================

/**
 * Configura todos os manipuladores IPC do aplicativo
 */
function configurarManipuladoresIPC() {
    
    // =====================================================
    // AUTENTICAÇÃO E LOGIN
    // =====================================================
    
    /**
     * Processa tentativa de login do usuário
     */
    ipcMain.handle('tentar-login', async (evento, { usuario, senha }) => {
        try {
            console.log(`[Login] Tentativa de login para usuário: ${usuario}`);
            
            // Validação usando sistema dual (fixos + cadastrados)
            const credenciaisValidas = await validarCredenciais(usuario, senha);
            
            if (credenciaisValidas) {
                console.log(`[Login] Login aprovado para: ${usuario}`);
                
                // Fecha janela de login e abre principal
                if (janelaLogin) {
                    janelaLogin.close();
                }
                criarJanelaPrincipal();
                
                return { sucesso: true, mensagem: 'Login realizado com sucesso!' };
            } else {
                console.log(`[Login] Login rejeitado para: ${usuario}`);
                return { sucesso: false, mensagem: 'Usuário ou senha incorretos.' };
            }
        } catch (erro) {
            console.error('[Login] Erro durante autenticação:', erro);
            return { sucesso: false, mensagem: 'Erro interno no sistema.' };
        }
    });

    /**
     * Abre janela de cadastro
     */
    ipcMain.handle('abrir-janela-cadastro', async () => {
        try {
            criarJanelaCadastro();
            return { sucesso: true };
        } catch (erro) {
            console.error('[Cadastro] Erro ao abrir janela:', erro);
            return { sucesso: false, mensagem: 'Erro ao abrir tela de cadastro.' };
        }
    });

    // =====================================================
    // GERENCIAMENTO DE USUÁRIOS
    // =====================================================
    
    /**
     * Registra novo usuário no sistema
     */
    ipcMain.handle('registrar-novo-usuario', async (evento, dadosUsuario) => {
        try {
            console.log('[Cadastro] Registrando novo usuário:', dadosUsuario.usuario);
            
            const resultado = await gerenciadorUsuarios.criarUsuario(
                dadosUsuario.usuario,
                dadosUsuario.senha,
                dadosUsuario.email,
                dadosUsuario.nomeCompleto
            );
            
            if (resultado.sucesso) {
                console.log('[Cadastro] Usuário cadastrado com sucesso:', dadosUsuario.usuario);
                return { sucesso: true, mensagem: 'Usuário cadastrado com sucesso!' };
            } else {
                return { sucesso: false, mensagem: resultado.mensagem };
            }
        } catch (erro) {
            console.error('[Cadastro] Erro ao registrar usuário:', erro);
            return { sucesso: false, mensagem: 'Erro interno ao cadastrar usuário.' };
        }
    });

    /**
     * Lista todos os usuários cadastrados
     */
    ipcMain.handle('listar-usuarios', async () => {
        try {
            const usuarios = await gerenciadorUsuarios.listarUsuarios();
            return { sucesso: true, usuarios };
        } catch (erro) {
            console.error('[Usuarios] Erro ao listar usuários:', erro);
            return { sucesso: false, mensagem: 'Erro ao carregar lista de usuários.' };
        }
    });

    // =====================================================
    // WHATSAPP - CONFIGURAÇÃO E MENSAGENS
    // =====================================================
    
    /**
     * Configura credenciais da API do WhatsApp Business
     */
    ipcMain.handle('configurar-credenciais-whatsapp', async (evento, { token, id }) => {
        try {
            TOKEN_WHATSAPP = token;
            ID_NUMERO_TELEFONE = id;
            
            console.log('[WhatsApp] Credenciais configuradas');
            return { sucesso: true, mensagem: 'Credenciais configuradas com sucesso!' };
        } catch (erro) {
            console.error('[WhatsApp] Erro ao configurar credenciais:', erro);
            return { sucesso: false, mensagem: 'Erro ao configurar credenciais.' };
        }
    });

    /**
     * Envia mensagem via API do WhatsApp Business
     */
    ipcMain.handle('enviar-mensagem-whatsapp', async (evento, { numero, mensagem }) => {
        try {
            if (!TOKEN_WHATSAPP || !ID_NUMERO_TELEFONE) {
                return { sucesso: false, mensagem: 'Credenciais não configuradas.' };
            }

            const url = `https://graph.facebook.com/${VERSAO_API}/${ID_NUMERO_TELEFONE}/messages`;
            const dados = {
                messaging_product: 'whatsapp',
                to: numero,
                text: { body: mensagem }
            };

            const resposta = await axios.post(url, dados, {
                headers: {
                    'Authorization': `Bearer ${TOKEN_WHATSAPP}`,
                    'Content-Type': 'application/json'
                }
            });

            console.log('[WhatsApp] Mensagem enviada:', resposta.data);
            return { sucesso: true, dados: resposta.data };
        } catch (erro) {
            console.error('[WhatsApp] Erro ao enviar mensagem:', erro);
            return { sucesso: false, mensagem: 'Erro ao enviar mensagem.' };
        }
    });

    // =====================================================
    // JANELAS SECUNDÁRIAS
    // =====================================================
    
    /**
     * Abre janela de histórico de conversas
     */
    ipcMain.handle('abrir-janela-historico', async () => {
        try {
            criarJanelaHistorico();
            return { sucesso: true };
        } catch (erro) {
            console.error('[Historico] Erro ao abrir janela:', erro);
            return { sucesso: false, mensagem: 'Erro ao abrir histórico.' };
        }
    });

    /**
     * Envia mensagem no chat interno entre atendentes
     */
    ipcMain.handle('enviar-mensagem-interna', async (evento, { remetente, mensagem }) => {
        try {
            if (conexaoWSInterna && conexaoWSInterna.readyState === WebSocket.OPEN) {
                const dadosMensagem = {
                    type: 'internal',
                    from: remetente,
                    texto: mensagem,
                    timestamp: Date.now()
                };
                
                conexaoWSInterna.send(JSON.stringify(dadosMensagem));
                console.log('[ChatInterno] Mensagem enviada:', dadosMensagem);
                
                return { sucesso: true };
            } else {
                return { sucesso: false, mensagem: 'Chat interno não conectado.' };
            }
        } catch (erro) {
            console.error('[ChatInterno] Erro ao enviar mensagem:', erro);
            return { sucesso: false, mensagem: 'Erro ao enviar mensagem interna.' };
        }
    });
}

// =========================================================================
// 6. EVENTOS DO APLICATIVO ELECTRON
// =========================================================================

/**
 * Quando o aplicativo estiver pronto
 */
app.whenReady().then(() => {
    console.log('[App] Aplicativo iniciado com sucesso');
    
    // Configura manipuladores IPC
    configurarManipuladoresIPC();
    
    // Cria janela de login
    criarJanelaLogin();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            criarJanelaLogin();
        }
    });
});

/**
 * Quando todas as janelas forem fechadas
 */
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

/**
 * Antes do aplicativo fechar
 */
app.on('before-quit', () => {
    console.log('[App] Aplicativo sendo fechado...');
    
    // Fecha conexões WebSocket
    if (conexaoWS) {
        conexaoWS.close();
    }
    if (conexaoWSInterna) {
        conexaoWSInterna.close();
    }
    
    // Fecha clientes WhatsApp
    Object.values(clientesWhatsapp).forEach(cliente => {
        if (cliente) {
            cliente.destroy();
        }
    });
});

// =========================================================================
// 7. EXPORTAÇÕES
// =========================================================================

module.exports = {
    criarJanelaLogin,
    criarJanelaPrincipal,
    criarJanelaCadastro,
    criarJanelaHistorico
};

console.log('[App] Módulo principal carregado');
