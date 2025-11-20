/**
 * =========================================================================
 * VALIDADOR DE CREDENCIAIS - SISTEMA DE AUTENTICAÇÃO
 * =========================================================================
 * 
 * Este módulo é responsável por validar as credenciais de login dos usuários.
 * Utiliza um sistema híbrido que combina:
 * - Usuários fixos (definidos no código para administradores)
 * - Usuários cadastrados dinamicamente (salvos em arquivo JSON)
 * 
 * O sistema prioriza usuários fixos e depois verifica usuários cadastrados.
 * 
 * @author Sistema Chat Atendimento
 * @version 2.0.0
 * @since 2024
 */

const gerenciadorUsuarios = require('./gerenciador-usuarios');

// =========================================================================
// USUÁRIOS FIXOS DO SISTEMA
// =========================================================================

/**
 * Lista de usuários fixos com acesso administrativo
 * 🔐 Em produção, considere usar variáveis de ambiente ou banco de dados
 */
const USUARIOS_FIXOS = {
    'admin': '1234',
    'supervisor': 'senha123', 
    'koldri': '13051987'
};

// =========================================================================
// FUNÇÕES DE VALIDAÇÃO
// =========================================================================

/**
 * Valida as credenciais de login combinando usuários fixos e cadastrados
 * 
 * @param {string} nomeUsuario - Nome do usuário para login
 * @param {string} senha - Senha do usuário
 * @returns {Promise<boolean>} true se as credenciais forem válidas
 * 
 * @example
 * const valido = await validarCredenciais('admin', '1234');
 * if (valido) {
 *   console.log('Login aprovado');
 * }
 */
async function validarCredenciais(nomeUsuario, senha) {
    try {
        console.log(`[Validador] Validando credenciais para usuário: ${nomeUsuario}`);
        
        // 1. Primeiro verifica usuários fixos (prioridade)
        if (USUARIOS_FIXOS[nomeUsuario]) {
            const senhaCorreta = USUARIOS_FIXOS[nomeUsuario];
            
            if (senha === senhaCorreta) {
                console.log(`[Validador] ✅ Login aprovado (usuário fixo): ${nomeUsuario}`);
                return true;
            } else {
                console.log(`[Validador] ❌ Senha incorreta para usuário fixo: ${nomeUsuario}`);
                return false;
            }
        }
        
        // 2. Se não for usuário fixo, verifica usuários cadastrados
        console.log(`[Validador] Usuário não é fixo, verificando cadastros dinâmicos...`);
        
        const usuarioEncontrado = await gerenciadorUsuarios.buscarUsuarioPorNome(nomeUsuario);
        
        if (usuarioEncontrado) {
            const senhaValida = await gerenciadorUsuarios.validarSenhaUsuario(nomeUsuario, senha);
            
            if (senhaValida) {
                console.log(`[Validador] ✅ Login aprovado (usuário cadastrado): ${nomeUsuario}`);
                return true;
            } else {
                console.log(`[Validador] ❌ Senha incorreta para usuário cadastrado: ${nomeUsuario}`);
                return false;
            }
        }
        
        // 3. Se chegou até aqui, o usuário não existe
        console.log(`[Validador] ❌ Usuário não encontrado: ${nomeUsuario}`);
        return false;
        
    } catch (erro) {
        console.error('[Validador] Erro durante validação de credenciais:', erro);
        return false;
    }
}

/**
 * Verifica se um usuário é administrador do sistema
 * 
 * @param {string} nomeUsuario - Nome do usuário
 * @returns {boolean} true se for administrador
 */
function ehAdministrador(nomeUsuario) {
    return USUARIOS_FIXOS.hasOwnProperty(nomeUsuario);
}

/**
 * Lista todos os usuários fixos (sem senhas por segurança)
 * 
 * @returns {Array<string>} Lista com nomes dos usuários fixos
 */
function listarUsuariosFixos() {
    return Object.keys(USUARIOS_FIXOS);
}

/**
 * Obtém estatísticas do sistema de autenticação
 * 
 * @returns {Promise<Object>} Objeto com estatísticas
 */
async function obterEstatisticasAutenticacao() {
    try {
        const usuariosCadastrados = await gerenciadorUsuarios.listarUsuarios();
        const totalUsuariosFixos = Object.keys(USUARIOS_FIXOS).length;
        const totalUsuariosCadastrados = usuariosCadastrados.length;
        
        return {
            usuariosFixos: totalUsuariosFixos,
            usuariosCadastrados: totalUsuariosCadastrados,
            totalUsuarios: totalUsuariosFixos + totalUsuariosCadastrados,
            ultimaVerificacao: new Date().toISOString()
        };
    } catch (erro) {
        console.error('[Validador] Erro ao obter estatísticas:', erro);
        return {
            usuariosFixos: Object.keys(USUARIOS_FIXOS).length,
            usuariosCadastrados: 0,
            totalUsuarios: Object.keys(USUARIOS_FIXOS).length,
            erro: erro.message
        };
    }
}

// =========================================================================
// EXPORTAÇÕES
// =========================================================================

module.exports = {
    validarCredenciais,
    ehAdministrador,
    listarUsuariosFixos,
    obterEstatisticasAutenticacao
};

console.log('[Validador] Módulo de validação de credenciais carregado');
