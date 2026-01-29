/**
 * Instância Singleton do Pool WhatsApp
 * Exporta a instância global para ser usada em rotas e outros módulos
 */

let instanciaPool = null;

/**
 * Obtém a instância do pool (se existir)
 */
function obterPool() {
    return instanciaPool;
}

/**
 * Define a instância do pool
 */
function definirPool(pool) {
    instanciaPool = pool;
}

/**
 * Verifica se a instância existe
 */
function temPool() {
    return instanciaPool !== null;
}

module.exports = {
    obterPool,
    definirPool,
    temPool
};
