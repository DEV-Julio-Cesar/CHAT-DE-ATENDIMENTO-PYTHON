# ⚡ Guia Rápido - Gerenciador de Comandos

## 🎯 O Que É?

Uma interface web onde você **escreve e gerencia** as respostas que seu robô dará aos clientes, sem precisar mexer em código!

## 🚀 Como Usar em 3 Passos

### 1️⃣ **Acesse a Interface**
```
http://localhost:3333/gerenciador-comandos.html
```

### 2️⃣ **Crie seu Primeiro Comando**
- **ID**: `oi` (identificador único)
- **Tipo**: `Saudação`
- **Resposta**: `Olá! 👋 Como posso ajudar você?`
- **Palavras-chave**: `oi`, `olá`, `opa`, `e aí`
- **Prioridade**: `10` (máximo = mais importante)
- **Ativo**: ✓ Marcado

### 3️⃣ **Clique em "Salvar Comando"**

## ✨ Exemplos Prontos

### Exemplo 1: Saudação
```
ID: saudacao
Tipo: Saudação
Resposta: Oi! 👋 Bem-vindo! Como posso ajudar?
Palavras: oi, olá, opa, e aí
Prioridade: 10
```

### Exemplo 2: Horário
```
ID: horario
Tipo: Informação
Resposta: 📅 Abrimos de seg-sex 9h-18h, sábado 10h-14h
Palavras: horário, funcionamento, aberto, open
Prioridade: 8
```

### Exemplo 3: Preço
```
ID: preco
Tipo: Informação
Resposta: 💰 Começamos em R$ 99/mês. Quer um catálogo?
Palavras: preço, valor, quanto custa, caro
Prioridade: 7
```

## 🎮 Funcionalidades Principais

| Ação | Como Fazer |
|------|-----------|
| ✅ **Criar** | Preencha o formulário → Clique "Salvar" |
| ✏️ **Editar** | Clique no comando → Altere → Clique "Atualizar" |
| 🗑️ **Deletar** | Clique no comando → Clique "Deletar" → Confirme |
| 🔍 **Buscar** | Digite na barra de busca |
| 📊 **Ver Stats** | Veja total/ativos/inativos no topo |

## 🔧 Configurações Importantes

Na aba **"⚙️ Configurações"**:

```
✓ Usar Base de Conhecimento     (sempre ativo!)
✓ Usar Gemini AI                (fallback inteligente)
✓ Fallback para IA              (se comando não encontrar)
  Confiança Mínima: 70%          (reconhecimento rigoroso)
  Tempo de Resposta: 15s         (máximo de espera)
  Resposta Padrão: "Desculpe..." (se nada funcionar)
```

## 💾 Backup

### Exportar (Segurança)
1. Clique em "📥 Importar/Exportar"
2. Clique "📋 Copiar"
3. Cole num arquivo `.json` para backup

### Importar (Restaurar)
1. Cole um `.json` no campo
2. Clique "📥 Importar"

## 🧪 Como o Sistema Funciona

```
Cliente: "Oi, tudo bem?"
         ↓
Sistema: Procura comando com palavra "oi"
         ↓
         ✅ Encontrou! Score: 90%
         ↓
Robô: "Olá! 👋 Como posso ajudar você?"
```

Se não encontrar com confiança ≥70%, cai para **Gemini AI** (inteligência).

## 📋 Checklist ao Criar Comando

- [ ] ID é único (sem espaços, sem maiúsculas)
- [ ] Tipo selecionado
- [ ] Resposta clara e completa
- [ ] Mínimo 2-3 palavras-chave
- [ ] Prioridade definida (1-10)
- [ ] Marcado como "Ativo"
- [ ] Testado (via interface ou API)

## 🚨 Dúvidas Frequentes

**P: Quantos comandos posso criar?**  
R: Ilimitado! Quanto mais, melhor a experiência.

**P: O que é "Confiança Mínima"?**  
R: Se você colocar 70%, o comando só é usado se houver 70%+ de correspondência com as palavras-chave.

**P: Posso usar emojis?**  
R: Sim! Recomendamos para tornar mais amigável.

**P: Como atualizar sem perder dados?**  
R: Sempre exporte/backup antes de grandes mudanças!

**P: Qual prioridade usar?**  
R: 10 = urgente, 5 = normal, 1 = raro. Use números maiores para o que é mais importante.

## 🎯 Estratégia Recomendada

1. **Semana 1**: Crie 10-15 comandos básicos
2. **Semana 2**: Teste com clientes, refine palavras-chave
3. **Semana 3+**: Adicione mais conforme feedback

## 📞 Precisa de Mais?

- Documentação completa: [GERENCIADOR-COMANDOS.md](./GERENCIADOR-COMANDOS.md)
- Endpoints API: Mesmo arquivo
- Logs de erro: `dados/logs/`

---

🎉 **Pronto para começar? Acesse http://localhost:3333/gerenciador-comandos.html**
