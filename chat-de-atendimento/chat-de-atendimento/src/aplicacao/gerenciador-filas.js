/**
 * 🎯 Gerenciador de Filas de Atendimento
 * 
 * Gerencia os 3 estados de atendimento:
 * 1. AUTOMACAO - Cliente recém chegou, bot está respondendo
 * 2. ESPERA - Bot não resolveu, aguardando atendente humano
 * 3. ATENDIMENTO - Atendente assumiu a conversa
 */

const fs = require('fs-extra');
const path = require('path');
const logger = require('../infraestrutura/logger');

const FILE_FILAS = path.join(__dirname, '../../dados/filas-atendimento.json');

// Estados possíveis
const ESTADOS = {
    AUTOMACAO: 'automacao',
    ESPERA: 'espera',
    ATENDIMENTO: 'atendimento',
    ENCERRADO: 'encerrado'
};

/**
 * Estrutura de dados:
 * {
 *   conversas: [
 *     {
 *       id: "uuid",
 *       clientId: "whatsapp-1",
 *       chatId: "5511999999999@c.us",
 *       estado: "automacao|espera|atendimento|encerrado",
 *       atendente: "usuario" | null,
 *       criadoEm: "2026-01-11T10:00:00Z",
 *       atualizadoEm: "2026-01-11T10:05:00Z",
 *       tentativasBot: 0,
 *       historicoEstados: [
 *         { estado: "automacao", timestamp: "..." },
 *         { estado: "espera", timestamp: "...", motivo: "bot_nao_resolveu" }
 *       ],
 *       metadata: {
 *         nomeContato: "João Silva",
 *         ultimaMensagem: "Preciso de ajuda",
 *         mensagensNaoLidas: 3
 *       }
 *     }
 *   ]
 * }
 */

async function ensureFile() {
    await fs.ensureFile(FILE_FILAS);
    try {
        await fs.readJson(FILE_FILAS);
    } catch {
        await fs.writeJson(FILE_FILAS, { conversas: [] }, { spaces: 2 });
    }
}

async function load() {
    await ensureFile();
    return fs.readJson(FILE_FILAS);
}

async function save(data) {
    await fs.writeJson(FILE_FILAS, data, { spaces: 2 });
}

/**
 * Cria nova conversa em estado de AUTOMAÇÃO
 */
async function criarConversa(clientId, chatId, metadata = {}) {
    const data = await load();
    
    // Verifica se já existe
    const existe = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado !== ESTADOS.ENCERRADO
    );
    
    if (existe) {
        logger.info(`[Filas] Conversa já existe: ${chatId}`);
        return { success: true, conversa: existe };
    }
    
    const conversa = {
        id: `${clientId}-${chatId}-${Date.now()}`,
        clientId,
        chatId,
        estado: ESTADOS.AUTOMACAO,
        atendente: null,
        criadoEm: new Date().toISOString(),
        atualizadoEm: new Date().toISOString(),
        tentativasBot: 0,
        historicoEstados: [
            { estado: ESTADOS.AUTOMACAO, timestamp: new Date().toISOString() }
        ],
        metadata: {
            nomeContato: metadata.nomeContato || chatId,
            ultimaMensagem: metadata.ultimaMensagem || '',
            mensagensNaoLidas: 0,
            ...metadata
        }
    };
    
    data.conversas.push(conversa);
    await save(data);
    
    logger.sucesso(`[Filas] Nova conversa criada: ${chatId} (AUTOMAÇÃO)`);
    return { success: true, conversa };
}

/**
 * Move conversa de AUTOMAÇÃO para ESPERA
 * (Quando bot não consegue resolver)
 */
async function moverParaEspera(clientId, chatId, motivo = 'bot_nao_resolveu') {
    const data = await load();
    const conversa = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado === ESTADOS.AUTOMACAO
    );
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada ou não está em automação' };
    }
    
    conversa.estado = ESTADOS.ESPERA;
    conversa.atualizadoEm = new Date().toISOString();
    conversa.historicoEstados.push({
        estado: ESTADOS.ESPERA,
        timestamp: new Date().toISOString(),
        motivo
    });
    
    await save(data);
    logger.info(`[Filas] Conversa movida para ESPERA: ${chatId} - Motivo: ${motivo}`);
    
    return { success: true, conversa };
}

/**
 * Atendente assume conversa da ESPERA
 * Move para ATENDIMENTO
 */
async function assumirConversa(clientId, chatId, atendente) {
    const data = await load();
    const conversa = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado === ESTADOS.ESPERA
    );
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada ou não está em espera' };
    }
    
    // Verificar se outro atendente já assumiu
    if (conversa.atendente && conversa.atendente !== atendente) {
        return { success: false, message: `Já assumida por ${conversa.atendente}` };
    }
    
    conversa.estado = ESTADOS.ATENDIMENTO;
    conversa.atendente = atendente;
    conversa.atualizadoEm = new Date().toISOString();
    conversa.historicoEstados.push({
        estado: ESTADOS.ATENDIMENTO,
        timestamp: new Date().toISOString(),
        atendente
    });
    
    await save(data);
    logger.sucesso(`[Filas] Conversa assumida por ${atendente}: ${chatId}`);
    
    return { success: true, conversa };
}

/**
 * Encerra atendimento
 */
async function encerrarConversa(clientId, chatId, atendente) {
    const data = await load();
    const conversa = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado === ESTADOS.ATENDIMENTO
    );
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada ou não está em atendimento' };
    }
    
    if (conversa.atendente !== atendente) {
        return { success: false, message: 'Você não é o atendente desta conversa' };
    }
    
    conversa.estado = ESTADOS.ENCERRADO;
    conversa.atualizadoEm = new Date().toISOString();
    conversa.historicoEstados.push({
        estado: ESTADOS.ENCERRADO,
        timestamp: new Date().toISOString(),
        atendente
    });
    
    await save(data);
    logger.info(`[Filas] Conversa encerrada por ${atendente}: ${chatId}`);
    
    return { success: true, conversa };
}

/**
 * Lista conversas por estado
 */
async function listarPorEstado(estado, atendente = null) {
    const data = await load();
    let conversas = data.conversas.filter(c => c.estado === estado);
    
    // Se é ATENDIMENTO, filtra pelo atendente
    if (estado === ESTADOS.ATENDIMENTO && atendente) {
        conversas = conversas.filter(c => c.atendente === atendente);
    }
    
    // Ordena por mais recente
    conversas.sort((a, b) => new Date(b.atualizadoEm) - new Date(a.atualizadoEm));
    
    return conversas;
}

/**
 * Obtém estatísticas das filas
 */
async function obterEstatisticas() {
    const data = await load();
    
    const stats = {
        total: data.conversas.filter(c => c.estado !== ESTADOS.ENCERRADO).length,
        automacao: data.conversas.filter(c => c.estado === ESTADOS.AUTOMACAO).length,
        espera: data.conversas.filter(c => c.estado === ESTADOS.ESPERA).length,
        atendimento: data.conversas.filter(c => c.estado === ESTADOS.ATENDIMENTO).length,
        encerradas: data.conversas.filter(c => c.estado === ESTADOS.ENCERRADO).length,
        tempoMedioEspera: calcularTempoMedioEspera(data.conversas)
    };
    
    return stats;
}

function calcularTempoMedioEspera(conversas) {
    const conversasEspera = conversas.filter(c => 
        c.estado === ESTADOS.ESPERA || c.estado === ESTADOS.ATENDIMENTO
    );
    
    if (conversasEspera.length === 0) return 0;
    
    const tempos = conversasEspera.map(c => {
        const inicioEspera = c.historicoEstados.find(h => h.estado === ESTADOS.ESPERA);
        const fimEspera = c.historicoEstados.find(h => h.estado === ESTADOS.ATENDIMENTO);
        
        if (!inicioEspera || !fimEspera) return 0;
        
        return new Date(fimEspera.timestamp) - new Date(inicioEspera.timestamp);
    });
    
    const soma = tempos.reduce((acc, t) => acc + t, 0);
    return Math.round(soma / tempos.length / 1000 / 60); // minutos
}

/**
 * Atualiza metadata de conversa
 */
async function atualizarMetadata(clientId, chatId, metadata) {
    const data = await load();
    const conversa = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado !== ESTADOS.ENCERRADO
    );
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada' };
    }
    
    conversa.metadata = { ...conversa.metadata, ...metadata };
    conversa.atualizadoEm = new Date().toISOString();
    
    await save(data);
    return { success: true, conversa };
}

/**
 * Incrementa tentativas do bot
 */
async function incrementarTentativasBot(clientId, chatId) {
    const data = await load();
    const conversa = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado === ESTADOS.AUTOMACAO
    );
    
    if (!conversa) {
        return { success: false };
    }
    
    conversa.tentativasBot++;
    conversa.atualizadoEm = new Date().toISOString();
    
    // Se passou de 3 tentativas, move para espera automaticamente
    if (conversa.tentativasBot >= 3) {
        await moverParaEspera(clientId, chatId, 'limite_tentativas_bot');
    } else {
        await save(data);
    }
    
    return { success: true, tentativas: conversa.tentativasBot };
}

/**
 * Atribui conversa diretamente a um atendente (de qualquer estado)
 */
async function atribuirConversa(clientId, chatId, atendente, atendenteOrigem = null) {
    const data = await load();
    const conversa = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado !== ESTADOS.ENCERRADO
    );
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada' };
    }
    
    const estadoAnterior = conversa.estado;
    conversa.estado = ESTADOS.ATENDIMENTO;
    conversa.atendente = atendente;
    conversa.atualizadoEm = new Date().toISOString();
    conversa.historicoEstados.push({
        estado: ESTADOS.ATENDIMENTO,
        timestamp: new Date().toISOString(),
        atendente,
        atribuidoPor: atendenteOrigem
    });
    
    await save(data);
    logger.info(`[Filas] Conversa atribuída de ${estadoAnterior} para ${atendente}: ${chatId}`);
    
    return { success: true, conversa };
}

/**
 * Transfere conversa de um atendente para outro
 */
async function transferirConversa(clientId, chatId, atendenteDestino, atendenteOrigem) {
    const data = await load();
    const conversa = data.conversas.find(c => 
        c.clientId === clientId && c.chatId === chatId && c.estado === ESTADOS.ATENDIMENTO
    );
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada ou não está em atendimento' };
    }
    
    if (conversa.atendente !== atendenteOrigem) {
        return { success: false, message: 'Você não pode transferir conversa de outro atendente' };
    }
    
    conversa.atendente = atendenteDestino;
    conversa.atualizadoEm = new Date().toISOString();
    conversa.historicoEstados.push({
        estado: ESTADOS.ATENDIMENTO,
        timestamp: new Date().toISOString(),
        atendente: atendenteDestino,
        transferidoDe: atendenteOrigem
    });
    
    await save(data);
    logger.info(`[Filas] Conversa transferida de ${atendenteOrigem} para ${atendenteDestino}: ${chatId}`);
    
    return { success: true, conversa };
}

/**
 * Atribui múltiplas conversas para um atendente de uma vez
 */
async function atribuirMultiplos(conversasIds, atendente, atendenteOrigem = null) {
    const data = await load();
    const resultados = [];
    
    for (const id of conversasIds) {
        const conversa = data.conversas.find(c => c.id === id && c.estado !== ESTADOS.ENCERRADO);
        
        if (conversa) {
            conversa.estado = ESTADOS.ATENDIMENTO;
            conversa.atendente = atendente;
            conversa.atualizadoEm = new Date().toISOString();
            conversa.historicoEstados.push({
                estado: ESTADOS.ATENDIMENTO,
                timestamp: new Date().toISOString(),
                atendente,
                atribuidoPor: atendenteOrigem,
                lote: true
            });
            resultados.push({ id, success: true });
        } else {
            resultados.push({ id, success: false, message: 'Conversa não encontrada' });
        }
    }
    
    await save(data);
    logger.info(`[Filas] ${resultados.filter(r => r.success).length} conversas atribuídas em lote para ${atendente}`);
    
    return { success: true, resultados };
}

/**
 * Encerra múltiplas conversas de uma vez
 */
async function encerrarMultiplos(conversasIds, atendente) {
    const data = await load();
    const resultados = [];
    
    for (const id of conversasIds) {
        const conversa = data.conversas.find(c => c.id === id && c.estado !== ESTADOS.ENCERRADO);
        
        if (conversa) {
            // Verifica se o atendente tem permissão
            if (conversa.estado === ESTADOS.ATENDIMENTO && conversa.atendente !== atendente) {
                resultados.push({ id, success: false, message: 'Conversa de outro atendente' });
                continue;
            }
            
            conversa.estado = ESTADOS.ENCERRADO;
            conversa.atualizadoEm = new Date().toISOString();
            conversa.historicoEstados.push({
                estado: ESTADOS.ENCERRADO,
                timestamp: new Date().toISOString(),
                atendente,
                lote: true
            });
            resultados.push({ id, success: true });
        } else {
            resultados.push({ id, success: false, message: 'Conversa não encontrada' });
        }
    }
    
    await save(data);
    logger.info(`[Filas] ${resultados.filter(r => r.success).length} conversas encerradas em lote por ${atendente}`);
    
    return { success: true, resultados };
}

/**
 * Lista todos atendentes com conversas ativas
 */
async function listarAtendentes() {
    const data = await load();
    const atendentes = new Set();
    
    data.conversas
        .filter(c => c.atendente && c.estado !== ESTADOS.ENCERRADO)
        .forEach(c => atendentes.add(c.atendente));
    
    return Array.from(atendentes).sort();
}

module.exports = {
    ESTADOS,
    criarConversa,
    moverParaEspera,
    assumirConversa,
    encerrarConversa,
    listarPorEstado,
    obterEstatisticas,
    atualizarMetadata,
    incrementarTentativasBot,
    atribuirConversa,
    transferirConversa,
    atribuirMultiplos,
    encerrarMultiplos,
    listarAtendentes,
    // Novas funções auxiliares
    buscarPorChatId,
    adicionarConversa,
    atualizarUltimaMensagem,
    atualizarTentativasBot
};

// === Funções Auxiliares ===

/**
 * Busca conversa ativa por chatId
 */
async function buscarPorChatId(chatId) {
    const data = await load();
    return data.conversas.find(c => c.chatId === chatId && c.estado !== ESTADOS.ENCERRADO);
}

/**
 * Adiciona nova conversa (alias para criarConversa com interface simplificada)
 */
async function adicionarConversa({ clientId, chatId, nomeContato, ultimaMensagem }) {
    return criarConversa(clientId, chatId, { nomeContato, ultimaMensagem });
}

/**
 * Atualiza última mensagem recebida
 */
async function atualizarUltimaMensagem(chatId, mensagem) {
    const data = await load();
    const conversa = data.conversas.find(c => c.chatId === chatId && c.estado !== ESTADOS.ENCERRADO);
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada' };
    }
    
    conversa.metadata = conversa.metadata || {};
    conversa.metadata.ultimaMensagem = mensagem;
    conversa.atualizadoEm = new Date().toISOString();
    
    await save(data);
    return { success: true };
}

/**
 * Atualiza contador de tentativas do bot
 */
async function atualizarTentativasBot(chatId, tentativas) {
    const data = await load();
    const conversa = data.conversas.find(c => c.chatId === chatId && c.estado !== ESTADOS.ENCERRADO);
    
    if (!conversa) {
        return { success: false, message: 'Conversa não encontrada' };
    }
    
    conversa.tentativasBot = tentativas;
    conversa.atualizadoEm = new Date().toISOString();
    
    await save(data);
    return { success: true };
}
