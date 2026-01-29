// Exemplos de uso do Sistema de IA Humanizada
// Demonstra como integrar o ServicoIAHumanizada em suas rotas e controllers

const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');

// ============ INICIALIZAÇÃO ============
const servicoIA = new ServicoIAHumanizada({
    servico: 'Chat de Atendimento WhatsApp',
    empresa: 'Sua Empresa'
});

// ============ EXEMPLOS DE USO ============

/**
 * EXEMPLO 1: Processar mensagem de cliente comum
 * Tipo: Dúvida sobre funcionamento
 */
async function exemplo_MensagemComum() {
    console.log('\n=== EXEMPLO 1: Mensagem Comum ===\n');
    
    const resultado = await servicoIA.procesarMensagemCliente(
        'Oi! Como funciona o serviço de vocês?',
        'cliente_123',
        'duvida',
        { nome: 'João Silva' }
    );

    console.log('Resposta do cliente (João Silva):');
    console.log(resultado.resposta);
    console.log('\n---\n');
}

/**
 * EXEMPLO 2: Primeira interação com cliente novo
 */
async function exemplo_PrimeiraInteracao() {
    console.log('\n=== EXEMPLO 2: Primeira Interação ===\n');
    
    const resultado = await servicoIA.procesarMensagemCliente(
        'Oi, chegaram aqui pra primeiro atendimento',
        'cliente_456',
        'saudacao',
        { nome: 'Maria Santos' }
    );

    console.log('Resposta inicial para novo cliente:');
    console.log(resultado.resposta);
    console.log('\n---\n');
}

/**
 * EXEMPLO 3: Cliente com problema técnico
 */
async function exemplo_ProblemaComHistorico() {
    console.log('\n=== EXEMPLO 3: Problema com Histórico ===\n');
    
    const resultado = await servicoIA.processarProblemaComHistorico(
        'Não consigo acessar minha conta. Recebo erro 403',
        'cliente_789',
        [
            'Reiniciar o navegador',
            'Limpar cache',
            'Tentar em outro navegador'
        ]
    );

    console.log('Resposta para problema com histórico:');
    console.log(resultado.resposta);
    console.log('\n---\n');
}

/**
 * EXEMPLO 4: Cliente insatisfeito/reclamando
 */
async function exemplo_ClienteInsatisfeito() {
    console.log('\n=== EXEMPLO 4: Cliente Insatisfeito ===\n');
    
    const resultado = await servicoIA.processarClienteInsatisfeito(
        'Estou muito frustrado! Fiz o pagamento ontem e até agora nada!',
        'cliente_001',
        'Cliente pagou e ainda não recebeu o serviço. Primeira reclamação dele.'
    );

    console.log('Resposta para cliente insatisfeito:');
    console.log(resultado.resposta);
    console.log('\n---\n');
}

/**
 * EXEMPLO 5: Pergunta diagnóstica para entender melhor
 */
async function exemplo_PerguntaDiagnostica() {
    console.log('\n=== EXEMPLO 5: Pergunta Diagnóstica ===\n');
    
    const resultado = await servicoIA.fazerPerguntaDiagnostica(
        'Meu sistema está lento',
        'cliente_555'
    );

    console.log('Pergunta diagnóstica:');
    console.log(resultado.pergunta);
    console.log('\n---\n');
}

/**
 * EXEMPLO 6: Responder feedback positivo
 */
async function exemplo_FeedbackPositivo() {
    console.log('\n=== EXEMPLO 6: Feedback Positivo ===\n');
    
    const resultado = await servicoIA.responderFeedbackPositivo(
        'Vocês foram incríveis! Resolveram meu problema em minutos. Recomendo!',
        'cliente_abc',
        'Ana'
    );

    console.log('Resposta ao feedback positivo:');
    console.log(resultado.resposta);
    console.log('\n---\n');
}

/**
 * EXEMPLO 7: Conversa multi-turno (múltiplas mensagens)
 */
async function exemplo_ConversaMultiTurno() {
    console.log('\n=== EXEMPLO 7: Conversa Multi-Turno ===\n');
    
    const idCliente = 'cliente_multi_999';
    const nomeCliente = 'Pedro';

    // Primeira mensagem
    console.log('Cliente: Oi, preciso de ajuda com um pedido');
    let resposta = await servicoIA.procesarMensagemCliente(
        'Oi, preciso de ajuda com um pedido',
        idCliente,
        'duvida',
        { nome: nomeCliente }
    );
    console.log(`Bot: ${resposta.resposta}\n`);

    // Segunda mensagem
    console.log('Cliente: É, fiz um pedido semana passada e ainda não chegou');
    resposta = await servicoIA.procesarMensagemCliente(
        'É, fiz um pedido semana passada e ainda não chegou',
        idCliente,
        'problema',
        { nome: nomeCliente }
    );
    console.log(`Bot: ${resposta.resposta}\n`);

    // Terceira mensagem
    console.log('Cliente: Qual o número de rastreio?');
    resposta = await servicoIA.procesarMensagemCliente(
        'Qual o número de rastreio?',
        idCliente,
        'duvida',
        { nome: nomeCliente }
    );
    console.log(`Bot: ${resposta.resposta}\n`);

    console.log('---\n');
}

// ============ EXEMPLO DE INTEGRAÇÃO EM ROTA EXPRESS ============

/**
 * Integração exemplo para rota de chat
 */
function exemploRotaExpress() {
    const express = require('express');
    const router = express.Router();

    /**
     * POST /api/chat/mensagem
     * Processa mensagem do cliente
     */
    router.post('/chat/mensagem', async (req, res) => {
        try {
            const { mensagem, idCliente, nomeCliente, tipoSolicitacao = 'duvida' } = req.body;

            if (!mensagem || !idCliente) {
                return res.status(400).json({ 
                    error: 'mensagem e idCliente são obrigatórios' 
                });
            }

            const resultado = await servicoIA.procesarMensagemCliente(
                mensagem,
                idCliente,
                tipoSolicitacao,
                { nome: nomeCliente }
            );

            res.json({
                success: resultado.success,
                resposta: resultado.resposta,
                tipo: resultado.tipo,
                timestamp: resultado.timestamp
            });

        } catch (erro) {
            console.error('[Chat API] Erro:', erro);
            res.status(500).json({ 
                error: 'Erro ao processar mensagem',
                details: erro.message 
            });
        }
    });

    /**
     * POST /api/chat/problema
     * Reportar um problema com histórico
     */
    router.post('/chat/problema', async (req, res) => {
        try {
            const { descricao, idCliente, tentativas = [] } = req.body;

            const resultado = await servicoIA.processarProblemaComHistorico(
                descricao,
                idCliente,
                tentativas
            );

            res.json({
                success: resultado.success,
                resposta: resultado.resposta
            });

        } catch (erro) {
            res.status(500).json({ error: erro.message });
        }
    });

    /**
     * POST /api/chat/insatisfacao
     * Cliente expressando insatisfação
     */
    router.post('/chat/insatisfacao', async (req, res) => {
        try {
            const { motivo, idCliente, historico = '' } = req.body;

            const resultado = await servicoIA.processarClienteInsatisfeito(
                motivo,
                idCliente,
                historico
            );

            res.json({
                success: resultado.success,
                resposta: resultado.resposta
            });

        } catch (erro) {
            res.status(500).json({ error: erro.message });
        }
    });

    /**
     * POST /api/chat/pergunta-diagnostica
     * Fazer pergunta para entender melhor
     */
    router.post('/chat/pergunta-diagnostica', async (req, res) => {
        try {
            const { situacao, idCliente } = req.body;

            const resultado = await servicoIA.fazerPerguntaDiagnostica(
                situacao,
                idCliente
            );

            res.json({
                success: resultado.success,
                pergunta: resultado.pergunta
            });

        } catch (erro) {
            res.status(500).json({ error: erro.message });
        }
    });

    /**
     * POST /api/chat/feedback
     * Cliente enviando feedback positivo
     */
    router.post('/chat/feedback', async (req, res) => {
        try {
            const { feedback, idCliente, nomeCliente } = req.body;

            const resultado = await servicoIA.responderFeedbackPositivo(
                feedback,
                idCliente,
                nomeCliente
            );

            res.json({
                success: resultado.success,
                resposta: resultado.resposta
            });

        } catch (erro) {
            res.status(500).json({ error: erro.message });
        }
    });

    /**
     * GET /api/chat/:idCliente/info
     * Obter informações da conversa
     */
    router.get('/chat/:idCliente/info', (req, res) => {
        const info = servicoIA.obterInfoConversa(req.params.idCliente);
        
        if (info) {
            res.json({ success: true, data: info });
        } else {
            res.status(404).json({ success: false, message: 'Conversa não encontrada' });
        }
    });

    /**
     * DELETE /api/chat/:idCliente/limpar
     * Limpar histórico da conversa
     */
    router.delete('/chat/:idCliente/limpar', (req, res) => {
        const resultado = servicoIA.limparConversa(req.params.idCliente);
        res.json(resultado);
    });

    return router;
}

// ============ PARA USAR ESTES EXEMPLOS ============
/*

Se você quer testar os exemplos localmente, execute:

    node -e "
    const exemplos = require('./exemplos-uso-ia-humanizada');
    
    // Execute um exemplo por vez:
    // await exemplos.exemplo_MensagemComum();
    // await exemplos.exemplo_PrimeiraInteracao();
    // await exemplos.exemplo_ProblemaComHistorico();
    // await exemplos.exemplo_ClienteInsatisfeito();
    // await exemplos.exemplo_PerguntaDiagnostica();
    // await exemplos.exemplo_FeedbackPositivo();
    // await exemplos.exemplo_ConversaMultiTurno();
    "

Se você está usando Express, integre assim em seu servidor:

    const exemplos = require('./exemplos-uso-ia-humanizada');
    app.use('/api', exemplos.exemploRotaExpress());

*/

module.exports = {
    servicoIA,
    exemplo_MensagemComum,
    exemplo_PrimeiraInteracao,
    exemplo_ProblemaComHistorico,
    exemplo_ClienteInsatisfeito,
    exemplo_PerguntaDiagnostica,
    exemplo_FeedbackPositivo,
    exemplo_ConversaMultiTurno,
    exemploRotaExpress
};
