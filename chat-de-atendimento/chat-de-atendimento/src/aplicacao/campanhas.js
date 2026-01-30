const fs = require('fs-extra');
const path = require('path');

const FILE_PATH = path.join(__dirname, '../../dados/campanhas.json');

const DEFAULT_DATA = {
    campanhas: []
};

const CAMPANHA_TEMPLATE = {
    canais: ['whatsapp'],
    mensagemBase: '',
    finalidade: 'venda',
    finalidadeDescricao: '',
    usarAgenteIA: true,
    instrucoesIA: '',
    status: 'rascunho',
    agendadoPara: null,
    destinatarios: [],
    destinatariosDetalhados: [],
    clientePreferencial: null,
    historicoEnvios: [],
    createdAt: null,
    updatedAt: null
};

function extrairSomenteDigitos(valor) {
    return String(valor || '').replace(/[^0-9]/g, '');
}

function normalizarDestinatariosDetalhados(lista = []) {
    if (!Array.isArray(lista)) return [];
    const vistos = new Set();
    const detalhados = [];

    for (const item of lista) {
        if (!item) continue;
        const telefoneSanitizado = extrairSomenteDigitos(item.telefone || item.telefoneSanitizado || item.numero);
        if (!telefoneSanitizado || telefoneSanitizado.length < 8 || vistos.has(telefoneSanitizado)) {
            continue;
        }

        vistos.add(telefoneSanitizado);

        const cpfSanitizado = (() => {
            const cpf = extrairSomenteDigitos(item.cpf || item.cpfSanitizado);
            return cpf.length ? cpf : null;
        })();

        detalhados.push({
            nome: item.nome?.toString().trim() || null,
            telefone: telefoneSanitizado,
            cpf: cpfSanitizado
        });
    }

    return detalhados;
}

function sanitizarDestinatarios(lista = []) {
    if (!Array.isArray(lista)) return [];
    const normalizados = new Set();
    for (const item of lista) {
        if (!item) continue;
        const somenteDigitos = String(item).replace(/[^0-9]/g, '');
        if (somenteDigitos.length >= 8) {
            normalizados.add(somenteDigitos);
        }
    }
    return Array.from(normalizados);
}

function gerarIdEnvio() {
    return `env_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

async function ensureFile() {
    await fs.ensureFile(FILE_PATH);
    try {
        await fs.readJson(FILE_PATH);
    } catch (erro) {
        await fs.writeJson(FILE_PATH, DEFAULT_DATA, { spaces: 2 });
    }
}

async function carregarArquivo() {
    await ensureFile();
    const data = await fs.readJson(FILE_PATH);
    return {
        ...DEFAULT_DATA,
        ...data,
        campanhas: Array.isArray(data?.campanhas) ? data.campanhas : []
    };
}

async function salvarArquivo(conteudo) {
    await fs.writeJson(FILE_PATH, conteudo, { spaces: 2 });
    return conteudo;
}

function gerarIdCampanha() {
    return `cmp_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

function normalizarCampanha(payload = {}) {
    const agora = new Date().toISOString();
    const destinatariosDetalhados = normalizarDestinatariosDetalhados(payload.destinatariosDetalhados || CAMPANHA_TEMPLATE.destinatariosDetalhados);
    const destinatarios = destinatariosDetalhados.length > 0
        ? destinatariosDetalhados.map((dest) => dest.telefone)
        : sanitizarDestinatarios(payload.destinatarios || CAMPANHA_TEMPLATE.destinatarios);
    return {
        id: payload.id || gerarIdCampanha(),
        nome: payload.nome?.trim() || 'Campanha sem nome',
        canais: Array.isArray(payload.canais) && payload.canais.length > 0 ? [...new Set(payload.canais)] : [...CAMPANHA_TEMPLATE.canais],
        mensagemBase: payload.mensagemBase?.trim() || CAMPANHA_TEMPLATE.mensagemBase,
        finalidade: payload.finalidade || CAMPANHA_TEMPLATE.finalidade,
        finalidadeDescricao: payload.finalidadeDescricao?.trim() || CAMPANHA_TEMPLATE.finalidadeDescricao,
        usarAgenteIA: payload.usarAgenteIA !== undefined ? Boolean(payload.usarAgenteIA) : CAMPANHA_TEMPLATE.usarAgenteIA,
        instrucoesIA: payload.instrucoesIA?.trim() || CAMPANHA_TEMPLATE.instrucoesIA,
        status: payload.status || CAMPANHA_TEMPLATE.status,
        agendadoPara: payload.agendadoPara || CAMPANHA_TEMPLATE.agendadoPara,
        destinatarios,
        destinatariosDetalhados,
        clientePreferencial: payload.clientePreferencial || CAMPANHA_TEMPLATE.clientePreferencial,
        historicoEnvios: Array.isArray(payload.historicoEnvios) ? payload.historicoEnvios : [...CAMPANHA_TEMPLATE.historicoEnvios],
        createdAt: payload.createdAt || agora,
        updatedAt: agora
    };
}

async function listarCampanhas() {
    const data = await carregarArquivo();
    return data.campanhas.sort((a, b) => new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0));
}

async function salvarCampanha(payload) {
    const data = await carregarArquivo();
    const campanhaNormalizada = normalizarCampanha(payload);
    const indiceExistente = data.campanhas.findIndex((c) => c.id === campanhaNormalizada.id);

    if (indiceExistente >= 0) {
        data.campanhas[indiceExistente] = {
            ...data.campanhas[indiceExistente],
            ...campanhaNormalizada,
            updatedAt: new Date().toISOString()
        };
    } else {
        data.campanhas.push(campanhaNormalizada);
    }

    await salvarArquivo(data);
    return { success: true, campanha: campanhaNormalizada };
}

async function removerCampanha(id) {
    if (!id) {
        throw new Error('ID da campanha é obrigatório para remoção.');
    }

    const data = await carregarArquivo();
    const tamanhoAnterior = data.campanhas.length;
    data.campanhas = data.campanhas.filter((campanha) => campanha.id !== id);

    if (data.campanhas.length === tamanhoAnterior) {
        return { success: false, message: 'Campanha não encontrada.' };
    }

    await salvarArquivo(data);
    return { success: true };
}

async function obterCampanhaPorId(id) {
    if (!id) return null;
    const data = await carregarArquivo();
    const campanha = data.campanhas.find((c) => c.id === id);
    return campanha || null;
}

async function registrarHistoricoEnvio(idCampanha, registro = {}) {
    if (!idCampanha) {
        throw new Error('ID da campanha é obrigatório para registrar envio.');
    }

    const data = await carregarArquivo();
    const indice = data.campanhas.findIndex((c) => c.id === idCampanha);
    if (indice < 0) {
        throw new Error('Campanha não encontrada para registrar envio.');
    }

    const agora = new Date().toISOString();
    const campanha = data.campanhas[indice];
    campanha.historicoEnvios = Array.isArray(campanha.historicoEnvios) ? campanha.historicoEnvios : [];

    const registroFinal = {
        idEnvio: registro.idEnvio || gerarIdEnvio(),
        dataExecucao: registro.dataExecucao || agora,
        totalDestinatarios: registro.totalDestinatarios || 0,
        canaisAtivos: registro.canaisAtivos || campanha.canais,
        resultados: registro.resultados || {},
        mensagemUtilizada: registro.mensagemUtilizada || campanha.mensagemBase,
        clientId: registro.clientId || campanha.clientePreferencial || null,
        observacoes: registro.observacoes || null,
        status: registro.statusFinal || 'executado',
        duracaoMs: Number.isFinite(registro.duracaoMs) ? registro.duracaoMs : null,
        iaAtivada: registro.iaAtivada ?? Boolean(campanha.usarAgenteIA),
        promptIA: registro.promptIA || null,
        instrucoesIA: registro.instrucoesIA || campanha.instrucoesIA || '',
        destaquesIA: registro.destaquesIA || null,
        usouFallbackCliente: Boolean(registro.usouFallbackCliente)
    };

    campanha.historicoEnvios.unshift(registroFinal);
    campanha.status = registroFinal.status;
    campanha.updatedAt = agora;

    data.campanhas[indice] = campanha;
    await salvarArquivo(data);
    return campanha;
}

module.exports = {
    listarCampanhas,
    salvarCampanha,
    removerCampanha,
    obterCampanhaPorId,
    registrarHistoricoEnvio,
    sanitizarDestinatarios
};
