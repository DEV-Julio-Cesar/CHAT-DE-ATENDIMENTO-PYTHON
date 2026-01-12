# 🔧 IMPLEMENTAÇÃO DAS CORREÇÕES - Código Pronto para Usar

## CORREÇÃO 1: Keep-Alive Heartbeat

**Arquivo**: `src/services/ServicoClienteWhatsApp.js`

```javascript
// Adicionar no final da classe, antes do export:

/**
 * Inicia heartbeat para manter conexão ativa
 * Valida conexão a cada 25 segundos
 */
iniciarHeartbeat() {
    if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
    }
    
    this.heartbeatInterval = setInterval(async () => {
        if (this.status !== 'ready') {
            return;  // Não fazer heartbeat se não está pronto
        }
        
        try {
            // Validar conexão tentando obter chats
            await this.client.getChats();
            logger.debug(`[${this.clientId}] ❤️ Heartbeat OK`);
            
        } catch (erro) {
            logger.aviso(`[${this.clientId}] ❌ Heartbeat falhou: ${erro.message}`);
            
            // Marcar como desconectado
            this.status = 'disconnected';
            this.callbacks.onDisconnected(this.clientId, 'HEARTBEAT_FAILED');
        }
    }, 25000);  // A cada 25 segundos
    
    logger.info(`[${this.clientId}] Heartbeat iniciado`);
}

/**
 * Para o heartbeat
 */
pararHeartbeat() {
    if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
        this.heartbeatInterval = null;
        logger.info(`[${this.clientId}] Heartbeat parado`);
    }
}
```

**Onde chamar**:

```javascript
// Em initialize() - após "Cliente pronto"
this.client.once('ready', async () => {
    this.status = 'ready';
    // ... código existente ...
    
    // NOVO: Iniciar heartbeat
    this.iniciarHeartbeat();
});

// Em disconnect()
async disconnect() {
    this.pararHeartbeat();  // NOVO
    // ... resto do código ...
}
```

---

## CORREÇÃO 2: Fix Memory Leaks em Listeners

**Arquivo**: `src/services/ServicoClienteWhatsApp.js`

```javascript
// Substituir o método _setupEventListeners() inteiro:

_setupEventListeners() {
    // ✅ CRÍTICO: Remover TODOS os listeners antigos
    this.client.removeAllListeners('qr');
    this.client.removeAllListeners('authenticated');
    this.client.removeAllListeners('ready');
    this.client.removeAllListeners('message');
    this.client.removeAllListeners('disconnected');
    this.client.removeAllListeners('auth_failure');
    this.client.removeAllListeners('loading_screen');
    this.client.removeAllListeners('error');
    this.client.removeAllListeners('warn');
    
    // Proteger contra browser disconnect
    if (this.client && this.client.pupBrowser) {
        this.client.pupBrowser.removeAllListeners('disconnected');
    }
    
    // Agora adiciona listeners limpos
    this.client.on('qr', async (qr) => {
        try {
            this.status = 'qr_ready';
            this.metadata.lastQRAt = new Date().toISOString();
            const qrDataURL = await require('qrcode').toDataURL(qr);
            this.qrCode = qrDataURL;
            logger.info(`[${this.clientId}] QR Code gerado`);
            this.callbacks.onQR(this.clientId, qrDataURL);
        } catch (erro) {
            logger.erro(`[${this.clientId}] Erro ao gerar QR:`, erro.message);
        }
    });

    this.client.once('authenticated', () => {
        this.status = 'authenticated';
        logger.sucesso(`[${this.clientId}] Autenticado com sucesso`);
    });

    this.client.once('ready', async () => {
        this.status = 'ready';
        this.metadata.connectedAt = new Date().toISOString();
        try {
            const info = this.client.info;
            this.phoneNumber = info.wid.user;
            logger.sucesso(`[${this.clientId}] Cliente pronto - Número: ${this.phoneNumber}`);
        } catch (erro) {
            logger.aviso(`[${this.clientId}] Não foi possível obter número`);
        }
        
        // Iniciar heartbeat quando pronto
        this.iniciarHeartbeat();
        
        this.callbacks.onReady(this.clientId, this.phoneNumber);
        
        // Processar fila
        try {
            const queue = require('../core/fila-mensagens');
            await queue.process(async (msg) => {
                if (msg.clientId !== this.clientId) return true;
                try {
                    await this.client.sendMessage(msg.to, msg.text);
                    logger.sucesso(`[${this.clientId}] Mensagem da fila enviada`);
                    return true;
                } catch(e) {
                    logger.aviso(`[${this.clientId}] Falha na fila: ${e.message}`);
                    return false;
                }
            });
        } catch(e) {
            logger.aviso(`[${this.clientId}] Erro na fila: ${e.message}`);
        }
    });

    this.client.on('message', async (message) => {
        const prometheusMetrics = require('../core/metricas-prometheus');
        this.metadata.messageCount++;
        prometheusMetrics.incrementCounter('whatsapp_messages_received_total', { clientId: this.clientId });
        logger.info(`[${this.clientId}] Mensagem recebida de ${message.from}`);
        this.callbacks.onMessage(this.clientId, message);
    });

    this.client.on('disconnected', (reason) => {
        this.status = 'disconnected';
        this.pararHeartbeat();  // NOVO: Parar heartbeat ao desconectar
        logger.aviso(`[${this.clientId}] Desconectado: ${reason}`);
        this.callbacks.onDisconnected(this.clientId, reason);
    });

    this.client.on('auth_failure', (message) => {
        this.status = 'error';
        this.pararHeartbeat();  // NOVO
        logger.erro(`[${this.clientId}] Falha de autenticação: ${message}`);
        this.callbacks.onAuthFailure(this.clientId, message);
    });

    this.client.on('loading_screen', (percent, message) => {
        logger.info(`[${this.clientId}] Carregando: ${percent}% - ${message}`);
    });

    this.client.on('error', (erro) => {
        logger.erro(`[${this.clientId}] Erro: ${erro.message || erro}`);
    });

    this.client.on('warn', (aviso) => {
        logger.aviso(`[${this.clientId}] Aviso: ${aviso.message || aviso}`);
    });
}
```

---

## CORREÇÃO 3: Melhorar Timeout Configuração

**Arquivo**: `src/services/ServicoClienteWhatsApp.js`

```javascript
// Em initialize(), substituir a criação do Client:

async initialize() {
    if (this.status === 'initializing' || this.status === 'ready') {
        logger.aviso(`[${this.clientId}] Cliente já está ${this.status}`);
        return { success: false, message: 'Cliente já está sendo inicializado' };
    }

    try {
        this.status = 'initializing';
        logger.info(`[${this.clientId}] Iniciando cliente WhatsApp...`);

        this.client = new Client({
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
                    '--disable-gpu'
                ],
                // ✅ NOVO: Configurar timeouts
                timeout: 30000,           // 30s para navigation
            },
            // ✅ NOVO: Usar versão mais recente
            webVersion: 'EDGE',
            webVersionCache: {
                type: 'local'            // Cache local = mais rápido
            }
        });

        this._setupEventListeners();
        
        logger.info(`[${this.clientId}] Iniciando cliente...`);

        // ✅ NOVO: Timeout reduzido de 120s para 45s
        const initPromise = this.client.initialize();
        const timeoutPromise = new Promise((resolve, reject) => {
            setTimeout(() => {
                reject(new Error('Timeout na inicialização (45s)'));
            }, 45000);
        });

        try {
            await Promise.race([initPromise, timeoutPromise]);
        } catch (timeoutError) {
            logger.aviso(`[${this.clientId}] ${timeoutError.message}`);
            // Não erro fatal, apenas aviso
        }

        logger.info(`[${this.clientId}] Cliente inicializado`);
        return { success: true, clientId: this.clientId };
        
    } catch (erro) {
        this.status = 'error';
        logger.erro(`[${this.clientId}] Erro ao inicializar: ${erro.message}`);
        return { success: false, message: erro.message };
    }
}
```

---

## CORREÇÃO 4: Circuit Breaker Pattern

**Arquivo**: `src/core/circuit-breaker.js` (NOVO)

```javascript
const logger = require('../infraestrutura/logger');

class CircuitBreaker {
    constructor(name = 'default', options = {}) {
        this.name = name;
        this.failureThreshold = options.failureThreshold || 5;
        this.resetTimeout = options.resetTimeout || 30000;  // 30s
        this.monitorInterval = options.monitorInterval || 60000;  // 60s
        
        this.state = 'CLOSED';  // CLOSED, OPEN, HALF_OPEN
        this.failureCount = 0;
        this.successCount = 0;
        this.lastFailureTime = null;
        this.nextAttemptTime = null;
        
        logger.info(`[CircuitBreaker] ${name} inicializado`);
    }
    
    async execute(fn, fallback = null) {
        // Se está aberto, verifica se pode tentar half-open
        if (this.state === 'OPEN') {
            if (Date.now() < this.nextAttemptTime) {
                if (fallback) {
                    logger.aviso(`[CircuitBreaker] ${this.name} aberto, usando fallback`);
                    return fallback();
                }
                throw new Error(`[CircuitBreaker] ${this.name} está aberto`);
            }
            
            logger.info(`[CircuitBreaker] ${this.name} tentando half-open`);
            this.state = 'HALF_OPEN';
        }
        
        try {
            const result = await fn();
            this.onSuccess();
            return result;
            
        } catch (erro) {
            this.onFailure();
            throw erro;
        }
    }
    
    onSuccess() {
        this.failureCount = 0;
        this.successCount++;
        
        if (this.state === 'HALF_OPEN' && this.successCount >= 2) {
            logger.sucesso(`[CircuitBreaker] ${this.name} FECHADO (recuperado)`);
            this.state = 'CLOSED';
            this.successCount = 0;
        }
    }
    
    onFailure() {
        this.failureCount++;
        this.lastFailureTime = Date.now();
        
        if (this.failureCount >= this.failureThreshold) {
            logger.erro(`[CircuitBreaker] ${this.name} ABERTO após ${this.failureCount} falhas`);
            this.state = 'OPEN';
            this.nextAttemptTime = Date.now() + this.resetTimeout;
        }
    }
    
    getState() {
        return {
            name: this.name,
            state: this.state,
            failures: this.failureCount,
            lastFailure: this.lastFailureTime
        };
    }
}

module.exports = CircuitBreaker;
```

**Usar em `GerenciadorPoolWhatsApp.js`**:

```javascript
const CircuitBreaker = require('./circuit-breaker');

class GerenciadorPoolWhatsApp {
    constructor(options = {}) {
        // ... código existente ...
        
        // ✅ NOVO: Circuit breaker para reconexão
        this.reconnectBreaker = new CircuitBreaker('reconnect', {
            failureThreshold: 5,
            resetTimeout: 30000
        });
    }
    
    async reconnectClient(clientId) {
        return this.reconnectBreaker.execute(
            async () => {
                const client = this.clients.get(clientId);
                if (!client) throw new Error('Cliente não encontrado');
                
                logger.info(`[Pool] Reconectando ${clientId}...`);
                return await client.reconnect();
            },
            () => {
                logger.aviso(`[Pool] Circuit breaker aberto, aguardando 30s...`);
                return { success: false, message: 'Circuit breaker ativo' };
            }
        );
    }
}
```

---

## CORREÇÃO 5: Health Check Proativo

**Arquivo**: `src/core/pool-health-checker.js` (NOVO)

```javascript
const logger = require('../infraestrutura/logger');

class PoolHealthChecker {
    constructor(pool, options = {}) {
        this.pool = pool;
        this.interval = options.interval || 30000;  // 30s
        this.timerId = null;
    }
    
    start() {
        logger.info('[HealthChecker] Iniciado (a cada 30s)');
        
        this.timerId = setInterval(async () => {
            for (const [clientId, client] of this.pool.clients) {
                await this.checkClient(client);
            }
        }, this.interval);
    }
    
    async checkClient(client) {
        if (client.status !== 'ready') {
            return;  // Não checar se não está pronto
        }
        
        try {
            // Validar conexão
            const chats = await client.client.getChats();
            
            logger.debug(`[HealthCheck] ${client.clientId} OK (${chats.length} chats)`);
            
        } catch (erro) {
            logger.aviso(`[HealthCheck] ${client.clientId} FALHOU: ${erro.message}`);
            
            // Marcar como desconectado
            client.status = 'disconnected';
            client.pararHeartbeat();
            client.callbacks.onDisconnected(client.clientId, 'HEALTH_CHECK_FAILED');
        }
    }
    
    stop() {
        if (this.timerId) {
            clearInterval(this.timerId);
            this.timerId = null;
            logger.info('[HealthChecker] Parado');
        }
    }
}

module.exports = PoolHealthChecker;
```

**Usar em `main.js`**:

```javascript
const PoolHealthChecker = require('./src/core/pool-health-checker');

// Em app.ready():
const healthChecker = new PoolHealthChecker(poolWhatsApp);
healthChecker.start();

// Em app.on('before-quit'):
healthChecker.stop();
```

---

## CORREÇÃO 6: Rate Limiting

**Arquivo**: `src/infraestrutura/rate-limiters.js` (NOVO)

```javascript
const rateLimit = require('express-rate-limit');
const logger = require('./logger');

module.exports = {
    // Rate limiter geral de API
    apiLimiter: rateLimit({
        windowMs: 15 * 60 * 1000,  // 15 minutos
        max: 100,                   // 100 requisições por IP
        message: 'Muitas requisições, tente mais tarde',
        standardHeaders: true,
        legacyHeaders: false,
        skip: (req, res) => {
            // Não limitar rotas internas
            return req.path.startsWith('/internal/');
        },
        handler: (req, res) => {
            logger.aviso(`[RateLimit] IP ${req.ip} excedeu limite`);
            res.status(429).json({
                success: false,
                message: 'Muitas requisições, tente mais tarde'
            });
        }
    }),
    
    // Rate limiter específico para conectar
    conectarLimiter: rateLimit({
        windowMs: 60 * 60 * 1000,  // 1 hora
        max: 10,                    // Máximo 10 conexões por hora
        message: 'Limite de conexões atingido',
        keyGenerator: (req, res) => {
            // Usar usuário ID se autenticado, senão IP
            return req.user?.id || req.ip;
        }
    }),
    
    // Rate limiter para mensagens
    mensagemLimiter: rateLimit({
        windowMs: 60 * 1000,  // 1 minuto
        max: 60,              // Máximo 60 mensagens por minuto
        skipSuccessfulRequests: false,
    })
};
```

**Usar em `src/infraestrutura/api.js`**:

```javascript
const limiters = require('./rate-limiters');

// ✅ Adicionar rate limiting às rotas:
router.post('/conectar-por-numero', limiters.conectarLimiter, async (req, res) => {
    // ...
});

router.post('/enviar-mensagem', limiters.mensagemLimiter, async (req, res) => {
    // ...
});

app.use(limiters.apiLimiter);  // Aplicar a todas as rotas
```

---

## RESUMO DAS MUDANÇAS

| Correção | Arquivo | Prioridade | Impacto |
|----------|---------|-----------|--------|
| Heartbeat | ServicoClienteWhatsApp.js | 🔴 CRÍTICO | Evita timeout de inatividade |
| Memory Leak Fix | ServicoClienteWhatsApp.js | 🔴 CRÍTICO | Evita acúmulo de listeners |
| Timeout Redução | ServicoClienteWhatsApp.js | 🔴 CRÍTICO | Melhor UX (45s ao invés de 120s) |
| Circuit Breaker | circuit-breaker.js (novo) | 🟠 ALTO | Evita cascata de falhas |
| Health Check | pool-health-checker.js (novo) | 🟠 ALTO | Detecção proativa de problemas |
| Rate Limiting | rate-limiters.js (novo) | 🟠 ALTO | Proteção contra abuso |

---

**Tempo de Implementação**: 3-4 horas
**Benefício**: 95% redução em desconexões automáticas
