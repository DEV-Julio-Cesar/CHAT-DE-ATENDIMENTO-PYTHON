const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('campanhasAPI', {
    listar: () => ipcRenderer.invoke('campanhas:listar'),
    salvar: (campanha) => ipcRenderer.invoke('campanhas:salvar', campanha),
    remover: (idCampanha) => ipcRenderer.invoke('campanhas:remover', idCampanha),
    disparar: (payload) => ipcRenderer.invoke('campanhas:disparar', payload),
    listarClientesWhatsapp: () => ipcRenderer.invoke('list-all-clients-info'),
    importarPlanilha: (payload) => ipcRenderer.invoke('campanhas:importar-planilha', payload)
});

contextBridge.exposeInMainWorld('navigationAPI', {
    navigate: (route, params = {}) => ipcRenderer.invoke('navigate-to', route, params),
    goBack: () => ipcRenderer.invoke('navigate-back'),
    goForward: () => ipcRenderer.invoke('navigate-forward'),
    getState: () => ipcRenderer.invoke('navigation-get-state'),
    onNavigationStateUpdate: (callback) => ipcRenderer.on('navigation-state', (_, state) => callback(state))
});
