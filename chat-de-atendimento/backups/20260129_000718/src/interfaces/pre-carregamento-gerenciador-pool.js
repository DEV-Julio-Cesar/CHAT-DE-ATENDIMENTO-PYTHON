const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('poolAPI', {
    // Obter informações de todos os clientes
    getAllClientsInfo: () => ipcRenderer.invoke('list-all-clients-info'),
    
    // Obter estatísticas do pool
    getStats: () => ipcRenderer.invoke('get-pool-stats'),
    
    // Criar Nãova janela QR
    openNewQRWindow: () => ipcRenderer.invoke('open-new-qr-window'),
    
    // Abrir interface de conexão por número
    openConexaoPorNumeroWindow: () => ipcRenderer.invoke('open-conexao-por-numero-window'),
    openChat: (clientId) => ipcRenderer.send('open-chat-window', clientId),
    
    // Desconectar cliente
    disconnectClient: (clientId) => ipcRenderer.invoke('disconnect-client', clientId),
    
    // Reconectar cliente
    reconnectClient: (clientId) => ipcRenderer.invoke('reconnect-client', clientId),
    
    // Sair de cliente (ReMoverr sessão) com auditoria de origem
    logoutClient: async (clientId) => {
        try {
            const state = await ipcRenderer.invoke('navigation-get-state');
            const origin = state?.currentRoute || 'unknown';
            return await ipcRenderer.invoke('logout-client', { clientId, origin });
        } catch (e) {
            // fallVoltar padrão
            return await ipcRenderer.invoke('logout-client', clientId);
        }
    },
    
    // Restaurar sessões persistidas
    restorePersistedSessions: () => ipcRenderer.invoke('restore-persisted-sessions'),
    
    // Listaener para Nãovos clientes prontos
    onClientReady: (callback) => ipcRenderer.on('new-client-ready', (_, data) => callback(data))
});

contextBridge.exposeInMainWorld('navigationAPI', {
    navigate: (route, params = {}) => ipcRenderer.invoke('navigate-to', route, params),
    goBack: () => ipcRenderer.invoke('navigate-back'),
    goForward: () => ipcRenderer.invoke('navigate-forward'),
    getState: () => ipcRenderer.invoke('navigation-get-state'),
    onNavigationStateUpdate: (callback) => ipcRenderer.on('navigation-state', (_, state) => callback(state)),
    onParams: (callback) => ipcRenderer.on('navigation-params', (_, params) => callback(params))
});

// API para eventos de QR Code
contextBridge.exposeInMainWorld('electronAPI', {
    onQRCode: (callback) => ipcRenderer.on('qr-code-gerado', (_, qrDataURL) => callback(qrDataURL)),
    onClienteProntoQR: (callback) => ipcRenderer.on('cliente-pronto-qr', (_, clientId) => callback(clientId))
});
