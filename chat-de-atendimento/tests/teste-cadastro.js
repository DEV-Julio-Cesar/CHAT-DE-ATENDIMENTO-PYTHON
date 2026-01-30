#!/usr/bin/env node
// =========================================================================
// TESTE DE SISTEMA DE CADASTRO
// =========================================================================

const fs = require('fs-extra');

console.log('👤 TESTANDO SISTEMA DE CADASTRO...\n');

async function testarCadastro() {
    try {
        const gerenciadorUsuarios = require('../src/aplicacao/gerenciador-usuarios');
        
        console.log('✅ Módulo de gerenciamento de usuários carregado');
        
        // Listar usuários existentes
        const usuariosAntes = await gerenciadorUsuarios.listarUsuarios();
        console.log(`📋 Usuários antes do teste: ${usuariosAntes.length}`);
        
        // Criar usuário de teste
        const usuarioTeste = {
            username: 'teste_' + Date.now(),
            password: 'senha123',
            nome: 'Usuário de Teste',
            email: 'teste@exemplo.com',
            role: 'atendente'
        };
        
        console.log(`🔄 Criando usuário de teste: ${usuarioTeste.username}`);
        
        const resultadoCadastro = await gerenciadorUsuarios.cadastrarUsuario(usuarioTeste);
        
        if (resultadoCadastro.success) {
            console.log('✅ Usuário criado com sucesso');
            
            // Verificar se o usuário foi realmente criado
            const usuariosDepois = await gerenciadorUsuarios.listarUsuarios();
            const usuarioCriado = usuariosDepois.find(u => u.username === usuarioTeste.username);
            
            if (usuarioCriado) {
                console.log('✅ Usuário encontrado na lista');
                console.log(`📝 Nome: ${usuarioCriado.nome}`);
                console.log(`📧 Email: ${usuarioCriado.email}`);
                console.log(`🔑 Role: ${usuarioCriado.role}`);
                
                // Remover usuário de teste
                console.log('🗑️  Removendo usuário de teste...');
                await gerenciadorUsuarios.removerUsuario(usuarioTeste.username);
                console.log('✅ Usuário de teste removido');
            } else {
                console.log('❌ Usuário não encontrado após criação');
            }
        } else {
            console.log('❌ Falha ao criar usuário:', resultadoCadastro.message);
        }
        
        // Testar cadastro com dados inválidos
        console.log('\n🔄 Testando validação de dados...');
        
        const usuarioInvalido = {
            username: '', // username vazio
            password: '123', // senha muito curta
            nome: '',
            email: 'email_invalido'
        };
        
        const resultadoInvalido = await gerenciadorUsuarios.cadastrarUsuario(usuarioInvalido);
        
        if (!resultadoInvalido.success) {
            console.log('✅ Validação de dados funcionando');
            console.log(`📝 Erro esperado: ${resultadoInvalido.message}`);
        } else {
            console.log('❌ Sistema aceitou dados inválidos');
        }
        
        console.log('\n🎉 TESTE DE CADASTRO CONCLUÍDO');
        
    } catch (erro) {
        console.error('❌ ERRO NO TESTE DE CADASTRO:', erro.message);
        process.exit(1);
    }
}

testarCadastro();