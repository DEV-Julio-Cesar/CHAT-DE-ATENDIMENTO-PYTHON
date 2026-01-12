# 🚀 REFERÊNCIA RÁPIDA - IA Humanizada

Colinha para programadores - todos os métodos e exemplos em um lugar.

---

## 📦 IMPORTAÇÃO

```javascript
const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');
const servicoIA = new ServicoIAHumanizada({
    servico: 'Chat de Atendimento',
    empresa: 'Sua Empresa'
});
```

---

## 🎯 MÉTODOS - REFERÊNCIA RÁPIDA

### 1️⃣ Processar Mensagem (Mais Usado)
```javascript
const resultado = await servicoIA.procesarMensagemCliente(
    'texto da mensagem',           // string (obrigatório)
    'cliente_123',                 // ID único (obrigatório)
    'duvida',                      // tipo (opcional: saudacao|duvida|problema|reclamacao|feedback|oferta)
    { nome: 'João' }               // info (opcional)
);

// Response:
// {
//   success: true/false,
//   resposta: "Resposta humanizada...",
//   tipo: "duvida",
//   timestamp: Date
// }
```

**Tipos disponíveis:**
```
saudacao      → Primeira interação (tom amigável)
duvida        → Pergunta comum (tom profissional)
problema      → Problema técnico (tom solução)
reclamacao    → Cliente insatisfeito (tom atencioso)
feedback      → Elogio/sugestão (tom amigável)
oferta        → Sugerir serviço (tom profissional)
```

---

### 2️⃣ Problema com Histórico
```javascript
const resultado = await servicoIA.processarProblemaComHistorico(
    'Não consigo fazer login',          // descrição (obrigatório)
    'cliente_123',                      // ID (obrigatório)
    ['Reiniciar', 'Limpar cache']       // tentativas anteriores (opcional)
);

// Response:
// {
//   success: true/false,
//   resposta: "Vamos tentar algo diferente...",
//   tipo: "resolucao_problema"
// }
```

---

### 3️⃣ Cliente Frustrado
```javascript
const resultado = await servicoIA.processarClienteInsatisfeito(
    'Estou muito frustrado!',           // motivo (obrigatório)
    'cliente_123',                      // ID (obrigatório)
    'Contexto do problema...'           // histórico (opcional)
);

// Response:
// {
//   success: true/false,
//   resposta: "Sinto muito pelos problemas. Vou resolver isso!",
//   tipo: "insatisfacao"
// }
```

---

### 4️⃣ Pergunta Diagnóstica
```javascript
const resultado = await servicoIA.fazerPerguntaDiagnostica(
    'Meu sistema está lento',           // situação (obrigatório)
    'cliente_123'                       // ID (obrigatório)
);

// Response:
// {
//   success: true/false,
//   pergunta: "Quando começou a ficar lento?"
// }
```

---

### 5️⃣ Feedback Positivo
```javascript
const resultado = await servicoIA.responderFeedbackPositivo(
    'Vocês foram incríveis!',           // feedback (obrigatório)
    'cliente_123',                      // ID (obrigatório)
    'João'                              // nome (opcional)
);

// Response:
// {
//   success: true/false,
//   resposta: "Fico feliz em saber que apreciou!"
// }
```

---

### 6️⃣ Info da Conversa
```javascript
const info = servicoIA.obterInfoConversa('cliente_123');

// Response:
// {
//   idCliente: "cliente_123",
//   nomeCliente: "João",
//   primeiraInteracao: false,
//   ultimaAtualizacao: Date,
//   totalMensagens: 5
// }

// Ou null se conversa não existe
```

---

### 7️⃣ Limpar Conversa
```javascript
const resultado = servicoIA.limparConversa('cliente_123');

// Response:
// { success: true }  ou  { success: false, message: "..." }
```

---

## 💡 EXEMPLOS PRONTOS

### Exemplo 1: Integração Simples
```javascript
async function atenderCliente(msg, idCliente, nome) {
    const resultado = await servicoIA.procesarMensagemCliente(
        msg,
        idCliente,
        'duvida',
        { nome }
    );
    
    return resultado.resposta;
}

// Usar
const resposta = await atenderCliente('Oi!', 'cli123', 'João');
console.log(resposta); // Resposta humanizada
```

### Exemplo 2: Com Tratamento de Erro
```javascript
async function atenderComErro(msg, idCliente) {
    try {
        const resultado = await servicoIA.procesarMensagemCliente(
            msg, idCliente, 'duvida'
        );
        
        if (resultado.success) {
            return resultado.resposta;
        } else {
            return 'Um atendente irá ajudá-lo em breve!';
        }
    } catch (erro) {
        console.error(erro);
        return 'Desculpe, houve um erro.';
    }
}
```

### Exemplo 3: Conversa Multi-Turno
```javascript
const idCliente = 'cliente_chat_001';

// Msg 1
let r1 = await servicoIA.procesarMensagemCliente(
    'Oi!', idCliente, 'saudacao', { nome: 'Ana' }
);
console.log(r1.resposta);

// Msg 2 (histórico mantido!)
let r2 = await servicoIA.procesarMensagemCliente(
    'Como funciona?', idCliente, 'duvida'
);
console.log(r2.resposta); // Responde com contexto da msg 1
```

### Exemplo 4: Diagnosticar e Resolver
```javascript
async function diagnosticarProblema(descricao, idCliente) {
    // Fazer pergunta diagnóstica
    const diag = await servicoIA.fazerPerguntaDiagnostica(
        descricao, idCliente
    );
    console.log(diag.pergunta);
    
    // Depois resolver o problema
    const resultado = await servicoIA.processarProblemaComHistorico(
        descricao,
        idCliente,
        [] // Sem tentativas anteriores
    );
    
    return resultado.resposta;
}
```

### Exemplo 5: Fluxo Completo
```javascript
async function fluxoCompleto(msg, idCliente, nome) {
    // Verificar tipo
    let tipo = 'duvida';
    if (msg.includes('problema')) tipo = 'problema';
    if (msg.includes('não funciona')) tipo = 'problema';
    if (msg.includes('obrigado')) tipo = 'feedback';
    
    // Processar
    const resultado = await servicoIA.procesarMensagemCliente(
        msg, idCliente, tipo, { nome }
    );
    
    // Guardar em histórico/BD (opcional)
    // await salvarConversa(idCliente, msg, resultado.resposta);
    
    return resultado.resposta;
}
```

---

## 🔧 CONFIGURAÇÃO

### Arquivo: dados/config-ia-humanizada.json
```json
{
  "iaHumanizada": {
    "configuracoes": {
      "empresa": "Seu Nome",
      "servico": "Chat de Atendimento"
    },
    "mensagensPersonalizadas": {
      "boasVindas": "Olá! Como posso ajudar?",
      "primeira_interacao": "Oi {nome}! Bem-vindo!"
    },
    "limites": {
      "tamanhoMaximoResposta": 4,
      "tempoEsperaDados": 15000
    }
  }
}
```

### Variáveis de Ambiente
```bash
# .env
GEMINI_API_KEY=sua-chave-aqui
NODE_ENV=production
```

### Código
```javascript
// config/configuracoes-principais.js
module.exports = {
    geminiApiKey: process.env.GEMINI_API_KEY,
    servico: 'Chat de Atendimento',
    empresa: 'Seu Negócio'
};
```

---

## 📡 ENDPOINTS REST

Se usando a rota `chat-ia-integracao.js`:

```
POST   /api/chat/mensagem              Processar mensagem
POST   /api/chat/problema              Reportar problema
POST   /api/chat/insatisfacao          Cliente insatisfeito
POST   /api/chat/pergunta-diagnostica  Fazer pergunta
POST   /api/chat/feedback              Enviar feedback
GET    /api/chat/:idCliente/info       Info da conversa
DELETE /api/chat/:idCliente/limpar     Limpar histórico
```

### Exemplos cURL

```bash
# Processar mensagem
curl -X POST http://localhost:3000/api/chat/mensagem \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Oi!","idCliente":"cli123","nomeCliente":"João"}'

# Obter info
curl http://localhost:3000/api/chat/cli123/info

# Limpar histórico
curl -X DELETE http://localhost:3000/api/chat/cli123/limpar
```

---

## 🧪 TESTES

### Rodar Testes
```bash
npm run teste:ia-humanizada
```

### Teste Manual
```javascript
const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');
const servicoIA = new ServicoIAHumanizada();

(async () => {
    const resultado = await servicoIA.procesarMensagemCliente(
        'Oi, tudo bem?',
        'teste_' + Date.now(),
        'saudacao'
    );
    
    console.log(resultado.resposta);
})();
```

---

## ⚡ DICAS RÁPIDAS

| Dica | Código |
|------|--------|
| **Sempre use ID único** | `idCliente: user.id` |
| **Inclua nome quando tiver** | `{ nome: user.name }` |
| **Trate erros** | `if (resultado.success) { ... }` |
| **Mantenha histórico** | Use mesmo `idCliente` |
| **Detecte emoções** | Sistema faz automático |
| **Customize mensagens** | Edite `config-ia-humanizada.json` |
| **Teste antes** | `npm run teste:ia-humanizada` |

---

## 🔍 DEBUGGING

### Log de Erro
```javascript
const resultado = await servicoIA.procesarMensagemCliente(...);

if (!resultado.success) {
    console.log('Erro:', resultado.message);
    console.log('Resposta fallback:', resultado.resposta);
}
```

### Ver Histórico
```javascript
const info = servicoIA.obterInfoConversa('cliente_123');
console.log(`Total de mensagens: ${info.totalMensagens}`);
```

### Limpar Tudo
```javascript
servicoIA.limparConversa('cliente_123');
```

---

## 🚨 ERROS COMUNS

| Erro | Solução |
|------|---------|
| **"API Key não configurada"** | Verifique `config/configuracoes-principais.js` |
| **"Timeout"** | Verifique conexão de internet |
| **"Histórico perdido"** | Use sempre mesmo `idCliente` |
| **"Resposta vazia"** | Verifique se API Key é válida |
| **"Gemini API error"** | Verifique quota da API |

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- `GUIA-IA-HUMANIZADA.md` - Guia completo
- `QUICK-START-IA.md` - Primeiros passos
- `GUIA-INTEGRACAO-IA.md` - Integração específica
- `exemplos-uso-ia-humanizada.js` - 7 exemplos
- `teste-ia-humanizada.js` - Testes

---

## 🎯 FLOW TÍPICO

```
Mensagem do Cliente
    ↓
servicoIA.procesarMensagemCliente()
    ↓
Gera prompt contextualizado
    ↓
Envia para Gemini
    ↓
Recebe resposta
    ↓
Adiciona ao histórico
    ↓
Retorna para sua app
    ↓
Mostra para cliente
```

---

## 💻 CÓDIGO MÍNIMO FUNCIONAL

```javascript
// 1. Importar
const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');

// 2. Criar instância
const servicoIA = new ServicoIAHumanizada();

// 3. Usar
async function main() {
    const resultado = await servicoIA.procesarMensagemCliente(
        'Oi!',
        'cliente_1',
        'duvida',
        { nome: 'João' }
    );
    
    console.log(resultado.resposta);
}

main();
```

**É isso! 3 linhas para começar.** 🎉

---

## 🎓 PRÓXIMAS ETAPAS

1. ✅ Ler este documento
2. ✅ Copiar "Código Mínimo Funcional"
3. ✅ Rodar `npm run teste:ia-humanizada`
4. ✅ Integrar em sua aplicação
5. ✅ Customizar mensagens
6. ✅ Testar com usuários reais

---

**Bookmark este documento para referência rápida!** 🔖
