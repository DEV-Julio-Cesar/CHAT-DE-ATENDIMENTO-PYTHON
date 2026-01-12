contextBridge.exposeInMainWorld('iaAPI', {
    perguntarGemini: ({ mensagem, contexto }) => ipcRenderer.invoke('ia:gemini:perguntar', { mensagem, contexto })
});
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('chatAPI', {
    aoDefinirCliente: (callback) => ipcRenderer.on('set-client-id', (_, id) => callback(id)),
    aoNovaMensagem: (callback) => ipcRenderer.on('nova-mensagem-recebida', (_, data) => callback(data)),
    listarChats: (clientId) => ipcRenderer.invoke('list-whatsapp-chats', clientId),
    carregarHistorico: (clientId, chatId) => ipcRenderer.invoke('load-chat-history', { clientId, chatId }),
    enviarMensagem: (clientId, chatId, message) => ipcRenderer.invoke('send-whatsapp-message', { clientId, chatId, message }),
    listarMensagensRapidas: () => ipcRenderer.invoke('quick-messages-list'),
    obterMensagemRapida: (codigo) => ipcRenderer.invoke('quick-messages-get', codigo),
    adicionarMensagemRapida: (codigo, texto) => ipcRenderer.invoke('quick-messages-add', { codigo, texto }),
    removerMensagemRapida: (codigo) => ipcRenderer.invoke('quick-messages-remove', codigo),
    registrarUsoMensagemRapida: (codigo) => ipcRenderer.invoke('quick-messages-registrar-uso', codigo),
    metricasMensagensRapidas: () => ipcRenderer.invoke('quick-messages-metrics'),
    resetMetricasMensagensRapidas: () => ipcRenderer.invoke('quick-messages-metrics-reset')
});

// API de Filas de Atendimento
contextBridge.exposeInMainWorld('filasAPI', {
    criarConversa: (clientId, chatId, metadata) => ipcRenderer.invoke('filas:criar-conversa', { clientId, chatId, metadata }),
    moverParaEspera: (clientId, chatId, motivo) => ipcRenderer.invoke('filas:mover-espera', { clientId, chatId, motivo }),
    assumirConversa: (clientId, chatId, atendente) => ipcRenderer.invoke('filas:assumir', { clientId, chatId, atendente }),
    encerrarConversa: (clientId, chatId, atendente) => ipcRenderer.invoke('filas:encerrar', { clientId, chatId, atendente }),
    listarPorEstado: (estado, atendente) => ipcRenderer.invoke('filas:listar-por-estado', { estado, atendente }),
    obterEstatisticas: () => ipcRenderer.invoke('filas:estatisticas'),
    atualizarMetadata: (clientId, chatId, metadata) => ipcRenderer.invoke('filas:atualizar-metadata', { clientId, chatId, metadata }),
    // Novas operações avançadas
    atribuirConversa: (clientId, chatId, atendente, atendenteOrigem) => ipcRenderer.invoke('filas:atribuir', { clientId, chatId, atendente, atendenteOrigem }),
    transferirConversa: (clientId, chatId, atendenteDestino, atendenteOrigem) => ipcRenderer.invoke('filas:transferir', { clientId, chatId, atendenteDestino, atendenteOrigem }),
    atribuirMultiplos: (conversasIds, atendente, atendenteOrigem) => ipcRenderer.invoke('filas:atribuir-multiplos', { conversasIds, atendente, atendenteOrigem }),
    encerrarMultiplos: (conversasIds, atendente) => ipcRenderer.invoke('filas:encerrar-multiplos', { conversasIds, atendente }),
    listarAtendentes: () => ipcRenderer.invoke('filas:listar-atendentes')
});

contextBridge.exposeInMainWorld('navigationAPI', {
    navigate: (route, params = {}) => ipcRenderer.invoke('navigate-to', route, params),
    goBack: () => ipcRenderer.invoke('navigate-back'),
    goForward: () => ipcRenderer.invoke('navigate-forward'),
    getState: () => ipcRenderer.invoke('navigation-get-state'),
    onNavigationStateUpdate: (callback) => ipcRenderer.on('navigation-state', (_, state) => callback(state)),
    onParams: (callback) => ipcRenderer.on('navigation-params', (_, params) => callback(params))
});