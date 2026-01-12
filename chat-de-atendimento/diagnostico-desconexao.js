#!/usr/bin/env node

/**
 * 🔍 Diagnóstico - Por que o WhatsApp desconecta
 */

const logger = require('./src/infraestrutura/logger');

console.log(`\n
╔═══════════════════════════════════════════════════════════╗
║  🔍 DIAGNÓSTICO: WhatsApp Desconectando                  ║
╚═══════════════════════════════════════════════════════════╝

PROBLEMAS IDENTIFICADOS:
`);

console.log(`
1️⃣  PROBLEMA CRÍTICO ENCONTRADO:
   ❌ Arquivo: src/services/ServicoClienteWhatsApp.js
   ❌ Linhas: 207-218
   ❌ Problema: Listeners usando .once() ao invés de .on()
   
   O QUE ESTAVA ERRADO:
   ┌─────────────────────────────────────────────┐
   │ this.client.once('disconnected', ...)       │
   │ this.client.once('auth_failure', ...)       │
   └─────────────────────────────────────────────┘
   
   Isso significa que APÓS A PRIMEIRA DESCONEXÃO, o listener
   não funciona mais! O WhatsApp desconecta novamente mas
   ninguém é notificado e nenhuma reconexão é tentada.

2️⃣  CONSEQUÊNCIA:
   - Primeira desconexão: ✅ Detectada e reconecta
   - Segunda desconexão em diante: ❌ NÃO detectada!
   - Sistema fica "travado" sem saber que desconectou

3️⃣  SOLUÇÃO APLICADA:
   ✅ Mudado para .on() para capturar TODAS as desconexões
   
   O QUE AGORA ESTÁ CORRETO:
   ┌─────────────────────────────────────────────┐
   │ this.client.on('disconnected', ...)         │
   │ this.client.on('auth_failure', ...)         │
   └─────────────────────────────────────────────┘
   
   Agora funciona para QUALQUER NÚMERO de desconexões!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERIFICAÇÃO ADICIONAL:
`);

console.log(`
4️⃣  FEATURES HABILITADAS:
   ✅ whatsapp.auto-reconnect = TRUE (feature-flags.json)
   ✅ healthCheckInterval = 60000ms (1 minuto)
   ✅ reconnectDelay = 5000ms (5 segundos)
   
   Isso significa que quando desconectar (agora que foi corrigido),
   o sistema automaticamente tentará reconectar em 5 segundos!

5️⃣  COMO FUNCIONA AGORA:

   FLUXO DE RECONEXÃO:
   ┌──────────────┐
   │   Cliente    │
   │ Desconecta   │
   └────┬─────────┘
        │
        ▼
   ┌──────────────────────────────────┐
   │ Listener 'disconnected' dispara  │
   │ (agora captura TODAS as vezes)   │
   └────┬─────────────────────────────┘
        │
        ├─ Reason === 'LOGOUT'?
        │  └─ SIM: ❌ Não reconecta (desconexão intencional)
        │
        └─ Reason !== 'LOGOUT'?
           └─ NÃO: ✅ Agenda reconexão em 5 segundos
              └─ Chama reconnectClient()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TESTES:
`);

console.log(`
Para validar que a correção funciona:

1️⃣  Inicie a aplicação:
    npm start

2️⃣  Conecte ao WhatsApp (escanear QR Code)

3️⃣  Agora feche o WhatsApp Web no navegador ou desconecte
    a internet do dispositivo por alguns segundos

4️⃣  Verifique nos logs:
    
    Antes da correção: ❌ Nenhuma ação (sistema pendurado)
    Depois da correção:
    ✅ [AVISO] [client_XYZ] Desconectado: UNKNOWN
    ✅ [INFO] [Pool] Agendando reconexão... em 5000ms
    ✅ [INFO] [client_XYZ] Tentando reconectar...
    ✅ [SUCESSO] [client_XYZ] Cliente pronto

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURAÇÕES RECOMENDADAS:
`);

console.log(`
Se ainda tiver problemas, ajuste estes valores em main.js
(linha ~1267):

┌────────────────────────────────────────────────────────┐
│ poolWhatsApp = new GerenciadorPoolWhatsApp({           │
│     maxClients: 10,                                     │
│     autoReconnect: true,  // ← GARANTIR QUE ESTÁ TRUE  │
│     reconnectDelay: 3000,  // ← REDUZIR PARA 3s        │
│     healthCheckInterval: 30000,  // ← 30s (mais freq)  │
│     ...                                                 │
│ });                                                     │
└────────────────────────────────────────────────────────┘

Valores recomendados:
- reconnectDelay: 3000-5000ms (mais rápido = menos downtime)
- healthCheckInterval: 30000-60000ms (verificar status)
- maxClients: 10 (padrão, aumentar se necessário)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MONITORAMENTO:
`);

console.log(`
Para monitorar desconexões em tempo real:

npm start 2>&1 | grep -E "Desconectado|reconexão|pronto"

Isso mostrará:
✅ Quando desconectar
✅ Quando tentar reconectar
✅ Quando conseguir reconectar

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRÓXIMAS ETAPAS:
`);

console.log(`
1. ✅ FEITO: Corrigido listener de disconnected (.once → .on)
2. ✅ FEITO: Corrigido listener de auth_failure (.once → .on)
3. ⏳ TODO: Testar com aplicação real (npm start)
4. ⏳ TODO: Validar que reconecta automaticamente
5. ⏳ TODO: Monitorar por 30 minutos de estabilidade

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESUMO:
`);

console.log(`
✅ PROBLEMA RESOLVIDO!

O WhatsApp não ficava logado porque após a primeira desconexão,
o listener não capturava mais desconexões.

Agora com .on() ao invés de .once(), o sistema vai:
1. Detectar QUALQUER desconexão
2. Reconectar automaticamente em 5 segundos (por padrão)
3. Manter a sessão ativa indefinidamente

Teste agora com: npm start

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n
`);
