/**
 * Diagnóstico Completo de Login
 * Verifica cada etapa do processo de autenticação
 */

const fs = require('fs-extra');
const path = require('path');

async function diagnostico() {
    console.log('\n🔍 DIAGNÓSTICO COMPLETO DO SISTEMA DE LOGIN\n');
    console.log('═══════════════════════════════════════════════════════════\n');
    
    // 1. Verificar arquivos necessários
    console.log('1️⃣  VERIFICANDO ARQUIVOS NECESSÁRIOS\n');
    
    const filesCheck = [
        { name: 'main.js', path: './main.js' },
        { name: 'login.html', path: './src/interfaces/login.html' },
        { name: 'pre-carregamento-login.js', path: './src/interfaces/pre-carregamento-login.js' },
        { name: 'validacao-credenciais.js', path: './src/aplicacao/validacao-credenciais.js' },
        { name: 'usuarios.json', path: './dados/usuarios.json' }
    ];
    
    for (const file of filesCheck) {
        const exists = await fs.pathExists(file.path);
        console.log(`   ${exists ? '✅' : '❌'} ${file.name}`);
    }
    
    // 2. Verificar conteúdo do usuarios.json
    console.log('\n2️⃣  VERIFICANDO ARQUIVO DE USUÁRIOS\n');
    
    try {
        const users = await fs.readJson('./dados/usuarios.json');
        console.log(`   ✅ Arquivo carregado`);
        console.log(`   📊 Total de usuários: ${users.usuarios.length}`);
        
        const admin = users.usuarios.find(u => u.username === 'admin');
        if (admin) {
            console.log(`   ✅ Admin encontrado`);
            console.log(`      - Email: ${admin.email}`);
            console.log(`      - Role: ${admin.role}`);
            console.log(`      - Ativo: ${admin.ativo}`);
            console.log(`      - Password hash: ${admin.password.substring(0, 20)}...`);
        } else {
            console.log(`   ❌ Admin NÃO encontrado!`);
        }
    } catch (error) {
        console.log(`   ❌ Erro ao ler usuarios.json: ${error.message}`);
    }
    
    // 3. Testar validação de credenciais
    console.log('\n3️⃣  TESTANDO VALIDAÇÃO DE CREDENCIAIS\n');
    
    try {
        const validacao = require('./src/aplicacao/validacao-credenciais');
        
        // Teste 1: Admin correto
        console.log('   Teste 1: admin/admin');
        const teste1 = await validacao.validarCredenciais('admin', 'admin');
        console.log(`      ${teste1 ? '✅' : '❌'} Resultado: ${teste1}`);
        
        // Teste 2: Obter role
        console.log('\n   Teste 2: Obter role do admin');
        const role = await validacao.obterNivelPermissao('admin');
        console.log(`      ✅ Role: ${role}`);
        
        // Teste 3: Obter dados
        console.log('\n   Teste 3: Obter dados do admin');
        const dados = await validacao.obterDadosUsuario('admin');
        if (dados) {
            console.log(`      ✅ Dados obtidos:`);
            console.log(`         - Username: ${dados.username}`);
            console.log(`         - Email: ${dados.email}`);
            console.log(`         - Role: ${dados.role}`);
        } else {
            console.log(`      ❌ Dados não encontrados`);
        }
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}`);
        console.log(`      Stack: ${error.stack}`);
    }
    
    // 4. Verificar estrutura de HTML/JS
    console.log('\n4️⃣  VERIFICANDO ESTRUTURA DO LOGIN.HTML\n');
    
    try {
        const html = await fs.readFile('./src/interfaces/login.html', 'utf-8');
        
        const checks = [
            { name: 'Form ID', pattern: /id="loginForm"/ },
            { name: 'Username input', pattern: /id="username"/ },
            { name: 'Password input', pattern: /id="password"/ },
            { name: 'Submit button', pattern: /id="btnLogin"/ },
            { name: 'authAPI usage', pattern: /window\.authAPI\.tentarLogin/ },
            { name: 'navigationAPI usage', pattern: /window\.navigationAPI\.navigate/ }
        ];
        
        for (const check of checks) {
            const found = check.pattern.test(html);
            console.log(`   ${found ? '✅' : '❌'} ${check.name}`);
        }
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}`);
    }
    
    // 5. Verificar preload
    console.log('\n5️⃣  VERIFICANDO PRELOAD\n');
    
    try {
        const preload = await fs.readFile('./src/interfaces/pre-carregamento-login.js', 'utf-8');
        
        const checks = [
            { name: 'contextBridge imported', pattern: /contextBridge/ },
            { name: 'authAPI exposed', pattern: /authAPI/ },
            { name: 'tentarLogin method', pattern: /tentarLogin/ },
            { name: 'navigationAPI exposed', pattern: /navigationAPI/ },
            { name: 'navigate method', pattern: /navigate/ }
        ];
        
        for (const check of checks) {
            const found = check.pattern.test(preload);
            console.log(`   ${found ? '✅' : '❌'} ${check.name}`);
        }
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}`);
    }
    
    // 6. Verificar main.js handlers
    console.log('\n6️⃣  VERIFICANDO IPC HANDLERS NO MAIN.JS\n');
    
    try {
        const main = await fs.readFile('./main.js', 'utf-8');
        
        const checks = [
            { name: 'login-attempt handler', pattern: /ipcMain\.handle\('login-attempt'/ },
            { name: 'navigate-to handler', pattern: /ipcMain\.handle\('navigate-to'/ },
            { name: 'validarCredenciais imported', pattern: /validarCredenciais/ },
            { name: 'obterNivelPermissao imported', pattern: /obterNivelPermissao/ }
        ];
        
        for (const check of checks) {
            const found = check.pattern.test(main);
            console.log(`   ${found ? '✅' : '❌'} ${check.name}`);
        }
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}`);
    }
    
    // 7. Simular fluxo completo
    console.log('\n7️⃣  SIMULANDO FLUXO COMPLETO DE LOGIN\n');
    
    try {
        const validacao = require('./src/aplicacao/validacao-credenciais');
        const gerenciadorUsuarios = require('./src/aplicacao/gerenciador-usuarios');
        
        console.log('   Passo 1: Validar credenciais admin/admin');
        const valido = await validacao.validarCredenciais('admin', 'admin');
        console.log(`      ${valido ? '✅' : '❌'} Credenciais válidas: ${valido}`);
        
        if (valido) {
            console.log('\n   Passo 2: Obter role');
            const role = await validacao.obterNivelPermissao('admin');
            console.log(`      ✅ Role: ${role}`);
            
            console.log('\n   Passo 3: Obter dados do usuário');
            const dados = await validacao.obterDadosUsuario('admin');
            console.log(`      ✅ Dados obtidos: ${dados ? 'sim' : 'não'}`);
            
            console.log('\n   Passo 4: Registrar login');
            await gerenciadorUsuarios.registrarLogin('admin');
            console.log(`      ✅ Login registrado`);
            
            console.log('\n   ✅ FLUXO COMPLETO FUNCIONANDO!');
        } else {
            console.log(`      ❌ Credenciais inválidas!`);
        }
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}`);
        console.log(`      Stack: ${error.stack}`);
    }
    
    console.log('\n═══════════════════════════════════════════════════════════\n');
    console.log('✨ DIAGNÓSTICO CONCLUÍDO\n');
}

diagnostico().catch(console.error);
