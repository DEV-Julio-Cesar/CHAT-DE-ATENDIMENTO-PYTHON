/**
 * Gerenciador de Base de Conhecimento do Robô
 * Permite adicionar, editar, deletar e usar comandos/respostas
 */

const fs = require('fs-extra');
const path = require('path');
const logger = require('../infraestrutura/logger');

const BASE_CONHECIMENTO_FILE = path.join(__dirname, '../../dados/base-conhecimento-robo.json');

class GerenciadorBaseConhecimento {
    constructor() {
        this.baseConhecimento = null;
        this.cache = new Map();
    }

    /**
     * Carrega a base de conhecimento do arquivo
     */
    async carregar() {
        try {
            if (!await fs.pathExists(BASE_CONHECIMENTO_FILE)) {
                logger.info('[Base Conhecimento] Arquivo não existe, criando...');
                await this.criarPadrao();
            }

            this.baseConhecimento = await fs.readJson(BASE_CONHECIMENTO_FILE);
            this._construirCache();
            logger.info('[Base Conhecimento] Carregada com sucesso');
            return this.baseConhecimento;
        } catch (erro) {
            logger.erro('[Base Conhecimento] Erro ao carregar:', erro.message);
            return null;
        }
    }

    /**
     * Salva a base de conhecimento no arquivo
     */
    async salvar() {
        try {
            await fs.writeJson(BASE_CONHECIMENTO_FILE, this.baseConhecimento, { spaces: 2 });
            this._construirCache();
            logger.info('[Base Conhecimento] Salva com sucesso');
            return { success: true };
        } catch (erro) {
            logger.erro('[Base Conhecimento] Erro ao salvar:', erro.message);
            return { success: false, message: erro.message };
        }
    }

    /**
     * Cria arquivo padrão
     */
    async criarPadrao() {
        try {
            const padrao = {
                comandos: [],
                configuracoes: {
                    usar_base_conhecimento: true,
                    usar_ia_gemini: true,
                    fazer_fallback_ia: true,
                    minimo_confianca: 70,
                    tempo_resposta_segundos: 15,
                    resposta_padrao_nao_entendi: 'Desculpe, não entendi. Um atendente irá ajudá-lo!'
                }
            };

            await fs.writeJson(BASE_CONHECIMENTO_FILE, padrao, { spaces: 2 });
            this.baseConhecimento = padrao;
            logger.info('[Base Conhecimento] Arquivo padrão criado');
        } catch (erro) {
            logger.erro('[Base Conhecimento] Erro ao criar padrão:', erro.message);
        }
    }

    /**
     * Procura um comando pela mensagem do cliente
     */
    async encontrarComando(mensagem) {
        if (!this.baseConhecimento) {
            await this.carregar();
        }

        const mensagemLower = mensagem.toLowerCase().trim();
        let melhorMatch = null;
        let melhorScore = 0;

        // Procurar em ordem de prioridade
        const comandosOrdenados = [...this.baseConhecimento.comandos]
            .filter(cmd => cmd.ativo)
            .sort((a, b) => b.prioridade - a.prioridade);

        for (const comando of comandosOrdenados) {
            const score = this._calcularScore(mensagemLower, comando.palavras_chave);

            if (score > melhorScore) {
                melhorScore = score;
                melhorMatch = { ...comando, confianca: score };
            }
        }

        // Retornar apenas se confiança mínima atingida
        const minConfianca = this.baseConhecimento.configuracoes.minimo_confianca || 70;

        if (melhorScore >= minConfianca) {
            return melhorMatch;
        }

        return null;
    }

    /**
     * Calcula score de correspondência
     */
    _calcularScore(mensagem, palavrasChave) {
        let matches = 0;

        for (const palavra of palavrasChave) {
            if (mensagem.includes(palavra.toLowerCase())) {
                matches++;
            }
        }

        // Score: (matches encontradas / total de palavras chave) * 100
        return (matches / palavrasChave.length) * 100;
    }

    /**
     * Obtém todos os comandos
     */
    obterComandos() {
        if (!this.baseConhecimento) {
            return [];
        }

        return this.baseConhecimento.comandos.sort((a, b) => b.prioridade - a.prioridade);
    }

    /**
     * Obtém um comando por ID
     */
    obterComandoPorId(id) {
        if (!this.baseConhecimento) {
            return null;
        }

        return this.baseConhecimento.comandos.find(cmd => cmd.id === id);
    }

    /**
     * Cria um novo comando
     */
    async criarComando(comando) {
        if (!this.baseConhecimento) {
            await this.carregar();
        }

        // Validar
        if (!comando.id || !comando.resposta || !comando.palavras_chave) {
            return { success: false, message: 'ID, resposta e palavras-chave são obrigatórios' };
        }

        // Verificar duplicata
        if (this.baseConhecimento.comandos.find(cmd => cmd.id === comando.id)) {
            return { success: false, message: 'Já existe um comando com este ID' };
        }

        // Definir padrões
        const novoComando = {
            id: comando.id,
            palavras_chave: comando.palavras_chave || [],
            tipo: comando.tipo || 'generico',
            resposta: comando.resposta,
            prioridade: comando.prioridade || 5,
            ativo: comando.ativo !== false,
            criado_em: new Date(),
            atualizado_em: new Date()
        };

        this.baseConhecimento.comandos.push(novoComando);
        await this.salvar();

        logger.info(`[Base Conhecimento] Comando criado: ${comando.id}`);
        return { success: true, comando: novoComando };
    }

    /**
     * Atualiza um comando existente
     */
    async atualizarComando(id, atualizacoes) {
        if (!this.baseConhecimento) {
            await this.carregar();
        }

        const indice = this.baseConhecimento.comandos.findIndex(cmd => cmd.id === id);

        if (indice === -1) {
            return { success: false, message: 'Comando não encontrado' };
        }

        // Atualizar
        this.baseConhecimento.comandos[indice] = {
            ...this.baseConhecimento.comandos[indice],
            ...atualizacoes,
            id, // Não permite mudar ID
            atualizado_em: new Date()
        };

        await this.salvar();

        logger.info(`[Base Conhecimento] Comando atualizado: ${id}`);
        return { success: true, comando: this.baseConhecimento.comandos[indice] };
    }

    /**
     * Deleta um comando
     */
    async deletarComando(id) {
        if (!this.baseConhecimento) {
            await this.carregar();
        }

        const indice = this.baseConhecimento.comandos.findIndex(cmd => cmd.id === id);

        if (indice === -1) {
            return { success: false, message: 'Comando não encontrado' };
        }

        const deletado = this.baseConhecimento.comandos.splice(indice, 1)[0];
        await this.salvar();

        logger.info(`[Base Conhecimento] Comando deletado: ${id}`);
        return { success: true, comando: deletado };
    }

    /**
     * Obtém as configurações
     */
    obterConfiguracoes() {
        if (!this.baseConhecimento) {
            return {};
        }

        return this.baseConhecimento.configuracoes;
    }

    /**
     * Atualiza as configurações
     */
    async atualizarConfiguracoes(novasConfigs) {
        if (!this.baseConhecimento) {
            await this.carregar();
        }

        this.baseConhecimento.configuracoes = {
            ...this.baseConhecimento.configuracoes,
            ...novasConfigs
        };

        await this.salvar();

        logger.info('[Base Conhecimento] Configurações atualizadas');
        return { success: true, configuracoes: this.baseConhecimento.configuracoes };
    }

    /**
     * Ativa/desativa um comando
     */
    async ativarDesativarComando(id, ativo) {
        return this.atualizarComando(id, { ativo });
    }

    /**
     * Constrói cache interno
     */
    _construirCache() {
        this.cache.clear();

        if (!this.baseConhecimento) return;

        this.baseConhecimento.comandos.forEach(cmd => {
            if (cmd.ativo) {
                cmd.palavras_chave.forEach(palavra => {
                    if (!this.cache.has(palavra)) {
                        this.cache.set(palavra, []);
                    }
                    this.cache.get(palavra).push(cmd.id);
                });
            }
        });
    }

    /**
     * Obtém estatísticas da base de conhecimento
     */
    obterEstatisticas() {
        if (!this.baseConhecimento) {
            return {
                total_comandos: 0,
                comandos_ativos: 0,
                comandos_inativos: 0,
                tipos: {}
            };
        }

        const comandos = this.baseConhecimento.comandos;
        const tipos = {};

        comandos.forEach(cmd => {
            tipos[cmd.tipo] = (tipos[cmd.tipo] || 0) + 1;
        });

        return {
            total_comandos: comandos.length,
            comandos_ativos: comandos.filter(c => c.ativo).length,
            comandos_inativos: comandos.filter(c => !c.ativo).length,
            tipos
        };
    }

    /**
     * Exporta a base de conhecimento em JSON
     */
    exportar() {
        return JSON.stringify(this.baseConhecimento, null, 2);
    }

    /**
     * Importa uma base de conhecimento
     */
    async importar(json) {
        try {
            const dados = JSON.parse(json);

            // Validar estrutura
            if (!dados.comandos || !Array.isArray(dados.comandos)) {
                return { success: false, message: 'Estrutura inválida' };
            }

            this.baseConhecimento = dados;
            await this.salvar();

            logger.info('[Base Conhecimento] Importada com sucesso');
            return { success: true };
        } catch (erro) {
            logger.erro('[Base Conhecimento] Erro ao importar:', erro.message);
            return { success: false, message: erro.message };
        }
    }

    /**
     * Procura por comandos
     */
    buscar(termo) {
        if (!this.baseConhecimento) {
            return [];
        }

        const termoLower = termo.toLowerCase();

        return this.baseConhecimento.comandos.filter(cmd =>
            cmd.id.includes(termoLower) ||
            cmd.resposta.toLowerCase().includes(termoLower) ||
            cmd.palavras_chave.some(p => p.includes(termoLower))
        );
    }
}

module.exports = GerenciadorBaseConhecimento;
