# Guia de Uso: Sistema de IA Humanizada

Um sistema completo de chatbot com respostas humanizadas e receptivas baseado em prompts inteligentes com Google Gemini.

## 📋 Visão Geral

Este sistema foi desenvolvido para tornar seu atendimento automático genuinamente humanizado. As respostas:
- São naturais e empáticas
- Adaptam-se ao contexto e sentimento do cliente
- Mantêm histórico de conversa para contexto
- Usam linguagem acessível e acolhedora

## 🚀 Como Começar

### 1. Instalação

Já está integrado ao seu projeto. Os arquivos criados são:

```
src/aplicacao/
├── gerador-prompts-ia.js          # Gerador de prompts contextualizados
├── servico-ia-humanizada.js       # Serviço principal (use este!)
└── exemplos-uso-ia-humanizada.js  # Exemplos de implementação
```

### 2. Importação Básica

```javascript
const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');

// Criar instância do serviço
const servicoIA = new ServicoIAHumanizada({
    servico: 'Chat de Atendimento WhatsApp',
    empresa: 'Sua Empresa'
});
```

## 💡 Casos de Uso

### Caso 1: Processar Mensagem de Cliente (Mais Comum)

```javascript
const resultado = await servicoIA.procesarMensagemCliente(
    'Oi! Como funciona o serviço de vocês?',  // Mensagem do cliente
    'cliente_123',                             // ID único do cliente
    'duvida',                                  // Tipo: 'duvida', 'problema', 'saudacao', etc
    { nome: 'João Silva' }                     // Info do cliente (opcional)
);

console.log(resultado.resposta); // Resposta humanizada
```

**Tipos de Solicitação Suportados:**
- `saudacao` - Primeiro contato
- `duvida` - Pergunta sobre funcionamento
- `problema` - Problema técnico
- `feedback` - Feedback/sugestão
- `oferta` - Sugerir serviço
- `reclamacao` - Cliente insatisfeito
- `sugestao` - Sugestão de melhoria

---

### Caso 2: Problema Técnico com Histórico de Tentativas

```javascript
const resultado = await servicoIA.processarProblemaComHistorico(
    'Não consigo acessar minha conta. Recebo erro 403',
    'cliente_789',
    [
        'Reiniciar o navegador',      // Tentativas anteriores
        'Limpar cache',
        'Tentar em outro navegador'
    ]
);
```

A IA vai:
- Reconhecer que tentativas anteriores falharam
- NÃO sugerir as mesmas soluções
- Oferecer novas abordagens

---

### Caso 3: Cliente Insatisfeito/Frustrado

```javascript
const resultado = await servicoIA.processarClienteInsatisfeito(
    'Estou muito frustrado! Fiz o pagamento ontem e até agora nada!',
    'cliente_001',
    'Cliente pagou e ainda não recebeu o serviço. Primeira reclamação dele.'
);
```

A IA vai:
- Reconhecer o sentimento
- Pedir desculpas sinceras
- Validar a frustração
- Oferecer ação concreta

---

### Caso 4: Fazer uma Pergunta Diagnóstica

```javascript
const resultado = await servicoIA.fazerPerguntaDiagnostica(
    'Meu sistema está lento',
    'cliente_555'
);

console.log(resultado.pergunta); // Uma pergunta bem pensada
```

Útil para entender melhor o problema antes de oferecer solução.

---

### Caso 5: Responder Feedback Positivo

```javascript
const resultado = await servicoIA.responderFeedbackPositivo(
    'Vocês foram incríveis! Resolveram meu problema em minutos!',
    'cliente_abc',
    'Ana'
);
```

---

### Caso 6: Conversa Multi-Turno (Múltiplas Mensagens)

O sistema mantém histórico automaticamente:

```javascript
const idCliente = 'cliente_multi_999';

// 1ª mensagem
let r1 = await servicoIA.procesarMensagemCliente(
    'Oi, preciso de ajuda com um pedido',
    idCliente,
    'duvida',
    { nome: 'Pedro' }
);
console.log(r1.resposta);

// 2ª mensagem (histórico é mantido automaticamente!)
let r2 = await servicoIA.procesarMensagemCliente(
    'É, fiz um pedido semana passada e ainda não chegou',
    idCliente,
    'problema'
);
console.log(r2.resposta); // Responde considerando a 1ª mensagem
```

## 🔌 Integração com Express

```javascript
const express = require('express');
const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');

const app = express();
const servicoIA = new ServicoIAHumanizada();

// Middleware
app.use(express.json());

/**
 * POST /api/chat
 * Body: { mensagem, idCliente, nomeCliente, tipoSolicitacao }
 */
app.post('/api/chat', async (req, res) => {
    const { mensagem, idCliente, nomeCliente, tipoSolicitacao = 'duvida' } = req.body;
    
    const resultado = await servicoIA.procesarMensagemCliente(
        mensagem,
        idCliente,
        tipoSolicitacao,
        { nome: nomeCliente }
    );
    
    res.json({
        success: resultado.success,
        resposta: resultado.resposta,
        tipo: resultado.tipo
    });
});

/**
 * GET /api/chat/:idCliente/info
 * Obter informações da conversa
 */
app.get('/api/chat/:idCliente/info', (req, res) => {
    const info = servicoIA.obterInfoConversa(req.params.idCliente);
    res.json(info);
});

/**
 * DELETE /api/chat/:idCliente/limpar
 * Limpar histórico da conversa
 */
app.delete('/api/chat/:idCliente/limpar', (req, res) => {
    const resultado = servicoIA.limparConversa(req.params.idCliente);
    res.json(resultado);
});

app.listen(3000);
```

## 🎯 Perfis de Resposta

O sistema adapta o tom automaticamente:

| Tipo | Tom | Características |
|------|-----|-----------------|
| **Atencioso** | Cuidadoso e empático | "Ouço você", "Entendo sua situação" |
| **Profissional** | Claro e direto | Informação estruturada, exemplos práticos |
| **Amigável** | Descontraído | Linguagem coloquial, perguntas abertas |
| **Solução** | Orientado para resolver | Diagnosticar → Oferecer opções → Próximos passos |

## 🧠 Detecção de Emoção

O sistema detecta automaticamente:
- **Frustrado**: Palavras como "não funciona", "erro", "😠"
- **Urgente**: "urgente", "rápido", "já", "!!!!"
- **Confuso**: "não entendi", "como funciona?"
- **Feliz**: "legal", "adorei", "😊", "obrigado"
- **Neutro**: Outras mensagens

E adapta a resposta conforme a emoção detectada.

## 📚 Exemplos Completos

Veja o arquivo `src/aplicacao/exemplos-uso-ia-humanizada.js` para:
- `exemplo_MensagemComum()` - Pergunta simples
- `exemplo_PrimeiraInteracao()` - Novo cliente
- `exemplo_ProblemaComHistorico()` - Problema técnico
- `exemplo_ClienteInsatisfeito()` - Cliente frustrado
- `exemplo_PerguntaDiagnostica()` - Fazer diagnóstico
- `exemplo_FeedbackPositivo()` - Responder elogio
- `exemplo_ConversaMultiTurno()` - Conversa completa

## ⚙️ Configuração Avançada

### Customizar Perfis

```javascript
const gerador = new GeradorPromptsIA({
    servico: 'Seu Serviço',
    horarioComercial: '09:00-18:00'
});

// Criar prompt customizado
const prompt = gerador.criarPromptBase('Cliente', 'duvida', {
    historico: 'Cliente já tentou X',
    problema: 'Descrição do problema'
});
```

### Gerenciar Histórico

```javascript
// Obter info da conversa
const info = servicoIA.obterInfoConversa('cliente_123');
// { idCliente, nomeCliente, primeiraInteracao, ultimaAtualizacao, totalMensagens }

// Limpar histórico
servicoIA.limparConversa('cliente_123');
```

## 🔒 Boas Práticas

1. **Sempre use ID único do cliente** para manter contexto
2. **Inclua o nome** quando disponível (aumenta humanização)
3. **Escolha o tipo de solicitação correto** para melhor adaptação
4. **Limite histórico** - Sistema mantém últimas 10 mensagens automaticamente
5. **Trate erros** - Sempre tenha resposta fallback

```javascript
const resultado = await servicoIA.procesarMensagemCliente(...);

if (resultado.success) {
    enviarAoCliente(resultado.resposta);
} else {
    // Fallback humanizado
    enviarAoCliente('Um atendente irá ajudá-lo em breve!');
}
```

## 🚨 Troubleshooting

### "Gemini API Key não configurada"
Verifique seu arquivo de configuração:
```javascript
// config/configuracoes-principais.js
module.exports = {
    geminiApiKey: process.env.GEMINI_API_KEY
    // ou
    // geminiApiKey: 'sua-chave-aqui'
};
```

### Respostas muito curtas
O sistema limita a 2-4 parágrafos por design (para mobile). Ajuste em `servico-ia-humanizada.js`.

### Histórico não mantém contexto
Certifique-se de usar o MESMO `idCliente` em todas as mensagens do mesmo cliente.

## 📊 Métricas e Monitoramento

```javascript
// Verificar saúde de uma conversa
const info = servicoIA.obterInfoConversa('cliente_123');
console.log(`Cliente: ${info.nomeCliente}`);
console.log(`Total de mensagens: ${info.totalMensagens}`);
console.log(`Última atualização: ${info.ultimaAtualizacao}`);
```

## 🎓 Dicas de Implementação

### Para WhatsApp
```javascript
// No seu handler de mensagens WhatsApp
client.on('message', async (msg) => {
    const resultado = await servicoIA.procesarMensagemCliente(
        msg.body,
        msg.from.split('@')[0],    // ID do cliente
        detectarTipoMensagem(msg),
        { nome: msg.from }
    );
    
    msg.reply(resultado.resposta);
});
```

### Para Web Chat
```javascript
// No seu endpoint de chat
router.post('/chat', async (req, res) => {
    const { userId, message, userType } = req.body;
    
    const resultado = await servicoIA.procesarMensagemCliente(
        message,
        userId,
        userType,
        { nome: req.session.userName }
    );
    
    res.json({ resposta: resultado.resposta });
});
```

## 📞 Suporte

Para questões sobre implementação, verifique:
1. `exemplos-uso-ia-humanizada.js` - Exemplos práticos
2. `gerador-prompts-ia.js` - Documentação de prompts
3. `servico-ia-humanizada.js` - Métodos disponíveis

---

**Seu atendimento agora é verdadeiramente humanizado! 🎉**
