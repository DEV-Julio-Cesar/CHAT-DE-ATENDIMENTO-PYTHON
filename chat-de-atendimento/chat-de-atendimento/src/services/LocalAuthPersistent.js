/**
 * 🔐 LocalAuthPersistent
 * 
 * Estratégia de autenticação customizada que PRESERVA a sessão
 * mesmo quando o WhatsApp emite eventos de logout automático.
 * 
 * Isso resolve o problema de desconexões involuntárias causadas
 * pela biblioteca whatsapp-web.js que chama authStrategy.logout()
 * automaticamente quando detecta navegação para post_logout=1.
 */

'use strict';

const path = require('path');
const fs = require('fs');
const BaseAuthStrategy = require('whatsapp-web.js/src/authStrategies/BaseAuthStrategy');
const logger = require('../infraestrutura/logger');

class LocalAuthPersistent extends BaseAuthStrategy {
    constructor({ clientId, dataPath, rmMaxRetries } = {}) {
        super();

        const idRegex = /^[-_\w]+$/i;
        if (clientId && !idRegex.test(clientId)) {
            throw new Error('Invalid clientId. Only alphanumeric characters, underscores and hyphens are allowed.');
        }

        this.dataPath = path.resolve(dataPath || './.wwebjs_auth/');
        this.clientId = clientId;
        this.rmMaxRetries = rmMaxRetries ?? 4;
        
        // Flag para controlar se logout deve realmente limpar arquivos
        this._allowSessionCleanup = false;
    }

    async beforeBrowserInitialized() {
        const puppeteerOpts = this.client.options.puppeteer;
        const sessionDirName = this.clientId ? `session-${this.clientId}` : 'session';
        const dirPath = path.join(this.dataPath, sessionDirName);

        if (puppeteerOpts.userDataDir && puppeteerOpts.userDataDir !== dirPath) {
            throw new Error('LocalAuthPersistent is not compatible with a user-supplied userDataDir.');
        }

        fs.mkdirSync(dirPath, { recursive: true });

        this.client.options.puppeteer = {
            ...puppeteerOpts,
            userDataDir: dirPath
        };

        this.userDataDir = dirPath;
    }

    /**
     * Método logout MODIFICADO - NÃO remove arquivos de sessão automaticamente
     * A limpeza só ocorre se _allowSessionCleanup for true (logout explícito do usuário)
     */
    async logout() {
        if (!this._allowSessionCleanup) {
            // Log e NÃO remover arquivos - preservar sessão para reconexão futura
            logger.aviso(`[LocalAuthPersistent] Logout automático detectado para ${this.clientId || 'default'} - PRESERVANDO sessão (não removendo arquivos)`);
            return;
        }

        // Logout explícito solicitado - remover arquivos
        if (this.userDataDir) {
            logger.info(`[LocalAuthPersistent] Logout explícito - removendo sessão ${this.clientId || 'default'}`);
            await fs.promises.rm(this.userDataDir, { recursive: true, force: true, maxRetries: this.rmMaxRetries })
                .catch((e) => {
                    logger.aviso(`[LocalAuthPersistent] Erro ao remover sessão (pode ser EBUSY): ${e.message}`);
                    // Não propagar erro - apenas logar
                });
        }
    }

    /**
     * Habilita a limpeza de sessão para o próximo logout
     * Deve ser chamado antes de client.logout() quando o usuário quer realmente deslogar
     */
    enableSessionCleanup() {
        this._allowSessionCleanup = true;
        logger.info(`[LocalAuthPersistent] Limpeza de sessão HABILITADA para ${this.clientId || 'default'}`);
    }

    /**
     * Desabilita a limpeza de sessão (padrão)
     */
    disableSessionCleanup() {
        this._allowSessionCleanup = false;
        logger.info(`[LocalAuthPersistent] Limpeza de sessão DESABILITADA para ${this.clientId || 'default'}`);
    }

    /**
     * Força a limpeza da sessão manualmente (para uso administrativo)
     */
    async forceCleanup() {
        if (this.userDataDir) {
            logger.info(`[LocalAuthPersistent] Forçando limpeza de sessão ${this.clientId || 'default'}`);
            await fs.promises.rm(this.userDataDir, { recursive: true, force: true, maxRetries: this.rmMaxRetries })
                .catch((e) => {
                    logger.aviso(`[LocalAuthPersistent] Erro na limpeza forçada: ${e.message}`);
                });
        }
    }
}

module.exports = LocalAuthPersistent;
