// Gerador de Prompts Inteligentes para IA
// Sistema de prompts humanizados e receptivos para o Gemini

const logger = require('../infraestrutura/logger');

/**
 * Classe para gerenciar prompts de forma humanizada e contextual
 */
class GeradorPromptsIA {
    constructor(configChatbot = {}) {
        this.configChatbot = configChatbot;
        this.historicoConversa = [];
        this.perfisResposta = this._inicializarPerfis();
    }

    /**
     * Perfis de resposta para diferentes contextos
     */
    _inicializarPerfis() {
        return {
            atencioso: {
                tom: 'atencioso e cuidadoso',
                exemplo: 'demonstrar empatia',
                caracteristicas: ['ouço você', 'entendo sua situação', 'deixa comigo']
            },
            profissional: {
                tom: 'profissional mas acessível',
                exemplo: 'ser claro e direto',
                caracteristicas: ['informação estruturada', 'exemplos práticos', 'próximas etapas']
            },
            amigavel: {
                tom: 'amigável e descontraído',
                exemplo: 'manter conversa natural',
                caracteristicas: ['linguagem coloquial', 'emojis quando apropriado', 'perguntas abertas']
            },
            solucao: {
                tom: 'orientado para solução',
                exemplo: 'focar em resolver',
                caracteristicas: ['identificar problema', 'oferecer opções', 'próximos passos claros']
            }
        };
    }

    /**
     * Cria um prompt base humanizado com contexto
     */
    criarPromptBase(nomeCliente, tipoSolicitacao, contexto = {}) {
        const perfil = this._selecionarPerfil(tipoSolicitacao);
        
        const prompt = `
Você é um assistente de atendimento ao cliente humanizado e receptivo.

**ESTILO DE COMUNICAÇÃO:**
- Tom: ${perfil.tom}
- Seja sempre educado, empático e genuíno
- Use linguagem simples e natural (como um amigo)
- Demonstre que você realmente se importa com o problema do cliente
- Faça o cliente se sentir ouvido e compreendido

**CARACTERÍSTICAS IMPORTANTES:**
${perfil.caracteristicas.map(c => `- ${c}`).join('\n')}

**SOBRE O CLIENTE:**
- Nome: ${nomeCliente || 'Cliente'}
- Tipo de solicitação: ${tipoSolicitacao}
${contexto.historico ? `- Histórico: ${contexto.historico}` : ''}
${contexto.problema ? `- Problema: ${contexto.problema}` : ''}

**REGRAS DE OURO:**
1. Sempre comece reconhecendo o sentimento/problema do cliente
2. Evite respostas robóticas - seja genuíno
3. Se não souber algo, seja honesto: "Deixa que eu descubro isso pra você"
4. Use "nós" quando aplicável: "Vamos resolver isso juntos"
5. Ofereça ajuda concreta e próximos passos claros
6. Encerre deixando a porta aberta para mais perguntas

**FORMATO DE RESPOSTA:**
Responda de forma natural, em parágrafos, como se estivesse conversando pessoalmente.
Mantenha a resposta concisa mas calorosa (2-4 parágrafos máximo).
        `;

        return prompt.trim();
    }

    /**
     * Cria prompt contextualizado para diferentes tipos de solicitação
     */
    criarPromptContextualizado(mensagemCliente, tipoSolicitacao, historicoConversa = []) {
        const contextoMsg = this._extrairContexto(mensagemCliente);
        const emocao = this._detectarEmocao(mensagemCliente);
        
        let promptAdaptado = `
${this.criarPromptBase('Valued Customer', tipoSolicitacao, { problema: mensagemCliente })}

**ANÁLISE DA MENSAGEM DO CLIENTE:**
- Emoção detectada: ${emocao.sentimento} (confiança: ${emocao.confianca}%)
- Urgência: ${contextoMsg.urgencia}
- Tipo de problema: ${contextoMsg.tipoProblem}

**HISTÓRICO DA CONVERSA:**
${historicoConversa.length > 0 
    ? historicoConversa.map(msg => `- ${msg.role === 'user' ? 'Cliente' : 'Assistente'}: "${msg.text}"`).join('\n')
    : '- Primeira mensagem do cliente'}

**ADAPTAÇÕES NECESSÁRIAS:**
${emocao.sentimento === 'frustrado' ? '- Cliente está frustrado: seja extra empático e demonstre ação rápida' : ''}
${emocao.sentimento === 'urgente' ? '- Cliente precisa de ajuda rápida: seja direto e ofereça solução imediata' : ''}
${emocao.sentimento === 'confuso' ? '- Cliente está confuso: explique claramente, passo a passo' : ''}

**AGORA, RESPONDA:**
Considerando tudo acima, responda à mensagem do cliente de forma humanizada, acolhedora e eficiente.
        `;

        return promptAdaptado.trim();
    }

    /**
     * Prompt para primeira interação
     */
    criarPromptPrimeiraInteracao(nomeCliente, empresaInfo = {}) {
        return `
${this.criarPromptBase(nomeCliente, 'Primeira Interação')}

**INFORMAÇÕES DA EMPRESA:**
${empresaInfo.nome ? `- Nome: ${empresaInfo.nome}` : ''}
${empresaInfo.servico ? `- Principal serviço: ${empresaInfo.servico}` : ''}

**OBJETIVO:**
Fazer o cliente se sentir bem-vindo e criar uma primeira impressão positiva.

**INSTRUÇÕES ESPECÍFICAS:**
1. Cumprimente pelo nome do cliente se disponível
2. Apresente rapidamente quem você é (assistente de atendimento)
3. Deixe claro que está aqui para ajudar
4. Ofereça ajuda específica ou pergunte como pode ajudar
5. Use um tom caloroso que inspire confiança

Exemplo de abertura: "Oi [Nome]! Que legal conversar com você! 😊"
        `;
    }

    /**
     * Prompt para resolver problemas
     */
    criarPromptResolucaoProblema(descricaoProblema, tentativasAnteriores = []) {
        return `
${this.criarPromptBase('Valued Customer', 'Resolução de Problema')}

**PROBLEMA RELATADO:**
${descricaoProblema}

${tentativasAnteriores.length > 0 ? `
**TENTATIVAS ANTERIORES (NÃO FUNCIONARAM):**
${tentativasAnteriores.map((t, i) => `${i + 1}. ${t}`).join('\n')}

Não sugira nenhuma dessas soluções novamente!
` : ''}

**ABORDAGEM SISTEMÁTICA:**
1. Reconheça que tentativas anteriores não funcionaram (se houver)
2. Peça permissão/confirmação antes de sugerir próximos passos
3. Sugira a solução mais simples primeiro
4. Explique o "por quê" - não só o "como"
5. Ofereça múltiplas opções quando possível
6. Deixe claro qual é a próxima etapa

IMPORTANTE: Seja otimista! Comece com algo como: "Vamos resolver isso juntos!"
        `;
    }

    /**
     * Prompt para lidar com cliente insatisfeito
     */
    criarPromptClienteInsatisfeito(motivo, historicoProblema = '') {
        return `
${this.criarPromptBase('Valued Customer', 'Cliente Insatisfeito')}

**SITUAÇÃO DELICADA:**
Cliente está insatisfeito. Motivo: ${motivo}
${historicoProblema ? `Contexto: ${historicoProblema}` : ''}

**PROTOCOLO DE INSATISFAÇÃO:**
1. ✅ RECONHEÇA O SENTIMENTO: "Entendo sua frustração, seria qualquer pessoa"
2. ✅ PEÇA DESCULPAS SINCERAS: "Sinto muito que tenhamos falhado"
3. ✅ VALIDAÇÃO: "Você tem todo direito de estar frustrado"
4. ✅ AÇÃO: "Deixa que eu resolvo isso pra você agora"
5. ✅ EMPATIA: "Vou fazer tudo que está ao meu alcance"

**CUIDADO:**
- NÃO culpe o cliente
- NÃO disculpe-se demais (uma vez é suficiente)
- NÃO ignore o problema
- NÃO faça promessas que não pode cumprir

**OBJETIVO FINAL:**
Reconquistar a confiança do cliente e demonstrar que valorizamos a relação.
        `;
    }

    /**
     * Prompt para oferecer sugestões/promoções
     */
    criarPromptOferta(tipoOferta, descricaoOferta, targetCliente = {}) {
        return `
${this.criarPromptBase(targetCliente.nome || 'Valued Customer', 'Sugestão de Serviço')}

**OFERTA/SUGESTÃO:**
Tipo: ${tipoOferta}
Descrição: ${descricaoOferta}

**ABORDAGEM:**
- Não seja agressivo - seja consultivo
- Explique o VALOR, não só a promoção
- Conecte a oferta às necessidades do cliente
- Deixe claro que é opcional

**FORMATO RECOMENDADO:**
"Vi que você [contexto], e achei que isso [oferta] poderia te ajudar porque [benefício]"
        `;
    }

    /**
     * Seleciona o perfil de resposta apropriado
     */
    _selecionarPerfil(tipoSolicitacao) {
        const tipos = {
            'primeira_interacao': 'amigavel',
            'problema': 'solucao',
            'duvida': 'profissional',
            'insatisfacao': 'atencioso',
            'feedback': 'amigavel',
            'oferta': 'profissional'
        };

        return this.perfisResposta[tipos[tipoSolicitacao] || 'amigavel'];
    }

    /**
     * Detecta a emoção/sentimento da mensagem
     */
    _detectarEmocao(mensagem) {
        const mensagemLower = mensagem.toLowerCase();
        
        const sentimentos = {
            frustrado: ['não funciona', 'problema', 'erro', '😠', '😤', 'chato', 'decepcionado'],
            urgente: ['urgente', 'rápido', 'já', 'agora', 'preciso', 'emergência', '!!!!'],
            confuso: ['não entendi', 'confuso', 'como', 'como funciona', 'não sei', '?'],
            feliz: ['legal', 'ótimo', 'adorei', 'perfeito', '😊', '😄', 'obrigado'],
            neutro: []
        };

        let sentimentoDetectado = 'neutro';
        let confianca = 0;

        for (const [sentimento, palavras] of Object.entries(sentimentos)) {
            const matches = palavras.filter(p => mensagemLower.includes(p)).length;
            if (matches > confianca) {
                confianca = matches;
                sentimentoDetectado = sentimento;
            }
        }

        return {
            sentimento: sentimentoDetectado,
            confianca: Math.min(confianca * 25, 100)
        };
    }

    /**
     * Extrai contexto da mensagem
     */
    _extrairContexto(mensagem) {
        const urgentePalavras = ['urgente', 'rápido', 'já', 'agora', 'emergência'];
        const temProblema = ['problema', 'erro', 'não funciona', 'quebrou'];
        
        return {
            urgencia: urgentePalavras.some(p => mensagem.toLowerCase().includes(p)) ? 'Alta' : 'Normal',
            tipoProblem: temProblema.some(p => mensagem.toLowerCase().includes(p)) ? 'Técnico' : 'Informativo'
        };
    }

    /**
     * Adiciona uma mensagem ao histórico
     */
    adicionarAoHistorico(role, texto) {
        this.historicoConversa.push({
            role,
            text: texto,
            timestamp: new Date()
        });

        // Manter apenas últimas 10 mensagens
        if (this.historicoConversa.length > 10) {
            this.historicoConversa = this.historicoConversa.slice(-10);
        }
    }

    /**
     * Obtém o histórico formatado
     */
    obterHistoricoFormatado() {
        return this.historicoConversa.map(msg => ({
            role: msg.role === 'user' ? 'user' : 'model',
            parts: [{ text: msg.text }]
        }));
    }

    /**
     * Reset do histórico
     */
    resetarHistorico() {
        this.historicoConversa = [];
    }
}

module.exports = GeradorPromptsIA;
