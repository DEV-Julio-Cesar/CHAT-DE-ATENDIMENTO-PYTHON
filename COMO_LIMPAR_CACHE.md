# 🔄 Como Limpar o Cache do Navegador

## ⚠️ PROBLEMA
As modificações foram feitas no código, mas o navegador está mostrando a versão antiga em cache.

## ✅ SOLUÇÃO RÁPIDA

### Opção 1: Hard Refresh (RECOMENDADO)
Pressione as teclas:
- **Windows/Linux**: `Ctrl + Shift + R` ou `Ctrl + F5`
- **Mac**: `Cmd + Shift + R`

### Opção 2: Limpar Cache Manualmente

#### Google Chrome / Edge
1. Pressione `Ctrl + Shift + Delete`
2. Selecione "Imagens e arquivos em cache"
3. Clique em "Limpar dados"
4. Recarregue a página: `F5`

#### Firefox
1. Pressione `Ctrl + Shift + Delete`
2. Selecione "Cache"
3. Clique em "Limpar agora"
4. Recarregue a página: `F5`

### Opção 3: Modo Anônimo/Privado
1. Abra uma janela anônima:
   - Chrome/Edge: `Ctrl + Shift + N`
   - Firefox: `Ctrl + Shift + P`
2. Acesse: `http://127.0.0.1:8000/chat`

### Opção 4: DevTools (Para Desenvolvedores)
1. Pressione `F12` para abrir DevTools
2. Clique com botão direito no ícone de recarregar
3. Selecione "Esvaziar cache e recarregar forçadamente"

---

## 📋 VERIFICAR SE AS ABAS APARECERAM

Após limpar o cache, você deve ver:

### ✅ 3 ABAS no topo da sidebar de conversas:
1. **🤖 AUTOMAÇÃO** (com badge de contador)
2. **⏳ ESPERA** (com badge de contador)
3. **💬 ATIVO** (com badge de contador)

### ✅ Cada aba deve ter:
- Ícone colorido
- Nome do estado
- Badge com número de conversas

### ✅ Ao clicar nas abas:
- A aba fica destacada (fundo branco)
- Lista de conversas muda
- Badges atualizam

---

## 🔍 COMO CONFIRMAR QUE ESTÁ FUNCIONANDO

1. Abra o DevTools (`F12`)
2. Vá na aba "Network"
3. Recarregue a página (`Ctrl + R`)
4. Procure por `chat` na lista
5. Verifique se o Status é `200` e o Size não está como "(disk cache)"

---

## 🐛 SE AINDA NÃO FUNCIONAR

Execute no console do navegador (F12 → Console):

```javascript
// Limpar todo o cache
caches.keys().then(keys => keys.forEach(key => caches.delete(key)));

// Recarregar sem cache
location.reload(true);
```

---

## 📞 TESTE FINAL

Após limpar o cache, você deve ver algo assim:

```
┌─────────────────────────────────┐
│ 💬 Conversas            [🏠]    │
│ [🔍 Buscar conversas...]        │
├─────────────────────────────────┤
│ 🤖 AUTOMAÇÃO    ⏳ ESPERA  💬 ATIVO │
│    [0]           [0]        [0]  │
├─────────────────────────────────┤
│ [+ Nova Conversa]               │
├─────────────────────────────────┤
│ (Lista de conversas aqui)       │
└─────────────────────────────────┘
```

---

## ✅ CONFIRMAÇÃO

Se você vê as 3 abas (Automação, Espera, Ativo), está funcionando!

Se não vê, tente:
1. Fechar TODAS as abas do navegador
2. Abrir novamente
3. Acessar: http://127.0.0.1:8000/chat

---

**Data**: 12/02/2026  
**Versão**: 2.0.0  
**Status**: ✅ Código atualizado, aguardando limpeza de cache
