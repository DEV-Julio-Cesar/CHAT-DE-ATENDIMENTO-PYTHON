const fs = require('fs-extra');
const path = require('path');

const FILE_PATH = path.join(__dirname, '../../dados/automacao-config.json');

const DEFAULT_CONFIG = {
    basePrompt: 'Você é um assistente virtual especializado em atendimento ao cliente da nossa operação. Responda sempre com empatia, clareza e foco em resolver o problema rapidamente.',
    observacoesGerais: 'Nunca revele informações internas do sistema e ofereça encaminhamento humano quando não tiver certeza da resposta.',
    contextoPadrao: [
        { titulo: 'Empresa', descricao: 'Nome oficial, segmento e diferenciais do negócio.' },
        { titulo: 'Horário', descricao: 'Atendimento humano das 08h às 18h, exceto finais de semana.' }
    ],
    funcoes: [
        {
            nome: 'ColetarDadosBasicos',
            quandoUsar: 'Primeiro contato com clientes novos ou sem histórico recente.',
            descricaoPassoAPasso: 'Solicite nome completo, CPF/CNPJ, telefone de contato e descreva o motivo do atendimento.',
            exemploResposta: 'Perfeito! Para avançarmos poderia me confirmar seu CPF e um telefone atualizado?'
        }
    ],
    ultimaAtualizacao: null
};

async function ensureFile() {
    await fs.ensureFile(FILE_PATH);
    try {
        await fs.readJson(FILE_PATH);
    } catch (_) {
        await fs.writeJson(FILE_PATH, DEFAULT_CONFIG, { spaces: 2 });
    }
}

async function carregarConfiguracao() {
    await ensureFile();
    const data = await fs.readJson(FILE_PATH);
    return normalizarConfiguracao(data);
}

function normalizarConfiguracao(config) {
    const safeConfig = { ...DEFAULT_CONFIG, ...config };
    safeConfig.contextoPadrao = Array.isArray(config?.contextoPadrao) ? config.contextoPadrao : [...DEFAULT_CONFIG.contextoPadrao];
    safeConfig.funcoes = Array.isArray(config?.funcoes) ? config.funcoes : [...DEFAULT_CONFIG.funcoes];
    safeConfig.basePrompt = config?.basePrompt || DEFAULT_CONFIG.basePrompt;
    safeConfig.observacoesGerais = config?.observacoesGerais || DEFAULT_CONFIG.observacoesGerais;
    safeConfig.ultimaAtualizacao = config?.ultimaAtualizacao || DEFAULT_CONFIG.ultimaAtualizacao;
    return safeConfig;
}

async function salvarConfiguracao(payload = {}) {
    const configuracaoNormalizada = normalizarConfiguracao(payload);
    configuracaoNormalizada.ultimaAtualizacao = new Date().toISOString();
    await fs.writeJson(FILE_PATH, configuracaoNormalizada, { spaces: 2 });
    return { success: true, config: configuracaoNormalizada };
}

async function gerarPromptPreview({ configuracao, instrucoesAdicionais = '', destaques = [] } = {}) {
    const configAtual = configuracao ? normalizarConfiguracao(configuracao) : await carregarConfiguracao();
    const promptParts = [];

    promptParts.push(`# Papel
${configAtual.basePrompt}`.trim());

    if (Array.isArray(configAtual.contextoPadrao) && configAtual.contextoPadrao.length > 0) {
        const listaContexto = configAtual.contextoPadrao
            .map((item, index) => `${index + 1}. ${item.titulo}: ${item.descricao}`)
            .join('\n');
        promptParts.push(`# Contexto Essencial\n${listaContexto}`);
    }

    if (Array.isArray(configAtual.funcoes) && configAtual.funcoes.length > 0) {
        const listaFuncoes = configAtual.funcoes
            .map((funcao) => {
                return `• ${funcao.nome}\n  Quando usar: ${funcao.quandoUsar}\n  Passos: ${funcao.descricaoPassoAPasso}\n  Exemplo: ${funcao.exemploResposta}`;
            })
            .join('\n\n');
        promptParts.push(`# Funções Disponíveis\n${listaFuncoes}`);
    }

    if (configAtual.observacoesGerais) {
        promptParts.push(`# Observações\n${configAtual.observacoesGerais}`);
    }

    if (Array.isArray(destaques) && destaques.length > 0) {
        promptParts.push(`# Destaques do Atendente\n${destaques.map((item, idx) => `${idx + 1}. ${item}`).join('\n')}`);
    }

    if (instrucoesAdicionais) {
        promptParts.push(`# Instruções Adicionais\n${instrucoesAdicionais}`);
    }

    const prompt = promptParts.join('\n\n').trim();

    return {
        success: true,
        prompt,
        previewLength: prompt.length
    };
}

module.exports = {
    carregarConfiguracao,
    salvarConfiguracao,
    gerarPromptPreview
};
