// ISP Customer Support - Chat JavaScript

class ChatManager {
    constructor() {
        this.currentConversation = null;
        this.conversations = [];
        this.socket = null;
        this.init();
    }

    async init() {
        await this.loadConversations();
        this.setupEventListeners();
        this.connectWebSocket();
        this.startAutoRefresh();
    }

    // Carregar conversas
    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const data = await response.json();
            this.conversations = data.data || [];
            this.renderConversations();
        } catch (error) {
            console.error('Erro ao carregar conversas:', error);
            this.showNotification('Erro ao carregar conversas', 'error');
        }
    }

    // Renderizar lista de conversas
    renderConversations() {
        const container = document.getElementById('conversations-list');
        if (!container) return;

        container.innerHTML = '';

        // Agrupar por status
        const grouped = this.groupConversationsByStatus();
        
        Object.keys(grouped).forEach(status => {
            if (grouped[status].length > 0) {
                // Header do grupo
                const groupHeader = document.createElement('div');
                groupHeader.className = 'conversation-group-header';
                groupHeader.innerHTML = `
                    <h4>${this.getStatusLabel(status)} (${grouped[status].length})</h4>
                `;
                container.appendChild(groupHeader);

                // Conversas do grupo
                grouped[status].forEach(conv => {
                    const item = this.createConversationItem(conv);
                    container.appendChild(item);
                });
            }
        });
    }

    // Agrupar conversas por status
    groupConversationsByStatus() {
        return {
            'espera': this.conversations.filter(c => c.status === 'waiting'),
            'atribuido': this.conversations.filter(c => c.status === 'assigned'),
            'automacao': this.conversations.filter(c => c.status === 'automation')
        };
    }

    // Criar item de conversa
    createConversationItem(conversation) {
        const item = document.createElement('div');
        item.className = `conversation-item ${conversation.id === this.currentConversation?.id ? 'active' : ''}`;
        item.dataset.conversationId = conversation.id;
        
        const avatar = conversation.customer_name.charAt(0).toUpperCase();
        const statusClass = `status-${conversation.status}`;
        const timeAgo = this.formatTimeAgo(conversation.created_at);
        
        item.innerHTML = `
            <div class="conversation-avatar">${avatar}</div>
            <div class="conversation-info">
                <div class="conversation-name">${conversation.customer_name}</div>
                <div class="conversation-preview">
                    <span class="status-badge ${statusClass}">${this.getStatusLabel(conversation.status)}</span>
                    ${conversation.last_message || 'Sem mensagens'}
                </div>
            </div>
            <div class="conversation-meta">
                <div class="conversation-time">${timeAgo}</div>
                <div class="conversation-count">${conversation.messages_count || 0}</div>
            </div>
        `;

        item.addEventListener('click', () => this.selectConversation(conversation));
        return item;
    }

    // Selecionar conversa
    async selectConversation(conversation) {
        this.currentConversation = conversation;
        
        // Atualizar UI
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-conversation-id="${conversation.id}"]`)?.classList.add('active');

        // Carregar mensagens
        await this.loadMessages(conversation.id);
        this.renderChatHeader(conversation);
    }

    // Carregar mensagens
    async loadMessages(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/messages`);
            const data = await response.json();
            this.renderMessages(data.messages || []);
        } catch (error) {
            console.error('Erro ao carregar mensagens:', error);
            this.showNotification('Erro ao carregar mensagens', 'error');
        }
    }

    // Renderizar header do chat
    renderChatHeader(conversation) {
        const header = document.getElementById('chat-header');
        if (!header) return;

        const avatar = conversation.customer_name.charAt(0).toUpperCase();
        const statusClass = `status-${conversation.status}`;
        
        header.innerHTML = `
            <div class="chat-customer-info">
                <div class="chat-customer-avatar">${avatar}</div>
                <div class="chat-customer-details">
                    <h3>${conversation.customer_name}</h3>
                    <p>
                        <span class="status-badge ${statusClass}">${this.getStatusLabel(conversation.status)}</span>
                        • ${conversation.phone || 'Telefone não informado'}
                    </p>
                </div>
            </div>
            <div class="chat-actions">
                ${this.renderChatActions(conversation)}
            </div>
        `;
    }

    // Renderizar ações do chat
    renderChatActions(conversation) {
        const actions = [];
        
        switch (conversation.status) {
            case 'waiting':
                actions.push(`
                    <button class="btn btn-primary" onclick="chatManager.assignConversation('${conversation.id}')">
                        <i class="fas fa-user-plus"></i> Atribuir
                    </button>
                `);
                break;
                
            case 'assigned':
                actions.push(`
                    <button class="btn btn-success" onclick="chatManager.startAutomation('${conversation.id}')">
                        <i class="fas fa-robot"></i> Automação
                    </button>
                    <button class="btn btn-warning" onclick="chatManager.transferConversation('${conversation.id}')">
                        <i class="fas fa-exchange-alt"></i> Transferir
                    </button>
                `);
                break;
                
            case 'automation':
                actions.push(`
                    <button class="btn btn-primary" onclick="chatManager.takeOverConversation('${conversation.id}')">
                        <i class="fas fa-user"></i> Assumir
                    </button>
                `);
                break;
        }
        
        actions.push(`
            <button class="btn btn-danger" onclick="chatManager.closeConversation('${conversation.id}')">
                <i class="fas fa-times"></i> Encerrar
            </button>
        `);
        
        return actions.join('');
    }

    // Renderizar mensagens
    renderMessages(messages) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        container.innerHTML = '';

        messages.forEach(message => {
            const messageEl = this.createMessageElement(message);
            container.appendChild(messageEl);
        });

        // Scroll para o final
        container.scrollTop = container.scrollHeight;
    }

    // Criar elemento de mensagem
    createMessageElement(message) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${message.sender_type === 'customer' ? 'incoming' : 'outgoing'}`;
        
        const time = new Date(message.created_at).toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageEl.innerHTML = `
            <div class="message-bubble">
                <div class="message-text">${this.escapeHtml(message.content)}</div>
                <div class="message-time">${time}</div>
            </div>
        `;
        
        return messageEl;
    }

    // Ações das conversas
    async assignConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/assign`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.showNotification('Conversa atribuída com sucesso', 'success');
                await this.loadConversations();
            }
        } catch (error) {
            this.showNotification('Erro ao atribuir conversa', 'error');
        }
    }

    async startAutomation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/automate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.showNotification('Automação iniciada', 'success');
                await this.loadConversations();
            }
        } catch (error) {
            this.showNotification('Erro ao iniciar automação', 'error');
        }
    }

    async takeOverConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/takeover`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.showNotification('Conversa assumida', 'success');
                await this.loadConversations();
            }
        } catch (error) {
            this.showNotification('Erro ao assumir conversa', 'error');
        }
    }

    async closeConversation(conversationId) {
        if (!confirm('Tem certeza que deseja encerrar esta conversa?')) return;
        
        try {
            const response = await fetch(`/api/conversations/${conversationId}/close`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.showNotification('Conversa encerrada', 'success');
                await this.loadConversations();
                this.currentConversation = null;
                document.getElementById('chat-header').innerHTML = '';
                document.getElementById('chat-messages').innerHTML = '';
            }
        } catch (error) {
            this.showNotification('Erro ao encerrar conversa', 'error');
        }
    }

    // Enviar mensagem
    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message || !this.currentConversation) return;
        
        try {
            const response = await fetch(`/api/conversations/${this.currentConversation.id}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: message })
            });
            
            if (response.ok) {
                input.value = '';
                await this.loadMessages(this.currentConversation.id);
            }
        } catch (error) {
            this.showNotification('Erro ao enviar mensagem', 'error');
        }
    }

    // Setup event listeners
    setupEventListeners() {
        // Enter para enviar mensagem
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }

        // Botão enviar
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
    }

    // WebSocket connection (desabilitado temporariamente)
    connectWebSocket() {
        console.log('WebSocket desabilitado temporariamente');
        // try {
        //     const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        //     const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
        //     
        //     this.socket = new WebSocket(wsUrl);
        //     
        //     this.socket.onopen = () => {
        //         console.log('WebSocket conectado');
        //     };
        //     
        //     this.socket.onmessage = (event) => {
        //         const data = JSON.parse(event.data);
        //         this.handleWebSocketMessage(data);
        //     };
        //     
        //     this.socket.onclose = () => {
        //         console.log('WebSocket desconectado');
        //         // Tentar reconectar após 5 segundos
        //         setTimeout(() => this.connectWebSocket(), 5000);
        //     };
        // } catch (error) {
        //     console.error('Erro ao conectar WebSocket:', error);
        // }
    }

    // Handle WebSocket messages
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'new_message':
                if (this.currentConversation?.id === data.conversation_id) {
                    this.loadMessages(data.conversation_id);
                }
                this.loadConversations(); // Atualizar lista
                break;
                
            case 'conversation_updated':
                this.loadConversations();
                break;
        }
    }

    // Auto refresh
    startAutoRefresh() {
        setInterval(() => {
            this.loadConversations();
        }, 30000); // Atualizar a cada 30 segundos
    }

    // Utility functions
    getStatusLabel(status) {
        const labels = {
            'waiting': 'Espera',
            'assigned': 'Atribuído',
            'automation': 'Automação',
            'closed': 'Encerrado'
        };
        return labels[status] || status;
    }

    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (days > 0) return `${days}d`;
        if (hours > 0) return `${hours}h`;
        if (minutes > 0) return `${minutes}m`;
        return 'agora';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        // Criar notificação
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Adicionar ao DOM
        document.body.appendChild(notification);
        
        // Remover após 3 segundos
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Inicializar quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
    window.chatManager = new ChatManager();
});

// Funções globais para os botões
window.assignConversation = (id) => window.chatManager.assignConversation(id);
window.startAutomation = (id) => window.chatManager.startAutomation(id);
window.takeOverConversation = (id) => window.chatManager.takeOverConversation(id);
window.closeConversation = (id) => window.chatManager.closeConversation(id);