# 🪟 Sistema de Navegação de Janelas

## ✨ O Que Foi Implementado

O sistema agora possui **navegação inteligente** que **fecha automaticamente a janela anterior** ao abrir uma nova, proporcionando uma experiência mais limpa e profissional.

---

## 🎯 Comportamento Implementado

### Fluxo de Login
```
1. Aplicação inicia → Abre janela de LOGIN
2. Usuário faz login com sucesso
3. Abre janela PRINCIPAL
4. ✅ Janela de LOGIN é FECHADA automaticamente
```

### Navegação Entre Telas
```
PRINCIPAL → POOL MANAGER
✅ Fecha PRINCIPAL, abre POOL MANAGER

POOL MANAGER → CHATBOT
✅ Fecha POOL MANAGER, abre CHATBOT

CHATBOT → DASHBOARD
✅ Fecha CHATBOT, abre DASHBOARD
```

### Botões de Navegação
```
[← Voltar]  - Volta para tela anterior
[Avançar →] - Avança para próxima tela (se houver)
[🏠 Início] - Sempre volta para PRINCIPAL
```

---

## 🔧 Mudanças Técnicas Realizadas

### 1. **GerenciadorJanelas Centralizado**

Todas as janelas agora são gerenciadas pelo `GerenciadorJanelas`:

```javascript
// ❌ ANTES (método antigo - múltiplas janelas abertas)
createLoginWindow();
createMainWindow();
createChatWindow();

// ✅ AGORA (gerenciador - uma janela por vez)
gerenciadorJanelas.navigate('login');
gerenciadorJanelas.navigate('principal');
gerenciadorJanelas.navigate('chat');
```

### 2. **Inicialização da Aplicação**

```javascript
// main.js - app.whenReady()
app.whenReady().then(async () => {
    // 1. Inicializar Window Manager
    gerenciadorJanelas = new GerenciadorJanelas();
    
    // 2. Configurar handlers de navegação
    setupNavigationHandlers();
    
    // 3. Configurar IPC handlers
    configurarManipuladoresIPC();
    
    // 4. Criar menu
    criarMenuPrincipal();
    
    // 5. Abrir tela de login
    gerenciadorJanelas.navigate('login');
});
```

### 3. **Handlers IPC de Navegação**

```javascript
// Handlers configurados em setupNavigationHandlers()
ipcMain.handle('navigate-to', async (_event, route, params) => {
    gerenciadorJanelas.navigate(route, params);
    return { success: true };
});

ipcMain.handle('navigate-back', async () => {
    return { success: gerenciadorJanelas.goBack() };
});

ipcMain.handle('navigate-forward', async () => {
    return { success: gerenciadorJanelas.goForward() };
});
```

### 4. **Fluxo de Login**

No arquivo `login.html`:

```javascript
// Após login bem-sucedido
if (resultado.success) {
    toast.success('Login realizado com sucesso!');
    
    setTimeout(async () => {
        // Navega para tela principal
        // GerenciadorJanelas fecha login automaticamente
        await window.navigationAPI.navigate('principal');
    }, 800);
}
```

### 5. **Remoção de Código Legado**

Funções antigas comentadas (não mais usadas):

```javascript
// ❌ DEPRECATED - Mantidas apenas para referência
// createLoginWindow()
// createMainWindow()
// createHistoryWindow()
```

Variáveis globais removidas:

```javascript
// ❌ Não mais necessárias
// let loginWindow = null;
// let mainWindow = null;
// let historyWindow = null;
```

### 6. **Atualização de Referências**

Todas as referências a `mainWindow` foram atualizadas:

```javascript
// ❌ ANTES
if (mainWindow) {
    mainWindow.webContents.send('mensagem', data);
}

// ✅ AGORA
if (gerenciadorJanelas && gerenciadorJanelas.currentWindow) {
    gerenciadorJanelas.currentWindow.webContents.send('mensagem', data);
}
```

---

## 📋 Rotas Disponíveis

O `GerenciadorJanelas` suporta as seguintes rotas:

| Rota | Arquivo | Descrição |
|------|---------|-----------|
| `login` | `login.html` | Tela de autenticação |
| `principal` | `index.html` | Dashboard principal |
| `pool-manager` | `gerenciador-pool.html` | Gerenciador de conexões WhatsApp |
| `chat` | `chat.html` | Interface de chat |
| `dashboard` | `painel.html` | Métricas e estatísticas |
| `chatbot` | `chatbot.html` | Configuração do chatbot |
| `usuarios` | `usuarios.html` | Gerenciamento de usuários |
| `history` | `historico.html` | Histórico de conversas |
| `cadastro` | `cadastro.html` | Cadastro de novo usuário |
| `health` | `saude.html` | Health check do sistema |

---

## 🎮 Como Usar (Para Desenvolvedores)

### Navegar Para Nova Tela

```javascript
// Dentro do renderer process (HTML/JS)
await window.navigationAPI.navigate('pool-manager');
await window.navigationAPI.navigate('chat', { clientId: '123' });
```

### Voltar/Avançar

```javascript
// Voltar para tela anterior
await window.navigationAPI.goBack();

// Avançar para próxima (se houver histórico)
await window.navigationAPI.goForward();
```

### Obter Estado de Navegação

```javascript
const state = await window.navigationAPI.getState();
console.log(state);
// {
//   canGoBack: true,
//   canGoForward: false,
//   currentRoute: 'principal'
// }
```

### Escutar Mudanças de Estado

```javascript
window.navigationAPI.onNavigationStateUpdate((state) => {
    console.log('Estado mudou:', state);
    // Atualizar UI conforme necessário
});
```

### Receber Parâmetros de Navegação

```javascript
// Quando uma tela recebe parâmetros
window.navigationAPI.onParams((params) => {
    console.log('Parâmetros recebidos:', params);
    // Ex: { clientId: '123' }
});
```

---

## 🧭 Barra de Navegação

Todas as telas podem incluir a barra de navegação:

```javascript
// No final do HTML, antes de </body>
<script src="barra-navegacao.js"></script>
<script>
    initNavigationBar('Título da Página');
</script>
```

A barra inclui:
- `← Voltar` (habilitado se houver histórico)
- `Avançar →` (habilitado se houver histórico futuro)
- `🏠 Início` (sempre habilitado, vai para 'principal')

---

## 📊 Histórico de Navegação

O sistema mantém um histórico de navegação:

```javascript
// Exemplo de histórico após navegação
[
    { route: 'login', params: {} },
    { route: 'principal', params: {} },
    { route: 'pool-manager', params: {} },
    { route: 'chat', params: { clientId: '123' } }
]
// Índice atual: 3 (chat)
```

### Resetar Histórico

```javascript
// No main process
gerenciadorJanelas.resetHistory('principal');
// Limpa histórico e define 'principal' como nova raiz
```

---

## 🔍 Debugging

### Ver Logs de Navegação

Todos os eventos de navegação são logados:

```
[INFO] [GerenciadorJanelas] Navegando para: login
[INFO] [GerenciadorJanelas] Navegando para: principal
[INFO] [GerenciadorJanelas] Voltando para: principal
```

### Verificar Janela Atual

```javascript
// No main process
console.log('Janela atual:', gerenciadorJanelas.getCurrentRoute());
console.log('Pode voltar?', gerenciadorJanelas.canGoBack());
console.log('Pode avançar?', gerenciadorJanelas.canGoForward());
```

---

## ⚙️ Configuração de Novas Rotas

Para adicionar uma nova rota ao sistema:

```javascript
// Em GerenciadorJanelas.js
this.windowConfigs = {
    // ... rotas existentes ...
    
    'minha-nova-tela': {
        file: 'src/interfaces/minha-tela.html',
        preload: 'src/interfaces/pre-carregamento-minha-tela.js',
        width: 1000,
        height: 700,
        resizable: true,
        title: 'Minha Nova Tela'
    }
};
```

Depois, navegue normalmente:

```javascript
gerenciadorJanelas.navigate('minha-nova-tela', { param1: 'valor' });
```

---

## 🐛 Problemas Conhecidos

### ⚠️ Auditoria Log Missing
```
[AUDIT] Falha ao registrar evento: ENOENT: no such file or directory
```
**Solução**: Criar pasta `src/dados/` se não existir. O sistema continua funcionando normalmente.

### ⚠️ Janela Não Fecha
Se uma janela anterior não fecha, verifique:
1. Se está usando `gerenciadorJanelas.navigate()` e não as funções antigas
2. Se `setupNavigationHandlers()` foi chamado apenas uma vez
3. Se o preload script expõe `window.navigationAPI`

---

## 📈 Benefícios da Implementação

✅ **Única Janela Aberta**: Economia de memória e CPU
✅ **Navegação Intuitiva**: Usuário sabe onde está sempre
✅ **Histórico Funcional**: Botão Voltar/Avançar como em navegador
✅ **Código Limpo**: Gerenciamento centralizado
✅ **Fácil Manutenção**: Uma única classe controla tudo
✅ **Experiência Profissional**: Interface moderna e fluida

---

## 🚀 Próximos Passos (Opcional)

Melhorias futuras possíveis:

1. **Animações de Transição**: Fade in/out entre telas
2. **Breadcrumbs**: Mostrar caminho de navegação
3. **Atalhos de Teclado**: Ctrl+← para voltar, Ctrl+→ para avançar
4. **Persistência**: Salvar última tela aberta e restaurar ao iniciar
5. **Tabs**: Múltiplas janelas em abas (como navegador)

---

**Implementado em:** 11/01/2026  
**Status:** ✅ Completo e Funcionando  
**Versão:** 2.0.0
