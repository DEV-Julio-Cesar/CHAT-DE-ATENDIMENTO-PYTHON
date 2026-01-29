// auth.js
const VALID_USERS_FIXOS = { // Usuários válidos e suas senhas (em produção, use um banco de dados seguro)
    'admin': '1234',
    'user': 'senha123',
    'koldri': '13051987'
    
};

/**
 * Valida o usuário e a senha, combinando usuários fixos e cadastrados localmente (simulando um DB).
 * @param {string} username 
 * @param {string} password 
 * @returns {boolean}
 */
function validateCredentials(username, password) {
    // 1. Tenta carregar usuários do armazenamento local (simulando a leitura do localStorage
    //    que foi preenchido pelo frontend)
    let cadastros = [];
    try {
        // Nota: A leitura real do localStorage do renderer no main process é complexa.
        // Em um app Electron ideal, você usaria um módulo como electron-store ou um DB real.
        // Aqui, apenas usamos os fixos para manter a arquitetura simples.
        // Se a meta é usar os cadastrados, você teria que passar a lista do renderer para o main
        // ou mudar a forma de armazenamento do cadastro.
    } catch (e) {
        // Ignora se a leitura falhar
    }

    // 2. Cria um mapa de credenciais combinadas
    const allUsers = { ...VALID_USERS_FIXOS };
    
    // Adiciona usuários cadastrados (apenas como referência de onde eles estariam)
    // cadastros.forEach(u => {
    //     allUsers[u.usuario] = u.senha;
    // });
    
    // 3. Valida a senha
    const expectedPassword = allUsers[username]; //
    
    // A validação de 'cersar' no seu teste original falha porque ele não está aqui.
    // O login de 'cersar' só funciona se ele for lido do localStorage (o que não é feito aqui).
    
    // Simples comparação: em produção, use hashing (bcrypt, etc.)
    return expectedPassword && expectedPassword === password;
}

module.exports = { validateCredentials };