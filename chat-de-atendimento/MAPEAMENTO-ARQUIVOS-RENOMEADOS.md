# Mapeamento de Arquivos Renomeados

## Interfaces (src/interfaces)

### Componentes UI
- `confirmation-modal.js` → `modal-confirmacao.js`
- `loading-states.js` → `estados-carregamento.js`
- `toast-notifications.js` → `notificacoes-toast.js`
- `navigation-api.js` → `api-navegacao.js`
- `navigation-bar.js` → `barra-navegacao.js`

### Pre-carregamentos (Preloads)
- `preload.js` → `pre-carregamento.js`
- `preload-cadastro.js` → `pre-carregamento-cadastro.js`
- `preload-chat.js` → `pre-carregamento-chat.js`
- `preload-chatbot.js` → `pre-carregamento-chatbot.js`
- `preload-dashboard.js` → `pre-carregamento-painel.js`
- `preload-health.js` → `pre-carregamento-saude.js`
- `preload-history.js` → `pre-carregamento-historico.js`
- `preload-login.js` → `pre-carregamento-login.js`
- `preload-pool-manager.js` → `pre-carregamento-gerenciador-pool.js`
- `preload-principal.js` → `pre-carregamento-principal.js`
- `preload-qr.js` → `pre-carregamento-qr.js`
- `preload-usuarios.js` → `pre-carregamento-usuarios.js`

### Páginas HTML
- `dashboard.html` → `painel.html`
- `health.html` → `saude.html`
- `history.html` → `historico.html`
- `pool-manager.html` → `gerenciador-pool.html`
- `qr-window.html` → `janela-qr.html`

## Services (src/services)
- `WindowManager.js` → `GerenciadorJanelas.js`
- `WhatsAppPoolManager.js` → `GerenciadorPoolWhatsApp.js`
- `WhatsAppClientService.js` → `ServicoClienteWhatsApp.js`

## Core (src/core)
- `cache.js` → `armazenamento-cache.js`
- `circuit-breaker.js` → `disjuntor-circuito.js`
- `config-manager.js` → `gerenciador-configuracoes.js`
- `di.js` → `injecao-dependencias.js`
- `error-handler.js` → `tratador-erros.js`
- `feature-flags.js` → `sinalizadores-recursos.js`
- `input-validator.js` → `validador-entradas.js`
- `message-queue.js` → `fila-mensagens.js`
- `performance-monitor.js` → `monitor-desempenho.js`
- `prometheus-metrics.js` → `metricas-prometheus.js`
- `rate-limiter.js` → `limitador-taxa.js`
- `retry-policy.js` → `politica-retentativas.js`

## Nomenclatura de Variáveis e Funções

### Convenções Adotadas
- **Variáveis**: camelCase em português (ex: `usuarioLogado`, `listaChats`)
- **Funções**: camelCase em português (ex: `carregarDados`, `enviarMensagem`)
- **Constantes**: UPPER_SNAKE_CASE em português (ex: `PORTA_SERVIDOR`, `TEMPO_EXPIRACAO`)
- **Classes**: PascalCase em português (ex: `GerenciadorJanelas`, `ServicoCliente`)
- **Callbacks**: sufixo descritivo (ex: `aoClicarBotao`, `quandoReceberMensagem`)
- **Arrays**: plural descritivo (ex: `mensagens`, `usuarios`, `listaChats`)

### Exemplos de Renomeação
- `client` → `cliente`
- `message` → `mensagem`
- `chatId` → `idChat`
- `callback` → `aoCompletar` / `quandoPronto`
- `onMessage` → `aoReceberMensagem`
- `handleClick` → `manipularClique`
- `fetchData` → `buscarDados`
- `updateState` → `atualizarEstado`
- `isValid` → `estaValido`
- `hasError` → `possuiErro`
