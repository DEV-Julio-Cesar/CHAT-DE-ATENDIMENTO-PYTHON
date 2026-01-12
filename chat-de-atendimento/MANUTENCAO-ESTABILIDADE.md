# 🛡️ GUIA DE MANUTENÇÃO - MANTER SISTEMA ESTÁVEL

## ⚠️ Coisas Que NÃO DEVEM ser Feitas

### ❌ NÃO FAZER #1: Re-adicionar listeners sem limpar

```javascript
// ❌ ERRADO - Vai duplicar eventos!
_setupEventListeners() {
    this.client.on('ready', async () => { ... });
    this.client.on('ready', async () => { ... }); // Duplicate!
}

// ✅ CORRETO - Limpar primeiro
_setupEventListeners() {
    if (this.client) {
        this.client.removeAllListeners('ready');
    }
    this.client.once('ready', async () => { ... });
}
```

---

### ❌ NÃO FAZER #2: Habilitar auto-reconnect por padrão

```javascript
// ❌ ERRADO - Vai causar loop LOGOUT
autoReconnect: true,  // Reconecta mesmo em LOGOUT!

// ✅ CORRETO - Desabilitado por padrão
autoReconnect: false,  // Requer explicitly enabled
```

---

### ❌ NÃO FAZER #3: Acessar window sem verificar se existe

```javascript
// ❌ ERRADO - Vai dar null reference
if (this.currentWindow) {
    this.currentWindow.close();
}
this.currentWindow = new BrowserWindow(...);
this.currentWindow.webContents.send(...); // Pode ser null!

// ✅ CORRETO - Verificar sempre
if (this.currentWindow && !this.currentWindow.isDestroyed()) {
    this.currentWindow.webContents.send(...);
}
```

---

## ✅ Melhores Práticas

### Prática 1: Limpeza de Recursos

```javascript
// Sempre limpar listeners antigos antes de novos
class ServiceCliente {
    setup() {
        this.cleanup(); // ← Sempre primeiro
        this._setupNewListeners();
    }
    
    cleanup() {
        if (this.client) {
            this.client.removeAllListeners();
        }
    }
}
```

---

### Prática 2: Transições Seguras

```javascript
// Ao mudar de página:
navigate(route) {
    // 1. Fechar com segurança
    if (this.currentWindow) {
        try {
            this.currentWindow.close();
        } catch (e) {
            logger.aviso(`Erro ao fechar: ${e.message}`);
        }
        this.currentWindow = null; // ← Set immediately
    }
    
    // 2. Aguardar um pouco
    setTimeout(() => {
        // 3. Criar novo
        this.currentWindow = new BrowserWindow(...);
    }, 100);
}
```

---

### Prática 3: Proteção de Null

```javascript
// Pattern seguro para acessar janelas
accessWindow(callback) {
    if (!this.currentWindow) {
        logger.aviso('Janela não existe');
        return;
    }
    
    if (this.currentWindow.isDestroyed()) {
        logger.aviso('Janela foi destruída');
        return;
    }
    
    try {
        callback(this.currentWindow);
    } catch (erro) {
        logger.erro(`Erro ao acessar janela: ${erro.message}`);
        this.currentWindow = null;
    }
}
```

---

## 📋 Checklist de Implementação

Antes de fazer qualquer mudança no código, verificar:

- [ ] **Event Listeners**: Se adicionar listeners, chamou `removeAllListeners()` primeiro?
- [ ] **Auto-reconnect**: Está desabilitado por padrão? Só habilitado explicitamente?
- [ ] **Null Checks**: Antes de acessar `window.webContents`, verificou `!isDestroyed()`?
- [ ] **Try-Catch**: Operações críticas (close, send) têm tratamento de erro?
- [ ] **Logs**: Há logs de todos os estados críticos?
- [ ] **Testes**: Testou a mudança por pelo menos 5 minutos?

---

## 🔄 Processo de Atualização Segura

### Passo 1: Backup
```bash
# Copiar arquivos críticos
copy dados/atendimentos.json dados/atendimentos.json.backup
copy dados/filas-atendimento.json dados/filas-atendimento.json.backup
```

### Passo 2: Modificar
- Fazer mudança no código
- Verificar checklist acima
- Adicionar logs

### Passo 3: Testar Localmente
```bash
npm start
# Deixar rodar por 5+ minutos
# Verificar logs em tempo real
# Testar navegação entre páginas
# Enviar mensagem de teste
```

### Passo 4: Validar
```bash
# Se houver erro, restaurar backup:
copy dados/atendimentos.json.backup dados/atendimentos.json
npm start
```

### Passo 5: Deploy
```bash
# Só depois de validado:
# Fazer pull, npm start em produção
```

---

## 🚨 Sinais de Alerta

Se vir algum destes, PARAR imediatamente:

### Sinal 1: Duplicação de Eventos
```
[INFO] Cliente pronto
[INFO] Cliente pronto
[INFO] Cliente pronto
```
**Ação:** Procurar por listeners sendo adicionados múltiplas vezes

---

### Sinal 2: Loop LOGOUT
```
[AVISO] Desconectado: LOGOUT
[INFO] Agendando reconexão...
[AVISO] Desconectado: LOGOUT
[INFO] Agendando reconexão...
```
**Ação:** Verificar auto-reconnect está desabilitado

---

### Sinal 3: Null Reference
```
[ERRO] Cannot read properties of null (reading 'webContents')
```
**Ação:** Adicionar null checks antes de acessar window

---

### Sinal 4: CPU Alta
```
CPU: 95%+ | Memory: 500MB+
```
**Ação:** Procurar por loops infinitos ou listeners duplicados

---

## 📊 Monitoramento Recomendado

### Log Patterns para Monitorar

```javascript
// Bom sinal ✅
[SUCESSO] Cliente pronto - Número: 5584920024786
[SUCESSO] Login bem-sucedido
[INFO] Navigation Navegando para: principal

// Sinal de alerta ⚠️
[AVISO] Desconectado
[INFO] Agendando reconexão

// Problema crítico ❌
[ERRO] Cannot read properties of null
[ERRO] Protocol error
[ERRO] Unhandled rejection
```

---

## 🔧 Ferramentas de Debug

### Verificar Listeners
```javascript
// Em qualquer arquivo
console.log(client.listenerCount('ready')); // Deve ser 1
console.log(client.listenerCount('message')); // Pode ser >1
```

### Verificar Window State
```javascript
console.log(this.currentWindow === null); // Deve ser false quando ativo
console.log(this.currentWindow.isDestroyed()); // Deve ser false quando ativo
```

### Verificar Configuração
```javascript
console.log(config.autoReconnect); // Deve ser false
console.log(config.reconnectDelay); // Deve ser >5000ms
```

---

## 📞 Troubleshooting Rápido

### Problema: "Cannot read properties of null"

```
1. Procurar na stack trace qual arquivo/linha
2. Verificar se está acessando window/webContents
3. Adicionar: if (window && !window.isDestroyed())
4. Testar novamente
```

---

### Problema: "Cliente pronto" aparece 3x

```
1. Procurar por _setupEventListeners
2. Verificar se tem removeAllListeners()
3. Se não tem, adicionar antes dos listeners
4. Trocar .on() → .once() para eventos single-fire
5. Testar novamente
```

---

### Problema: Desconexões frequentes

```
1. Verificar logs por "LOGOUT"
2. Se vir auto-reconexão após LOGOUT, problema found
3. Verificar GerenciadorPoolWhatsApp reason !== 'LOGOUT'
4. Se não tem esse check, adicionar
5. Testar novamente
```

---

## 🎓 Lições Aprendidas

1. **Event Listeners são cumulativos**: cada `.on()` ADICIONA, não substitui
2. **Window close é assíncrono**: pode levar ms para completar
3. **LOGOUT é intencional**: não deve trigger reconexão automática
4. **Null checks salvam**: sempre verificar antes de acessar
5. **Logs são gold**: sem logs, impossível debugar remotely

---

## 📝 Documentação Relacionada

- [RELATORIO-CORRECOES-WHATSAPP.md](RELATORIO-CORRECOES-WHATSAPP.md) - Detalhes técnicos
- [VALIDACAO-FINAL.md](VALIDACAO-FINAL.md) - Resultados de testes
- [RESUMO-VISUAL.md](RESUMO-VISUAL.md) - Visualização antes/depois

---

## ✅ Conclusão

O sistema está estável quando:

- ✅ Eventos disparam exatamente 1x
- ✅ Nenhum loop de reconexão
- ✅ Navegação sem erros
- ✅ Logs limpos e legíveis
- ✅ CPU/Memory normais
- ✅ Sem crashes em 24+ horas

Manter essas práticas e o sistema permanecerá estável!

---

**Última Atualização:** 11 de Janeiro de 2026  
**Versão:** 2.0.0  
**Status:** ✅ ESTÁVEL
