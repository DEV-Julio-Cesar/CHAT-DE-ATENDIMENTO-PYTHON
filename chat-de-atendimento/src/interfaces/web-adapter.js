// =========================================================================
// ADAPTADOR WEB - SUBSTITUI AS APIS DO ELECTRON PARA FUNCIONAR NO NAVEGADOR
// =========================================================================

(function() {
    'use strict';
    
    console.log('[Web Adapter] Inicializando adaptador web...');
    
    // =========================================================================
    // CONFIGURAÇÕES
    // =========================================================================
    const API_BASE = window.location.origin;
    
    // Detectar se está em produção (Railway) ou desenvolvimento
    const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
    
    let WS_URL, CHAT_WS_URL;
    
    if (isProduction) {
        // Em produção, usar WSS (WebSocket Secure) com o mesmo domínio
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        WS_URL = `${wsProtocol}//${window.location.host}/ws`;
        CHAT_WS_URL = `${wsProtocol}//${window.location.host}/chat-ws`;
        
        console.log('[Web Adapter] Modo produção detectado');
        console.log('[Web Adapter] WS_URL:', WS_URL);
        console.log('[Web Adapter] CHAT_WS_URL:', CHAT_WS_URL);
    } else {
        // Em desenvolvimento, usar portas específicas
        WS_URL = `ws://${window.location.hostname}:8080`;
        CHAT_WS_URL = `ws://${window.location.hostname}:9090`;
        
        console.log('[Web Adapter] Modo desenvolvimento detectado');
        console.log('[Web Adapter] WS_URL:', WS_URL);
        console.log('[Web Adapter] CHAT_WS_URL:', CHAT_WS_URL);
    }
    
    // =========================================================================
    // SERVER-SENT EVENTS PARA COMUNICAÇÃO EM TEMPO REAL
    // =========================================================================
    let eventSource = null;
    let chatEventSource = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    
    function connectEventSource() {
        try {
            console.log('[SSE] Conectando em:', `${API_BASE}/api/events`);
            eventSource = new EventSource(`${API_BASE}/api/events`);
            
            eventSource.onopen = () => {
                console.log('[SSE] Conectado ao servidor');
                reconnectAttempts = 0;
            };
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[SSE] Mensagem recebida:', data);
                    handleServerMessage(data);
                } catch (error) {
                    console.error('[SSE] Erro ao processar mensagem:', error);
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('[SSE] Erro de conexão:', error);
                eventSource.close();
                
                if (reconnectAttempts < maxReconnectAttempts) {
                    console.log(`[SSE] Tentativa de reconexão ${reconnectAttempts + 1}/${maxReconnectAttempts} em 3s...`);
                    setTimeout(() => {
                        reconnectAttempts++;
                        connectEventSource();
                    }, 3000);
                } else {
                    console.error('[SSE] Máximo de tentativas de reconexão atingido');
                }
            };
            
        } catch (error) {
            console.error('[SSE] Erro ao conectar:', error);
        }
    }
    
    function connectChatEventSource() {
        try {
            console.log('[Chat SSE] Conectando em:', `${API_BASE}/api/chat-events`);
            chatEventSource = new EventSource(`${API_BASE}/api/chat-events`);
            
            chatEventSource.onopen = () => {
                console.log('[Chat SSE] Conectado');
            };
            
            chatEventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    // Disparar evento customizado para mensagens de chat interno
                    window.dispatchEvent(new CustomEvent('internal-chat-message', { detail: data }));
                } catch (error) {
                    console.error('[Chat SSE] Erro ao processar mensagem:', error);
                }
            };
            
            chatEventSource.onerror = (error) => {
                console.error('[Chat SSE] Erro:', error);
                setTimeout(() => {
                    connectChatEventSource();
                }, 3000);
            };
            
        } catch (error) {
            console.error('[Chat SSE] Erro ao conectar:', error);
        }
    }
    
    function handleServerMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('[SSE] Conectado com ID:', data.clientId);
                break;
            case 'qr-generated':
                console.log('[SSE] QR Code recebido para cliente:', data.data.clientId);
                window.dispatchEvent(new CustomEvent('qr-generated', { detail: data.data }));
                break;
            case 'client-ready':
                console.log('[SSE] Cliente pronto:', data.data.clientId);
                window.dispatchEvent(new CustomEvent('client-ready', { detail: data.data }));
                break;
            case 'new-message':
                console.log('[SSE] Nova mensagem:', data.data);
                window.dispatchEvent(new CustomEvent('new-message', { detail: data.data }));
                break;
            default:
                console.log('[SSE] Mensagem não reconhecida:', data.type);
        }
    }
    
    // =========================================================================
    // API HTTP HELPER
    // =========================================================================
    async function apiRequest(endpoint, options = {}) {
        try {
            const response = await fetch(`${API_BASE}/api${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error(`[API] Erro em ${endpoint}:`, error);
            throw error;
        }
    }
    
    // =========================================================================
    // ADAPTADOR PARA API DE AUTENTICAÇÃO
    // =========================================================================
    window.authAPI = {
        async tentarLogin(username, password) {
            try {
                const result = await apiRequest('/login', {
                    method: 'POST',
                    body: JSON.stringify({ username, password })
                });
                
                if (result.success) {
                    // Salvar dados do usuário no localStorage
                    localStorage.setItem('currentUser', JSON.stringify(result.user));
                }
                
                return result;
            } catch (error) {
                return { success: false, message: error.message };
            }
        },
        
        fecharJanela() {
            // No navegador, redirecionar para página principal
            window.location.href = '/principal';
        },
        
        abrirCadastro() {
            // Abrir em nova aba ou redirecionar
            window.open('/cadastro', '_blank');
        }
    };
    
    // =========================================================================
    // ADAPTADOR PARA API DE NAVEGAÇÃO
    // =========================================================================
    window.navigationAPI = {
        navigate(page, params = {}) {
            const routes = {
                'login': '/login',
                'principal': '/principal',
                'chat-filas': '/chat-filas',
                'campanhas': '/campanhas',
                'usuarios': '/usuarios',
                'automacao': '/automacao',
                'dashboard': '/dashboard'
            };
            
            const url = routes[page] || '/';
            
            // Adicionar parâmetros como query string se necessário
            if (Object.keys(params).length > 0) {
                const searchParams = new URLSearchParams(params);
                window.location.href = `${url}?${searchParams.toString()}`;
            } else {
                window.location.href = url;
            }
        }
    };
    
    // =========================================================================
    // ADAPTADOR PARA API DO WHATSAPP
    // =========================================================================
    window.electronAPI = {
        async listarClientesConectados() {
            try {
                const result = await apiRequest('/whatsapp/clients');
                return result.success ? Object.keys(result.clients) : [];
            } catch (error) {
                console.error('[WhatsApp API] Erro ao listar clientes:', error);
                return [];
            }
        },
        
        async iniciarNovaConexao() {
            try {
                return await apiRequest('/whatsapp/create-client', {
                    method: 'POST'
                });
            } catch (error) {
                return { success: false, message: error.message };
            }
        },
        
        async enviarMensagem(clientId, chatId, message) {
            try {
                return await apiRequest('/whatsapp/send-message', {
                    method: 'POST',
                    body: JSON.stringify({ clientId, chatId, message })
                });
            } catch (error) {
                return { success: false, message: error.message };
            }
        },
        
        // Eventos do WhatsApp
        aoQRGerado(callback) {
            window.addEventListener('qr-generated', (event) => {
                callback(event.detail.qrDataURL);
            });
        },
        
        aoClienteProntoQR(callback) {
            window.addEventListener('client-ready', (event) => {
                callback(event.detail.clientId);
            });
        },
        
        aoClientePronto(callback) {
            window.addEventListener('client-ready', (event) => {
                callback(event.detail.clientId);
            });
        },
        
        // Funções de navegação (compatibilidade)
        abrirPoolManager() {
            window.open('/pool-manager', '_blank');
        },
        
        abrirDashboard() {
            window.location.href = '/dashboard';
        },
        
        abrirChatbot() {
            window.location.href = '/automacao';
        },
        
        abrirAutomacao() {
            window.location.href = '/automacao';
        },
        
        abrirCampanhas() {
            window.location.href = '/campanhas';
        },
        
        abrirUsuarios() {
            window.location.href = '/usuarios';
        },
        
        abrirChat(clientId) {
            window.location.href = `/chat-filas?clientId=${clientId}`;
        }
    };
    
    // =========================================================================
    // ADAPTADOR PARA API DE USUÁRIOS
    // =========================================================================
    window.cadastroAPI = {
        async cadastrar(userData) {
            try {
                return await apiRequest('/users', {
                    method: 'POST',
                    body: JSON.stringify(userData)
                });
            } catch (error) {
                return { success: false, message: error.message };
            }
        }
    };
    
    // =========================================================================
    // ADAPTADOR PARA TEMA
    // =========================================================================
    window.electronAPI.getTheme = async function() {
        const theme = localStorage.getItem('theme') || 'light';
        return { theme };
    };
    
    window.electronAPI.setTheme = async function(theme) {
        localStorage.setItem('theme', theme);
        return { success: true, theme };
    };
    
    // =========================================================================
    // ADAPTADOR PARA VERIFICAÇÃO DE SESSÃO
    // =========================================================================
    window.electronAPI.verificarSessao = async function() {
        const user = localStorage.getItem('currentUser');
        if (user) {
            return { success: true, usuario: JSON.parse(user) };
        } else {
            return { success: false, message: 'Sessão não encontrada' };
        }
    };
    
    // =========================================================================
    // CHAT INTERNO
    // =========================================================================
    window.chatInternoAPI = {
        async enviarMensagem(from, texto) {
            try {
                const response = await apiRequest('/chat-message', {
                    method: 'POST',
                    body: JSON.stringify({ from, texto })
                });
                return { sucesso: response.success };
            } catch (error) {
                console.error('[Chat Interno] Erro ao enviar mensagem:', error);
                return { sucesso: false, erro: error.message };
            }
        }
    };
    
    // =========================================================================
    // POOL API PARA GERENCIADOR
    // =========================================================================
    window.poolAPI = {
        async getAllClientsInfo() {
            try {
                const result = await apiRequest('/whatsapp/clients');
                if (result.success) {
                    return Object.entries(result.clients).map(([id, info]) => ({
                        clientId: id,
                        status: info.status || 'idle',
                        isReady: info.ready || false,
                        phoneNumber: info.phoneNumber || null,
                        metadata: {
                            createdAt: info.createdAt || new Date().toISOString(),
                            messageCount: info.messageCount || 0
                        }
                    }));
                }
                return [];
            } catch (error) {
                console.error('[Pool API] Erro ao obter clientes:', error);
                return [];
            }
        },
        
        async getStats() {
            try {
                const result = await apiRequest('/status');
                if (result.success) {
                    return {
                        currentClients: result.status.whatsapp.clients || 0,
                        readyClients: 0, // Será calculado no frontend
                        totalMessages: 0 // Placeholder
                    };
                }
                return { currentClients: 0, readyClients: 0, totalMessages: 0 };
            } catch (error) {
                console.error('[Pool API] Erro ao obter stats:', error);
                return { currentClients: 0, readyClients: 0, totalMessages: 0 };
            }
        },
        
        async openNewQRWindow() {
            try {
                const result = await apiRequest('/whatsapp/create-client', {
                    method: 'POST'
                });
                return result;
            } catch (error) {
                return { success: false, message: error.message };
            }
        },
        
        async openConexaoPorNumeroWindow() {
            // Abrir página de conexão por número
            window.open('/conectar-numero', '_blank');
        },
        
        async openChat(clientId) {
            window.open(`/chat-filas?clientId=${clientId}`, '_blank');
        },
        
        async disconnectClient(clientId) {
            // Implementar quando necessário
            return { success: false, message: 'Função não implementada' };
        },
        
        async reconnectClient(clientId) {
            // Implementar quando necessário
            return { success: false, message: 'Função não implementada' };
        },
        
        async logoutClient(clientId) {
            // Implementar quando necessário
            return { success: false, message: 'Função não implementada' };
        },
        
        async restorePersistedSessions() {
            // Implementar quando necessário
            return { restored: 0, total: 0 };
        },
        
        onClientReady(callback) {
            window.addEventListener('client-ready', (event) => {
                callback(event.detail);
            });
        }
    };
    
    // =========================================================================
    // INICIALIZAÇÃO
    // =========================================================================
    function inicializar() {
        console.log('[Web Adapter] Inicializando adaptador web...');
        
        // Conectar SSE
        connectEventSource();
        connectChatEventSource();
        
        // Verificar se há usuário logado
        const user = localStorage.getItem('currentUser');
        if (user && window.location.pathname !== '/login') {
            console.log('[Web Adapter] Usuário logado encontrado');
        } else if (!user && window.location.pathname !== '/login') {
            console.log('[Web Adapter] Redirecionando para login...');
            window.location.href = '/login';
        }
    }
    
    // Inicializar quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializar);
    } else {
        inicializar();
    }
    
    console.log('[Web Adapter] Adaptador web carregado com sucesso');
    
})();