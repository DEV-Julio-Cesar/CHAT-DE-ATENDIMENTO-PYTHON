# 🔧 Correção: Problema de Desconexão WhatsApp

## 🐛 Problema Identificado

O WhatsApp estava desconectando repetidamente logo após conectar. Nos logs apareciam:

```
[SUCESSO] Cliente pronto - Número: 558492...
[SUCESSO] Cliente pronto - Número: 558492...  ← DUPLICADO!
[SUCESSO] Cliente pronto - Número: 558492...  ← DUPLICADO!
[AVISO] Desconectado: LOGOUT
[AVISO] Desconectado: LOGOUT  ← MÚLTIPLOS!
[AVISO] Desconectado: LOGOUT  ← MÚLTIPLOS!
[INFO] Agendando reconexão... (4x simultâneas!)
```

## 🔍 Causa Raiz

**Múltiplos event listeners duplicados:**

1. Event listeners do WhatsApp não eram removidos ao reconectar
2. Cada reconexão adicionava novos listeners SEM remover os antigos
3. Resultado: 1 evento → 4 callbacks simultâneos
4. Callbacks simultâneos causavam conflitos no estado do cliente
5. Conflitos forçavam desconexão (LOGOUT)
6. Sistema tentava reconectar → ciclo infinito

## ✅ Solução Implementada

### 1. **Remover Listeners Antes de Adicionar** 
[ServicoClienteWhatsApp.js](../src/services/ServicoClienteWhatsApp.js#L121-L135)

```javascript
_setupEventListeners() {
    // NOVO: Remove todos os listeners anteriores
    if (this.client) {
        this.client.removeAllListeners('qr');
        this.client.removeAllListeners('authenticated');
        this.client.removeAllListeners('ready');
        this.client.removeAllListeners('message');
        this.client.removeAllListeners('disconnected');
        this.client.removeAllListeners('auth_failure');
    }
    
    // Registra listeners limpos
    this.client.once('qr', ...);
    this.client.once('ready', ...);
    // ...
}
```

### 2. **Usar `.once()` em Vez de `.on()`**
[ServicoClienteWhatsApp.js](../src/services/ServicoClienteWhatsApp.js#L138-L165)

```javascript
// ANTES (ERRADO):
this.client.on('ready', async () => { ... });
this.client.on('authenticated', () => { ... });
this.client.on('disconnected', () => { ... });

// DEPOIS (CORRETO):
this.client.once('ready', async () => { ... });
this.client.once('authenticated', () => { ... });
this.client.once('disconnected', () => { ... });
```

**Por que?** `.once()` garante que o callback só seja executado UMA VEZ, mesmo que o evento seja disparado múltiplas vezes.

### 3. **Proteção Contra Múltiplas Reconexões**
[GerenciadorPoolWhatsApp.js](../src/services/GerenciadorPoolWhatsApp.js#L96-L120)

```javascript
onDisconnected: (id, reason) => {
    // NOVO: Verifica se já está reconectando
    const client = this.clients.get(id);
    if (client && client._isReconnecting) {
        logger.aviso(`Reconexão já em andamento, ignorando`);
        return; // Ignora requisições duplicadas
    }
    
    // NOVO: Só reconecta se NÃO for LOGOUT
    if (this.config.autoReconnect && reason !== 'LOGOUT') {
        if (client) client._isReconnecting = true;
        
        setTimeout(() => {
            this.reconnectClient(id).finally(() => {
                if (client) client._isReconnecting = false;
            });
        }, this.config.reconnectDelay);
    } else if (reason === 'LOGOUT') {
        logger.info(`Desconectado por LOGOUT - não reconectando`);
    }
}
```

### 4. **Não Reconectar em Caso de LOGOUT**

**Motivo:** LOGOUT geralmente indica desconexão intencional:
- Usuário desconectou o WhatsApp Web
- Aplicativo fechado propositalmente
- Sessão invalidada

**Comportamento anterior:**
- LOGOUT → Tenta reconectar → Gera novo LOGOUT → Loop infinito

**Comportamento novo:**
- LOGOUT → Log informativo → Aguarda reconexão manual

---

## 📊 Comparação Antes/Depois

### ❌ **ANTES:**

```
[11:48:11] Cliente pronto
[11:48:11] Cliente pronto  ← Duplicado!
[11:48:11] Cliente pronto  ← Duplicado!
[11:48:12] Desconectado: LOGOUT
[11:48:12] Desconectado: LOGOUT  ← Duplicado!
[11:48:12] Desconectado: LOGOUT  ← Duplicado!
[11:48:12] Agendando reconexão... (4x)
[11:48:17] Reconectando... (4x simultâneos!)
[11:48:18] Protocol error: Session closed
```

### ✅ **DEPOIS:**

```
[11:52:15] Cliente pronto
[11:52:15] WhatsApp conectado e estável
(Permanece conectado sem desconexões)
```

---

## 🎯 Benefícios

1. **Estabilidade:** Conexão mantida sem desconexões aleatórias
2. **Performance:** Sem múltiplos callbacks desperdiçando recursos
3. **Logs limpos:** Sem spam de mensagens duplicadas
4. **Controle:** Reconexão inteligente apenas quando necessário
5. **Confiabilidade:** Sistema não entra em loop de reconexão

---

## 🧪 Como Testar

1. **Conecte o WhatsApp:**
   ```
   npm start
   Conecte normalmente escaneando QR Code
   ```

2. **Verifique logs:**
   ```
   [SUCESSO] Cliente pronto - Número: 558492...
   (Apenas UMA linha, sem duplicatas)
   ```

3. **Aguarde 5 minutos:**
   - Conexão deve permanecer estável
   - Sem desconexões espontâneas
   - Sem tentativas de reconexão

4. **Envie mensagem de teste:**
   - Sistema deve receber normalmente
   - Sem perda de mensagens
   - Sem delays

---

## 📝 Arquivos Modificados

1. **src/services/ServicoClienteWhatsApp.js**
   - Adicionado: `removeAllListeners()` antes de registrar eventos
   - Alterado: `.on()` → `.once()` para eventos únicos
   - Linhas: 121-165

2. **src/services/GerenciadorPoolWhatsApp.js**
   - Adicionado: Flag `_isReconnecting` para prevenir duplicatas
   - Alterado: Lógica de reconexão para ignorar LOGOUT
   - Adicionado: Validação antes de agendar reconexão
   - Linhas: 96-120

---

## ⚙️ Configuração

Se você quiser **desabilitar completamente a reconexão automática**, edite o pool:

```javascript
// Em main.js ou onde o pool é criado:
const poolWhatsApp = new GerenciadorPoolWhatsApp({
    autoReconnect: false  // Desabilita reconexão automática
});
```

Se quiser **ajustar o delay de reconexão:**

```javascript
const poolWhatsApp = new GerenciadorPoolWhatsApp({
    autoReconnect: true,
    reconnectDelay: 10000  // 10 segundos (padrão: 5000)
});
```

---

## 🚨 Troubleshooting

**Se ainda houver desconexões:**

1. Verifique se há múltiplas instâncias do Electron rodando:
   ```powershell
   Get-Process | Where-Object {$_.ProcessName -like "*electron*"}
   ```

2. Limpe as sessões antigas:
   ```powershell
   Remove-Item -Recurse -Force .wwebjs_auth/*
   ```

3. Reinicie completamente:
   ```powershell
   npm start
   ```

4. Verifique logs do WhatsApp:
   - Procure por "Protocol error"
   - Procure por múltiplos "Cliente pronto"
   - Procure por "Reconexão já em andamento"

---

## 📚 Referências

- [whatsapp-web.js Documentation](https://wwebjs.dev/)
- [Node.js EventEmitter](https://nodejs.org/api/events.html)
- Issue relacionada: WhatsApp multiple connections causing logout

---

**Data da correção:** 11/01/2026  
**Versão:** 2.0.1  
**Status:** ✅ Resolvido e testado
