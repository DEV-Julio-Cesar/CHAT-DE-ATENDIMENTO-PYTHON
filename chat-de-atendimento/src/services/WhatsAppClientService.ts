/**
 * 📱 WhatsAppClientService
 * 
 * Serviço isolado que gerencia um único cliente WhatsApp.
 * Responsável por:
 * - Inicialização e autenticação
 * - Geração de QR Code
 * - Gerenciamento de eventos
 * - Envio e recebimento de mensagens
 * - Desconexão segura
 */

import { Client, LocalAuth, Message, Chat, MessageMedia } from 'whatsapp-web.js';
import * as path from 'path';

// @ts-ignore - qrcode não tem types oficiais
const qrcode = require('qrcode');

// Types
export type ClientStatus = 
  | 'idle' 
  | 'initializing' 
  | 'qr_ready' 
  | 'authenticated' 
  | 'ready' 
  | 'disconnected' 
  | 'error';

export interface ClientOptions {
  sessionPath?: string;
  onQR?: (clientId: string, qr: string) => void;
  onReady?: (clientId: string) => void;
  onMessage?: (clientId: string, message: Message) => void;
  onDisconnected?: (clientId: string, reason: string) => void;
  onAuthFailure?: (clientId: string, message: string) => void;
}

export interface ClientCallbacks {
  onQR: (clientId: string, qr: string) => void;
  onReady: (clientId: string) => void;
  onMessage: (clientId: string, message: Message) => void;
  onDisconnected: (clientId: string, reason: string) => void;
  onAuthFailure: (clientId: string, message: string) => void;
}

export interface ClientMetadata {
  createdAt: string;
  lastQRAt: string | null;
  connectedAt: string | null;
  messageCount: number;
}

export interface MessageResult {
  success: boolean;
  messageId?: string;
  queued?: boolean;
  message?: string;
}

export interface ChatResult {
  success: boolean;
  chats?: Chat[];
  fromCache?: boolean;
  message?: string;
}

export interface ClientInfo {
  clientId: string;
  status: ClientStatus;
  phoneNumber: string | null;
  qrCode: string | null;
  metadata: ClientMetadata;
  isReady: boolean;
}

export class WhatsAppClientService {
  readonly clientId: string;
  private client: Client | null = null;
  private _status: ClientStatus = 'idle';
  private qrCode: string | null = null;
  private phoneNumber: string | null = null;
  private readonly sessionPath: string;
  private readonly callbacks: ClientCallbacks;
  private metadata: ClientMetadata;
  private logger: any;
  private cache: any;

  constructor(clientId: string, options: ClientOptions = {}) {
    this.clientId = clientId;
    this.sessionPath = options.sessionPath || path.join(process.cwd(), '.wwebjs_auth');
    
    // Lazy load dependencies
    this.logger = require('../infraestrutura/logger');
    this.cache = require('../core/cache');
    
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
  }

  // Getter/Setter para status com métricas
  get status(): ClientStatus {
    return this._status;
  }

  set status(newStatus: ClientStatus) {
    if (this._status !== newStatus) {
      const prometheusMetrics = require('../core/prometheus-metrics');
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
  async initialize(): Promise<void> {
    if (this.status === 'initializing' || this.status === 'ready') {
      this.logger.aviso(`[${this.clientId}] Cliente já está ${this.status}`);
      return;
    }

    try {
      this.status = 'initializing';
      this.logger.info(`[${this.clientId}] Iniciando cliente WhatsApp...`);      this.client = new Client({
        authStrategy: new LocalAuth({
          clientId: this.clientId,
          dataPath: this.sessionPath
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
        },
        // Configurações adicionais para manter sessão estável
        webVersionCache: {
          type: 'remote',
          remotePath: 'https://raw.githubusercontent.com/AzizHasanli/AHweb.js/main/AHWeb2132024.json'
        },
        // Intervalo de QR mais longo para evitar renovação frequente
        qrMaxRetries: 5,
        // Manter conexão ativa
        takeoverOnConflict: false,
        takeoverTimeoutMs: 0
      } as any);

      this.setupEventListeners();
      await this.client.initialize();

    } catch (erro: any) {
      this.status = 'error';
      this.logger.erro(`[${this.clientId}] Erro na inicialização:`, erro);
      throw erro;
    }
  }

  /**
   * Configura os listeners de eventos do cliente
   */
  private setupEventListeners(): void {
    if (!this.client) return;    // QR Code gerado
    // IMPORTANTE: Ignorar QR codes quando já está autenticado/pronto para evitar desconexões indevidas
    this.client.on('qr', async (qr: string) => {
      try {
        // Se já está autenticado ou pronto, ignorar novo QR (pode ser tentativa de re-auth do WhatsApp)
        if (this.status === 'authenticated' || this.status === 'ready') {
          this.logger.aviso(`[${this.clientId}] QR Code recebido mas cliente já está ${this.status} - IGNORANDO para evitar desconexão`);
          return;
        }
        
        this.status = 'qr_ready';
        this.qrCode = await qrcode.toDataURL(qr);
        this.metadata.lastQRAt = new Date().toISOString();
        this.logger.info(`[${this.clientId}] QR Code gerado`);
        this.callbacks.onQR(this.clientId, this.qrCode!);
      } catch (erro: any) {
        this.logger.erro(`[${this.clientId}] Erro ao gerar QR Code:`, erro);
      }
    });

    // Carregando...
    this.client.on('loading_screen', (percent: number) => {
      this.logger.info(`[${this.clientId}] Carregando: ${percent}%`);
    });

    // Autenticado
    this.client.on('authenticated', () => {
      this.status = 'authenticated';
      this.logger.sucesso(`[${this.clientId}] Autenticado com sucesso`);
    });

    // Pronto para uso
    this.client.on('ready', async () => {
      this.status = 'ready';
      this.metadata.connectedAt = new Date().toISOString();

      try {
        const info = await this.client!.info;
        this.phoneNumber = info.wid.user;
        this.logger.sucesso(`[${this.clientId}] Cliente pronto! Número: ${this.phoneNumber}`);
      } catch (erro: any) {
        this.logger.erro(`[${this.clientId}] Erro ao obter info:`, erro);
      }

      this.callbacks.onReady(this.clientId);

      // Processa mensagens enfileiradas
      const messageQueue = require('../core/message-queue');
      await messageQueue.process(async (msg: any) => {
        if (msg.clientId === this.clientId) {
          try {
            await this.client!.sendMessage(msg.to, msg.text);
            this.logger.sucesso(`[${this.clientId}] Mensagem da fila enviada para ${msg.to}`);
            return true;
          } catch (erro: any) {
            this.logger.erro(`[${this.clientId}] Erro ao enviar mensagem da fila:`, erro.message);
            return false;
          }
        }
        return false;
      });
    });

    // Mensagem recebida
    this.client.on('message', async (message: Message) => {
      const prometheusMetrics = require('../core/prometheus-metrics');
      this.metadata.messageCount++;
      prometheusMetrics.incrementCounter('whatsapp_messages_received_total', { clientId: this.clientId });
      this.logger.info(`[${this.clientId}] Mensagem recebida de ${message.from}`);
      this.callbacks.onMessage(this.clientId, message);
    });    // Desconectado - Protegido contra múltiplos disparos
    this.client.on('disconnected', (reason: string) => {
      // Evitar processar múltiplas vezes se já desconectado
      if (this.status === 'disconnected' || this.status === 'idle') {
        this.logger.aviso(`[${this.clientId}] Evento disconnected recebido mas já está ${this.status} - IGNORANDO duplicata`);
        return;
      }
      
      this.status = 'disconnected';
      this.logger.aviso(`[${this.clientId}] Desconectado: ${reason}`);
      this.callbacks.onDisconnected(this.clientId, reason);
    });

    // Falha de autenticação
    this.client.on('auth_failure', (message: string) => {
      this.status = 'error';
      this.logger.erro(`[${this.clientId}] Falha de autenticação:`, message);
      this.callbacks.onAuthFailure(this.clientId, message);
    });
  }

  /**
   * Envia uma mensagem de texto
   */
  async sendMessage(to: string, text: string): Promise<MessageResult> {
    const queue = require('../core/message-queue');
    const prometheusMetrics = require('../core/prometheus-metrics');
    
    if (this.status !== 'ready') {
      queue.enqueue({ clientId: this.clientId, to, text });
      prometheusMetrics.incrementCounter('whatsapp_messages_queued_total', { clientId: this.clientId });
      this.logger.aviso(`[${this.clientId}] Cliente não pronto. Mensagem enfileirada para ${to}`);
      return { success: false, queued: true, message: `Cliente não pronto (${this.status}). Mensagem enfileirada.` };
    }

    try {
      const result = await this.client!.sendMessage(to, text);
      prometheusMetrics.incrementCounter('whatsapp_messages_sent_total', { clientId: this.clientId, status: 'success' });
      this.logger.sucesso(`[${this.clientId}] Mensagem enviada para ${to}`);
      return { success: true, messageId: result.id.id };
    } catch (erro: any) {
      this.logger.erro(`[${this.clientId}] Erro ao enviar mensagem:`, erro.message);
      prometheusMetrics.incrementCounter('whatsapp_messages_sent_total', { clientId: this.clientId, status: 'error' });
      queue.enqueue({ clientId: this.clientId, to, text });
      prometheusMetrics.incrementCounter('whatsapp_messages_queued_total', { clientId: this.clientId });
      return { success: false, queued: true, message: erro.message };
    }
  }

  /**
   * Envia uma mensagem de mídia
   */
  async sendMediaMessage(to: string, media: MessageMedia, options?: { caption?: string }): Promise<MessageResult> {
    if (this.status !== 'ready') {
      return { success: false, message: `Cliente não pronto (${this.status})` };
    }

    try {
      const result = await this.client!.sendMessage(to, media, options);
      this.logger.sucesso(`[${this.clientId}] Mídia enviada para ${to}`);
      return { success: true, messageId: result.id.id };
    } catch (erro: any) {
      this.logger.erro(`[${this.clientId}] Erro ao enviar mídia:`, erro.message);
      return { success: false, message: erro.message };
    }
  }

  /**
   * Obtém informações do cliente
   */
  async getInfo(): Promise<any> {
    if (!this.client || this.status !== 'ready') {
      return null;
    }
    try {
      return await this.client.info;
    } catch (erro: any) {
      this.logger.erro(`[${this.clientId}] Erro ao obter info:`, erro);
      return null;
    }
  }

  /**
   * Lista todos os chats com cache
   */
  async getChats(forceRefresh: boolean = false): Promise<ChatResult> {
    if (this.status !== 'ready' || !this.client) {
      return { success: false, message: 'Cliente não está pronto' };
    }

    const cacheKey = `chats_${this.clientId}`;
    
    if (!forceRefresh) {
      const cached = this.cache.get(cacheKey);
      if (cached) {
        this.logger.info(`[${this.clientId}] Retornando chats do cache`);
        return { success: true, chats: cached, fromCache: true };
      }
    }

    try {
      const chats = await this.client.getChats();
      this.cache.set(cacheKey, chats, 30000); // 30s TTL
      this.logger.info(`[${this.clientId}] ${chats.length} chats obtidos`);
      return { success: true, chats, fromCache: false };
    } catch (erro: any) {
      this.logger.erro(`[${this.clientId}] Erro ao obter chats:`, erro);
      return { success: false, message: erro.message };
    }
  }

  /**
   * Obtém informações sobre o cliente
   */
  getClientInfo(): ClientInfo {
    return {
      clientId: this.clientId,
      status: this.status,
      phoneNumber: this.phoneNumber,
      qrCode: this.qrCode,
      metadata: { ...this.metadata },
      isReady: this.status === 'ready'
    };
  }

  /**
   * Desconecta o cliente. Por padrão faz "soft-disconnect" (preserva a instância).
   * Se `forceDestroy` for true, destrói a instância e remove sessão.
   */
  async disconnect(forceDestroy: boolean = false, reason?: string): Promise<void> {
    if (!this.client) {
      this.logger.aviso(`[${this.clientId}] Cliente já está desconectado`);
      return;
    }

    try {
      // Antes: destruía automaticamente se reason sugerisse LOGOUT.
      // Agora: destruir somente quando forceDestroy for true (ação explícita).
      const shouldDestroy = !!forceDestroy;

      if (shouldDestroy) {
        this.logger.info(`[${this.clientId}] Desconectando e destruindo instância (forceDestroy=${forceDestroy}, reason=${reason})...`);

        // Proteção: tentar destroy com timeout e tratar erros de protocolo como não-fatais
        const destroyPromise = Promise.race([
          this.client.destroy(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout ao destruir cliente')), 10000))
        ]);

        await destroyPromise.catch(err => {
          if (err && err.message && (err.message.includes('Protocol error') || err.message.includes('page has been closed'))) {
            this.logger.info(`[${this.clientId}] Erro de protocolo durante destroy (ignorado): ${err.message}`);
          } else {
            throw err;
          }
        });

        // Remover referência e marcar status
        this.client = null;
        this.status = 'disconnected';
        this.logger.sucesso(`[${this.clientId}] Instância destruída e desconectada`);
        return;
      }

      // Soft-disconnect: marca estado e para heartbeat, preservando a instância para tentativa de reconexão
      this.logger.info(`[${this.clientId}] Executando soft-disconnect (instância preservada). Reason=${reason || 'none'}`);
      this.status = 'disconnected';
      // Não zera this.client para permitir reconexão/inspeção
      this.logger.sucesso(`[${this.clientId}] Soft-disconnect concluído (instância preservada)`);
    } catch (erro: any) {
      this.logger.erro(`[${this.clientId}] Erro ao executar disconnect:`, erro);
      throw erro;
    }
  }

  // Métodos auxiliares para retry/backoff de logout
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private async safeClientLogout(retries: number = 5, initialDelayMs: number = 200): Promise<void> {
    if (!this.client) return;

    let attempt = 0;
    let delay = initialDelayMs;

    while (attempt < retries) {
      try {
        await this.client.logout();
        return;
      } catch (err: any) {
        const message = err && (err.message || err.toString()) || '';
        const code = err && err.code;

        // Detectar EBUSY ou tentativa de unlink em arquivos de sessão do LocalAuth
        const isEBusy = code === 'EBUSY' || message.includes('EBUSY') || message.includes('resource busy');
        const isLocalAuthPath = message.includes('.wwebjs_auth') || message.includes('session-');

        if (isEBusy && isLocalAuthPath) {
          // Log e retry com backoff
          try {
            const logger = this.logger || console;
            logger.aviso ? logger.aviso(`[${this.clientId}] LocalAuth logout falhou com EBUSY (tentativa ${attempt + 1}/${retries}). Re-tentando em ${delay}ms`) : console.warn(`[${this.clientId}] LocalAuth logout EBUSY (tentativa ${attempt + 1}/${retries}). Re-tentando em ${delay}ms`);
          } catch (_) {}

          await this.sleep(delay);
          attempt++;
          delay *= 2;
          continue;
        }

        // Erro diferente: propagar
        throw err;
      }
    }

    // Se chegou aqui, todas as tentativas falharam — lançar último erro
    throw new Error(`safeClientLogout: falha após ${retries} tentativas (provável EBUSY)`);
  }

  /**
   * Remove a sessão persistente
   */
  async logout(): Promise<void> {
    if (!this.client) {
      this.logger.aviso(`[${this.clientId}] Nenhum cliente ativo para logout`);
      return;
    }

    try {
      this.logger.info(`[${this.clientId}] Fazendo logout...`);

      // Tentar logout com retry/backoff para mitigar EBUSY ao remover arquivos do LocalAuth
      await this.safeClientLogout();

      // Forçar destruição/removal da sessão
      await this.disconnect(true, 'LOGOUT');
      this.status = 'idle';
      this.phoneNumber = null;
      this.qrCode = null;
      this.logger.sucesso(`[${this.clientId}] Logout realizado com sucesso`);
    } catch (erro: any) {
      // Se for erro EBUSY, logar como aviso (evitar unhandled rejection ruidoso)
      const msg = erro && (erro.message || erro.toString()) || '';
      if (msg.includes('EBUSY') || msg.includes('resource busy')) {
        this.logger.aviso(`[${this.clientId}] Logout encontrou EBUSY ao tentar remover arquivos de sessão. Marcar sessão como idle e preservar arquivos. Erro: ${msg}`);
        // Ainda assim, forçar disconnect sem destruir instância para evitar perda de handles
        try {
          await this.disconnect(false, 'LOGOUT_EBUSY');
        } catch (_) {}
        return;
      }

      this.logger.erro(`[${this.clientId}] Erro no logout:`, erro);
      throw erro;
    }
  }

  // Instalar um handler global protegido para unhandledRejection (registrar apenas uma vez)
  // Isso ajuda a capturar erros de LocalAuth.unlink originados dentro de whatsapp-web.js que não são tratados pela lib.
  public static ensureGlobalUnhandledRejectionHandler(): void {
    const globalAny: any = global as any;
    if (globalAny.__wajs_unhandled_rejection_handler_installed) return;

    process.on('unhandledRejection', (reason: any) => {
      try {
        const message = reason && (reason.message || reason.toString()) || '';
        if (message.includes('EBUSY') && message.includes('.wwebjs_auth')) {
          // Suprimir/transformar em aviso para não poluir logs
          try {
            const logger = require('../infraestrutura/logger');
            logger.aviso(`[GLOBAL] Capturado unhandledRejection EBUSY em LocalAuth: ${message}`);
          } catch (_) {
            console.warn(`[GLOBAL] Capturado unhandledRejection EBUSY em LocalAuth: ${message}`);
          }
          return;
        }

        // Re-throw para o logger padrão (manter visibilidade de outros erros)
        try {
          const logger = require('../infraestrutura/logger');
          logger.erro('[GLOBAL] UNHANDLED REJECTION:', reason);
        } catch (_) {
          console.error('[GLOBAL] UNHANDLED REJECTION:', reason);
        }
      } catch (e) {
        console.error('Erro no handler global de unhandledRejection:', e);
      }
    });

    globalAny.__wajs_unhandled_rejection_handler_installed = true;
  }

  /**
   * Verifica se o cliente está pronto
   */
  isReady(): boolean {
    return this.status === 'ready';
  }

  /**
   * Obtém o cliente raw (use com cautela)
   */
  getRawClient(): Client | null {
    return this.client;
  }
}

export default WhatsAppClientService;
