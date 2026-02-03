/**
 * Mobile App JavaScript - CIANET Atendente
 * Versão: 3.0
 * 
 * Features:
 * - WebSocket para atualizações em tempo real
 * - IndexedDB para offline
 * - Touch gestures
 * - Push notifications
 */

// ============================================================================
// CONFIGURAÇÃO
// ============================================================================

const API_BASE = window.location.origin + '/api';
const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

// Estado da aplicação
const appState = {
    token: localStorage.getItem('token'),
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    currentConversation: null,
    conversations: [],
    isOnline: navigator.onLine,
    ws: null
};

// ============================================================================
// AUTENTICAÇÃO
// ============================================================================

async function login(email, password) {
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE}/auth/v2/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Falha no login');
        }
        
        const data = await response.json();
        
        // Salvar tokens
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        appState.token = data.access_token;
        appState.user = data.user;
        
        // Conectar WebSocket
        connectWebSocket();
        
        // Ir para o chat
        showChatScreen();
        
        showToast('Login realizado com sucesso!', 'success');
        
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function logout() {
    try {
        await fetch(`${API_BASE}/auth/v2/logout`, {
            method: 'POST',
            headers: authHeaders()
        });
    } catch (e) {
        // Ignorar erros no logout
    }
    
    // Limpar storage
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    
    appState.token = null;
    appState.user = null;
    
    // Desconectar WebSocket
    if (appState.ws) {
        appState.ws.close();
    }
    
    showLoginScreen();
}

async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        logout();
        return false;
    }
    
    try {
        const response = await fetch(`${API_BASE}/auth/v2/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (!response.ok) {
            logout();
            return false;
        }
        
        const data = await response.json();
        
        localStorage.setItem('token', data.access_token);
        if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
        }
        
        appState.token = data.access_token;
        
        return true;
        
    } catch (error) {
        logout();
        return false;
    }
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${appState.token}`
    };
}

// ============================================================================
// WEBSOCKET
// ============================================================================

function connectWebSocket() {
    if (!appState.token) return;
    
    const wsUrl = `${WS_BASE}/chat?token=${appState.token}`;
    
    appState.ws = new WebSocket(wsUrl);
    
    appState.ws.onopen = () => {
        console.log('[WS] Connected');
        updateConnectionStatus(true);
    };
    
    appState.ws.onclose = () => {
        console.log('[WS] Disconnected');
        updateConnectionStatus(false);
        
        // Reconectar após 3 segundos
        setTimeout(() => {
            if (appState.token) {
                connectWebSocket();
            }
        }, 3000);
    };
    
    appState.ws.onerror = (error) => {
        console.error('[WS] Error:', error);
    };
    
    appState.ws.onmessage = (event) => {
        handleWebSocketMessage(JSON.parse(event.data));
    };
}

function handleWebSocketMessage(data) {
    console.log('[WS] Message:', data);
    
    switch (data.type) {
        case 'new_message':
            handleNewMessage(data.payload);
            break;
            
        case 'conversation_assigned':
            handleConversationAssigned(data.payload);
            break;
            
        case 'conversation_closed':
            handleConversationClosed(data.payload);
            break;
            
        case 'queue_update':
            handleQueueUpdate(data.payload);
            break;
            
        case 'typing':
            handleTypingIndicator(data.payload);
            break;
    }
}

function handleNewMessage(payload) {
    const { conversation_id, message } = payload;
    
    // Se é a conversa atual, adicionar mensagem
    if (appState.currentConversation?.id === conversation_id) {
        appendMessage(message);
        scrollToBottom();
    }
    
    // Atualizar lista de conversas
    updateConversationPreview(conversation_id, message);
    
    // Notificação se não é a conversa atual
    if (appState.currentConversation?.id !== conversation_id) {
        showNotification('Nova mensagem', message.content);
        playNotificationSound();
    }
}

function handleConversationAssigned(payload) {
    showToast(`Nova conversa atribuída: ${payload.client_name}`, 'info');
    loadConversations();
}

function handleConversationClosed(payload) {
    if (appState.currentConversation?.id === payload.conversation_id) {
        showToast('Conversa finalizada', 'info');
        appState.currentConversation = null;
        showConversationList();
    }
    loadConversations();
}

function handleQueueUpdate(payload) {
    updateQueueBadge(payload.count);
}

function handleTypingIndicator(payload) {
    if (appState.currentConversation?.id === payload.conversation_id) {
        showTypingIndicator(payload.is_typing);
    }
}

// ============================================================================
// API CALLS
// ============================================================================

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                ...authHeaders(),
                ...options.headers
            }
        });
        
        if (response.status === 401) {
            // Token expirado, tentar refresh
            const refreshed = await refreshToken();
            
            if (refreshed) {
                // Tentar novamente
                return apiCall(endpoint, options);
            }
            
            return null;
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro na requisição');
        }
        
        return response.json();
        
    } catch (error) {
        if (!appState.isOnline) {
            showToast('Você está offline', 'warning');
        } else {
            showToast(error.message, 'error');
        }
        return null;
    }
}

async function loadConversations() {
    const data = await apiCall('/conversations/v2/?status=in_progress&status=waiting');
    
    if (data) {
        appState.conversations = data.items || [];
        renderConversationList();
    }
}

async function loadConversation(id) {
    const data = await apiCall(`/conversations/v2/${id}`);
    
    if (data) {
        appState.currentConversation = data;
        renderConversation();
    }
}

async function loadMessages(conversationId) {
    const data = await apiCall(`/conversations/v2/${conversationId}/messages`);
    
    if (data) {
        renderMessages(data.items || []);
        scrollToBottom();
    }
}

async function sendMessage(content) {
    if (!appState.currentConversation) return;
    
    // Adicionar mensagem otimisticamente
    const tempMessage = {
        id: 'temp-' + Date.now(),
        content,
        sender_type: 'attendant',
        created_at: new Date().toISOString(),
        sending: true
    };
    
    appendMessage(tempMessage);
    scrollToBottom();
    
    // Enviar via API
    const data = await apiCall(`/conversations/v2/${appState.currentConversation.id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content, message_type: 'text' })
    });
    
    if (data) {
        // Substituir mensagem temporária
        updateTempMessage(tempMessage.id, data);
    } else {
        // Marcar como falha
        markMessageFailed(tempMessage.id);
        
        // Salvar para sync offline
        if (!appState.isOnline) {
            savePendingMessage(content);
        }
    }
}

async function assignConversation(conversationId) {
    const data = await apiCall(`/conversations/v2/${conversationId}/assign`, {
        method: 'POST'
    });
    
    if (data) {
        showToast('Conversa atribuída a você', 'success');
        loadConversations();
    }
}

async function closeConversation(conversationId, resolution) {
    const data = await apiCall(`/conversations/v2/${conversationId}/close`, {
        method: 'POST',
        body: JSON.stringify({ resolution })
    });
    
    if (data) {
        showToast('Conversa finalizada', 'success');
        appState.currentConversation = null;
        showConversationList();
        loadConversations();
    }
}

async function transferConversation(conversationId, targetUserId, reason) {
    const data = await apiCall(`/conversations/v2/${conversationId}/transfer`, {
        method: 'POST',
        body: JSON.stringify({ target_user_id: targetUserId, reason })
    });
    
    if (data) {
        showToast('Conversa transferida', 'success');
        appState.currentConversation = null;
        showConversationList();
        loadConversations();
    }
}

// ============================================================================
// RENDERIZAÇÃO
// ============================================================================

function renderConversationList() {
    const list = document.getElementById('conversation-list');
    if (!list) return;
    
    if (appState.conversations.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">💬</div>
                <p>Nenhuma conversa ativa</p>
                <small>As novas conversas aparecerão aqui</small>
            </div>
        `;
        return;
    }
    
    list.innerHTML = appState.conversations.map(conv => `
        <div class="conversation-item ${conv.status === 'waiting' ? 'waiting' : ''}" 
             onclick="openConversation(${conv.id})"
             data-id="${conv.id}">
            <div class="avatar">${getInitials(conv.client_name)}</div>
            <div class="conversation-info">
                <div class="conversation-header">
                    <span class="client-name">${escapeHtml(conv.client_name)}</span>
                    <span class="time">${formatTime(conv.last_message_at)}</span>
                </div>
                <div class="conversation-preview">
                    ${escapeHtml(conv.last_message || 'Nova conversa')}
                </div>
                <div class="conversation-meta">
                    <span class="status-badge ${conv.status}">${conv.status}</span>
                    ${conv.unread_count ? `<span class="unread-badge">${conv.unread_count}</span>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function renderConversation() {
    const conv = appState.currentConversation;
    if (!conv) return;
    
    // Header
    const header = document.getElementById('chat-header');
    if (header) {
        header.innerHTML = `
            <button class="back-btn" onclick="showConversationList()">←</button>
            <div class="chat-header-info">
                <div class="avatar">${getInitials(conv.client_name)}</div>
                <div>
                    <div class="client-name">${escapeHtml(conv.client_name)}</div>
                    <div class="client-phone">${conv.client_phone}</div>
                </div>
            </div>
            <button class="menu-btn" onclick="showChatMenu()">⋮</button>
        `;
    }
    
    // Carregar mensagens
    loadMessages(conv.id);
}

function renderMessages(messages) {
    const container = document.getElementById('messages-container');
    if (!container) return;
    
    container.innerHTML = messages.map(msg => createMessageHTML(msg)).join('');
}

function appendMessage(message) {
    const container = document.getElementById('messages-container');
    if (!container) return;
    
    container.insertAdjacentHTML('beforeend', createMessageHTML(message));
}

function createMessageHTML(message) {
    const isClient = message.sender_type === 'client';
    const isBot = message.sender_type === 'bot';
    
    const senderClass = isClient ? 'client' : (isBot ? 'bot' : 'attendant');
    const sendingClass = message.sending ? 'sending' : '';
    const failedClass = message.failed ? 'failed' : '';
    
    return `
        <div class="message ${senderClass} ${sendingClass} ${failedClass}" data-id="${message.id}">
            <div class="message-bubble">
                <div class="message-content">${escapeHtml(message.content)}</div>
                <div class="message-time">
                    ${formatTime(message.created_at)}
                    ${message.sending ? '<span class="sending-indicator">⏳</span>' : ''}
                    ${message.failed ? '<span class="failed-indicator">❌</span>' : ''}
                </div>
            </div>
        </div>
    `;
}

// ============================================================================
// UI HELPERS
// ============================================================================

function showLoginScreen() {
    document.getElementById('login-screen').classList.add('active');
    document.getElementById('chat-screen').classList.remove('active');
}

function showChatScreen() {
    document.getElementById('login-screen').classList.remove('active');
    document.getElementById('chat-screen').classList.add('active');
    loadConversations();
}

function showConversationList() {
    document.getElementById('conversation-list-view').classList.add('active');
    document.getElementById('chat-view').classList.remove('active');
    appState.currentConversation = null;
}

function openConversation(id) {
    document.getElementById('conversation-list-view').classList.remove('active');
    document.getElementById('chat-view').classList.add('active');
    loadConversation(id);
}

function showLoading() {
    document.getElementById('loading-overlay')?.classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay')?.classList.remove('active');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function updateConnectionStatus(isOnline) {
    const indicator = document.getElementById('connection-status');
    if (indicator) {
        indicator.className = isOnline ? 'online' : 'offline';
        indicator.textContent = isOnline ? '🟢' : '🔴';
    }
}

function updateQueueBadge(count) {
    const badge = document.getElementById('queue-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    }
}

function showTypingIndicator(isTyping) {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.style.display = isTyping ? 'flex' : 'none';
    }
}

function scrollToBottom() {
    const container = document.getElementById('messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

// ============================================================================
// NOTIFICATIONS
// ============================================================================

async function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        const permission = await Notification.requestPermission();
        console.log('Notification permission:', permission);
    }
}

function showNotification(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/badge.png',
            tag: 'cianet-notification'
        });
    }
}

function playNotificationSound() {
    const audio = document.getElementById('notification-sound');
    if (audio) {
        audio.currentTime = 0;
        audio.play().catch(() => {});
    }
}

// ============================================================================
// OFFLINE SUPPORT
// ============================================================================

async function savePendingMessage(content) {
    const db = await openIndexedDB();
    const tx = db.transaction('pending-messages', 'readwrite');
    const store = tx.objectStore('pending-messages');
    
    store.add({
        conversation_id: appState.currentConversation?.id,
        content,
        token: appState.token,
        timestamp: Date.now()
    });
}

function openIndexedDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('cianet-offline', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('pending-messages')) {
                db.createObjectStore('pending-messages', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

// ============================================================================
// UTILITIES
// ============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getInitials(name) {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'agora';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}min`;
    if (diff < 86400000) return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function updateTempMessage(tempId, realMessage) {
    const el = document.querySelector(`.message[data-id="${tempId}"]`);
    if (el) {
        el.outerHTML = createMessageHTML(realMessage);
    }
}

function markMessageFailed(tempId) {
    const el = document.querySelector(`.message[data-id="${tempId}"]`);
    if (el) {
        el.classList.add('failed');
        el.classList.remove('sending');
        el.querySelector('.sending-indicator')?.remove();
    }
}

function updateConversationPreview(conversationId, message) {
    const el = document.querySelector(`.conversation-item[data-id="${conversationId}"]`);
    if (el) {
        const preview = el.querySelector('.conversation-preview');
        const time = el.querySelector('.time');
        
        if (preview) preview.textContent = message.content;
        if (time) time.textContent = formatTime(message.created_at);
        
        // Mover para o topo
        el.parentElement.prepend(el);
    }
}

// ============================================================================
// EVENT HANDLERS
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Service Worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => console.log('SW registered:', reg.scope))
            .catch(err => console.error('SW registration failed:', err));
    }
    
    // Online/Offline
    window.addEventListener('online', () => {
        appState.isOnline = true;
        updateConnectionStatus(true);
        
        // Trigger background sync
        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
            navigator.serviceWorker.ready.then(reg => {
                reg.sync.register('sync-messages');
            });
        }
    });
    
    window.addEventListener('offline', () => {
        appState.isOnline = false;
        updateConnectionStatus(false);
    });
    
    // Verificar autenticação
    if (appState.token && appState.user) {
        showChatScreen();
        connectWebSocket();
    } else {
        showLoginScreen();
    }
    
    // Request notification permission
    requestNotificationPermission();
    
    // Form handlers
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            login(email, password);
        });
    }
    
    const messageForm = document.getElementById('message-form');
    if (messageForm) {
        messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('message-input');
            const content = input.value.trim();
            
            if (content) {
                sendMessage(content);
                input.value = '';
            }
        });
    }
});

// Exportar funções globais
window.openConversation = openConversation;
window.showConversationList = showConversationList;
window.showChatMenu = () => console.log('Menu');
window.logout = logout;
