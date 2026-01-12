# 🛡️ Tratamento de Erros - WhatsApp Web.js + Puppeteer

## Problema Identificado

Quando o WhatsApp Web fecha a sessão ou o browser desconecta, ocorrem erros de protocolo que podem aparecer como:

```
[ERRO] ƒöÑ UNHANDLED REJECTION: {}
Protocol error (Runtime.callFunctionOn): Session closed. Most likely the page has been closed.
```

Estes erros vêm do Puppeteer (navegador headless) e são **completamente normais** durante:
- Fechamento seguro da sessão
- Desconexão do navegador
- Timeout de sessão
- Recarga da página de login

## Solução Implementada

### 1. **Tratador Global de Erros** (`tratador-erros.js`)

Adiciona filtros para erros benignos que são parte do ciclo de vida normal:

```javascript
// Erros esperados durante operações normais
if (errorMsg.includes('Session closed') || 
    errorMsg.includes('Protocol error') ||
    errorMsg.includes('Browser closed') ||
    errorMsg.includes('page has been closed')) {
  this.logger.info(`[WhatsApp] Sessão fechada (esperado): ...`);
  return; // Não processa como erro
}
```

**Benefício:** Elimina log noise enquanto preserva erros reais.

### 2. **Melhorias no ServicoClienteWhatsApp** 

#### 2.1 Disconnect com Proteção de Timeout

```javascript
async disconnect() {
    // Timeout de 5 segundos para destroy()
    const destroyPromise = Promise.race([
        this.client.destroy(),
        new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Timeout')), 5000)
        )
    ]);
    
    // Erros de protocolo durante destroy são ignorados (esperados)
    await destroyPromise.catch(err => {
        if (!err.message.includes('Protocol error') && 
            !err.message.includes('page has been closed')) {
            throw err;
        }
    });
}
```

**Benefício:** Disconnect não fica pendurado; erros esperados são ignorados.

#### 2.2 Listeners para Erros do Browser

```javascript
// Proteção contra desconexão não esperada do browser
if (this.client && this.client.pupBrowser) {
    this.client.pupBrowser.once('disconnected', () => {
        logger.aviso(`[${this.clientId}] Browser desconectou`);
        this.status = 'disconnected';
    });
}

// Listeners de erro e aviso
this.client.on('error', (erro) => {
    logger.erro(`[${this.clientId}] Erro do cliente:`, erro.message);
});

this.client.on('warn', (aviso) => {
    logger.aviso(`[${this.clientId}] Aviso:`, aviso.message);
});
```

**Benefício:** Qualquer erro de browser é capturado e registrado adequadamente.

### 3. **Limpeza de Listeners**

```javascript
_setupEventListeners() {
    // Remove listeners antigos
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
    
    // Proteção contra memory leaks
    if (this.client && this.client.pupBrowser) {
        this.client.pupBrowser.removeAllListeners('disconnected');
    }
}
```

**Benefício:** Previne memory leaks e listeners duplicados.

## Categorias de Erros

### ✅ Erros Benignos (Log como INFO)
- `Session closed` - Fechamento normal da sessão
- `Protocol error` - Erro de protocolo Puppeteer (esperado)
- `Browser closed` - Browser foi fechado
- `page has been closed` - Página foi recarregada

**Ação:** Apenas log informativo, sem alert

### ⚠️ Erros de Aviso (Log como AVISO)
- `Desconectado: <razão>` - Desconexão esperada
- `Browser desconectou` - Browser perdeu conexão
- `Cliente não pronto` - Cliente ainda inicializando

**Ação:** Log e tentativa de reconexão automática

### ❌ Erros Críticos (Log como ERRO)
- `Falha de autenticação` - QR não escaneado ou expirou
- `Erro ao enviar mensagem` - Falha real na entrega
- `Erro ao inicializar` - Cliente não conseguiu iniciar
- Qualquer outro erro não filtrado

**Ação:** Log, alerta e possível intervenção manual

## Fluxo de Tratamento

```
┌─────────────────────────────────────────┐
│   Erro Lançado / Rejeição               │
└─────────────────────────┬───────────────┘
                          │
                    ┌─────▼──────┐
                    │ É benigo?  │
                    └─────┬──────┘
                         / \
                   Sim  /   \  Não
                       /     \
          ┌──────────┐      ┌──────────────┐
          │Log INFO  │      │Log ERRO      │
          │Retorna   │      │Processa      │
          │(ignora)  │      │(handling)    │
          └──────────┘      └──────────────┘
```

## Resultado

### Antes ❌
```
[ERRO] ƒöÑ UNHANDLED REJECTION: {}
Protocol error (Runtime.callFunctionOn): Session closed...
[ERRO] ƒöÑ UNHANDLED REJECTION: {}
Protocol error (Runtime.callFunctionOn): Session closed...
[ERRO] ƒöÑ UNHANDLED REJECTION: {}
Protocol error (Runtime.callFunctionOn): Session closed...
```

### Depois ✅
```
[INFO] [WhatsApp] Sessão fechada (esperado): Protocol error (Runtime.callFunctionOn)
[INFO] [client_001] QR Code gerado
[INFO] [client_001] Carregando: 50% - Preparando navegador
✓ [SUCESSO] [client_001] Cliente pronto
```

## Monitoramento

Para monitorar erros reais, use:

```bash
# Ver apenas erros críticos
npm start 2>&1 | grep "^\[ERRO\]" | grep -v "Protocol error"

# Ver warning logs
npm start 2>&1 | grep "^\[AVISO\]"

# Ver apenas sucessos
npm start 2>&1 | grep "^\[SUCESSO\]"
```

## Recomendações

1. **Não Suprima Completamente:** Mantenha logs de INFO para auditoria
2. **Monitore Padrões:** Se vir muitos "Session closed", pode haver timeout
3. **Aumente Timeout:** Se `destroy()` frequently timeout, aumente de 5s para 10s
4. **Teste Desconexões:** Feche a página do WhatsApp e veja se reconecta
5. **Valide Listeners:** Nenhum listener deve permanecer pendente após disconnect

## Checklist de Validação

- [x] Erros benignos filtrados a INFO
- [x] unhandledRejection tratado globalmente
- [x] Listeners removidos antes de recriar
- [x] Timeout em destroy() com 5 segundos
- [x] Browser disconnect listeners adicionados
- [x] Error/warn listeners do cliente adicionados
- [x] Logs informativos mas sem ruído
- [x] Erros críticos ainda aparecem normalmente

## Debug

Se ainda ver UNHANDLED REJECTION, ative debug:

```javascript
// Em main.js, antes de require('../src/infraestrutura/api')
process.on('unhandledRejection', (reason, promise) => {
    console.error('🔴 UNHANDLED REJECTION:', {
        reason: reason,
        message: reason?.message,
        stack: reason?.stack,
        promise: promise
    });
});
```

## Referências

- [whatsapp-web.js Docs](https://wwebjs.dev/)
- [Puppeteer Documentation](https://pptr.dev/)
- [Node.js Error Handling](https://nodejs.org/en/docs/guides/nodejs-error-handling/)
