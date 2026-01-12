# 🔄 Fluxo de Atendimento WhatsApp Integrado com Filas

## 📋 Visão Geral

O sistema agora integra completamente o WhatsApp com o gerenciador de filas, seguindo um fluxo estruturado de 3 etapas:

```
WhatsApp → AUTOMAÇÃO → ESPERA → ATENDIMENTO
```

## 🎯 Estados das Conversas

### 1. 🤖 AUTOMAÇÃO (Inicial)
- **Quando:** Cliente envia primeira mensagem
- **O que acontece:**
  - Conversa criada automaticamente
  - Chatbot responde baseado em palavras-chave
  - Sistema conta tentativas do bot (máximo 3)
  
### 2. ⏳ ESPERA (Aguardando Atendente)
- **Quando:** 
  - Bot não sabe responder
  - Cliente solicita atendimento humano
  - Máximo de 3 tentativas do bot atingido
- **O que acontece:**
  - Mensagem automática: "Aguarde um momento, vou encaminhar você para um atendente. 😊"
  - Notificação enviada para todos atendentes
  - Conversa aguarda atribuição manual

### 3. 👤 ATENDIMENTO (Com Atendente)
- **Quando:** Atendente assume/atribui conversa
- **O que acontece:**
  - Bot para de responder
  - Apenas salva mensagens
  - Atendente responde manualmente via interface

---

## 🔧 Fluxo Detalhado

### Mensagem Recebida do WhatsApp

```javascript
1. Mensagem chega → Salva no histórico
2. Busca conversa nas filas
3. Se não existe → Cria em AUTOMAÇÃO
4. Atualiza última mensagem
5. Processa conforme estado atual
```

### Estado: AUTOMAÇÃO

```javascript
if (estado === 'automacao') {
    // Tenta responder com chatbot
    const resultado = roteamentoAutomatizado(mensagem);
    
    if (resultado.devResponder) {
        // Envia resposta do bot
        enviarMensagem(resultado.resposta);
        
        // Incrementa contador
        tentativas++;
        
        // Verifica se deve escalar
        if (resultado.escalar || tentativas >= 3) {
            moverParaEspera();
            notificarAtendentes();
        }
    } else {
        // Bot não sabe responder
        moverParaEspera();
        enviarMensagem("Aguarde, vou encaminhar para atendente 😊");
        notificarAtendentes();
    }
}
```

### Estado: ESPERA

```javascript
if (estado === 'espera') {
    // Apenas aguarda atendente
    // Salva mensagem
    // Notifica atualização na fila
}
```

### Estado: ATENDIMENTO

```javascript
if (estado === 'atendimento') {
    // Bot não responde
    // Salva mensagem
    // Notifica o atendente específico
}
```

---

## 📊 Regras do Chatbot

### Palavras-Chave Padrão

| Categoria | Palavras | Resposta |
|-----------|----------|----------|
| **Saudação** | oi, olá, bom dia, boa tarde | "Olá! Como posso ajudá-lo hoje?" |
| **Preços** | preço, valor, quanto custa | "Aguarde que um atendente irá responder" |
| **Horário** | horário, funcionamento | "Horário: Segunda a Sexta, 8h às 18h" |
| **Agradecimento** | obrigado, valeu | "Por nada! Estamos à disposição! 😊" |

### Horário de Atendimento

```json
{
  "inicio": "08:00",
  "fim": "22:00",
  "diasSemana": [2, 3, 4, 5]
}
```

**Fora do horário:** "No momento estamos fora do horário de atendimento. Retornaremos em breve!"

---

## 🎮 Operações do Atendente

### Assumir Conversa
```javascript
// Na interface chat-filas.html
assumirConversa(chatId, atendente);
// → Move de ESPERA para ATENDIMENTO
```

### Transferir Conversa
```javascript
transferirConversa(chatId, atendenteOrigem, atendenteDestino);
// → Mantém em ATENDIMENTO, troca atendente
```

### Encerrar Conversa
```javascript
encerrarConversa(chatId, atendente);
// → Move para ENCERRADO
```

---

## 🔔 Notificações

### Para Atendentes

**Nova conversa em espera:**
```javascript
{
  event: 'nova-conversa-aguardando',
  data: { chatId, clientId, nomeContato, ultimaMensagem }
}
```

**Atualização em espera:**
```javascript
{
  event: 'atualizacao-fila-espera',
  data: { chatId, ultimaMensagem }
}
```

**Nova mensagem em atendimento:**
```javascript
{
  event: 'nova-mensagem-atendimento',
  data: { chatId, clientId, atendenteAtribuido, mensagem }
}
```

---

## 📁 Arquivos de Configuração

### chatbot-rules.json
```json
{
  "ativo": true,
  "horarioAtendimento": { ... },
  "mensagemBoasVindas": "...",
  "palavrasChave": [ ... ]
}
```

### filas-atendimento.json
```json
{
  "conversas": [
    {
      "id": "uuid",
      "clientId": "whatsapp-1",
      "chatId": "5511999999999@c.us",
      "estado": "automacao|espera|atendimento|encerrado",
      "atendente": null,
      "tentativasBot": 0,
      "metadata": {
        "nomeContato": "João Silva",
        "ultimaMensagem": "..."
      }
    }
  ]
}
```

---

## ✅ Melhorias Implementadas

1. **Remoção do Gemini IA:** Sistema não usa mais IA para responder automaticamente
2. **Integração com Filas:** Todas mensagens agora passam pelo gerenciador de filas
3. **Limite de Tentativas:** Bot responde no máximo 3 vezes antes de escalar
4. **Notificações Estruturadas:** Eventos específicos para cada tipo de atualização
5. **Mensagens Contextualizadas:** Respostas diferentes para cada estado

---

## 🚀 Como Testar

1. **Envie mensagem via WhatsApp:**
   - Sistema cria conversa em AUTOMAÇÃO
   - Bot responde com palavras-chave configuradas

2. **Envie algo que o bot não sabe:**
   - Sistema move para ESPERA
   - Envia mensagem de aguardo
   - Notifica atendentes

3. **Atendente assume conversa:**
   - Na interface, clique em "Assumir"
   - Conversa move para ATENDIMENTO
   - Bot para de responder

4. **Atendente responde manualmente:**
   - Mensagens enviadas pela interface
   - Cliente recebe no WhatsApp

---

## 🔍 Logs de Debug

### Ver fluxo em tempo real:
```
[whatsapp-1] Nova mensagem de 5511999999999@c.us: Olá
[whatsapp-1] Nova conversa criada na fila AUTOMAÇÃO: 5511999999999@c.us
[whatsapp-1] Chatbot respondeu: Olá! Como posso ajudá-lo hoje?
[whatsapp-1] Conversa 5511999999999@c.us movida para ESPERA (tentativas: 3)
```

---

## 📞 Suporte

Para configurar palavras-chave customizadas ou ajustar horários de atendimento, edite:
- `dados/chatbot-rules.json` - Regras do chatbot
- `dados/provedor-config.json` - Configurações específicas de provedor de internet

