// ...existing code...
let isConnected = false;
let activeChatNumber = null;
let conversations = {}; // histórico por número

// DOM refs (pre-declared to be assigned on DOMContentLoaded)
let statusText, statusEl, btnSettings, settingsModal, btnCancelSettings, connectionForm, inputToken, inputPhoneId, btnConnect;
let conversationsContainer, mensagensDiv, chatForm, chatHeader, activeChatName, activeChatNumberEl, mensagemInput, placeholderChat;
let btnGenerateQR, btnConnectQR, qrcodeImage, qrcodeMessage;
const btnHistory = document.getElementById('btn-history-search'); // Ref do novo botão
btnHistory && btnHistory.addEventListener('click', () => {
    window.whatsappAPI.openHistorySearch();
});

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Refs ---
    statusText = document.getElementById('status-text');
    statusEl = document.getElementById('connection-status');
    btnSettings = document.getElementById('btn-settings');
    settingsModal = document.getElementById('settings-modal');
    btnCancelSettings = document.getElementById('btn-cancel-settings');
    connectionForm = document.getElementById('connection-form');
    inputToken = document.getElementById('input-token');
    inputPhoneId = document.getElementById('input-phone-id');
    btnConnect = document.getElementById('btn-connect');
    conversationsContainer = document.getElementById('conversations-container');
    mensagensDiv = document.getElementById('mensagens');
    chatForm = document.getElementById('chat-form');
    chatHeader = document.getElementById('chat-header');
    activeChatName = document.getElementById('active-chat-name');
    activeChatNumberEl = document.getElementById('active-chat-number');
    mensagemInput = document.getElementById('mensagem-input');
    placeholderChat = document.getElementById('placeholder-chat');

    // QR refs
    btnGenerateQR = document.getElementById('btn-generate-qr');
    btnConnectQR = document.getElementById('btn-connect-qr');
    qrcodeImage = document.getElementById('qrcode-image');
    qrcodeMessage = document.getElementById('qrcode-message');

    // --- Event listeners ---
    btnSettings && btnSettings.addEventListener('click', () => settingsModal.classList.remove('hidden'));
    btnCancelSettings && btnCancelSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));

    connectionForm && connectionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const token = inputToken.value.trim();
        const phoneId = inputPhoneId.value.trim();
        if (!token || !phoneId) return;
        btnConnect.textContent = 'Conectando...';
        try {
            const resultado = await window.whatsappAPI.configurarCredenciais(token, phoneId);
            if (resultado && resultado.sucesso) {
                updateConnectionStatus(true);
                settingsModal.classList.add('hidden');
                await loadAndDisplayChats();
            } else {
                console.error('Erro de conexão:', resultado && resultado.erro);
                updateConnectionStatus(false);
            }
        } catch (err) {
            console.error('Erro interno ao configurar credenciais:', err);
            updateConnectionStatus(false);
        } finally {
            btnConnect.textContent = 'Conectar API';
        }
    });

    // QR Flow: iniciar
    btnGenerateQR && btnGenerateQR.addEventListener('click', async () => {
        btnGenerateQR.textContent = 'Gerando...';
        btnGenerateQR.disabled = true;
        qrcodeMessage && (qrcodeMessage.textContent = 'Aguarde a geração do QR Code...');
        btnGenerateQR && btnGenerateQR.classList.add('hidden');
        try {
            const resultado = await window.whatsappAPI.iniciarConexaoQRCode();
            console.log('QR Flow iniciado:', resultado);
            qrcodeMessage && (qrcodeMessage.textContent = 'Inicialização bem-sucedida. Aguardando o QR Code...');
            qrcodeImage && qrcodeImage.classList.add('hidden');
            btnConnectQR && btnConnectQR.classList.add('hidden');
        } catch (err) {
            console.error('Falha ao iniciar QR Flow:', err);
            qrcodeMessage && (qrcodeMessage.textContent = `[ERRO] Falha ao iniciar QR Flow: ${err.message || err}`);
            if (btnGenerateQR) {
                btnGenerateQR.textContent = 'Gerar Código QR';
                btnGenerateQR.disabled = false;
                btnGenerateQR.classList.remove('hidden');
            }
        }
    });

    btnConnectQR && btnConnectQR.addEventListener('click', () => settingsModal.classList.add('hidden'));

    // Send message
    chatForm && chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!isConnected || !activeChatNumber) return;
        const texto = mensagemInput.value.trim();
        if (!texto) return;
        addMessageToHistory(activeChatNumber, { texto }, 'Eu', false);
        mensagemInput.value = '';
        try {
            const resultado = await window.whatsappAPI.enviarMensagem(activeChatNumber, texto);
            if (resultado && resultado.sucesso) {
                console.log('Mensagem enviada:', resultado.dados);
            } else {
                addMessageToHistory(activeChatNumber, { texto: `[ERRO] Falha no envio: ${resultado && resultado.erro ? resultado.erro : 'erro'}` }, 'Sistema', false);
            }
        } catch (err) {
            addMessageToHistory(activeChatNumber, { texto: `[ERRO] Falha interna: ${err.message}` }, 'Sistema', false);
        }
    });

    // IPC listeners
    window.whatsappAPI && window.whatsappAPI.onNovaMensagemRecebida && window.whatsappAPI.onNovaMensagemRecebida((novaMensagem) => {
        try {
            const num = novaMensagem.number || (novaMensagem.from ? novaMensagem.from.split('@')[0] : 'unknown');
            addMessageToHistory(num, novaMensagem, novaMensagem.name || 'Cliente', true);
        } catch (err) {
            console.error('Erro ao processar nova mensagem:', err);
        }
    });

    window.whatsappAPI && window.whatsappAPI.onQRCodeReceived && window.whatsappAPI.onQRCodeReceived((qrDataURL) => {
        try {
            if (qrcodeImage) {
                qrcodeImage.src = qrDataURL;
                qrcodeImage.classList.remove('hidden');
            }
            if (qrcodeMessage) qrcodeMessage.textContent = 'Escaneie o código com seu celular. Não feche esta tela!';
            if (btnGenerateQR) {
                btnGenerateQR.textContent = 'Aguardando Escaneamento...';
                btnGenerateQR.disabled = true;
                btnGenerateQR.classList.add('hidden');
            }
            if (btnConnectQR) {
                btnConnectQR.classList.remove('hidden');
                btnConnectQR.textContent = 'Aguardando Escaneamento...';
            }
        } catch (err) {
            console.error('Erro ao exibir QR:', err);
        }
    });

    window.whatsappAPI && window.whatsappAPI.onWhatsappReady && window.whatsappAPI.onWhatsappReady(handleWhatsappReady);

    // Initial UI state
    updateConnectionStatus(isConnected);
    // Removida a tentativa antecipada de carregar chats aqui.
    // O loadAndDisplayChats() será chamado apenas por handleWhatsappReady após conexão bem-sucedida.
});

// -------------------- Utilities & Core Functions (single implementations) --------------------

function updateConnectionStatus(connected) {
    isConnected = !!connected;
    if (statusText) {
        statusText.textContent = isConnected ? '✅ Conectado' : '❌ Desconectado';
        statusText.classList.toggle('text-green-600', isConnected);
        statusText.classList.toggle('text-red-600', !isConnected);
    }
    if (statusEl) {
        statusEl.classList.toggle('bg-green-100', isConnected);
        statusEl.classList.toggle('bg-red-100', !isConnected);
    }
    // 🚨 chamada a renderConversationsList() removida intencionalmente
}

function renderConversationsList() {
    if (!conversationsContainer) return;
    conversationsContainer.innerHTML = '';
    const sorted = Object.keys(conversations).sort((a, b) => (conversations[b].unread || 0) - (conversations[a].unread || 0));
    sorted.forEach(number => {
        const convo = conversations[number];
        const item = createConversationListItem(convo);
        conversationsContainer.appendChild(item);
    });
}

function createConversationListItem(convo) {
    const number = convo.number;
    const isActive = number === activeChatNumber;
    const last = convo.lastMessage || (convo.history && convo.history.length ? convo.history[convo.history.length - 1].texto : 'Nova conversa');
    const avatarUrl = convo.profilePicUrl || 'https://via.placeholder.com/40/CCCCCC/808080?text=C';

    const item = document.createElement('div');
    item.dataset.number = number;
    item.className = `p-3 flex items-center space-x-3 cursor-pointer border-b border-gray-100 transition duration-150 ${isActive ? 'bg-teal-100 border-l-4 border-teal-500' : 'hover:bg-gray-100'}`;
    item.innerHTML = `
        <img src="${avatarUrl}" alt="${convo.name || number}" class="w-10 h-10 rounded-full object-cover flex-shrink-0">
        <div class="flex-grow min-w-0">
            <p class="font-semibold text-gray-800 truncate">${convo.name || number}</p>
            <p class="text-xs text-gray-500 truncate">${(last || '').length > 30 ? (last || '').slice(0,30) + '...' : (last || '')}</p>
        </div>
        ${(convo.unread || 0) > 0 ? `<span class="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full flex-shrink-0">${convo.unread}</span>` : ''}
    `;
    item.addEventListener('click', () => setActiveChat(number));
    return item;
}

function setActiveChat(number) {
    if (!conversations[number]) return;
    activeChatNumber = number;

    // Visual active update
    document.querySelectorAll('#conversations-container > div').forEach(el => {
        el.classList.remove('bg-teal-100', 'border-l-4', 'border-teal-500');
    });
    const el = document.querySelector(`[data-number="${number}"]`);
    if (el) el.classList.add('bg-teal-100', 'border-l-4', 'border-teal-500');

    conversations[number].unread = 0;
    renderConversationsList();

    placeholderChat && placeholderChat.classList.add('hidden');
    chatHeader && chatHeader.classList.remove('hidden');
    chatForm && chatForm.classList.remove('hidden');
    activeChatName && (activeChatName.textContent = conversations[number].name || number);
    activeChatNumberEl && (activeChatNumberEl.textContent = number);
    renderChatMessages();
}

function renderChatMessages() {
    if (!mensagensDiv) return;
    mensagensDiv.innerHTML = '';
    if (!activeChatNumber) return;
    const history = conversations[activeChatNumber].history || [];
    history.forEach(msg => {
        const isMe = msg.sender === 'Eu';
        const bubbleClass = isMe ? 'bg-blue-500 text-white self-end rounded-br-none' : 'bg-white text-gray-800 self-start rounded-tl-none border border-gray-200';
        const msgEl = document.createElement('div');
        msgEl.className = `max-w-xs md:max-w-md p-3 my-2 rounded-xl shadow-sm ${bubbleClass}`;
        msgEl.textContent = msg.texto;
        mensagensDiv.appendChild(msgEl);
    });
    mensagensDiv.scrollTop = mensagensDiv.scrollHeight;
}

function addMessageToHistory(number, message, sender, isIncoming) {
    if (!conversations[number]) {
        conversations[number] = {
            name: message.name || `Cliente (${number.slice(-4)})`,
            number,
            history: [],
            unread: 0,
            profilePicUrl: ''
        };
    }
    conversations[number].history.push({
        texto: message.texto,
        sender,
        timestamp: new Date().toLocaleTimeString()
    });
    if (isIncoming) {
        if (number !== activeChatNumber) conversations[number].unread = (conversations[number].unread || 0) + 1;
        else renderChatMessages();
    }
    renderConversationsList();
    if (number === activeChatNumber) renderChatMessages();
}

async function loadAndDisplayChats() {
    try {
        console.log('Carregando conversas ativas do WhatsApp...');
        const response = await window.whatsappAPI.fetchChats();

        if (response && response.sucesso && Array.isArray(response.chats)) {
            conversations = conversations || {};
            response.chats.forEach(chat => {
                conversations[chat.number] = {
                    name: chat.name,
                    number: chat.number,
                    history: conversations[chat.number] ? conversations[chat.number].history : [],
                    unread: conversations[chat.number] ? conversations[chat.number].unread : 0,
                    profilePicUrl: chat.profilePicUrl || ''
                };
            });
            renderConversationsList();
        } else {
            console.error('Falha ao carregar chats:', response && response.erro);
        }
    } catch (e) {
        console.error('Erro IPC ao carregar chats:', e);
    }
}

function handleWhatsappReady() {
    updateConnectionStatus(true);
    settingsModal && settingsModal.classList.add('hidden');
    btnGenerateQR && btnGenerateQR.classList.add('hidden');
    qrcodeImage && qrcodeImage.classList.add('hidden');
    qrcodeMessage && (qrcodeMessage.textContent = '✅ Conexão estabelecida com sucesso! (Sessão salva)');
    btnConnectQR && (btnConnectQR.textContent = 'CONECTADO VIA QR', btnConnectQR.classList.remove('hidden'));
    loadAndDisplayChats();
}