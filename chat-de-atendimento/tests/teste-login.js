#!/usr/bin/env node
// =========================================================================
// TESTE DE SISTEMA DE LOGIN
// =========================================================================

const fs = require('fs-extra');
const path = require('path');

console.log('🔐 TESTANDO SISTEMA DE LOGIN...\n');

async function testarLogin() {
    try {
        // Importar módulos necessários
        const { validarCredenciais, obterNivelPermissao } = require('../src/aplicacao/validacao-credenciais');
        const gerenciadorUsuarios = require('../src/aplicacao/gerenciador-usuarios');
        
        console.log('✅ Módulos de autenticação carregados com sucesso');
        
        // Verificar se existe usuário admin padrão
        const usuarios = await gerenciadorUsuarios.listarUsuarios();
        console.log(`📋 Total de usuários cadastrados: ${usuarios.length}`);
        
        const adminExiste = usuarios.some(u => u.username === 'admin');
        if (adminExiste) {
            console.log('✅ Usuário admin encontrado');
            
            // Testar login do admin
            const loginValido = await validarCredenciais('admin', 'admin');
            if (loginValido) {
                console.log('✅ Login do admin funcionando');
                
                const nivel = await obterNivelPermissao('admin');
                console.log(`✅ Nível de permissão do admin: ${nivel}`);
            } else {
                console.log('❌ Falha no login do admin');
            }
        } else {
            console.log('⚠️  Usuário admin não encontrado');
            console.log('💡 Execute: npm run seed:admin');
        }
        
        // Testar login inválido
        const loginInvalido = await validarCredenciais('usuario_inexistente', 'senha_errada');
        if (!loginInvalido) {
            console.log('✅ Rejeição de login inválido funcionando');
        } else {
            console.log('❌ Sistema aceitou login inválido');
        }
        
        console.log('\n🎉 TESTE DE LOGIN CONCLUÍDO');
        
    } catch (erro) {
        console.error('❌ ERRO NO TESTE DE LOGIN:', erro.message);
        process.exit(1);
    }
}

testarLogin();