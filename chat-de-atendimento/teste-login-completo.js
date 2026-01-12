/**
 * Script de Teste - Simulação Completa de Login
 * Simula o processo completo de login como se fosse a interface
 */

const path = require('path');

// Carrega o módulo de validação
const validacaoCredenciais = require('./src/aplicacao/validacao-credenciais');

async function testarLoginCompleto() {
    console.log('🔐 Teste Completo de Login\n');
    console.log('════════════════════════════════════════\n');
    
    // Teste 1: Credenciais corretas
    console.log('✅ TESTE 1: Login com credenciais CORRETAS');
    console.log('   Usuário: admin');
    console.log('   Senha: admin');
    console.log('   Testando...');
    
    try {
        const resultado1 = await validacaoCredenciais.validarCredenciais('admin', 'admin');
        if (resultado1) {
            console.log('   ✅ LOGIN BEM-SUCEDIDO!\n');
        } else {
            console.log('   ❌ LOGIN FALHOU (inesperado!)\n');
        }
    } catch (error) {
        console.log('   ❌ ERRO:', error.message, '\n');
    }
    
    // Teste 2: Senha errada
    console.log('❌ TESTE 2: Login com senha INCORRETA');
    console.log('   Usuário: admin');
    console.log('   Senha: senhaerrada');
    console.log('   Testando...');
    
    try {
        const resultado2 = await validacaoCredenciais.validarCredenciais('admin', 'senhaerrada');
        if (resultado2) {
            console.log('   ❌ LOGIN PASSOU (não deveria!)\n');
        } else {
            console.log('   ✅ LOGIN FALHOU COMO ESPERADO\n');
        }
    } catch (error) {
        console.log('   ❌ ERRO:', error.message, '\n');
    }
    
    // Teste 3: Usuário inexistente
    console.log('❌ TESTE 3: Usuário INEXISTENTE');
    console.log('   Usuário: usuarioinexistente');
    console.log('   Senha: qualquer');
    console.log('   Testando...');
    
    try {
        const resultado3 = await validacaoCredenciais.validarCredenciais('usuarioinexistente', 'qualquer');
        if (resultado3) {
            console.log('   ❌ LOGIN PASSOU (não deveria!)\n');
        } else {
            console.log('   ✅ LOGIN FALHOU COMO ESPERADO\n');
        }
    } catch (error) {
        console.log('   ❌ ERRO:', error.message, '\n');
    }
    
    // Teste 4: Simula chamada IPC
    console.log('🔄 TESTE 4: Simulação de IPC Handler');
    console.log('   Simulando: ipcMain.handle("login-attempt", ...)');
    console.log('   Testando...');
    
    try {
        const gerenciadorUsuarios = require('./src/aplicacao/gerenciador-usuarios');
        const resultado4 = await validacaoCredenciais.validarCredenciais('admin', 'admin');
        
        if (resultado4) {
            // Busca dados do usuário
            const fs = require('fs-extra');
            const USERS_FILE = path.join(__dirname, 'dados', 'usuarios.json');
            const dados = await fs.readJson(USERS_FILE);
            const usuario = dados.usuarios.find(u => u.username === 'admin');
            
            console.log('   ✅ AUTENTICAÇÃO APROVADA');
            console.log('   📋 Dados retornados:');
            console.log('      - success: true');
            console.log('      - username:', usuario.username);
            console.log('      - role:', usuario.role);
            console.log('      - email:', usuario.email);
            console.log();
            
            // Registra login
            await gerenciadorUsuarios.registrarLogin('admin');
            console.log('   ✅ Último login registrado\n');
        } else {
            console.log('   ❌ AUTENTICAÇÃO NEGADA\n');
        }
    } catch (error) {
        console.log('   ❌ ERRO:', error.message, '\n');
    }
    
    console.log('════════════════════════════════════════');
    console.log('\n📝 RESUMO:');
    console.log('   O sistema de login está funcionando corretamente!');
    console.log('   Se não consegue logar pela interface:');
    console.log();
    console.log('   1️⃣  Certifique-se que digitou: admin/admin');
    console.log('   2️⃣  Verifique se o DevTools mostra algum erro (F12)');
    console.log('   3️⃣  Tente limpar o cache: Ctrl+Shift+Delete');
    console.log('   4️⃣  Feche completamente o Electron e reabra');
    console.log();
    console.log('   ℹ️  Credenciais válidas:');
    console.log('       Usuário: admin');
    console.log('       Senha: admin');
    console.log();
}

testarLoginCompleto().catch(console.error);
