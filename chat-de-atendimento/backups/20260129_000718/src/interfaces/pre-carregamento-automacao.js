const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('automacaoAPI', {
    carregar: () => ipcRenderer.invoke('automacao:obter-config'),
    salvar: (config) => ipcRenderer.invoke('automacao:salvar-config', config),
    gerarPrompt: (payload) => ipcRenderer.invoke('automacao:gerar-prompt', payload)
});

contextBridge.exposeInMainWorld('navigationAPI', {
    navigate: (route, params = {}) => ipcRenderer.invoke('navigate-to', route, params),
    goBack: () => ipcRenderer.invoke('navigate-back'),
    goForward: () => ipcRenderer.invoke('navigate-forward'),
    getState: () => ipcRenderer.invoke('navigation-get-state'),
    onNavigationStateUpdate: (callback) => ipcRenderer.on('navigation-state', (_, state) => callback(state))
});
