// Serviço de IA Humanizada
// Integra prompts contextualizados com Gemini para respostas humanizadas

const GeradorPromptsIA = require('./gerador-prompts-ia');
const { enviarPerguntaGemini } = require('./ia-gemini');
const logger = require('../infraestrutura/logger');

class ServicoIAHumanizada {
    constructor(configChatbot = {}) {
        this.gerador = new GeradorPromptsIA(configChatbot);
        this.configChatbot = configChatbot;
        this.conversas = new Map(); // Armazena conversas por cliente
    }

    /**
     * Processa mensagem do cliente e retorna resposta humanizada
     */
    async procesarMensagemCliente(mensagemCliente, idCliente, tipoSolicitacao = 'duvida', infoCliente = {}) {
        try {
            logger.info(`[IA Humanizada] Processando mensagem de ${idCliente}`);

            // Recupera ou cria conversa do cliente
            let conversa = this.conversas.get(idCliente);
            if (!conversa) {
                conversa = {
                    gerador: new GeradorPromptsIA(this.configChatbot),
                    idCliente,
                    nomeCliente: infoCliente.nome || 'Cliente',
                    primeiraInteracao: true,
                    ultimaAtualizacao: new Date()
                };
                this.conversas.set(idCliente, conversa);
            }

            // Cria prompt contextualizado
            const prompt = conversa.primeiraInteracao
                ? conversa.gerador.criarPromptPrimeiraInteracao(conversa.nomeCliente, {
                    servico: this.configChatbot.servico || 'atendimento'
                })
                : conversa.gerador.criarPromptContextualizado(
                    mensagemCliente,
                    this._mapearTipoSolicitacao(tipoSolicitacao),
                    conversa.gerador.historicoConversa
                );

            // Envia para Gemini com contexto
            const resposta = await enviarPerguntaGemini({
                mensagem: mensagemCliente,
                contexto: [
                    { role: 'user', parts: [{ text: prompt }] }
                ]
            });

            if (resposta.success) {
                // Adiciona ao histórico
                conversa.gerador.adicionarAoHistorico('user', mensagemCliente);
                conversa.gerador.adicionarAoHistorico('model', resposta.resposta);
                conversa.primeiraInteracao = false;
                conversa.ultimaAtualizacao = new Date();

                logger.info(`[IA Humanizada] Resposta gerada com sucesso para ${idCliente}`);
                
                return {
                    success: true,
                    resposta: resposta.resposta,
                    tipo: tipoSolicitacao,
                    timestamp: new Date()
                };
            } else {
                logger.erro(`[IA Humanizada] Erro ao gerar resposta: ${resposta.message}`);
                return {
                    success: false,
                    resposta: 'Desculpe, estou tendo dificuldades no momento. Um atendente irá ajudá-lo em breve!',
                    message: resposta.message
                };
            }

        } catch (erro) {
            logger.erro('[IA Humanizada] Erro ao processar mensagem:', erro);
            return {
                success: false,
                resposta: 'Desculpe, algo saiu do esperado. Estamos aqui para ajudar - um atendente irá responder em breve!',
                error: erro.message
            };
        }
    }

    /**
     * Processa problema técnico com histórico
     */
    async processarProblemaComHistorico(descricaoProblema, idCliente, tentativasAnteriores = []) {
        try {
            let conversa = this.conversas.get(idCliente);
            if (!conversa) {
                conversa = {
                    gerador: new GeradorPromptsIA(this.configChatbot),
                    idCliente,
                    nomeCliente: 'Cliente',
                    primeiraInteracao: true,
                    ultimaAtualizacao: new Date()
                };
                this.conversas.set(idCliente, conversa);
            }

            const prompt = conversa.gerador.criarPromptResolucaoProblema(
                descricaoProblema,
                tentativasAnteriores
            );

            const resposta = await enviarPerguntaGemini({
                mensagem: descricaoProblema,
                contexto: [
                    { role: 'user', parts: [{ text: prompt }] }
                ]
            });

            if (resposta.success) {
                conversa.gerador.adicionarAoHistorico('user', descricaoProblema);
                conversa.gerador.adicionarAoHistorico('model', resposta.resposta);
                conversa.ultimaAtualizacao = new Date();

                return {
                    success: true,
                    resposta: resposta.resposta,
                    tipo: 'resolucao_problema'
                };
            }

            return {
                success: false,
                resposta: 'Vamos resolver isso juntos! Deixa que eu consulto nossos especialistas e volto pra você em breve!'
            };

        } catch (erro) {
            logger.erro('[IA Humanizada] Erro ao processar problema:', erro);
            return {
                success: false,
                resposta: 'Vou transferir você para um especialista que poderá resolver isso melhor!'
            };
        }
    }

    /**
     * Processa cliente insatisfeito
     */
    async processarClienteInsatisfeito(motivo, idCliente, historicoProblema = '') {
        try {
            let conversa = this.conversas.get(idCliente);
            if (!conversa) {
                conversa = {
                    gerador: new GeradorPromptsIA(this.configChatbot),
                    idCliente,
                    nomeCliente: 'Cliente',
                    primeiraInteracao: false,
                    ultimaAtualizacao: new Date()
                };
                this.conversas.set(idCliente, conversa);
            }

            const prompt = conversa.gerador.criarPromptClienteInsatisfeito(motivo, historicoProblema);

            const resposta = await enviarPerguntaGemini({
                mensagem: motivo,
                contexto: [
                    { role: 'user', parts: [{ text: prompt }] }
                ]
            });

            if (resposta.success) {
                conversa.gerador.adicionarAoHistorico('user', motivo);
                conversa.gerador.adicionarAoHistorico('model', resposta.resposta);
                conversa.ultimaAtualizacao = new Date();

                return {
                    success: true,
                    resposta: resposta.resposta,
                    tipo: 'insatisfacao'
                };
            }

            return {
                success: false,
                resposta: 'Sinto muito pelos problemas. Um gerente irá entrar em contato com você pessoalmente em breve para resolver isso!'
            };

        } catch (erro) {
            logger.erro('[IA Humanizada] Erro ao processar insatisfação:', erro);
            return {
                success: false,
                resposta: 'Lamento pelos contratempos. Vou garantir que você receba atenção especial em breve!'
            };
        }
    }

    /**
     * Faz uma pergunta de diagnóstico
     */
    async fazerPerguntaDiagnostica(situacao, idCliente) {
        try {
            const prompt = `
Você é um assistente de diagnóstico empático e inteligente.

Situação: ${situacao}

Seu objetivo é fazer UMA pergunta bem pensada que ajude a entender melhor a situação do cliente.

INSTRUÇÕES:
- Seja empático e reconheça o que o cliente descreveu
- Faça uma pergunta aberta e relevante
- Não faça mais de uma pergunta por vez
- Mostre que você entende o contexto
- Use linguagem natural e amigável

Formato: Primeiro reconheça a situação, depois faça a pergunta.
            `;

            const resposta = await enviarPerguntaGemini({
                mensagem: situacao,
                contexto: [
                    { role: 'user', parts: [{ text: prompt }] }
                ]
            });

            return resposta.success 
                ? { success: true, pergunta: resposta.resposta }
                : { success: false, pergunta: 'Qual mais específico você pode ser sobre o problema?' };

        } catch (erro) {
            logger.erro('[IA Humanizada] Erro ao fazer pergunta diagnóstica:', erro);
            return { 
                success: false, 
                pergunta: 'Pode me contar mais detalhes do que está acontecendo?' 
            };
        }
    }

    /**
     * Gera resposta para feedback positivo
     */
    async responderFeedbackPositivo(feedbackTexto, idCliente, nomeCliente = 'Cliente') {
        try {
            const prompt = `
Você está recebendo feedback POSITIVO de um cliente.

Feedback: ${feedbackTexto}

Seu objetivo é responder com gratidão genuína, reconhecer o feedback e deixar o cliente sabendo que é apreciado.

INSTRUÇÕES:
- Seja genuinamente grato
- Reconheça o feedback específico
- Mostre que a opinião dele importa
- Ofereça ajuda futura

Use tom caloroso e sincero.
            `;

            const resposta = await enviarPerguntaGemini({
                mensagem: feedbackTexto,
                contexto: [
                    { role: 'user', parts: [{ text: prompt }] }
                ]
            });

            return resposta.success
                ? { success: true, resposta: resposta.resposta }
                : { 
                    success: false, 
                    resposta: `Fico feliz em saber que apreciou! ${nomeCliente}, sua satisfação é nossa prioridade!` 
                  };

        } catch (erro) {
            logger.erro('[IA Humanizada] Erro ao responder feedback:', erro);
            return { 
                success: false, 
                resposta: 'Obrigado pelo feedback! Vamos continuar melhorando para você!' 
            };
        }
    }

    /**
     * Limpa histórico de uma conversa
     */
    limparConversa(idCliente) {
        if (this.conversas.has(idCliente)) {
            this.conversas.delete(idCliente);
            logger.info(`[IA Humanizada] Conversa de ${idCliente} limpa`);
            return { success: true };
        }
        return { success: false, message: 'Conversa não encontrada' };
    }

    /**
     * Retorna informações da conversa
     */
    obterInfoConversa(idCliente) {
        const conversa = this.conversas.get(idCliente);
        if (!conversa) return null;

        return {
            idCliente: conversa.idCliente,
            nomeCliente: conversa.nomeCliente,
            primeiraInteracao: conversa.primeiraInteracao,
            ultimaAtualizacao: conversa.ultimaAtualizacao,
            totalMensagens: conversa.gerador.historicoConversa.length
        };
    }

    /**
     * Mapeia tipo de solicitação para perfil adequado
     */
    _mapearTipoSolicitacao(tipo) {
        const mapa = {
            'saudacao': 'primeira_interacao',
            'duvida': 'duvida',
            'problema': 'problema',
            'feedback': 'feedback',
            'oferta': 'oferta',
            'reclamacao': 'insatisfacao',
            'sugestao': 'feedback'
        };
        return mapa[tipo] || 'duvida';
    }
}

module.exports = ServicoIAHumanizada;
