#!/usr/bin/env node
// =========================================================================
// SCRIPT PARA CRIAR USUÁRIO ADMIN PADRÃO
// =========================================================================

const fs = require('fs-extra');
const bcrypt = require('bcryptjs');

console.log('👤 CRIANDO USUÁRIO ADMIN PADRÃO...\n');

async function criarAdmin() {
    try {
        const arquivoUsuarios = 'dados/usuarios.json';
        
        // Garantir que o arquivo existe
        await fs.ensureFile(arquivoUsuarios);
        
        let usuarios = [];
        
        // Tentar ler usuários existentes
        try {
            const conteudo = await fs.readFile(arquivoUsuarios, 'utf8');
            if (conteudo.trim()) {
                const dadosArquivo = JSON.parse(conteudo);
                // Verificar se é array direto ou objeto com propriedade usuarios
                if (Array.isArray(dadosArquivo)) {
                    usuarios = dadosArquivo;
                } else if (dadosArquivo.usuarios && Array.isArray(dadosArquivo.usuarios)) {
                    usuarios = dadosArquivo.usuarios;
                } else {
                    usuarios = [];
                }
            }
        } catch (erro) {
            console.log('📝 Criando novo arquivo de usuários...');
            usuarios = [];
        }
        
        // Verificar se admin já existe
        const adminExiste = usuarios.find(u => u.username === 'admin');
        
        if (adminExiste) {
            console.log('✅ Usuário admin já existe');
            console.log(`📧 Email: ${adminExiste.email}`);
            console.log(`🔑 Role: ${adminExiste.role}`);
            console.log(`📅 Criado em: ${adminExiste.criadoEm}`);
            
            // Atualizar senha se necessário
            let senhaHash;
            try {
                senhaHash = await bcrypt.hash('admin', 10);
            } catch (erro) {
                // Fallback para hash simples se bcrypt falhar
                const crypto = require('crypto');
                senhaHash = crypto.createHash('sha256').update('admin').digest('hex');
            }
            
            adminExiste.password = senhaHash;
            adminExiste.atualizadoEm = new Date().toISOString();
            
            await fs.writeJson(arquivoUsuarios, { usuarios }, { spaces: 2 });
            console.log('🔄 Senha do admin atualizada');
            
        } else {
            console.log('🔄 Criando usuário admin...');
            
            // Criar hash da senha
            let senhaHash;
            try {
                senhaHash = await bcrypt.hash('admin', 10);
                console.log('🔐 Usando bcrypt para hash da senha');
            } catch (erro) {
                // Fallback para hash simples se bcrypt falhar
                const crypto = require('crypto');
                senhaHash = crypto.createHash('sha256').update('admin').digest('hex');
                console.log('🔐 Usando SHA256 para hash da senha (fallback)');
            }
            
            const novoAdmin = {
                username: 'admin',
                password: senhaHash,
                nome: 'Administrador',
                email: 'admin@sistema.com',
                role: 'admin',
                ativo: true,
                criadoEm: new Date().toISOString(),
                ultimoLogin: null,
                atualizadoEm: new Date().toISOString()
            };
            
            usuarios.push(novoAdmin);
            
            await fs.writeJson(arquivoUsuarios, { usuarios }, { spaces: 2 });
            
            console.log('✅ Usuário admin criado com sucesso!');
            console.log(`👤 Username: admin`);
            console.log(`🔑 Password: admin`);
            console.log(`📧 Email: ${novoAdmin.email}`);
            console.log(`🎭 Role: ${novoAdmin.role}`);
        }
        
        console.log('\n🎉 SEED ADMIN CONCLUÍDO');
        console.log('\n💡 Agora você pode fazer login com:');
        console.log('   Username: admin');
        console.log('   Password: admin');
        
    } catch (erro) {
        console.error('❌ ERRO AO CRIAR ADMIN:', erro.message);
        process.exit(1);
    }
}

criarAdmin();