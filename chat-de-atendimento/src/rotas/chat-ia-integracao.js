/**
 * INTEGRAÇÃO PRONTA PARA USO
 * Exemplo completo para integrar em seu servidor Express
 * 
 * Copie este arquivo como src/rotas/chat-ia.js
 * Depois importe em seu main.js:
 * 
 *   const rotasChat = require('./src/rotas/chat-ia');
 *   app.use('/api', rotasChat);
 */

const express = require('express');
const ServicoIAHumanizada = require('../aplicacao/servico-ia-humanizada');
const logger = require('../infraestrutura/logger');

const router = express.Router();

// Instância global do serviço
const servicoIA = new ServicoIAHumanizada({
    servico: 'Chat de Atendimento WhatsApp',
    empresa: 'Seu Negócio'
});

/**
 * POST /api/chat/mensagem
 * 
 * Processa uma mensagem de cliente e retorna resposta humanizada
 * 
 * Body:
 * {
 *   "mensagem": "Oi, como funciona?",
 *   "idCliente": "cliente_123",
 *   "nomeCliente": "João Silva",
 *   "tipoSolicitacao": "duvida"  // opcional: saudacao, duvida, problema, etc
 * }
 * 
 * Response:
 * {
 *   "success": true,
 *   "resposta": "Resposta humanizada...",
 *   "tipo": "duvida"
 * }
 */
router.post('/chat/mensagem', async (req, res) => {
    try {
        const { 
            mensagem, 
            idCliente, 
            nomeCliente = 'Cliente',
            tipoSolicitacao = 'duvida' 
        } = req.body;

        // Validação
        if (!mensagem || !idCliente) {
            logger.erro('[Chat API] Dados incompletos');
            return res.status(400).json({
                success: false,
                error: 'mensagem e idCliente são obrigatórios'
            });
        }

        if (mensagem.length > 2000) {
            return res.status(400).json({
                success: false,
                error: 'Mensagem muito longa (máximo 2000 caracteres)'
            });
        }

        logger.info(`[Chat API] Nova mensagem de ${idCliente}: "${mensagem.substring(0, 50)}..."`);

        const resultado = await servicoIA.procesarMensagemCliente(
            mensagem.trim(),
            idCliente,
            tipoSolicitacao,
            { nome: nomeCliente }
        );

        res.json({
            success: resultado.success,
            resposta: resultado.resposta,
            tipo: resultado.tipo,
            timestamp: resultado.timestamp || new Date()
        });

    } catch (erro) {
        logger.erro('[Chat API] Erro ao processar mensagem:', erro.message);
        res.status(500).json({
            success: false,
            error: 'Erro ao processar mensagem',
            resposta: 'Desculpe, estamos com um problema técnico. Um atendente irá ajudar em breve!'
        });
    }
});

/**
 * POST /api/chat/problema
 * 
 * Reportar um problema técnico com histórico de tentativas
 * 
 * Body:
 * {
 *   "descricao": "Não consigo fazer login",
 *   "idCliente": "cliente_789",
 *   "tentativas": [
 *     "Reiniciar o navegador",
 *     "Limpar cache",
 *     "Tentar em outro navegador"
 *   ]
 * }
 */
router.post('/chat/problema', async (req, res) => {
    try {
        const { 
            descricao, 
            idCliente, 
            tentativas = [] 
        } = req.body;

        if (!descricao || !idCliente) {
            return res.status(400).json({
                success: false,
                error: 'descricao e idCliente são obrigatórios'
            });
        }

        logger.info(`[Chat API] Problema reportado por ${idCliente}`);

        const resultado = await servicoIA.processarProblemaComHistorico(
            descricao,
            idCliente,
            tentativas
        );

        res.json(resultado);

    } catch (erro) {
        logger.erro('[Chat API] Erro ao processar problema:', erro.message);
        res.status(500).json({
            success: false,
            resposta: 'Vou transferir você para um especialista!'
        });
    }
});

/**
 * POST /api/chat/insatisfacao
 * 
 * Cliente expressando insatisfação/frustração
 * 
 * Body:
 * {
 *   "motivo": "Estou frustrado com o serviço",
 *   "idCliente": "cliente_001",
 *   "historico": "Cliente já reclamou 2 vezes antes"  // opcional
 * }
 */
router.post('/chat/insatisfacao', async (req, res) => {
    try {
        const { 
            motivo, 
            idCliente, 
            historico = '' 
        } = req.body;

        if (!motivo || !idCliente) {
            return res.status(400).json({
                success: false,
                error: 'motivo e idCliente são obrigatórios'
            });
        }

        logger.info(`[Chat API] Insatisfação reportada por ${idCliente}`);

        const resultado = await servicoIA.processarClienteInsatisfeito(
            motivo,
            idCliente,
            historico
        );

        res.json(resultado);

    } catch (erro) {
        logger.erro('[Chat API] Erro ao processar insatisfação:', erro.message);
        res.status(500).json({
            success: false,
            resposta: 'Lamento pelos problemas. Um gerente irá entrar em contato!'
        });
    }
});

/**
 * POST /api/chat/pergunta-diagnostica
 * 
 * Fazer uma pergunta diagnóstica para entender melhor
 * 
 * Body:
 * {
 *   "situacao": "Meu sistema está lento",
 *   "idCliente": "cliente_555"
 * }
 * 
 * Response:
 * {
 *   "success": true,
 *   "pergunta": "Uma pergunta bem pensada..."
 * }
 */
router.post('/chat/pergunta-diagnostica', async (req, res) => {
    try {
        const { situacao, idCliente } = req.body;

        if (!situacao || !idCliente) {
            return res.status(400).json({
                success: false,
                error: 'situacao e idCliente são obrigatórios'
            });
        }

        const resultado = await servicoIA.fazerPerguntaDiagnostica(
            situacao,
            idCliente
        );

        res.json(resultado);

    } catch (erro) {
        logger.erro('[Chat API] Erro ao fazer pergunta:', erro.message);
        res.status(500).json({
            success: false,
            pergunta: 'Pode contar mais detalhes sobre o que está acontecendo?'
        });
    }
});

/**
 * POST /api/chat/feedback
 * 
 * Cliente enviando feedback positivo
 * 
 * Body:
 * {
 *   "feedback": "Vocês foram incríveis!",
 *   "idCliente": "cliente_abc",
 *   "nomeCliente": "Ana"  // opcional
 * }
 */
router.post('/chat/feedback', async (req, res) => {
    try {
        const { 
            feedback, 
            idCliente, 
            nomeCliente = 'Cliente' 
        } = req.body;

        if (!feedback || !idCliente) {
            return res.status(400).json({
                success: false,
                error: 'feedback e idCliente são obrigatórios'
            });
        }

        logger.info(`[Chat API] Feedback positivo de ${idCliente}`);

        const resultado = await servicoIA.responderFeedbackPositivo(
            feedback,
            idCliente,
            nomeCliente
        );

        res.json(resultado);

    } catch (erro) {
        logger.erro('[Chat API] Erro ao responder feedback:', erro.message);
        res.status(500).json({
            success: false,
            resposta: 'Obrigado pelo feedback! Vamos continuar melhorando!'
        });
    }
});

/**
 * GET /api/chat/:idCliente/info
 * 
 * Obter informações sobre a conversa de um cliente
 * 
 * Response:
 * {
 *   "idCliente": "cliente_123",
 *   "nomeCliente": "João Silva",
 *   "primeiraInteracao": false,
 *   "ultimaAtualizacao": "2024-01-11T10:30:00.000Z",
 *   "totalMensagens": 5
 * }
 */
router.get('/chat/:idCliente/info', (req, res) => {
    try {
        const info = servicoIA.obterInfoConversa(req.params.idCliente);
        
        if (info) {
            res.json({
                success: true,
                data: info
            });
        } else {
            res.status(404).json({
                success: false,
                message: 'Conversa não encontrada'
            });
        }

    } catch (erro) {
        logger.erro('[Chat API] Erro ao obter info:', erro.message);
        res.status(500).json({
            success: false,
            error: erro.message
        });
    }
});

/**
 * DELETE /api/chat/:idCliente/limpar
 * 
 * Limpar o histórico de conversa de um cliente
 * 
 * Response:
 * {
 *   "success": true
 * }
 */
router.delete('/chat/:idCliente/limpar', (req, res) => {
    try {
        const resultado = servicoIA.limparConversa(req.params.idCliente);
        
        if (resultado.success) {
            logger.info(`[Chat API] Conversa de ${req.params.idCliente} limpa`);
        }
        
        res.json(resultado);

    } catch (erro) {
        logger.erro('[Chat API] Erro ao limpar conversa:', erro.message);
        res.status(500).json({
            success: false,
            error: erro.message
        });
    }
});

/**
 * POST /api/chat/teste
 * 
 * Endpoint de teste para verificar se o serviço está funcionando
 * 
 * Body (opcional):
 * {
 *   "mensagem": "Oi!"  // opcional
 * }
 */
router.post('/chat/teste', async (req, res) => {
    try {
        const { mensagem = 'Oi! Como vocês estão?' } = req.body;
        
        logger.info('[Chat API] Teste iniciado');

        const resultado = await servicoIA.procesarMensagemCliente(
            mensagem,
            'teste_' + Date.now(),
            'duvida',
            { nome: 'Teste' }
        );

        res.json({
            success: resultado.success,
            resposta: resultado.resposta,
            status: 'IA funcionando corretamente ✅'
        });

    } catch (erro) {
        logger.erro('[Chat API] Erro no teste:', erro.message);
        res.status(500).json({
            success: false,
            error: erro.message,
            status: 'Erro ao testar IA ❌'
        });
    }
});

/**
 * GET /api/chat/saude
 * 
 * Verificar saúde do serviço
 */
router.get('/chat/saude', (req, res) => {
    res.json({
        status: 'online',
        servico: 'Chat IA Humanizada',
        timestamp: new Date(),
        endpoints: {
            'POST /api/chat/mensagem': 'Processar mensagem',
            'POST /api/chat/problema': 'Reportar problema',
            'POST /api/chat/insatisfacao': 'Cliente insatisfeito',
            'POST /api/chat/pergunta-diagnostica': 'Fazer diagnóstico',
            'POST /api/chat/feedback': 'Enviar feedback',
            'GET /api/chat/:idCliente/info': 'Info da conversa',
            'DELETE /api/chat/:idCliente/limpar': 'Limpar histórico',
            'POST /api/chat/teste': 'Testar serviço'
        }
    });
});

// Middleware de erro global
router.use((err, req, res, next) => {
    logger.erro('[Chat API] Erro não tratado:', err.message);
    res.status(500).json({
        success: false,
        error: 'Erro interno do servidor',
        message: err.message
    });
});

module.exports = router;

/**
 * COMO USAR ESTE ARQUIVO:
 * 
 * 1. Copie para src/rotas/chat-ia.js
 * 
 * 2. Em seu main.js ou app.js:
 * 
 *    const rotasChat = require('./src/rotas/chat-ia');
 *    app.use('/api', rotasChat);
 * 
 * 3. Agora você tem os seguintes endpoints:
 * 
 *    POST   /api/chat/mensagem              - Processar mensagem
 *    POST   /api/chat/problema              - Reportar problema
 *    POST   /api/chat/insatisfacao          - Cliente insatisfeito
 *    POST   /api/chat/pergunta-diagnostica  - Fazer pergunta
 *    POST   /api/chat/feedback              - Enviar feedback
 *    GET    /api/chat/:idCliente/info       - Info da conversa
 *    DELETE /api/chat/:idCliente/limpar     - Limpar histórico
 *    POST   /api/chat/teste                 - Testar
 *    GET    /api/chat/saude                 - Status
 * 
 * EXEMPLO DE USO COM CURL:
 * 
 *    curl -X POST http://localhost:3000/api/chat/mensagem \
 *      -H "Content-Type: application/json" \
 *      -d '{"mensagem":"Oi!","idCliente":"cli123","nomeCliente":"João"}'
 * 
 * EXEMPLO COM JAVASCRIPT:
 * 
 *    fetch('http://localhost:3000/api/chat/mensagem', {
 *      method: 'POST',
 *      headers: { 'Content-Type': 'application/json' },
 *      body: JSON.stringify({
 *        mensagem: 'Oi!',
 *        idCliente: 'cli123',
 *        nomeCliente: 'João'
 *      })
 *    })
 *    .then(r => r.json())
 *    .then(data => console.log(data.resposta))
 */
