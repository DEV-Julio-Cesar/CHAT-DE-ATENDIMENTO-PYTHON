/**
 * API REST para Gerenciamento da Base de Conhecimento do Robô
 * 
 * Endpoints:
 * GET  /api/base-conhecimento - Obtém toda a base
 * GET  /api/base-conhecimento/:id - Obtém um comando específico
 * POST /api/base-conhecimento - Cria novo comando
 * PUT  /api/base-conhecimento/:id - Atualiza comando
 * DELETE /api/base-conhecimento/:id - Deleta comando
 * GET  /api/base-conhecimento/configuracoes - Obtém configurações
 * PUT  /api/base-conhecimento/configuracoes - Atualiza configurações
 * POST /api/base-conhecimento/buscar - Busca comandos
 * POST /api/base-conhecimento/importar - Importa base
 */

const express = require('express');
const router = express.Router();
const logger = require('../infraestrutura/logger');
const GerenciadorBaseConhecimento = require('../aplicacao/gerenciador-base-conhecimento');

// Instanciar gerenciador
const gerenciador = new GerenciadorBaseConhecimento();

// Carregar base ao iniciar
gerenciador.carregar().catch(erro => {
    logger.erro('Erro ao carregar base de conhecimento', { erro: erro.message });
});

/**
 * GET /api/base-conhecimento
 * Obtém toda a base de conhecimento (comandos + configurações)
 */
router.get('/api/base-conhecimento', async (req, res) => {
    try {
        const comandos = gerenciador.obterComandos();
        const configuracoes = gerenciador.obterConfiguracoes();

        // Se solicitar apenas comandos
        if (req.query.apenas_comandos === 'true') {
            return res.json(comandos);
        }

        // Retornar estrutura completa
        res.json({
            comandos,
            configuracoes,
            total: comandos.length,
            ativos: comandos.filter(c => c.ativo).length,
            timestamp: new Date().toISOString()
        });
    } catch (erro) {
        logger.erro('Erro ao obter base de conhecimento', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao obter base de conhecimento' });
    }
});

/**
 * GET /api/base-conhecimento/:id
 * Obtém um comando específico
 */
router.get('/api/base-conhecimento/:id', async (req, res) => {
    try {
        const comando = gerenciador.obterComandoPorId(req.params.id);

        if (!comando) {
            return res.status(404).json({ message: 'Comando não encontrado' });
        }

        res.json(comando);
    } catch (erro) {
        logger.erro('Erro ao obter comando', { id: req.params.id, erro: erro.message });
        res.status(500).json({ message: 'Erro ao obter comando' });
    }
});

/**
 * POST /api/base-conhecimento
 * Cria novo comando
 */
router.post('/api/base-conhecimento', async (req, res) => {
    try {
        // Validar entrada
        const { id, tipo, resposta, palavras_chave, prioridade, ativo, categoria } = req.body;

        if (!id || !tipo || !resposta || !Array.isArray(palavras_chave) || palavras_chave.length === 0) {
            return res.status(400).json({
                message: 'Campos obrigatórios faltando: id, tipo, resposta, palavras_chave (array não vazio)'
            });
        }

        // Validar prioridade
        if (prioridade && (prioridade < 1 || prioridade > 10)) {
            return res.status(400).json({ message: 'Prioridade deve ser entre 1 e 10' });
        }

        // Validar tipos
        const tiposValidos = ['saudacao', 'informacao', 'problema', 'resposta_gentil', 'duvida', 'acao', 'generico'];
        if (!tiposValidos.includes(tipo)) {
            return res.status(400).json({
                message: `Tipo inválido. Tipos aceitos: ${tiposValidos.join(', ')}`
            });
        }

        // Verificar se ID já existe
        if (gerenciador.obterComandoPorId(id)) {
            return res.status(409).json({ message: 'Comando com este ID já existe' });
        }

        // Criar comando
        const comando = {
            id,
            tipo,
            resposta,
            categoria: categoria || '',
            palavras_chave: palavras_chave.map(p => p.toLowerCase().trim()),
            prioridade: prioridade || 5,
            ativo: ativo !== false,
            criado_em: new Date().toISOString(),
            atualizado_em: new Date().toISOString()
        };

        gerenciador.criarComando(comando);
        await gerenciador.salvar();

        logger.info('Comando criado', { id: comando.id });
        res.status(201).json(comando);
    } catch (erro) {
        logger.erro('Erro ao criar comando', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao criar comando' });
    }
});

/**
 * PUT /api/base-conhecimento/:id
 * Atualiza comando existente
 */
router.put('/api/base-conhecimento/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const { tipo, resposta, palavras_chave, prioridade, ativo, categoria } = req.body;

        // Verificar se comando existe
        const comandoExistente = gerenciador.obterComandoPorId(id);
        if (!comandoExistente) {
            return res.status(404).json({ message: 'Comando não encontrado' });
        }

        // Validar prioridade se fornecida
        if (prioridade && (prioridade < 1 || prioridade > 10)) {
            return res.status(400).json({ message: 'Prioridade deve ser entre 1 e 10' });
        }

        // Validar tipo se fornecido
        if (tipo) {
            const tiposValidos = ['saudacao', 'informacao', 'problema', 'resposta_gentil', 'duvida', 'acao', 'generico'];
            if (!tiposValidos.includes(tipo)) {
                return res.status(400).json({
                    message: `Tipo inválido. Tipos aceitos: ${tiposValidos.join(', ')}`
                });
            }
        }

        // Validar palavras-chave
        if (palavras_chave && !Array.isArray(palavras_chave)) {
            return res.status(400).json({ message: 'Palavras-chave deve ser um array' });
        }

        if (palavras_chave && palavras_chave.length === 0) {
            return res.status(400).json({ message: 'Deve haver pelo menos uma palavra-chave' });
        }

        // Preparar atualização
        const atualizacoes = {};
        if (tipo) atualizacoes.tipo = tipo;
        if (resposta) atualizacoes.resposta = resposta;
        if (categoria !== undefined) atualizacoes.categoria = categoria;
        if (palavras_chave) atualizacoes.palavras_chave = palavras_chave.map(p => p.toLowerCase().trim());
        if (prioridade !== undefined) atualizacoes.prioridade = prioridade;
        if (ativo !== undefined) atualizacoes.ativo = ativo;
        atualizacoes.atualizado_em = new Date().toISOString();

        gerenciador.atualizarComando(id, atualizacoes);
        await gerenciador.salvar();

        const comandoAtualizado = gerenciador.obterComandoPorId(id);
        logger.info('Comando atualizado', { id });
        res.json(comandoAtualizado);
    } catch (erro) {
        logger.erro('Erro ao atualizar comando', { id: req.params.id, erro: erro.message });
        res.status(500).json({ message: 'Erro ao atualizar comando' });
    }
});

/**
 * DELETE /api/base-conhecimento/:id
 * Deleta comando
 */
router.delete('/api/base-conhecimento/:id', async (req, res) => {
    try {
        const { id } = req.params;

        const comando = gerenciador.obterComandoPorId(id);
        if (!comando) {
            return res.status(404).json({ message: 'Comando não encontrado' });
        }

        gerenciador.deletarComando(id);
        await gerenciador.salvar();

        logger.info('Comando deletado', { id });
        res.json({ message: 'Comando deletado com sucesso', id });
    } catch (erro) {
        logger.erro('Erro ao deletar comando', { id: req.params.id, erro: erro.message });
        res.status(500).json({ message: 'Erro ao deletar comando' });
    }
});

/**
 * GET /api/base-conhecimento/configuracoes
 * Obtém configurações atuais
 */
router.get('/api/base-conhecimento/configuracoes', async (req, res) => {
    try {
        const configuracoes = gerenciador.obterConfiguracoes();
        res.json(configuracoes);
    } catch (erro) {
        logger.erro('Erro ao obter configurações', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao obter configurações' });
    }
});

/**
 * PUT /api/base-conhecimento/configuracoes
 * Atualiza configurações
 */
router.put('/api/base-conhecimento/configuracoes', async (req, res) => {
    try {
        const configuracoes = req.body;

        // Validar valores
        if (configuracoes.minimo_confianca && (configuracoes.minimo_confianca < 0 || configuracoes.minimo_confianca > 100)) {
            return res.status(400).json({ message: 'Confiança mínima deve estar entre 0 e 100' });
        }

        if (configuracoes.tempo_resposta_segundos && configuracoes.tempo_resposta_segundos < 1) {
            return res.status(400).json({ message: 'Tempo de resposta deve ser maior que 1' });
        }

        gerenciador.atualizarConfiguracoes(configuracoes);
        await gerenciador.salvar();

        logger.info('Configurações atualizadas');
        res.json({ message: 'Configurações salvas', configuracoes: gerenciador.obterConfiguracoes() });
    } catch (erro) {
        logger.erro('Erro ao atualizar configurações', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao atualizar configurações' });
    }
});

/**
 * POST /api/base-conhecimento/buscar
 * Busca comandos por termo
 */
router.post('/api/base-conhecimento/buscar', async (req, res) => {
    try {
        const { termo, tipo } = req.body;

        if (!termo && !tipo) {
            return res.status(400).json({ message: 'Fornça um termo ou tipo para buscar' });
        }

        let resultados = gerenciador.obterComandos();

        if (termo) {
            const termoLower = termo.toLowerCase();
            resultados = resultados.filter(cmd =>
                cmd.id.toLowerCase().includes(termoLower) ||
                cmd.resposta.toLowerCase().includes(termoLower) ||
                cmd.palavras_chave.some(p => p.includes(termoLower))
            );
        }

        if (tipo) {
            resultados = resultados.filter(cmd => cmd.tipo === tipo);
        }

        res.json(resultados);
    } catch (erro) {
        logger.erro('Erro ao buscar comandos', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao buscar comandos' });
    }
});

/**
 * POST /api/base-conhecimento/testar
 * Testa um comando contra uma mensagem
 */
router.post('/api/base-conhecimento/testar', async (req, res) => {
    try {
        const { mensagem } = req.body;

        if (!mensagem) {
            return res.status(400).json({ message: 'Mensagem é obrigatória' });
        }

        const resultado = gerenciador.encontrarComando(mensagem);

        res.json({
            mensagem,
            encontrado: resultado ? true : false,
            comando: resultado || null,
            confidencia: resultado ? resultado.score : 0
        });
    } catch (erro) {
        logger.erro('Erro ao testar comando', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao testar comando' });
    }
});

/**
 * GET /api/base-conhecimento/estatisticas
 * Retorna estatísticas da base
 */
router.get('/api/base-conhecimento/estatisticas', async (req, res) => {
    try {
        const stats = gerenciador.obterEstatisticas();
        res.json(stats);
    } catch (erro) {
        logger.erro('Erro ao obter estatísticas', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao obter estatísticas' });
    }
});

/**
 * POST /api/base-conhecimento/importar
 * Importa base de conhecimento a partir de JSON
 */
router.post('/api/base-conhecimento/importar', async (req, res) => {
    try {
        let json;

        // Tentar parsear como JSON string
        if (typeof req.body === 'string') {
            json = JSON.parse(req.body);
        } else {
            json = req.body;
        }

        // Validar estrutura
        if (!Array.isArray(json) && !json.comandos) {
            return res.status(400).json({
                message: 'Formato inválido. Deve ser um array de comandos ou objeto com propriedade "comandos"'
            });
        }

        gerenciador.importar(json);
        await gerenciador.salvar();

        logger.info('Base de conhecimento importada');
        res.json({
            message: 'Base importada com sucesso',
            total: gerenciador.obterComandos().length
        });
    } catch (erro) {
        logger.erro('Erro ao importar base', { erro: erro.message });
        res.status(400).json({ message: `Erro ao importar: ${erro.message}` });
    }
});

/**
 * GET /api/base-conhecimento/exportar
 * Exporta base de conhecimento como JSON
 */
router.get('/api/base-conhecimento/exportar', async (req, res) => {
    try {
        const dados = gerenciador.exportar();

        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Content-Disposition', `attachment; filename="base-conhecimento-${new Date().getTime()}.json"`);
        res.send(JSON.stringify(dados, null, 2));

        logger.info('Base de conhecimento exportada');
    } catch (erro) {
        logger.erro('Erro ao exportar base', { erro: erro.message });
        res.status(500).json({ message: 'Erro ao exportar base' });
    }
});

/**
 * PATCH /api/base-conhecimento/:id/ativar
 * Ativa comando
 */
router.patch('/api/base-conhecimento/:id/ativar', async (req, res) => {
    try {
        const { id } = req.params;

        const comando = gerenciador.obterComandoPorId(id);
        if (!comando) {
            return res.status(404).json({ message: 'Comando não encontrado' });
        }

        gerenciador.ativarDesativarComando(id, true);
        await gerenciador.salvar();

        logger.info('Comando ativado', { id });
        res.json({ message: 'Comando ativado', id });
    } catch (erro) {
        logger.erro('Erro ao ativar comando', { id: req.params.id, erro: erro.message });
        res.status(500).json({ message: 'Erro ao ativar comando' });
    }
});

/**
 * PATCH /api/base-conhecimento/:id/desativar
 * Desativa comando
 */
router.patch('/api/base-conhecimento/:id/desativar', async (req, res) => {
    try {
        const { id } = req.params;

        const comando = gerenciador.obterComandoPorId(id);
        if (!comando) {
            return res.status(404).json({ message: 'Comando não encontrado' });
        }

        gerenciador.ativarDesativarComando(id, false);
        await gerenciador.salvar();

        logger.info('Comando desativado', { id });
        res.json({ message: 'Comando desativado', id });
    } catch (erro) {
        logger.erro('Erro ao desativar comando', { id: req.params.id, erro: erro.message });
        res.status(500).json({ message: 'Erro ao desativar comando' });
    }
});

module.exports = router;
