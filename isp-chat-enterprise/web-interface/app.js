/**
 * ISP Chat - Sistema de Atendimento Enterprise
 * JavaScript principal da aplicação web
 */

class ISPChatApp {
    constructor() {
        // URLs dos serviços - usando API Gateway
        this.gatewayUrl = 'http://localhost:8000';  // API Gateway
        this.authUrl = `${this.gatewayUrl}/api/auth`;
        this.chatUrl = `${this.gatewayUrl}/api/chat`;
        this.wsUrl = 'ws://localhost:8002/ws';  // WebSocket direto
        this.token = localStorage.getItem('auth_token');
        this.currentUser = null;
        this.currentConversation = null;
        this.websocket = null;
        this.charts = {};
        
        this.init();
    }

    async init() {
        console.log('🚀 Iniciando ISP Chat App...');
        console.log('🔧 URLs configuradas:', {
            gatewayUrl: this.gatewayUrl,
            authUrl: this.authUrl,
            chatUrl: this.chatUrl,
            wsUrl: this.wsUrl
        });
        
        // Configurar axios
        this.setupAxios();
        
        // Verificar autenticação
        if (this.token) {
            console.log('🔑 Token encontrado, verificando...');
            await this.verifyToken();
        } else {
            console.log('🔐 Nenhum token encontrado, mostrando login');
            this.showLogin();
        }
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Esconder loading
        setTimeout(() => {
            const loadingScreen = document.getElementById('loading-screen');
            if (loadingScreen) {
                loadingScreen.classList.add('hidden');
                console.log('✅ Tela de loading escondida');
            }
        }, 1500);
    }

    setupAxios() {
        // Configurar interceptors do axios
        axios.defaults.timeout = 10000;
        
        axios.interceptors.request.use(
            (config) => {
                if (this.token) {
                    config.headers.Authorization = `Bearer ${this.token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        axios.interceptors.response.use(
            (response) => response,
            (error) => {
                if (error.response?.status === 401) {
                    this.logout();
                }
                return Promise.reject(error);
            }
        );
    }

    async verifyToken() {
        try {
            const response = await axios.post(`${this.authUrl}/verify`, {}, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            
            if (response.data.valid) {
                this.currentUser = response.data.user;
                this.showApp();
                this.loadDashboard();
            } else {
                console.error('Token inválido');
                this.logout();
            }
        } catch (error) {
            console.error('Token inválido:', error);
            this.logout();
        }
    }

    setupEventListeners() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });

        // Sidebar navigation
        document.querySelectorAll('.sidebar-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.dataset.section;
                this.navigateToSection(section);
            });
        });

        // Sidebar toggle (mobile)
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

        // Message input
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        document.getElementById('send-message').addEventListener('click', () => {
            this.sendMessage();
        });

        // Filters
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.applyMessageFilters();
        });

        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearMessageFilters();
        });

        // QR Code generation
        document.getElementById('generate-qr').addEventListener('click', () => {
            this.generateQRCode();
        });
    }

    async login() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        console.log('🔐 Tentando login...', { username, password: '***' });

        if (!username || !password) {
            this.showNotification('Preencha todos os campos', 'error');
            return;
        }

        try {
            console.log('📡 Fazendo requisição para:', `${this.authUrl}/login`);
            
            const response = await fetch(`${this.authUrl}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username,
                    password
                })
            });

            console.log('📥 Resposta recebida:', response.status);

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Login bem-sucedido!', data.user?.username);

                this.token = data.access_token;
                this.currentUser = data.user;
                
                localStorage.setItem('auth_token', this.token);
                
                this.showNotification('Login realizado com sucesso!', 'success');
                this.showApp();
                this.loadDashboard();
            } else {
                const errorData = await response.json();
                console.error('❌ Erro no login:', errorData);
                this.showNotification(
                    errorData.detail || 'Erro no login', 
                    'error'
                );
            }
            
        } catch (error) {
            console.error('❌ Erro na requisição:', error);
            this.showNotification(
                'Erro de conexão. Verifique se os serviços estão rodando.', 
                'error'
            );
        }
    }

    logout() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('auth_token');
        
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.showLogin();
        this.showNotification('Logout realizado com sucesso!', 'info');
    }

    showLogin() {
        console.log('🔐 Mostrando tela de login');
        const app = document.getElementById('app');
        const loginModal = document.getElementById('login-modal');
        
        if (app) app.classList.add('hidden');
        if (loginModal) {
            loginModal.classList.remove('hidden');
            console.log('✅ Modal de login exibido');
        } else {
            console.error('❌ Modal de login não encontrado!');
        }
    }

    showApp() {
        console.log('🏠 Mostrando aplicação principal');
        const loginModal = document.getElementById('login-modal');
        const app = document.getElementById('app');
        
        if (loginModal) loginModal.classList.add('hidden');
        if (app) {
            app.classList.remove('hidden');
            console.log('✅ Aplicação principal exibida');
        } else {
            console.error('❌ Elemento app não encontrado!');
        }
        
        // Atualizar informações do usuário
        if (this.currentUser) {
            const userNameEl = document.getElementById('user-name');
            const userRoleEl = document.getElementById('user-role');
            
            if (userNameEl) userNameEl.textContent = this.currentUser.username;
            if (userRoleEl) userRoleEl.textContent = this.getRoleDisplayName(this.currentUser.role);
            
            console.log('✅ Informações do usuário atualizadas');
        }
    }

    getRoleDisplayName(role) {
        const roles = {
            'admin': 'Administrador',
            'supervisor': 'Supervisor',
            'agent': 'Agente',
            'viewer': 'Visualizador'
        };
        return roles[role] || role;
    }

    navigateToSection(section) {
        // Atualizar sidebar ativo
        document.querySelectorAll('.sidebar-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-section="${section}"]`).classList.add('active');

        // Esconder todas as seções
        document.querySelectorAll('main section').forEach(sec => {
            sec.classList.add('hidden');
        });

        // Mostrar seção selecionada
        document.getElementById(`${section}-section`).classList.remove('hidden');

        // Carregar dados da seção
        switch (section) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'chat':
                this.loadChat();
                break;
            case 'campaigns':
                this.loadCampaigns();
                break;
            case 'whatsapp':
                this.loadWhatsApp();
                break;
            case 'messages':
                this.loadMessages();
                break;
            case 'users':
                this.loadUsers();
                break;
            case 'settings':
                this.loadSettings();
                break;
        }
    }

    async loadDashboard() {
        try {
            // Usar endpoint de teste para estatísticas
            const statsResponse = await axios.get(`${this.chatUrl}/test/conversations`);
            const stats = statsResponse.data;

            // Atualizar métricas básicas
            document.getElementById('total-conversations').textContent = stats.total || 0;
            document.getElementById('avg-response-time').textContent = '45s';
            document.getElementById('satisfaction-rate').textContent = '94%';
            document.getElementById('total-agents').textContent = '3';
            document.getElementById('agents-online').textContent = '2';

            // Carregar conversas recentes
            await this.loadRecentConversations();

            // Criar gráficos
            this.createCharts();

        } catch (error) {
            console.error('Erro ao carregar dashboard:', error);
            this.showNotification('Erro ao carregar dashboard', 'error');
        }
    }

    async loadRecentConversations() {
        try {
            const response = await axios.get(`${this.chatUrl}/test/conversations`);
            const conversations = response.data.conversations || [];

            const tbody = document.getElementById('recent-conversations');
            tbody.innerHTML = '';

            conversations.slice(0, 10).forEach(conv => {
                const row = document.createElement('tr');
                row.className = 'border-b border-gray-100 hover:bg-gray-50';
                
                row.innerHTML = `
                    <td class="py-3 px-4">
                        <div>
                            <div class="font-medium text-gray-800">${conv.customer_name || 'Cliente'}</div>
                            <div class="text-sm text-gray-600">${conv.customer_phone}</div>
                        </div>
                    </td>
                    <td class="py-3 px-4">
                        <span class="text-gray-600">${conv.agent_name || 'Não atribuído'}</span>
                    </td>
                    <td class="py-3 px-4">
                        <span class="status-badge ${this.getStatusClass(conv.status)}">${this.getStatusText(conv.status)}</span>
                    </td>
                    <td class="py-3 px-4">
                        <div class="flex items-center gap-2">
                            <i class="fab fa-whatsapp text-green-600"></i>
                            <span class="text-sm text-gray-600">WhatsApp</span>
                        </div>
                    </td>
                    <td class="py-3 px-4">
                        <span class="text-sm text-gray-600">${this.formatDate(conv.updated_at)}</span>
                    </td>
                    <td class="py-3 px-4">
                        <button class="text-blue-600 hover:text-blue-800" onclick="app.openConversation('${conv.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                `;
                
                tbody.appendChild(row);
            });

        } catch (error) {
            console.error('Erro ao carregar conversas recentes:', error);
        }
    }

    createCharts() {
        // Gráfico de conversas por hora
        const conversationsCtx = document.getElementById('conversations-chart').getContext('2d');
        
        if (this.charts.conversations) {
            this.charts.conversations.destroy();
        }

        this.charts.conversations = new Chart(conversationsCtx, {
            type: 'line',
            data: {
                labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                datasets: [{
                    label: 'Conversas',
                    data: [12, 8, 25, 45, 38, 22],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Gráfico de canais
        const channelsCtx = document.getElementById('channels-chart').getContext('2d');
        
        if (this.charts.channels) {
            this.charts.channels.destroy();
        }

        this.charts.channels = new Chart(channelsCtx, {
            type: 'doughnut',
            data: {
                labels: ['WhatsApp', 'Web Chat', 'Email'],
                datasets: [{
                    data: [75, 20, 5],
                    backgroundColor: [
                        '#25D366',
                        '#667eea',
                        '#f59e0b'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    async loadChat() {
        try {
            // Carregar lista de conversas
            const response = await axios.get(`${this.chatUrl}/conversations`);
            const conversations = response.data.conversations || [];

            const conversationsList = document.getElementById('conversations-list');
            conversationsList.innerHTML = '';

            conversations.forEach(conv => {
                const item = document.createElement('div');
                item.className = 'p-4 border-b border-gray-200 hover:bg-gray-50 cursor-pointer';
                item.onclick = () => this.selectConversation(conv);
                
                item.innerHTML = `
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
                            <i class="fas fa-user text-gray-600"></i>
                        </div>
                        <div class="flex-1">
                            <div class="flex items-center justify-between">
                                <h4 class="font-medium text-gray-800">${conv.customer_name || 'Cliente'}</h4>
                                <span class="text-xs text-gray-500">${this.formatTime(conv.updated_at)}</span>
                            </div>
                            <p class="text-sm text-gray-600">${conv.customer_phone}</p>
                            <div class="flex items-center gap-2 mt-1">
                                <span class="status-badge ${this.getStatusClass(conv.status)}">${this.getStatusText(conv.status)}</span>
                            </div>
                        </div>
                    </div>
                `;
                
                conversationsList.appendChild(item);
            });

        } catch (error) {
            console.error('Erro ao carregar chat:', error);
            this.showNotification('Erro ao carregar conversas', 'error');
        }
    }

    async selectConversation(conversation) {
        this.currentConversation = conversation;
        
        // Atualizar header do chat
        document.getElementById('chat-customer-name').textContent = conversation.customer_name || 'Cliente';
        document.getElementById('chat-customer-phone').textContent = conversation.customer_phone;
        document.getElementById('chat-status').textContent = this.getStatusText(conversation.status);
        document.getElementById('chat-status').className = `status-badge ${this.getStatusClass(conversation.status)}`;

        // Carregar mensagens
        await this.loadConversationMessages(conversation.id);

        // Conectar WebSocket
        this.connectWebSocket(conversation.id);
    }

    async loadConversationMessages(conversationId) {
        try {
            const response = await axios.get(`${this.chatUrl}/conversations/${conversationId}/messages`);
            const messages = response.data.messages || [];

            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML = '';

            messages.forEach(message => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-bubble ${message.direction}`;
                
                messageDiv.innerHTML = `
                    <div class="mb-1">
                        <strong>${message.sender_name || 'Sistema'}</strong>
                        <span class="text-xs opacity-75 ml-2">${this.formatTime(message.created_at)}</span>
                    </div>
                    <div>${message.content}</div>
                `;
                
                chatMessages.appendChild(messageDiv);
            });

            // Scroll para o final
            chatMessages.scrollTop = chatMessages.scrollHeight;

        } catch (error) {
            console.error('Erro ao carregar mensagens:', error);
        }
    }

    connectWebSocket(conversationId) {
        if (this.websocket) {
            this.websocket.close();
        }

        this.websocket = new WebSocket(`${this.wsUrl}/${conversationId}`);
        
        this.websocket.onopen = () => {
            console.log('WebSocket conectado');
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'new_message') {
                this.addMessageToChat(data.message);
            }
        };

        this.websocket.onclose = () => {
            console.log('WebSocket desconectado');
        };

        this.websocket.onerror = (error) => {
            console.error('Erro no WebSocket:', error);
        };
    }

    addMessageToChat(message) {
        const chatMessages = document.getElementById('chat-messages');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-bubble ${message.direction}`;
        
        messageDiv.innerHTML = `
            <div class="mb-1">
                <strong>${message.sender_name || 'Sistema'}</strong>
                <span class="text-xs opacity-75 ml-2">${this.formatTime(message.created_at)}</span>
            </div>
            <div>${message.content}</div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const content = input.value.trim();

        if (!content || !this.currentConversation) {
            return;
        }

        try {
            await axios.post(`${this.chatUrl}/conversations/${this.currentConversation.id}/messages`, {
                content,
                message_type: 'text',
                direction: 'outbound'
            });

            input.value = '';

        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            this.showNotification('Erro ao enviar mensagem', 'error');
        }
    }

    async loadCampaigns() {
        try {
            // Simular dados de campanhas
            const campaigns = [
                {
                    id: '1',
                    name: 'Promoção Black Friday',
                    status: 'active',
                    sent: 1250,
                    delivered: 1180,
                    opened: 890,
                    clicked: 234
                },
                {
                    id: '2',
                    name: 'Boas-vindas Novos Clientes',
                    status: 'active',
                    sent: 450,
                    delivered: 445,
                    opened: 320,
                    clicked: 89
                },
                {
                    id: '3',
                    name: 'Pesquisa de Satisfação',
                    status: 'completed',
                    sent: 800,
                    delivered: 785,
                    opened: 456,
                    clicked: 123
                }
            ];

            const campaignsGrid = document.getElementById('campaigns-grid');
            campaignsGrid.innerHTML = '';

            campaigns.forEach(campaign => {
                const card = document.createElement('div');
                card.className = 'card p-6';
                
                card.innerHTML = `
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="font-semibold text-gray-800">${campaign.name}</h3>
                        <span class="status-badge ${this.getCampaignStatusClass(campaign.status)}">${this.getCampaignStatusText(campaign.status)}</span>
                    </div>
                    
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="text-gray-600">Enviadas:</span>
                            <span class="font-medium">${campaign.sent}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Entregues:</span>
                            <span class="font-medium">${campaign.delivered}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Abertas:</span>
                            <span class="font-medium">${campaign.opened}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Cliques:</span>
                            <span class="font-medium">${campaign.clicked}</span>
                        </div>
                    </div>
                    
                    <div class="mt-4 pt-4 border-t border-gray-200">
                        <div class="flex gap-2">
                            <button class="btn btn-secondary btn-sm flex-1">
                                <i class="fas fa-eye"></i>
                                Ver
                            </button>
                            <button class="btn btn-primary btn-sm flex-1">
                                <i class="fas fa-edit"></i>
                                Editar
                            </button>
                        </div>
                    </div>
                `;
                
                campaignsGrid.appendChild(card);
            });

        } catch (error) {
            console.error('Erro ao carregar campanhas:', error);
            this.showNotification('Erro ao carregar campanhas', 'error');
        }
    }

    async loadWhatsApp() {
        try {
            // Simular números conectados
            const numbers = [
                {
                    id: '1',
                    phone: '+55 11 99999-9999',
                    name: 'Atendimento Principal',
                    status: 'connected',
                    lastSeen: new Date()
                },
                {
                    id: '2',
                    phone: '+55 11 88888-8888',
                    name: 'Suporte Técnico',
                    status: 'disconnected',
                    lastSeen: new Date(Date.now() - 3600000)
                }
            ];

            const numbersContainer = document.getElementById('whatsapp-numbers');
            numbersContainer.innerHTML = '';

            numbers.forEach(number => {
                const item = document.createElement('div');
                item.className = 'flex items-center justify-between p-4 border border-gray-200 rounded-lg';
                
                item.innerHTML = `
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                            <i class="fab fa-whatsapp text-green-600 text-xl"></i>
                        </div>
                        <div>
                            <h4 class="font-medium text-gray-800">${number.name}</h4>
                            <p class="text-sm text-gray-600">${number.phone}</p>
                            <p class="text-xs text-gray-500">Última vez: ${this.formatDate(number.lastSeen)}</p>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-3">
                        <span class="status-badge ${number.status === 'connected' ? 'status-online' : 'status-offline'}">
                            ${number.status === 'connected' ? 'Conectado' : 'Desconectado'}
                        </span>
                        <button class="text-gray-600 hover:text-gray-800">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                    </div>
                `;
                
                numbersContainer.appendChild(item);
            });

        } catch (error) {
            console.error('Erro ao carregar WhatsApp:', error);
            this.showNotification('Erro ao carregar números WhatsApp', 'error');
        }
    }

    async generateQRCode() {
        try {
            // Simular geração de QR Code
            const qrContainer = document.getElementById('qr-code');
            qrContainer.innerHTML = '<div class="loading"></div>';
            
            setTimeout(() => {
                qrContainer.innerHTML = `
                    <img src="https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=whatsapp-connection-${Date.now()}" 
                         alt="QR Code" class="w-full h-full object-contain">
                `;
            }, 2000);

            this.showNotification('QR Code gerado com sucesso!', 'success');

        } catch (error) {
            console.error('Erro ao gerar QR Code:', error);
            this.showNotification('Erro ao gerar QR Code', 'error');
        }
    }

    async loadMessages() {
        try {
            // Carregar agentes para filtro
            const agentsResponse = await axios.get(`${this.authUrl}/users?role=agent`);
            const agents = agentsResponse.data.users || [];

            const agentSelect = document.getElementById('filter-agent');
            agentSelect.innerHTML = '<option value="">Todos os Atendentes</option>';
            
            agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id;
                option.textContent = agent.username;
                agentSelect.appendChild(option);
            });

            // Carregar mensagens iniciais
            await this.loadMessagesData();

        } catch (error) {
            console.error('Erro ao carregar mensagens:', error);
            this.showNotification('Erro ao carregar mensagens', 'error');
        }
    }

    async loadMessagesData(filters = {}) {
        try {
            // Simular dados de mensagens
            const messages = [
                {
                    id: '1',
                    created_at: new Date(),
                    customer_name: 'João Silva',
                    customer_phone: '+55 11 99999-9999',
                    agent_name: 'Maria Santos',
                    channel: 'whatsapp',
                    content: 'Olá, preciso de ajuda com meu plano',
                    status: 'delivered'
                },
                {
                    id: '2',
                    created_at: new Date(Date.now() - 3600000),
                    customer_name: 'Ana Costa',
                    customer_phone: '+55 11 88888-8888',
                    agent_name: 'Pedro Oliveira',
                    channel: 'whatsapp',
                    content: 'Quando será instalado meu serviço?',
                    status: 'read'
                }
            ];

            const messagesTable = document.getElementById('messages-table');
            messagesTable.innerHTML = '';

            messages.forEach(message => {
                const row = document.createElement('tr');
                row.className = 'border-b border-gray-100 hover:bg-gray-50';
                
                row.innerHTML = `
                    <td class="py-3 px-4">
                        <div class="text-sm">
                            <div class="font-medium text-gray-800">${this.formatDate(message.created_at)}</div>
                            <div class="text-gray-600">${this.formatTime(message.created_at)}</div>
                        </div>
                    </td>
                    <td class="py-3 px-4">
                        <div>
                            <div class="font-medium text-gray-800">${message.customer_name}</div>
                            <div class="text-sm text-gray-600">${message.customer_phone}</div>
                        </div>
                    </td>
                    <td class="py-3 px-4">
                        <span class="text-gray-600">${message.agent_name}</span>
                    </td>
                    <td class="py-3 px-4">
                        <div class="flex items-center gap-2">
                            <i class="fab fa-whatsapp text-green-600"></i>
                            <span class="text-sm text-gray-600">WhatsApp</span>
                        </div>
                    </td>
                    <td class="py-3 px-4">
                        <div class="max-w-xs truncate text-sm text-gray-600">${message.content}</div>
                    </td>
                    <td class="py-3 px-4">
                        <span class="status-badge ${this.getMessageStatusClass(message.status)}">${this.getMessageStatusText(message.status)}</span>
                    </td>
                    <td class="py-3 px-4">
                        <button class="text-blue-600 hover:text-blue-800">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                `;
                
                messagesTable.appendChild(row);
            });

            // Atualizar contador
            document.getElementById('messages-count').textContent = `${messages.length} mensagens`;

        } catch (error) {
            console.error('Erro ao carregar dados de mensagens:', error);
        }
    }

    applyMessageFilters() {
        const filters = {
            customer: document.getElementById('filter-customer').value,
            agent: document.getElementById('filter-agent').value,
            channel: document.getElementById('filter-channel').value,
            date: document.getElementById('filter-date').value
        };

        this.loadMessagesData(filters);
        this.showNotification('Filtros aplicados', 'info');
    }

    clearMessageFilters() {
        document.getElementById('filter-customer').value = '';
        document.getElementById('filter-agent').value = '';
        document.getElementById('filter-channel').value = '';
        document.getElementById('filter-date').value = '';

        this.loadMessagesData();
        this.showNotification('Filtros limpos', 'info');
    }

    async loadUsers() {
        try {
            const response = await axios.get(`${this.authUrl}/users`);
            const users = response.data.users || [];

            const usersTable = document.getElementById('users-table');
            usersTable.innerHTML = '';

            users.forEach(user => {
                const row = document.createElement('tr');
                row.className = 'border-b border-gray-100 hover:bg-gray-50';
                
                row.innerHTML = `
                    <td class="py-3 px-4">
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                                <i class="fas fa-user text-gray-600 text-sm"></i>
                            </div>
                            <span class="font-medium text-gray-800">${user.username}</span>
                        </div>
                    </td>
                    <td class="py-3 px-4">
                        <span class="text-gray-600">${user.email}</span>
                    </td>
                    <td class="py-3 px-4">
                        <span class="text-gray-600">${this.getRoleDisplayName(user.role)}</span>
                    </td>
                    <td class="py-3 px-4">
                        <span class="status-badge ${user.is_active ? 'status-online' : 'status-offline'}">
                            ${user.is_active ? 'Ativo' : 'Inativo'}
                        </span>
                    </td>
                    <td class="py-3 px-4">
                        <span class="text-sm text-gray-600">${user.last_login ? this.formatDate(user.last_login) : 'Nunca'}</span>
                    </td>
                    <td class="py-3 px-4">
                        <div class="flex gap-2">
                            <button class="text-blue-600 hover:text-blue-800">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="text-red-600 hover:text-red-800">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                `;
                
                usersTable.appendChild(row);
            });

        } catch (error) {
            console.error('Erro ao carregar usuários:', error);
            this.showNotification('Erro ao carregar usuários', 'error');
        }
    }

    loadSettings() {
        // Configurações já estão no HTML
        console.log('Configurações carregadas');
    }

    // Utility methods
    getStatusClass(status) {
        const classes = {
            'waiting': 'status-busy',
            'in_progress': 'status-online',
            'resolved': 'status-online',
            'closed': 'status-offline'
        };
        return classes[status] || 'status-offline';
    }

    getStatusText(status) {
        const texts = {
            'waiting': 'Aguardando',
            'in_progress': 'Em Andamento',
            'resolved': 'Resolvida',
            'closed': 'Fechada'
        };
        return texts[status] || status;
    }

    getCampaignStatusClass(status) {
        const classes = {
            'active': 'status-online',
            'paused': 'status-busy',
            'completed': 'status-offline'
        };
        return classes[status] || 'status-offline';
    }

    getCampaignStatusText(status) {
        const texts = {
            'active': 'Ativa',
            'paused': 'Pausada',
            'completed': 'Concluída'
        };
        return texts[status] || status;
    }

    getMessageStatusClass(status) {
        const classes = {
            'sent': 'status-busy',
            'delivered': 'status-online',
            'read': 'status-online',
            'failed': 'status-offline'
        };
        return classes[status] || 'status-offline';
    }

    getMessageStatusText(status) {
        const texts = {
            'sent': 'Enviada',
            'delivered': 'Entregue',
            'read': 'Lida',
            'failed': 'Falhou'
        };
        return texts[status] || status;
    }

    formatDate(date) {
        if (!date) return '-';
        return new Date(date).toLocaleDateString('pt-BR');
    }

    formatTime(date) {
        if (!date) return '-';
        return new Date(date).toLocaleTimeString('pt-BR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    showNotification(message, type = 'info') {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.classList.add('show');

        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }

    async testConnection() {
        console.log('🔧 Testando conexão com os serviços...');
        
        const services = [
            { name: 'API Gateway', url: `${this.gatewayUrl}/health` },
            { name: 'Auth Service', url: `${this.authUrl}/health` },
            { name: 'Chat Service', url: `${this.chatUrl}/health` }
        ];
        
        let allOk = true;
        let message = '🔍 TESTE DE CONECTIVIDADE:\n\n';
        
        for (const service of services) {
            try {
                const response = await fetch(service.url, { 
                    method: 'GET',
                    timeout: 5000 
                });
                
                if (response.ok) {
                    const data = await response.json();
                    message += `✅ ${service.name}: ${data.status || 'OK'}\n`;
                    console.log(`✅ ${service.name} OK`);
                } else {
                    message += `❌ ${service.name}: HTTP ${response.status}\n`;
                    console.error(`❌ ${service.name} falhou:`, response.status);
                    allOk = false;
                }
            } catch (error) {
                message += `❌ ${service.name}: ${error.message}\n`;
                console.error(`❌ ${service.name} erro:`, error);
                allOk = false;
            }
        }
        
        if (allOk) {
            message += '\n🎉 Todos os serviços estão funcionando!';
            this.showNotification('Conexão OK! Serviços funcionando.', 'success');
        } else {
            message += '\n⚠️ Alguns serviços não estão respondendo.';
            this.showNotification('Problemas de conexão detectados.', 'warning');
        }
        
        console.log(message);
        alert(message);
    }

    openConversation(conversationId) {
        // Navegar para seção de chat e abrir conversa
        this.navigateToSection('chat');
        
        // Buscar e selecionar a conversa
        setTimeout(async () => {
            try {
                const response = await fetch(`${this.chatUrl}/conversations/${conversationId}`, {
                    headers: {
                        'Authorization': `Bearer ${this.token}`
                    }
                });
                if (response.ok) {
                    const conversation = await response.json();
                    this.selectConversation(conversation);
                }
            } catch (error) {
                console.error('Erro ao abrir conversa:', error);
            }
        }, 500);
    }
}

// Inicializar aplicação quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ISPChatApp();
});

// Adicionar estilos para botões pequenos
const style = document.createElement('style');
style.textContent = `
    .btn-sm {
        padding: 8px 16px;
        font-size: 14px;
    }
`;
document.head.appendChild(style);