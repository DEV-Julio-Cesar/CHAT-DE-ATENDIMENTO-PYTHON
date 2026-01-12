# 🎯 Sistema de Filas de Atendimento

## 📋 Visão Geral

Sistema profissional de gerenciamento de atendimento com **3 filas automáticas**:

1. **🤖 Automação** - Bot responde automaticamente
2. **⏳ Em Espera** - Aguardando atendente humano
3. **👤 Meu Atendimento** - Conversas que você está atendendo

---

## 🔄 Fluxo de Atendimento

```
┌─────────────┐
│   CLIENTE   │
│   ENVIA     │
│  MENSAGEM   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│  1️⃣  AUTOMAÇÃO              │
│  • Bot responde             │
│  • Até 3 tentativas         │
│  • Se resolver: ENCERRA     │
│  • Se não resolver: ↓       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  2️⃣  EM ESPERA              │
│  • Fila de aguardo          │
│  • Todos atendentes veem    │
│  • Botão "Assumir"          │
│  • Atendente clica: ↓       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  3️⃣  ATENDIMENTO            │
│  • Atribuído a 1 atendente  │
│  • Apenas ele vê            │
│  • Botão "Encerrar"         │
│  • Finaliza atendimento     │
└─────────────────────────────┘
```

---

## 🎯 Características das Abas

### 🤖 **Aba AUTOMAÇÃO**

**Quem vê:** Todos os atendentes

**O que mostra:**
- Conversas sendo respondidas pelo bot
- Contador de tentativas do bot (máx 3)
- Status: "Bot" em azul

**Ações disponíveis:**
- ✏️ Visualizar conversa
- 🔼 Escalar para humano (move para Espera)

**Transições:**
- ✅ Bot resolve → ENCERRADO
- ❌ Bot não resolve (3 tentativas) → EM ESPERA
- 👤 Usuário solicita humano → EM ESPERA

---

### ⏳ **Aba EM ESPERA**

**Quem vê:** Todos os atendentes

**O que mostra:**
- Conversas aguardando atendente
- Tempo de espera
- Botão "✓ Assumir" em cada conversa
- Status: "Aguardando" em laranja

**Ações disponíveis:**
- ✓ Assumir conversa (move para Atendimento)
- 👁️ Visualizar histórico

**Regras:**
- Primeiro atendente que clicar em "Assumir" pega a conversa
- Outros atendentes não podem assumir conversa já atribuída

---

### 👤 **Aba MEU ATENDIMENTO**

**Quem vê:** Apenas o atendente que assumiu

**O que mostra:**
- Apenas conversas atribuídas a você
- Status: "Em Atendimento" em verde
- Mensagens em tempo real

**Ações disponíveis:**
- 💬 Responder mensagens
- ✅ Encerrar atendimento

**Privacidade:**
- Outros atendentes **NÃO veem** suas conversas
- Você **NÃO vê** conversas de outros atendentes

---

## 📊 Estados da Conversa

| Estado | Cor | Ícone | Descrição |
|--------|-----|-------|-----------|
| **Automação** | 🔵 Azul | 🤖 | Bot está respondendo |
| **Espera** | 🟠 Laranja | ⏳ | Aguardando atendente |
| **Atendimento** | 🟢 Verde | 👤 | Atendente humano conversando |
| **Encerrado** | ⚫ Cinza | ✓ | Finalizado |

---

## 🚀 Como Usar

### **Para Atendentes:**

#### 1. Abrir Chat com Filas
```
Dashboard → Botão "Chat com Filas" (verde)
```

#### 2. Monitorar Aba "Em Espera"
- Veja conversas aguardando
- Badge mostra quantas estão esperando

#### 3. Assumir Conversa
```
Aba "Em Espera" → Clique "✓ Assumir" na conversa
```

#### 4. Atender Cliente
```
Aba "Meu Atendimento" → Responda as mensagens
```

#### 5. Encerrar Atendimento
```
Botão "Encerrar" no topo → Confirmação
```

---

### **Para Clientes:**

1. Cliente envia mensagem via WhatsApp
2. Bot responde automaticamente (Automação)
3. Se bot não resolver:
   - Conversa vai para fila de Espera
   - Atendente assume
   - Conversa humana inicia

---

## 🎨 Interface

### **Badges de Contador**

Cada aba mostra quantas conversas tem:

```
🤖 Automação (5)  ⏳ Em Espera (12)  👤 Meus Atendimentos (3)
```

### **Informações de Cada Conversa**

```
┌─────────────────────────────────┐
│ João Silva          5min  [Bot] │
│ Preciso de ajuda com...         │
│               [✓ Assumir]       │
└─────────────────────────────────┘
```

### **Área de Chat**

```
╔═════════════════════════════════╗
║ João Silva                      ║
║ Estado: Em Atendimento • 1 tent║
║                  [Encerrar]     ║
╠═════════════════════════════════╣
║                                 ║
║  [Mensagens aqui]               ║
║                                 ║
╠═════════════════════════════════╣
║ [Digite mensagem...] [Enviar]  ║
╚═════════════════════════════════╝
```

---

## ⚙️ Configurações do Sistema

### **Limites Automáticos**

| Configuração | Valor | Descrição |
|--------------|-------|-----------|
| Tentativas do Bot | 3 | Após 3 tentativas sem resolver, vai para Espera |
| Auto-refresh | 30s | Filas atualizam automaticamente a cada 30s |

### **Transições Automáticas**

1. **Bot → Espera** (automático após 3 tentativas)
2. **Espera → Atendimento** (manual - atendente assume)
3. **Atendimento → Encerrado** (manual - atendente encerra)
4. **Automação → Encerrado** (automático - bot resolveu)

---

## 📈 Métricas Disponíveis

O sistema rastreia:
- ✅ Total de conversas ativas
- 🤖 Conversas em automação
- ⏳ Conversas em espera
- 👤 Conversas em atendimento
- ⏱️ Tempo médio de espera
- 📊 Taxa de resolução do bot
- 👥 Atendimentos por atendente

---

## 🔒 Privacidade e Segurança

### **Isolamento de Atendimentos**
- ✅ Cada atendente vê **APENAS** seus atendimentos
- ✅ Histórico é privado por atendente
- ✅ Impossível assumir conversa já atribuída

### **Auditoria**
Todo o histórico é registrado:
- Quando conversa entrou em cada estado
- Quem assumiu
- Quando encerrou
- Motivo da transição

---

## 🛠️ Arquivos Criados

### **Código Backend**
```
src/aplicacao/gerenciador-filas.js
└─ Gerencia estados, transições, regras de negócio
```

### **Código Frontend**
```
src/interfaces/chat-filas.html
└─ Interface com 3 abas completa
```

### **Dados**
```
dados/filas-atendimento.json
└─ Armazena todas as conversas e estados
```

### **Configuração**
```
src/services/GerenciadorJanelas.js
└─ Rota 'chat-filas' adicionada
```

---

## 🎯 Casos de Uso

### **Caso 1: Cliente com Dúvida Simples**
```
1. Cliente: "Qual o horário?"
2. Bot responde: "9h-18h"
3. Cliente satisfeito
4. Status: ENCERRADO (bot resolveu)
```

### **Caso 2: Cliente com Problema Complexo**
```
1. Cliente: "Meu boleto não foi gerado"
2. Bot tenta 3x, não resolve
3. Movido para ESPERA automaticamente
4. Atendente assume
5. Atendente resolve e encerra
```

### **Caso 3: Cliente Solicita Humano**
```
1. Cliente: "Falar com atendente"
2. Bot detecta intenção
3. Clique em "Escalar para Humano"
4. Movido para ESPERA
5. Próximo atendente disponível assume
```

---

## 📞 Atalhos e Dicas

### **Atalhos de Teclado**
- `Enter` - Enviar mensagem
- `Ctrl+R` - Atualizar filas
- `Esc` - Fechar modal de confirmação

### **Dicas de Produtividade**
1. Mantenha aba "Em Espera" sempre visível
2. Use badges para priorizar
3. Encerre conversas resolvidas imediatamente
4. Bot tentou 3x? Cliente precisa de atenção especial

---

## 🚨 Troubleshooting

### "Não consigo assumir conversa"
- ✅ Verifique se outro atendente não assumiu primeiro
- ✅ Confirme que está na aba "Em Espera"

### "Minhas conversas não aparecem"
- ✅ Verifique se está na aba "Meu Atendimento"
- ✅ Clique em 🔄 para atualizar

### "Bot não está funcionando"
- ✅ Verifique configuração do chatbot
- ✅ Confirme que Base de Conhecimento está ativa

---

## 🎉 Pronto para Usar!

Acesse:
```
Dashboard → "Chat com Filas" (botão verde com borda)
```

Comece a atender clientes de forma profissional e organizada! 🚀

---

**Implementado em:** 11/01/2026  
**Status:** ✅ Pronto para Produção  
**Versão:** 1.0.0
