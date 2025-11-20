// users.js - Gerenciamento de usuários cadastrados
const fs = require('fs-extra');
const path = require('path');
const os = require('os');

// Define o caminho para o arquivo users.json
// Usa Electron app.getPath se disponível, senão usa um caminho padrão
let USERS_FILE;
try {
    const { app } = require('electron');
    USERS_FILE = path.join(app.getPath('userData'), 'users.json');
} catch (e) {
    // Fallback para testes fora do Electron
    USERS_FILE = path.join(os.homedir(), 'AppData', 'Roaming', 'chat-de-atendimento', 'users.json');
}

// 🆕 Array interno para armazenar usuários em memória
let usersArray = [];

/**
 * 🆕 Inicializa o array de usuários carregando os dados do arquivo
 */
function initializeUsersArray() {
    try {
        usersArray = loadCadastredUsers();
        console.log(`[Users] Array inicializado com ${usersArray.length} usuário(s)`);
    } catch (error) {
        console.error('[Users] Erro ao inicializar array de usuários:', error.message);
        usersArray = [];
    }
}

/**
 * 🆕 Sincroniza o array interno com o arquivo
 */
function syncArrayToFile() {
    try {
        saveCadastredUsers(usersArray);
        console.log('[Users] Array sincronizado com o arquivo');
    } catch (error) {
        console.error('[Users] Erro ao sincronizar array:', error.message);
    }
}

/**
 * 🆕 Obtém o array de usuários em memória
 * @returns {Array} Array de usuários
 */
function getUsersArray() {
    return [...usersArray]; // Retorna uma cópia para evitar modificações externas
}

/**
 * 🆕 Adiciona um usuário ao array interno
 * @param {Object} user - Usuário a ser adicionado
 */
function addUserToArray(user) {
    usersArray.push(user);
    console.log(`[Users] Usuário ${user.usuario} adicionado ao array`);
}

/**
 * 🆕 Remove um usuário do array interno
 * @param {string} username - Nome do usuário a ser removido
 * @returns {boolean} True se removido, false se não encontrado
 */
function removeUserFromArray(username) {
    const index = usersArray.findIndex(u => u.usuario === username);
    if (index !== -1) {
        usersArray.splice(index, 1);
        console.log(`[Users] Usuário ${username} removido do array`);
        return true;
    }
    return false;
}

/**
 * 🆕 Busca um usuário no array interno
 * @param {string} username - Nome do usuário
 * @returns {Object|null} Usuário encontrado ou null
 */
function findUserInArray(username) {
    return usersArray.find(u => u.usuario === username) || null;
}

/**
 * Carrega a lista de usuários cadastrados do arquivo users.json.
 * @returns {Array} Lista de usuários cadastrados
 */
function loadCadastredUsers() {
    try {
        if (fs.existsSync(USERS_FILE)) {
            const data = fs.readFileSync(USERS_FILE, 'utf8');
            return JSON.parse(data);
        }
    } catch (e) {
        console.error('[Users] Erro ao ler usuários persistidos:', e.message);
    }
    return [];
}

/**
 * Salva a lista de usuários cadastrados no arquivo users.json.
 * @param {Array} users - Lista de usuários para salvar
 */
function saveCadastredUsers(users) {
    try {
        // Garante que o diretório existe
        const dir = path.dirname(USERS_FILE);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        
        fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2), 'utf8');
        console.log(`[Users] ${users.length} usuário(s) salvo(s) em: ${USERS_FILE}`);
    } catch (e) {
        console.error('[Users] Erro ao salvar usuários persistidos:', e.message);
    }
}

/**
 * Registra um novo usuário no sistema (🆕 Usa array interno)
 * @param {Object} newUser - Dados do novo usuário
 * @returns {Object} Resultado da operação { success: boolean, message: string }
 */
function registerUser(newUser) {
    try {
        // Validações básicas
        if (!newUser.usuario || !newUser.senha) {
            return { success: false, message: 'Usuário e senha são obrigatórios.' };
        }

        // Verifica se o usuário já existe no array
        if (usersArray.some(u => u.usuario.toLowerCase() === newUser.usuario.toLowerCase())) {
            return { success: false, message: 'Usuário já cadastrado.' };
        }

        // Adiciona data de cadastro e ID único
        const userWithTimestamp = {
            id: Date.now(), // 🆕 ID único baseado em timestamp
            ...newUser,
            dataCadastro: new Date().toISOString(),
            ativo: true
        };

        // Adiciona ao array interno
        addUserToArray(userWithTimestamp);
        
        // Sincroniza com o arquivo
        syncArrayToFile();

        console.log(`[Users] Novo usuário cadastrado: ${newUser.usuario} (ID: ${userWithTimestamp.id})`);
        return { success: true, message: 'Usuário cadastrado com sucesso.', userId: userWithTimestamp.id };
    } catch (error) {
        console.error('[Users] Erro ao registrar usuário:', error.message);
        return { success: false, message: 'Erro interno ao cadastrar usuário.' };
    }
}

/**
 * Valida as credenciais de um usuário cadastrado (🆕 Usa array interno)
 * @param {string} username - Nome de usuário
 * @param {string} password - Senha
 * @returns {Object|null} Dados do usuário se válido, null se inválido
 */
function validateUser(username, password) {
    try {
        // Busca no array interno primeiro
        const foundUser = usersArray.find(u => 
            u.usuario === username && 
            u.senha === password &&
            u.ativo !== false
        );
        
        if (foundUser) {
            console.log(`[Users] Login válido para usuário: ${username} (Array)`);
            return foundUser;
        }
        
        console.log(`[Users] Login inválido para usuário: ${username}`);
        return null;
    } catch (error) {
        console.error('[Users] Erro ao validar usuário:', error.message);
        return null;
    }
}

/**
 * Lista todos os usuários cadastrados (sem senhas) (🆕 Usa array interno)
 * @returns {Array} Lista de usuários sem dados sensíveis
 */
function listUsers() {
    try {
        return usersArray.map(user => ({
            id: user.id,
            usuario: user.usuario,
            nome: user.nome,
            email: user.email,
            dataCadastro: user.dataCadastro,
            ativo: user.ativo
        }));
    } catch (error) {
        console.error('[Users] Erro ao listar usuários:', error.message);
        return [];
    }
}

/**
 * Obtém estatísticas dos usuários (🆕 Usa array interno)
 * @returns {Object} Estatísticas dos usuários
 */
function getUserStats() {
    try {
        const activeUsers = usersArray.filter(u => u.ativo !== false);
        
        return {
            total: usersArray.length,
            ativos: activeUsers.length,
            inativos: usersArray.length - activeUsers.length,
            arquivoPath: USERS_FILE,
            arraySize: usersArray.length
        };
    } catch (error) {
        console.error('[Users] Erro ao obter estatísticas:', error.message);
        return {
            total: 0,
            ativos: 0,
            inativos: 0,
            arquivoPath: USERS_FILE,
            arraySize: 0
        };
    }
}

/**
 * Remove um usuário do sistema (🆕 Usa array interno)
 * @param {string} username - Nome de usuário a ser removido
 * @returns {Object} Resultado da operação
 */
function removeUser(username) {
    try {
        const removed = removeUserFromArray(username);
        
        if (!removed) {
            return { success: false, message: 'Usuário não encontrado.' };
        }
        
        // Sincroniza com o arquivo
        syncArrayToFile();
        
        console.log(`[Users] Usuário removido do sistema: ${username}`);
        return { success: true, message: 'Usuário removido com sucesso.' };
    } catch (error) {
        console.error('[Users] Erro ao remover usuário:', error.message);
        return { success: false, message: 'Erro interno ao remover usuário.' };
    }
}

// 🆕 Inicializa o array na primeira importação do módulo
initializeUsersArray();

module.exports = {
    // Funções originais (atualizadas)
    loadCadastredUsers,
    saveCadastredUsers,
    registerUser,
    validateUser,
    listUsers,
    getUserStats,
    removeUser,
    
    // 🆕 Novas funções para trabalhar com array
    initializeUsersArray,
    syncArrayToFile,
    getUsersArray,
    addUserToArray,
    removeUserFromArray,
    findUserInArray,
    
    // Constantes
    USERS_FILE
};
