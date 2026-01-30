/**
 * =========================================================================
 * SERVIDOR CHAT INTERNO - COMUNICAÇÃO ENTRE ATENDENTES
 * =========================================================================
 * 
 * Este servidor gerencia a comunicação interna entre os atendentes do sistema.
 * Permite que os funcionários troquem mensagens em tempo real durante o
 * atendimento aos clientes.
 * 
 * Funcionalidades:
 * - Chat em tempo real entre atendentes
 * - Gerenciamento de múltiplas conexões
 * - Broadcast de mensagens para todos os conectados
 * - Notificações de entrada/saída de usuários
 * 
 * @author Sistema Chat Atendimento
 * @version 2.0.0
 * @since 2024
 */

const WebSocket = require('ws');

// =========================================================================
// CONFIGURAÇÕES DO SERVIDOR
// =========================================================================

const PORTA_CHAT_INTERNO = 9090;

// =========================================================================
// GERENCIAMENTO DE CONEXÕES
// =========================================================================

/**
 * Set para armazenar todas as conexões ativas
 * @type {Set<WebSocket>}
 */
let clientesConectados = new Set();

/**
 * Histórico de mensagens do chat interno
 * @type {Array<Object>}
 */
let historicoMensagens = [];

/**
 * Estatísticas do servidor
 */
let estatisticas = {
    totalConexoes: 0,
    mensagensEnviadas: 0,
    iniciadoEm: new Date().toISOString()
};

// =========================================================================
// CRIAÇÃO DO SERVIDOR
// =========================================================================

let servidorChatInterno;
let portaUsada = PORTA_CHAT_INTERNO;

// Tentar iniciar o servidor com fallback de porta
const tentarIniciarServidor = async (porta, maxTentativas = 10) => {
    for (let i = 0; i < maxTentativas; i++) {
        try {
            const server = new WebSocket.Server({ port: porta });
            portaUsada = porta;
            return server;
        } catch (erro) {
            if (erro.code === 'EADDRINUSE') {
                console.log(`⚠️  Porta ${porta} em uso. Tentando ${porta + 1}...`);
                porta++;
            } else {
                throw erro;
            }
        }
    }
    throw new Error(`Não foi possível iniciar o servidor após ${maxTentativas} tentativas`);
};

tentarIniciarServidor(PORTA_CHAT_INTERNO).then(server => {
    servidorChatInterno = server;
    
    console.log('💬 =======================================================');
    console.log('👥 SERVIDOR CHAT INTERNO - COMUNICAÇÃO ATENDENTES');
    console.log('💬 =======================================================');
    console.log(`📍 Servidor iniciado na porta: ${portaUsada}`);
    console.log(`🔗 URL de conexão: ws://localhost:${portaUsada}`);
    console.log('👤 Aguardando conexões dos atendentes...');
    console.log('💬 =======================================================\n');

    // =========================================================================
    // FUNÇÕES UTILITÁRIAS
    // =========================================================================

    /**
     * Envia mensagem para todos os clientes conectados
     * 
     * @param {Object} mensagem - Mensagem a ser enviada
     */
    function enviarParaTodosClientes(mensagem) {
        const mensagemJson = JSON.stringify(mensagem);
        
        clientesConectados.forEach(cliente => {
            if (cliente.readyState === WebSocket.OPEN) {
                cliente.send(mensagemJson);
            }
        });
        
        console.log(`📤 Mensagem enviada para ${clientesConectados.size} cliente(s)`);
    }

/**
 * Remove conexão inválida
 * 
 * @param {WebSocket} websocket - Conexão a ser removida
 */
function removerConexao(websocket) {
    clientesConectados.delete(websocket);
    console.log(`👤 Cliente desconectado. Total ativo: ${clientesConectados.size}`);
}

/**
 * Gera ID único para mensagem
 * 
 * @returns {string} ID único
 */
function gerarIdMensagem() {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
}

// =========================================================================
// GERENCIAMENTO DE CONEXÕES
// =========================================================================

    /**
     * Manipula novas conexões
     */
    servidorChatInterno.on('connection', websocket => {
        // Adiciona cliente à lista
        clientesConectados.add(websocket);
        estatisticas.totalConexoes++;
        
        console.log(`🎯 [NOVA CONEXÃO] Atendente conectado!`);
        console.log(`👥 Total de atendentes online: ${clientesConectados.size}`);
        console.log(`📊 Total de conexões desde o início: ${estatisticas.totalConexoes}`);
    console.log(`🕒 Horário: ${new Date().toLocaleString('pt-BR')}\n`);

    // Envia mensagem de boas-vindas
    const mensagemBoasVindas = {
        tipo: 'sistema',
        id: gerarIdMensagem(),
        texto: `Bem-vindo ao chat interno! Há ${clientesConectados.size} atendente(s) online.`,
        timestamp: Date.now(),
        dataFormatada: new Date().toLocaleString('pt-BR')
    };
    
    websocket.send(JSON.stringify(mensagemBoasVindas));

    // Envia histórico recente (últimas 10 mensagens)
    if (historicoMensagens.length > 0) {
        const historicoRecente = historicoMensagens.slice(-10);
        
        const mensagemHistorico = {
            tipo: 'historico',
            id: gerarIdMensagem(),
            mensagens: historicoRecente,
            timestamp: Date.now()
        };
        
        websocket.send(JSON.stringify(mensagemHistorico));
    }

    // Notifica outros atendentes sobre nova conexão
    const notificacaoNovaConexao = {
        tipo: 'notificacao',
        id: gerarIdMensagem(),
        subtipo: 'entrada',
        texto: 'Um novo atendente entrou no chat',
        totalOnline: clientesConectados.size,
        timestamp: Date.now(),
        dataFormatada: new Date().toLocaleString('pt-BR')
    };
    
    // Envia para todos exceto o que acabou de conectar
    clientesConectados.forEach(cliente => {
        if (cliente !== websocket && cliente.readyState === WebSocket.OPEN) {
            cliente.send(JSON.stringify(notificacaoNovaConexao));
        }
    });

    /**
     * Processa mensagens recebidas
     */
    websocket.on('message', dadosRecebidos => {
        try {
            const mensagemRecebida = JSON.parse(dadosRecebidos);
            
            console.log('📥 [MENSAGEM RECEBIDA]');
            console.log(`👤 De: ${mensagemRecebida.from || 'Anônimo'}`);
            console.log(`💬 Texto: "${mensagemRecebida.texto}"`);
            console.log(`🕒 Horário: ${new Date().toLocaleString('pt-BR')}\n`);
            
            // Processa apenas mensagens do tipo 'internal'
            if (mensagemRecebida.tipo === 'internal') {
                const mensagemProcessada = {
                    tipo: 'internal',
                    id: gerarIdMensagem(),
                    from: mensagemRecebida.from || 'Anônimo',
                    texto: mensagemRecebida.texto,
                    timestamp: Date.now(),
                    dataFormatada: new Date().toLocaleString('pt-BR')
                };
                
                // Adiciona ao histórico
                historicoMensagens.push(mensagemProcessada);
                
                // Limita o histórico a 100 mensagens
                if (historicoMensagens.length > 100) {
                    historicoMensagens = historicoMensagens.slice(-100);
                }
                
                // Envia para todos os clientes conectados
                enviarParaTodosClientes(mensagemProcessada);
                
                // Atualiza estatísticas
                estatisticas.mensagensEnviadas++;
                
                console.log(`📊 Mensagem #${estatisticas.mensagensEnviadas} processada e enviada`);
            }
            
        } catch (erro) {
            console.error('⚠️ [ERRO] Falha ao processar mensagem:', erro.message);
            
            // Envia mensagem de erro para o cliente
            const mensagemErro = {
                tipo: 'erro',
                id: gerarIdMensagem(),
                texto: 'Formato de mensagem inválido',
                timestamp: Date.now()
            };
            
            if (websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify(mensagemErro));
            }
        }
    });

    /**
     * Gerencia desconexão
     */
    websocket.on('close', () => {
        removerConexao(websocket);
        
        console.log('❌ [DESCONEXÃO] Atendente saiu do chat');
        console.log(`👥 Total de atendentes online: ${clientesConectados.size}`);
        console.log(`🕒 Horário: ${new Date().toLocaleString('pt-BR')}\n`);

        // Notifica outros atendentes sobre saída
        if (clientesConectados.size > 0) {
            const notificacaoSaida = {
                tipo: 'notificacao',
                id: gerarIdMensagem(),
                subtipo: 'saida',
                texto: 'Um atendente saiu do chat',
                totalOnline: clientesConectados.size,
                timestamp: Date.now(),
                dataFormatada: new Date().toLocaleString('pt-BR')
            };
            
            enviarParaTodosClientes(notificacaoSaida);
        }
    });

    /**
     * Gerencia erros na conexão
     */
    websocket.on('error', erro => {
        console.error('⚠️ [ERRO DE CONEXÃO]:', erro.message);
        removerConexao(websocket);
    });
});

// =========================================================================
// GERENCIAMENTO DO SERVIDOR
// =========================================================================

/**
 * Gerencia erros do servidor
 */
servidorChatInterno.on('error', erro => {
    console.error('💥 [ERRO DO SERVIDOR]:', erro);
});

/**
 * Função para obter estatísticas do servidor
 * 
 * @returns {Object} Estatísticas atuais
 */
function obterEstatisticas() {
    return {
        ...estatisticas,
        clientesAtivos: clientesConectados.size,
        totalMensagensHistorico: historicoMensagens.length,
        tempoAtivo: new Date().getTime() - new Date(estatisticas.iniciadoEm).getTime()
    };
}

/**
 * Envia estatísticas periodicamente (a cada 5 minutos)
 */
setInterval(() => {
    if (clientesConectados.size > 0) {
        const stats = obterEstatisticas();
        
        const mensagemEstatisticas = {
            tipo: 'estatisticas',
            id: gerarIdMensagem(),
            dados: stats,
            timestamp: Date.now()
        };
        
        console.log('📊 Enviando estatísticas para clientes conectados');
        enviarParaTodosClientes(mensagemEstatisticas);
    }
}, 5 * 60 * 1000); // 5 minutos

/**
 * Gerencia encerramento do servidor
 */
process.on('SIGINT', () => {
    console.log('\n🛑 [ENCERRANDO SERVIDOR CHAT INTERNO]');
    console.log('📊 Enviando notificação de encerramento...');
    
    // Notifica todos os clientes sobre encerramento
    const mensagemEncerramento = {
        tipo: 'sistema',
        id: gerarIdMensagem(),
        texto: 'Servidor de chat interno será encerrado em 5 segundos',
        timestamp: Date.now()
    };
    
    enviarParaTodosClientes(mensagemEncerramento);
    
    // Aguarda um pouco antes de fechar as conexões
    setTimeout(() => {
        clientesConectados.forEach(cliente => {
            cliente.terminate();
        });
        
        servidorChatInterno.close(() => {
            console.log('✅ Servidor de chat interno encerrado com sucesso!');
            console.log(`📊 Estatísticas finais:`, obterEstatisticas());
            process.exit(0);
        });
    }, 5000);
});

// =========================================================================
// INFORMAÇÕES DO SERVIDOR
// =========================================================================

    console.log('📋 INFORMAÇÕES DO SERVIDOR:');
    console.log(`📡 Porta: ${portaUsada}`);
    console.log(`💾 Histórico: Últimas 100 mensagens`);
    console.log(`📊 Estatísticas: A cada 5 minutos`);
    console.log(`🔄 Reconexão: Automática`);
    console.log('📝 Para parar o servidor: Ctrl+C\n');

    // =========================================================================
    // EXPORTAÇÃO
    // =========================================================================

    module.exports = {
        servidorChatInterno,
        obterEstatisticas,
        PORTA_CHAT_INTERNO: portaUsada
    };
}).catch(erro => {
    console.error('💥 [ERRO DO SERVIDOR]:', erro);
    process.exit(1);
});
