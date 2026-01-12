/**
 * 🔗 Rotas de Sincronização WhatsApp
 * 
 * Endpoints para:
 * - Gerar QR Code
 * - Validar QR Code com número de telefone
 * - Validação manual
 * - Sincronização com Meta/Facebook API
 * - Status de sessão
 */

const express = require('express');
const router = express.Router();
const logger = require('../infraestrutura/logger');
const gerenciadorSessao = require('../services/GerenciadorSessaoWhatsApp');
const { obterPool } = require('../services/instancia-pool');

// Helper para obter pool com validação
function getPoolValidado() {
    const pool = obterPool();
    if (!pool) {
        throw new Error('Pool WhatsApp não inicializado');
    }
    return pool;
}

/**
 * GET /api/whatsapp/qr-code
 * Gerar novo QR Code para sincronização
 */
router.get('/qr-code', async (req, res) => {
    try {
        const sessao = await gerenciadorSessao.obterStatus();

        if (sessao.ativo) {
            return res.json({
                success: true,
                message: 'WhatsApp já está sincronizado',
                telefone: sessao.telefone,
                status: sessao.status
            });
        }

        // Pegar cliente mais recente para obter QR
        const clientes = getPoolValidado().listarClientes();
        
        if (clientes.length === 0) {
            return res.status(400).json({
                success: false,
                message: 'Nenhum cliente WhatsApp disponível'
            });
        }

        const clienteAtual = clientes[clientes.length - 1];

        if (!clienteAtual.qrCode) {
            return res.status(400).json({
                success: false,
                message: 'QR Code ainda não foi gerado. Tente novamente em alguns segundos.'
            });
        }

        res.json({
            success: true,
            qrCode: clienteAtual.qrCode,
            clientId: clienteAtual.clientId,
            status: clienteAtual.status,
            message: 'QR Code gerado com sucesso'
        });
    } catch (erro) {
        logger.erro('[API] Erro ao gerar QR Code:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * POST /api/whatsapp/validar-qrcode
 * Validar QR Code com número de telefone
 */
router.post('/validar-qrcode', async (req, res) => {
    try {
        const { telefone } = req.body;

        // Validações
        if (!telefone) {
            return res.status(400).json({
                success: false,
                message: 'Telefone é obrigatório'
            });
        }

        // Criar sessão
        const clientes = getPoolValidado().listarClientes();
        const clienteAtual = clientes[clientes.length - 1];

        const resultado = await gerenciadorSessao.criarSessao(
            telefone,
            clienteAtual?.qrCode || null,
            'qrcode',
            {
                clientId: clienteAtual?.clientId,
                ip: req.ip,
                userAgent: req.headers['user-agent']
            }
        );

        if (!resultado.success) {
            return res.status(400).json(resultado);
        }

        // Tentar validar automaticamente
        const validacao = await gerenciadorSessao.validarSessao(
            resultado.sessaoId,
            'auto-qrcode'
        );

        if (validacao.success) {
            // Ativar sessão
            const ativacao = await gerenciadorSessao.ativarSessao(telefone);
            return res.json(ativacao);
        }

        res.json({
            success: true,
            message: 'QR Code validado. Aguardando confirmação no WhatsApp...',
            sessaoId: resultado.sessaoId,
            telefone
        });
    } catch (erro) {
        logger.erro('[API] Erro ao validar QR Code:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * POST /api/whatsapp/validar-manual
 * Validação manual com código
 */
router.post('/validar-manual', async (req, res) => {
    try {
        const { telefone, codigo } = req.body;

        if (!telefone || !codigo) {
            return res.status(400).json({
                success: false,
                message: 'Telefone e código são obrigatórios'
            });
        }

        const sessao = await gerenciadorSessao.obterStatus();

        if (!sessao.telefone || sessao.telefone !== telefone) {
            // Criar nova sessão
            const resultado = await gerenciadorSessao.criarSessao(
                telefone,
                null,
                'manual',
                {
                    ip: req.ip,
                    metodo: 'validacao_manual'
                }
            );

            if (!resultado.success) {
                return res.status(400).json(resultado);
            }

            const validacao = await gerenciadorSessao.validarSessao(
                resultado.sessaoId,
                codigo
            );

            if (!validacao.success) {
                return res.status(400).json(validacao);
            }

            const ativacao = await gerenciadorSessao.ativarSessao(telefone);
            return res.json(ativacao);
        }

        // Usar sessão existente
        const validacao = await gerenciadorSessao.validarSessao(
            sessao.telefone,
            codigo
        );

        if (!validacao.success) {
            return res.status(400).json(validacao);
        }

        const ativacao = await gerenciadorSessao.ativarSessao(telefone);
        res.json(ativacao);
    } catch (erro) {
        logger.erro('[API] Erro ao validar manualmente:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * POST /api/whatsapp/sincronizar-meta
 * Sincronizar com Meta/Facebook API
 */
router.post('/sincronizar-meta', async (req, res) => {
    try {
        const { telefone, accessToken } = req.body;

        if (!telefone || !accessToken) {
            return res.status(400).json({
                success: false,
                message: 'Telefone e access token são obrigatórios'
            });
        }

        const resultado = await gerenciadorSessao.sincronizarComMeta(
            accessToken,
            telefone
        );

        if (!resultado.success) {
            return res.status(400).json(resultado);
        }

        // Se sincronização bem-sucedida, ativar sessão
        const ativacao = await gerenciadorSessao.ativarSessao(telefone);
        res.json(ativacao);
    } catch (erro) {
        logger.erro('[API] Erro ao sincronizar com Meta:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * GET /api/whatsapp/status
 * Obter status atual da sincronização
 */
router.get('/status', async (req, res) => {
    try {
        const status = await gerenciadorSessao.obterStatus();
        res.json(status);
    } catch (erro) {
        logger.erro('[API] Erro ao obter status:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * POST /api/whatsapp/manter-vivo
 * Keep-alive para manter sessão ativa
 */
router.post('/manter-vivo', async (req, res) => {
    try {
        const status = await gerenciadorSessao.obterStatus();

        if (!status.ativo) {
            return res.status(400).json({
                success: false,
                message: 'Nenhuma sessão ativa'
            });
        }

        // Atualizar timestamp de última sincronização
        if (gerenciadorSessao.sessaoAtual) {
            gerenciadorSessao.sessaoAtual.ultima_sincronizacao = new Date().toISOString();
            await require('fs-extra').writeJson(
                gerenciadorSessao.sessaoFile,
                gerenciadorSessao.sessaoAtual,
                { spaces: 2 }
            );
        }

        res.json({
            success: true,
            message: 'Keep-alive atualizado',
            status: 'ativo',
            telefone: status.telefone
        });
    } catch (erro) {
        logger.erro('[API] Erro no keep-alive:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * POST /api/whatsapp/desconectar
 * Desconectar WhatsApp de forma segura
 */
router.post('/desconectar', async (req, res) => {
    try {
        if (gerenciadorSessao.sessaoAtual) {
            gerenciadorSessao.sessaoAtual.status = 'inativa';
            gerenciadorSessao.sessaoAtual.desconectada_em = new Date().toISOString();

            await require('fs-extra').writeJson(
                gerenciadorSessao.sessaoFile,
                gerenciadorSessao.sessaoAtual,
                { spaces: 2 }
            );
        }

        logger.sucesso('[API] WhatsApp desconectado com segurança');

        res.json({
            success: true,
            message: 'WhatsApp desconectado com sucesso'
        });
    } catch (erro) {
        logger.erro('[API] Erro ao desconectar:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * POST /api/whatsapp/conectar-por-numero
 * Conectar WhatsApp por número de telefone manual
 * 
 * Body: { telefone: "5511999999999", metodo: "numero-manual" }
 */
router.post('/conectar-por-numero', async (req, res) => {
    try {
        const { telefone, metodo = 'numero-manual' } = req.body;

        // Validar formato do telefone
        if (!telefone || !telefone.match(/^55\d{10,11}$/)) {
            return res.status(400).json({
                success: false,
                message: 'Formato de telefone inválido. Use: 5511999999999'
            });
        }

        logger.info(`[API] Iniciando conexão para número: ${telefone}`);

        // Criar novo cliente no pool
        const novoClienteResult = await getPoolValidado().createClient();
        
        if (!novoClienteResult.success) {
            return res.status(500).json({
                success: false,
                message: novoClienteResult.message || 'Erro ao criar cliente'
            });
        }

        const clientId = novoClienteResult.clientId;
        logger.info(`[API] Cliente criado: ${clientId}`);

        // Inicializar o cliente de forma assíncrona
        // Não aguarda inicialização completa aqui
        const cliente = getPoolValidado().clients.get(clientId);
        if (cliente) {
            cliente.initialize().catch(err => {
                logger.erro(`[API] Erro na inicialização do cliente ${clientId}:`, err.message);
            });
        }

        // Retornar clientId imediatamente - o QR code será enviado via IPC quando for gerado
        res.json({
            success: true,
            message: 'Cliente criado. Aguardando QR Code...',
            clientId,
            telefone,
            metodo
        });

    } catch (erro) {
        logger.erro('[API] Erro ao conectar por número:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

/**
 * GET /api/whatsapp/status/:clientId
 * Obter status de um cliente específico
 */
router.get('/status/:clientId', async (req, res) => {
    try {
        const { clientId } = req.params;
        
        const cliente = getPoolValidado().clients.get(clientId);
        if (!cliente) {
            return res.status(404).json({
                success: false,
                message: 'Cliente não encontrado'
            });
        }

        res.json({
            success: true,
            clientId,
            status: cliente.status,
            telefone: cliente.phoneNumber,
            qrCode: cliente.qrCode, // Retornar QR code se disponível
            ativo: cliente.status === 'ready',
            mensagem: {
                'ready': 'Cliente conectado e pronto',
                'disconnected': 'Cliente desconectado',
                'authenticated': 'Autenticação em andamento',
                'qr_ready': 'QR Code pronto para escanear',
                'error': 'Erro na conexão'
            }[cliente.status] || 'Status desconhecido'
        });
    } catch (erro) {
        logger.erro('[API] Erro ao obter status:', erro.message);
        res.status(500).json({
            success: false,
            message: erro.message
        });
    }
});

module.exports = router;

