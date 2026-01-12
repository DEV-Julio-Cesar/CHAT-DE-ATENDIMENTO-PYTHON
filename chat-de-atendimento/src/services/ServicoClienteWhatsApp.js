/**
 * 📱 ServicoClienteWhatsApp
 * 
 * Serviço isolado que gerencia um único cliente WhatsApp.
 * Responsável por:
 * - Inicialização e autenticação
 * - Geração de QR Code
 * - Gerenciamento de eventos
 * - Envio e recebimento de mensagens
 * - Desconexão segura
 */

const { Client } = require('whatsapp-web.js');
const LocalAuthPersistent = require('./LocalAuthPersistent');
const qrcode = require('qrcode');
const fs = require('fs-extra');
const path = require('path');
const logger = require('../infraestrutura/logger');

async function limparSessao(sessionPath, clientId, tentativas = 3) {
    const sessionDir = path.join(sessionPath, `session-${clientId}`);
    for (let tentativa = 1; tentativa <= tentativas; tentativa++) {
        try {
            await fs.remove(sessionDir);
            logger.info(`[${clientId}] Sessão local removida (${sessionDir})`);
            return true;
        } catch (erro) {
            logger.aviso(`[${clientId}] Falha ao remover sessão (tentativa ${tentativa}/${tentativas}): ${erro.message}`);
            if (tentativa === tentativas) {
                return false;
            }
            await new Promise(resolve => setTimeout(resolve, 500 * tentativa));
        }
    }
    return false;
}

class ServicoClienteWhatsApp {
    /**
     * @param {string} clientId - ID único do cliente
     * @param {Object} options - Opções de configuração
     * @param {string} options.sessionPath - Caminho base para sessões
     * @param {Function} options.onQR - Callback para QR Code gerado
     * @param {Function} options.onReady - Callback quando cliente está pronto
     * @param {Function} options.onMessage - Callback para mensagens recebidas
     * @param {Function} options.onDisconnected - Callback quando desconectado
     * @param {Function} options.onAuthFailure - Callback para falha de autenticação
     */
    constructor(clientId, options = {}) {
        this.clientId = clientId;
        this.client = null;
        this._status = 'idle'; // idle, initializing, qr_ready, authenticated, ready, disconnected, error
        this.qrCode = null;
        this.phoneNumber = null;
        this.sessionPath = options.sessionPath || path.join(process.cwd(), '.wwebjs_auth');
        
        // Referência à estratégia de autenticação (será definida em initialize())
        this._authStrategy = null;
        
        // Callbacks
        this.callbacks = {
            onQR: options.onQR || (() => {}),
            onReady: options.onReady || (() => {}),
            onMessage: options.onMessage || (() => {}),
            onDisconnected: options.onDisconnected || (() => {}),
            onAuthFailure: options.onAuthFailure || (() => {})
        };
        
        this.metadata = {
            createdAt: new Date().toISOString(),
            lastQRAt: null,
            connectedAt: null,
            messageCount: 0
        };

        // Guarda o último motivo de desconexão para decisões no Pool/HealthCheck
        this.lastDisconnectReason = null;

        // Heartbeat/Keep-alive - Aumentado para reduzir sobrecarga
        this._heartbeatTimer = null;
        this._heartbeatIntervalMs = 30000; // ✅ 30s (aumentado de 60s para detectar desconexões mais rápido)
        this._limpandoSessaoPromise = null;

        // Garantir contexto correto quando o pool chamar o utilitário
        this.limparSessaoLocal = this.limparSessaoLocal.bind(this);
    }


    // Getter/Setter para status com métricas
    get status() {
        return this._status;
    }

    set status(newStatus) {
        if (this._status !== newStatus) {
            const prometheusMetrics = require('../core/metricas-prometheus');
            prometheusMetrics.incrementCounter('whatsapp_status_changes_total', { 
                clientId: this.clientId, 
                from: this._status, 
                to: newStatus 
            });
            this._status = newStatus;
        }
    }

    /**
     * Inicializa o cliente WhatsApp
     */
    async initialize() {
        if (['initializing', 'authenticated', 'ready'].includes(this.status)) {
            logger.aviso(`[${this.clientId}] Cliente já está ${this.status} - pulando reinit`);
            return { success: true, message: 'Cliente já está inicializado', clientId: this.clientId };
        }

        try {
            this.status = 'initializing';
            logger.info(`[${this.clientId}] Iniciando cliente WhatsApp...`);

            // Criar instância do cliente com LocalAuthPersistent (preserva sessão em logout automático)
            // TESTE: headless=false para verificar se é detecção de automação
            const headless = false; // Mudar para true após teste
            
            // Guardar referência ao authStrategy para poder habilitar cleanup quando necessário
            this._authStrategy = new LocalAuthPersistent({
                clientId: this.clientId,
                dataPath: this.sessionPath
            });
            
            this.client = new Client({
                authStrategy: this._authStrategy,
                puppeteer: {
                    headless,
                    args: [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                        // Argumentos adicionais para evitar detecção e melhorar estabilidade
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-infobars',
                        '--window-size=1920,1080',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        // User agent para evitar detecção
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ]
                },// Configurações adicionais para manter sessão estável
                webVersionCache: {
                    type: 'local'
                },
                // Intervalo de QR mais longo para evitar renovação frequente
                qrMaxRetries: 10,
                // Permitir tomar controle da sessão se houver conflito (outra instância conectada)
                takeoverOnConflict: true,
                takeoverTimeoutMs: 5000
            });

            // Registrar listeners de eventos ANTES de inicializar
            // Isso garante que o evento de QR seja capturado
            this._setupEventListeners();

            logger.info(`[${this.clientId}] Listeners configurados, iniciando cliente...`);

            // Inicializar cliente com timeout maior (90s) para evitar timeouts falsos
            // Cliente pode levar tempo para escanear QR e autenticar
            const initPromise = this.client.initialize();
            const timeoutPromise = new Promise((resolve, reject) => {
                setTimeout(() => {
                    reject(new Error('Timeout de inicialização (90s) - verifique se QR foi escaneado'));
                }, 90000);
            });

            try {
                await Promise.race([initPromise, timeoutPromise]);
            } catch (timeoutError) {
                logger.aviso(`[${this.clientId}] ${timeoutError.message}`);
                // Não erro fatal, apenas aviso - o cliente pode estar aguardando QR
            }

            logger.info(`[${this.clientId}] Cliente inicializado, aguardando QR Code...`);
            return { success: true, clientId: this.clientId };
        } catch (erro) {
            this.status = 'error';
            logger.erro(`[${this.clientId}] Erro ao inicializar:`, erro.message);
            return { success: false, message: erro.message };
        }
    }

    /**
     * Configura listeners de eventos do cliente WhatsApp
     */
    _setupEventListeners() {
        // Remove todos os listeners anteriores para evitar duplicação
        if (this.client) {
            this.client.removeAllListeners('qr');
            this.client.removeAllListeners('authenticated');
            this.client.removeAllListeners('ready');
            this.client.removeAllListeners('message');
            this.client.removeAllListeners('disconnected');
            this.client.removeAllListeners('auth_failure');
            this.client.removeAllListeners('loading_screen');
            this.client.removeAllListeners('error');
            this.client.removeAllListeners('warn');
        }
        
        // Proteção contra erros não capturados do Puppeteer/Browser
        if (this.client && this.client.pupBrowser) {
            this.client.pupBrowser.removeAllListeners('disconnected');
        }
          // QR Code gerado
        // IMPORTANTE: Ignorar QR codes quando já está autenticado/pronto para evitar desconexões indevidas
        this.client.on('qr', async (qr) => {
            try {
                // Se já está autenticado ou pronto, ignorar novo QR (pode ser tentativa de re-auth do WhatsApp)
                if (this.status === 'authenticated' || this.status === 'ready') {
                    logger.aviso(`[${this.clientId}] QR Code recebido mas cliente já está ${this.status} - IGNORANDO para evitar desconexão`);
                    return;
                }
                
                // Proteção adicional: se conectou recentemente (menos de 30s), ignorar QR
                if (this.metadata.connectedAt) {
                    const timeSinceConnect = Date.now() - new Date(this.metadata.connectedAt).getTime();
                    if (timeSinceConnect < 30000) {
                        logger.aviso(`[${this.clientId}] QR Code recebido ${Math.round(timeSinceConnect/1000)}s após conexão - IGNORANDO`);
                        return;
                    }
                }
                
                this.status = 'qr_ready';
                this.metadata.lastQRAt = new Date().toISOString();
                
                // Converter QR para DataURL
                const qrDataURL = await qrcode.toDataURL(qr);
                this.qrCode = qrDataURL;
                
                logger.info(`[${this.clientId}] QR Code gerado`);
                this.callbacks.onQR(this.clientId, qrDataURL);
            } catch (erro) {
                logger.erro(`[${this.clientId}] Erro ao gerar QR Code:`, erro.message);
            }
        });

        // Autenticado
        this.client.once('authenticated', () => {
            this.status = 'authenticated';
            logger.sucesso(`[${this.clientId}] Autenticado com sucesso`);
        });

        // Cliente pronto - IMPORTANTE: once() para evitar múltiplas chamadas
        this.client.once('ready', async () => {
            this.status = 'ready';
            this.metadata.connectedAt = new Date().toISOString();
            
            // Obter informações do telefone
            try {
                const info = this.client.info;
                this.phoneNumber = info.wid.user;
                logger.sucesso(`[${this.clientId}] Cliente pronto - Número: ${this.phoneNumber}`);
            } catch (erro) {
                logger.aviso(`[${this.clientId}] Não foi possível obter número do telefone`);
            }
            
            this.callbacks.onReady(this.clientId, this.phoneNumber);

            // Iniciar heartbeat para manter conexão ativa
            try {
                this.iniciarHeartbeat();
            } catch (e) {
                logger.aviso(`[${this.clientId}] Falha ao iniciar heartbeat: ${e.message}`);
            }

            // Processar mensagens pendentes na fila para este cliente
            try {
                const queue = require('../core/fila-mensagens');
                await queue.process(async (msg) => {
                    if (msg.clientId !== this.clientId) return true; // Ignora outras
                    try {
                        const r = await this.client.sendMessage(msg.to, msg.text);
                        logger.sucesso(`[${this.clientId}] Mensagem (fila) enviada para ${msg.to}`);
                        return !!r;
                    } catch(e) {
                        logger.aviso(`[${this.clientId}] Falha ao enviar da fila para ${msg.to}: ${e.message}`);
                        return false;
                    }
                });
            } catch(e) {
                logger.aviso(`[${this.clientId}] Erro ao processar fila: ${e.message}`);
            }
        });

        // Mensagem recebida
        this.client.on('message', async (message) => {
            const prometheusMetrics = require('../core/metricas-prometheus');
            this.metadata.messageCount++;
            prometheusMetrics.incrementCounter('whatsapp_messages_received_total', { clientId: this.clientId });
            logger.info(`[${this.clientId}] Mensagem recebida de ${message.from}`);
            this.callbacks.onMessage(this.clientId, message);
        });        // Desconectado - Protegido contra múltiplos disparos
        this.client.on('disconnected', async (reason) => {
            // Evitar processar múltiplas vezes se já desconectado
            if (this.status === 'disconnected' || this.status === 'idle') {
                logger.aviso(`[${this.clientId}] Evento disconnected recebido mas já está ${this.status} - IGNORANDO duplicata`);
                return;
            }
            
            // Proteção contra LOGOUT "fantasma" que chega logo após conexão bem-sucedida
            // Isso pode acontecer quando o WhatsApp Web emite eventos de logout inválidos
            if (reason === 'LOGOUT' && this.metadata.connectedAt) {
                const timeSinceConnect = Date.now() - new Date(this.metadata.connectedAt).getTime();
                if (timeSinceConnect < 60000) { // Menos de 60 segundos desde a conexão
                    logger.aviso(`[${this.clientId}] LOGOUT recebido apenas ${Math.round(timeSinceConnect/1000)}s após conexão - IGNORANDO como falso positivo`);
                    // Não mudar status, manter conexão
                    return;
                }
            }
            
            const previousStatus = this.status;
            this.status = 'disconnected';
            this.lastDisconnectReason = reason;
            logger.aviso(`[${this.clientId}] Desconectado: ${reason}`);

            // Antes: limpava sessão automaticamente em caso de LOGOUT.
            // Alteração: não executar limpeza automática aqui — manter sessão para permitir reconexão automática
            // A limpeza/remoção da sessão só ocorrerá com logout() explícito.
            if (reason === 'LOGOUT') {
                logger.aviso(`[${this.clientId}] Recebido motivo LOGOUT — sessão mantida. Use logout() para remover sessão explicitamente.`);
            }

            // Auditoria de desconexão
            try {
                const auditoria = require('../infraestrutura/auditoria');
                auditoria.logAudit('whatsapp.disconnected', {
                    user: 'sistema',
                    details: { clientId: this.clientId, reason, previousStatus }
                });
            } catch {}

            // Parar heartbeat ao desconectar
            this.pararHeartbeat();
            this.callbacks.onDisconnected(this.clientId, reason);
        });

        // Falha de autenticação (MUDADO DE .once() PARA .on() PARA CAPTURAR MÚLTIPLAS FALHAS)
        this.client.on('auth_failure', (message) => {
            this.status = 'error';
            logger.erro(`[${this.clientId}] Falha de autenticação: ${message}`);
            // Parar heartbeat em falha de autenticação
            this.pararHeartbeat();
            this.callbacks.onAuthFailure(this.clientId, message);
        });

        // Erro de carregamento
        this.client.on('loading_screen', (percent, message) => {
            logger.info(`[${this.clientId}] Carregando: ${percent}% - ${message}`);
        });

        // Listener para erros do cliente (não deve ocorrer mas adicionado como precaução)
        this.client.on('error', (erro) => {
            logger.erro(`[${this.clientId}] Erro do cliente WhatsApp:`, erro.message || erro);
        });

        // Listener para avisos
        this.client.on('warn', (aviso) => {
            logger.aviso(`[${this.clientId}] Aviso do cliente WhatsApp:`, aviso.message || aviso);
        });

        // Proteção contra desconexão não esperada do browser
        // ✅ MUDANÇA: Em vez de destruir, apenas notificar (permite reconexão automática)
        if (this.client && this.client.pupBrowser) {
            this.client.pupBrowser.once('disconnected', async () => {
                logger.aviso(`[${this.clientId}] Browser do Puppeteer desconectou - aguardando reconexão automática`);
                const previousStatus = this.status;
                this.status = 'disconnected';
                this.lastDisconnectReason = 'BROWSER_DISCONNECTED';

                // Auditoria de desconexão do browser
                try {
                    const auditoria = require('../infraestrutura/auditoria');
                    auditoria.logAudit('whatsapp.browser_disconnected', {
                        user: 'sistema',
                        details: { clientId: this.clientId, previousStatus, recoveryAttempt: true }
                    });
                } catch {}

                // Parar heartbeat temporariamente
                this.pararHeartbeat();
                
                // ✅ NOVA LÓGICA: Notificar mas NÃO destruir
                // O pool tentará reconectar via health check
                logger.info(`[${this.clientId}] Aguardando reconexão automática do browser...`);
                try {
                    this.callbacks.onDisconnected(this.clientId, 'BROWSER_DISCONNECTED_RECOVERING');
                } catch {}
                
                // NÃO destruir - deixar a reconexão acontecer naturalmente
                // Destruição será feita apenas se o usuário fizer logout explícito
            });
        }
    }

    /**
     * Envia uma mensagem de texto
     * @param {string} to - Número do destinatário (formato: 5511999999999@c.us)
     * @param {string} text - Texto da mensagem
     */
    async sendMessage(to, text) {
        const queue = require('../core/fila-mensagens');
        const prometheusMetrics = require('../core/metricas-prometheus');
        
        if (this.status !== 'ready') {
            // Enfileira para tentativa posterior
            queue.enqueue({ clientId: this.clientId, to, text });
            prometheusMetrics.incrementCounter('whatsapp_messages_queued_total', { clientId: this.clientId });
            logger.aviso(`[${this.clientId}] Cliente não pronto. Mensagem enfileirada para ${to}`);
            return { success: false, queued: true, message: `Cliente não pronto (${this.status}). Mensagem enfileirada.` };
        }

        try {
            const result = await this.client.sendMessage(to, text);
            prometheusMetrics.incrementCounter('whatsapp_messages_sent_total', { clientId: this.clientId, status: 'success' });
            logger.sucesso(`[${this.clientId}] Mensagem enviada para ${to}`);
            return { success: true, messageId: result.id.id };
        } catch (erro) {
            logger.erro(`[${this.clientId}] Erro ao enviar mensagem:`, erro.message);
            prometheusMetrics.incrementCounter('whatsapp_messages_sent_total', { clientId: this.clientId, status: 'error' });
            // Enfileira para retry futuro
            queue.enqueue({ clientId: this.clientId, to, text });
            prometheusMetrics.incrementCounter('whatsapp_messages_queued_total', { clientId: this.clientId });
            return { success: false, queued: true, message: erro.message };
        }
    }

    /**
     * Envia uma mensagem de mídia
     * @param {string} to - Número do destinatário
     * @param {Object} media - Objeto de mídia (MessageMedia)
     * @param {Object} options - Opções adicionais (caption, etc)
     */
    async sendMedia(to, media, options = {}) {
        if (this.status !== 'ready') {
            return { success: false, message: `Cliente não está pronto. Status atual: ${this.status}` };
        }

        try {
            const result = await this.client.sendMessage(to, media, options);
            logger.sucesso(`[${this.clientId}] Mídia enviada para ${to}`);
            return { success: true, messageId: result.id.id };
        } catch (erro) {
            logger.erro(`[${this.clientId}] Erro ao enviar mídia:`, erro.message);
            return { success: false, message: erro.message };
        }
    }

    /**
     * Obtém informações do cliente
     */
    getInfo() {
        return {
            clientId: this.clientId,
            status: this.status,
            phoneNumber: this.phoneNumber,
            qrCode: this.qrCode,
            metadata: this.metadata,
            lastDisconnectReason: this.lastDisconnectReason,
            isReady: this.status === 'ready'
        };
    }

    /**
     * Obtém lista de chats com cache de 30s
     */
    async getChats(forceRefresh = false) {
        if (this.status !== 'ready') {
            return { success: false, message: 'Cliente não está pronto' };
        }

        const cache = require('../core/armazenamento-cache');
        const cacheKey = `chats:${this.clientId}`;

        if (!forceRefresh) {
            const cached = cache.get(cacheKey);
            if (cached) {
                logger.info(`[${this.clientId}] Chats retornados do cache`);
                return { success: true, chats: cached, fromCache: true };
            }
        }

        try {
            const chats = await this.client.getChats();
            const chatList = chats.map(c => ({
                id: c.id._serialized,
                name: c.name || c.id.user,
                isGroup: c.isGroup,
                unreadCount: c.unreadCount,
                timestamp: c.timestamp
            }));
            cache.set(cacheKey, chatList, 30000); // TTL 30s
            logger.info(`[${this.clientId}] Chats carregados e cacheados (${chatList.length} encontrados)`);
            return { success: true, chats: chatList, fromCache: false };
        } catch (erro) {
            logger.erro(`[${this.clientId}] Erro ao obter chats:`, erro.message);
            return { success: false, message: erro.message };
        }
    }

    /**
     * Obtém estado atual do cliente
     */
    async getState() {
        if (!this.client) {
            return 'DISCONNECTED';
        }

        try {
            const state = await this.client.getState();
            return state;
        } catch (erro) {
            const msg = (erro && erro.message) ? erro.message : String(erro);
            const isSessionClosed = msg.includes('Protocol error') || msg.includes('Session closed') || msg.includes('page has been closed');

            if (isSessionClosed) {
                // Tratar sessão já encerrada sem poluir logs
                const previousStatus = this.status;
                this.status = 'disconnected';
                this.lastDisconnectReason = 'BROWSER_DISCONNECTED';
                this.pararHeartbeat();
                try {
                    this.callbacks.onDisconnected(this.clientId, 'BROWSER_DISCONNECTED');
                } catch {}
                logger.aviso(`[${this.clientId}] Estado definido como DISCONNECTED (browser fechado; status anterior: ${previousStatus})`);
                return 'DISCONNECTED';
            }

            // Outros erros: logar e retornar nulo
            logger.erro(`[${this.clientId}] Erro ao obter estado:`, msg);
            return null;
        }
    }

    /**
     * Desconecta o cliente de forma segura
     * Por padrão realiza um "soft-disconnect" (preserva a instância para possibilidade de reconexão).
     * Se `forceDestroy` for true ou `reason` indicar LOGOUT, destrói a instância e limpa referência.
     */
    async disconnect(forceDestroy = false, reason = undefined) {
        if (!this.client) {
            return { success: true, message: 'Cliente já estava desconectado' };
        }

        try {
            // Determinar se devemos destruir a instância
            const remoteLogout = typeof reason === 'string' && /logout|remote_logout|LOGOUT/i.test(reason);
            const shouldDestroy = forceDestroy || remoteLogout;

            if (shouldDestroy) {
                logger.info(`[${this.clientId}] Desconectando e destruindo instância (forceDestroy=${forceDestroy}, reason=${reason})...`);

                // Parar heartbeat antes de desconectar
                this.pararHeartbeat();

                // Adicionar timeout e proteção contra erros de protocolo
                const destroyPromise = Promise.race([
                    this.client.destroy(),
                    new Promise((_, reject) =>
                        setTimeout(() => reject(new Error('Timeout ao desconectar')), 5000)
                    )
                ]);

                await destroyPromise.catch(err => {
                    // Erros de protocolo durante destroy são normais
                    if (!err.message.includes('Protocol error') && !err.message.includes('page has been closed')) {
                        throw err;
                    }
                    logger.info(`[${this.clientId}] Erro de protocolo durante destroy (esperado)`);
                });

                this.status = 'disconnected';
                this.client = null;
                logger.sucesso(`[${this.clientId}] Cliente desconectado e destruído com sucesso`);
                return { success: true };
            }

            // Soft-disconnect: marca estado e para heartbeat, preservando a instância para tentativa de reconexão
            logger.info(`[${this.clientId}] Executando soft-disconnect (instância preservada). Reason=${reason || 'none'}`);
            this.pararHeartbeat();
            this.status = 'disconnected';
            // Não zera this.client para permitir reconexão/inspeção
            logger.sucesso(`[${this.clientId}] Soft-disconnect concluído (instância preservada)`);
            return { success: true };
        } catch (erro) {
            logger.erro(`[${this.clientId}] Erro ao desconectar:`, erro.message);
            // Ao erro, tentar remover referência para evitar estados inconsistentes
            try { this.client = null; } catch {}
            this.status = 'disconnected';
            return { success: false, message: erro.message };
        }
    }

    /**
     * Reconecta o cliente (útil após falha)
     */
    async reconnect() {
        logger.info(`[${this.clientId}] Tentando reconectar...`);
        await this.disconnect();
        await new Promise(resolve => setTimeout(resolve, 2000)); // Aguarda 2s
        return await this.initialize();
    }

    /**
     * Inicia o heartbeat/keep-alive para evitar timeout por inatividade
     */
    iniciarHeartbeat() {
        if (this._heartbeatTimer) {
            logger.aviso(`[${this.clientId}] Heartbeat já ativo`);
            return;
        }
        if (!this.client) return;

        this._heartbeatTimer = setInterval(async () => {
            try {
                // Operação leve que mantém a sessão ativa
                const state = await this.client.getState();
                if (!state || state === 'DISCONNECTED') {
                    logger.aviso(`[${this.clientId}] Heartbeat detectou estado inválido: ${state}`);
                } else {
                    logger.debug && logger.debug(`[${this.clientId}] ❤️ Heartbeat OK (${state})`);
                }
            } catch (e) {
                // Falhas ocasionais são esperadas; não interrompe
                logger.aviso(`[${this.clientId}] Heartbeat falhou: ${e.message}`);
            }
        }, this._heartbeatIntervalMs);

        logger.info(`[${this.clientId}] Heartbeat iniciado (intervalo ${this._heartbeatIntervalMs}ms)`);
    }

    /**
     * Para o heartbeat/keep-alive
     */
    pararHeartbeat() {
        if (this._heartbeatTimer) {
            clearInterval(this._heartbeatTimer);
            this._heartbeatTimer = null;
            logger.info(`[${this.clientId}] Heartbeat parado`);
        }
    }

    /**
     * Garante que o cliente esteja desligado antes de remover arquivos da sessão
     */
    async limparSessaoLocal() {
        if (this._limpandoSessaoPromise) {
            return this._limpandoSessaoPromise;
        }

        this._limpandoSessaoPromise = (async () => {
            // Forçar destruição da instância antes de remover arquivos
            await this.disconnect(true, 'CLEANUP');
            const removed = await limparSessao(this.sessionPath, this.clientId);
            return removed;
        })();

        try {
            return await this._limpandoSessaoPromise;
        } finally {
            this._limpandoSessaoPromise = null;
        }
    }    /**
     * Logout e remove sessão (SOMENTE quando explicitamente solicitado pelo usuário)
     */
    async logout() {
        if (!this.client) {
            return { success: false, message: 'Cliente não está conectado' };
        }

        try {
            logger.info(`[${this.clientId}] Fazendo logout EXPLÍCITO e removendo sessão...`);
            const stack = new Error().stack || 'stack indisponível';
            logger.info(`[${this.clientId}] Origem do logout: ${stack}`);
            
            // IMPORTANTE: Habilitar limpeza de sessão antes do logout explícito
            if (this._authStrategy && typeof this._authStrategy.enableSessionCleanup === 'function') {
                this._authStrategy.enableSessionCleanup();
            }
            
            await this.client.logout();

            // Forçar destruição e remover arquivos da sessão
            await this.disconnect(true, 'LOGOUT');
            await limparSessao(this.sessionPath, this.clientId);

            this.status = 'idle';
            this.phoneNumber = null;
            this.qrCode = null;
            logger.sucesso(`[${this.clientId}] Logout realizado com sucesso`);
            return { success: true };
        } catch (erro) {
            logger.erro(`[${this.clientId}] Erro ao fazer logout:`, erro.message);
            return { success: false, message: erro.message };
        }
    }
}

module.exports = ServicoClienteWhatsApp;
