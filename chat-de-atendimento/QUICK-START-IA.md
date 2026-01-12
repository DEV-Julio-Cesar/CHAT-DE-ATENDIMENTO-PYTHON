# 🤖 Sistema de IA Humanizada - Quick Start

## O que foi criado?

Um sistema completo de **chatbot humanizado** que gera respostas automáticas genuínas e acolhedoras usando Google Gemini.

## 📦 Arquivos Criados

```
src/aplicacao/
├── gerador-prompts-ia.js           # Gerador inteligente de prompts
├── servico-ia-humanizada.js        # Serviço principal (USE ESTE!)
└── exemplos-uso-ia-humanizada.js   # Exemplos práticos

dados/
└── config-ia-humanizada.json       # Configurações personalizáveis

GUIA-IA-HUMANIZADA.md               # Documentação completa
teste-ia-humanizada.js              # Testes automatizados
QUICK-START-IA.md                   # Este arquivo
```

## ⚡ 30 Segundos de Código

```javascript
const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');
const servicoIA = new ServicoIAHumanizada();

// Responder cliente
const resultado = await servicoIA.procesarMensagemCliente(
    'Oi, como funciona?',
    'cliente_123',
    'duvida',
    { nome: 'João' }
);

console.log(resultado.resposta); // Resposta humanizada!
```

## 🚀 Primeiros Passos

### 1. **Rodar os Testes**
```bash
npm run teste:ia-humanizada
```

### 2. **Configurar API Key (IMPORTANTE!)**

Adicione sua chave Gemini em `config/configuracoes-principais.js`:

```javascript
module.exports = {
    // ... outras configs
    geminiApiKey: 'SUA-CHAVE-AQUI' // ou use variável de ambiente
};
```

Ou via variável de ambiente:
```bash
set GEMINI_API_KEY=sua-chave-aqui
```

### 3. **Usar em sua Aplicação**

**Em arquivo Express/API:**
```javascript
const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');

const servicoIA = new ServicoIAHumanizada({
    servico: 'Chat de Atendimento WhatsApp',
    empresa: 'Seu Negócio'
});

// Em sua rota
app.post('/api/chat', async (req, res) => {
    const { mensagem, idCliente, nomeCliente } = req.body;
    
    const resultado = await servicoIA.procesarMensagemCliente(
        mensagem,
        idCliente,
        'duvida',
        { nome: nomeCliente }
    );
    
    res.json({ resposta: resultado.resposta });
});
```

**Com WhatsApp:**
```javascript
client.on('message', async (msg) => {
    const resultado = await servicoIA.procesarMensagemCliente(
        msg.body,
        msg.from.split('@')[0],
        'duvida',
        { nome: 'Cliente' }
    );
    
    msg.reply(resultado.resposta);
});
```

## 🎯 Casos de Uso

### 1️⃣ Mensagem Comum
```javascript
await servicoIA.procesarMensagemCliente(
    'Oi!',
    'cliente_123',
    'duvida',  // ← tipo: duvida
    { nome: 'João' }
);
// Resposta humanizada e contextualizada
```

### 2️⃣ Problema Técnico
```javascript
await servicoIA.processarProblemaComHistorico(
    'Não consigo fazer login',
    'cliente_456',
    ['Reiniciar', 'Limpar cache']  // ← tentativas anteriores
);
// Não repete soluções anteriores, oferece novas
```

### 3️⃣ Cliente Frustrado
```javascript
await servicoIA.processarClienteInsatisfeito(
    'Estou muito frustrado!',
    'cliente_789',
    'Contexto do problema...'
);
// Reconhece frustração, pede desculpas, oferece ação
```

### 4️⃣ Fazer Diagnóstico
```javascript
const { pergunta } = await servicoIA.fazerPerguntaDiagnostica(
    'Meu sistema está lento',
    'cliente_555'
);
// Uma pergunta bem pensada para entender melhor
```

### 5️⃣ Responder Elogio
```javascript
await servicoIA.responderFeedbackPositivo(
    'Vocês foram incríveis!',
    'cliente_abc',
    'Ana'
);
// Resposta genuina e grata
```

## 🧪 Testar Sem Integração

```bash
# Roda testes automáticos de todos os recursos
npm run teste:ia-humanizada
```

Isso vai testar:
- ✅ Primeira interação
- ✅ Dúvida comum
- ✅ Conversa multi-turno
- ✅ Problema técnico
- ✅ Cliente frustrado
- ✅ Pergunta diagnóstica
- ✅ Feedback positivo
- ✅ Detecção de emoções
- ✅ Histórico
- ✅ Tratamento de erros

## 🎨 Personalizarização

Edite `dados/config-ia-humanizada.json` para customizar:

```json
{
  "iaHumanizada": {
    "configuracoes": {
      "empresa": "Seu Nome",
      "servico": "Seu Serviço"
    },
    "mensagensPersonalizadas": {
      "boasVindas": "Olá! Como posso ajudá-lo?",
      "primeira_interacao": "Oi {nome}! ...",
      "problema_detectado": "..."
    }
  }
}
```

## 📊 Características Principais

| Feature | Descrição |
|---------|-----------|
| **Humanização** | Respostas naturais, não robóticas |
| **Contextual** | Mantém histórico da conversa |
| **Emocional** | Detecta frustração, urgência, confusão |
| **Adaptável** | Diferentes tons (amigável, profissional, etc) |
| **Robusto** | Trata erros com fallbacks humanizados |
| **Rápido** | Respostas em segundos |
| **Rastreável** | Logs de todas as interações |

## 🔧 Métodos Disponíveis

```javascript
// Processar mensagem normal
servicoIA.procesarMensagemCliente(msg, idCliente, tipo, info)

// Resolver problema com histórico
servicoIA.processarProblemaComHistorico(desc, idCliente, tentativas)

// Cliente insatisfeito
servicoIA.processarClienteInsatisfeito(motivo, idCliente, historico)

// Pergunta diagnóstica
servicoIA.fazerPerguntaDiagnostica(situacao, idCliente)

// Responder feedback
servicoIA.responderFeedbackPositivo(feedback, idCliente, nome)

// Obter info da conversa
servicoIA.obterInfoConversa(idCliente)

// Limpar histórico
servicoIA.limparConversa(idCliente)
```

## 🆘 Troubleshooting

### "Erro: Gemini API Key não configurada"
```javascript
// Adicione em config/configuracoes-principais.js
geminiApiKey: 'sua-chave-aqui'
```

### "Teste falha"
- Verifique se a API Key está correta
- Confirme que tem internet
- Veja logs em `dados/logs/`

### "Histórico não mantém contexto"
- Use sempre o MESMO `idCliente` para mesmo cliente
- Sistema mantém últimas 10 mensagens automaticamente

## 📚 Documentação Completa

Para mais detalhes, veja:
- `GUIA-IA-HUMANIZADA.md` - Guia extenso com exemplos
- `src/aplicacao/exemplos-uso-ia-humanizada.js` - Código exemplo
- `teste-ia-humanizada.js` - Testes com exemplos reais

## 💡 Dicas

1. **Sempre use ID único do cliente** - Permite manter contexto
2. **Inclua o nome** - Aumenta humanização (use {nome} em prompts)
3. **Escolha o tipo correto** - Sistema adapta melhor
4. **Tenha fallback** - Se API falhar, tenha resposta humanizada
5. **Monitore logs** - Veja em `dados/logs/`

## 🎉 Você Agora Tem...

✅ Sistema de IA humanizada completo
✅ Respostas automáticas genuínas
✅ Detecção de emoções
✅ Manutenção de histórico
✅ Documentação completa
✅ Testes automáticos
✅ Exemplos de integração

---

**Próxima etapa:** Integre em suas rotas e teste com clientes reais!

Para integração em WhatsApp, Express, ou outras plataformas, veja `GUIA-IA-HUMANIZADA.md`.

---

Dúvidas? Veja os exemplos em `exemplos-uso-ia-humanizada.js` ou rode `npm run teste:ia-humanizada`
