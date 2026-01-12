/**
 * Script para Resetar e Recriar Usuário Admin
 * Resolve problemas de login recriando o usuário com credenciais corretas
 */

const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');

const USERS_FILE = path.join(__dirname, 'dados', 'usuarios.json');

function hashPassword(password) {
    return crypto.createHash('sha256').update(password).digest('hex');
}

async function resetarAdmin() {
    console.log('🔧 Resetando Usuário Admin\n');
    console.log('════════════════════════════════════════\n');
    
    try {
        // Backup do arquivo atual
        if (await fs.pathExists(USERS_FILE)) {
            const backup = USERS_FILE + '.backup.' + Date.now();
            await fs.copy(USERS_FILE, backup);
            console.log('✅ Backup criado:', path.basename(backup));
        }
        
        // Cria novo arquivo com admin resetado
        const novoAdmin = {
            usuarios: [
                {
                    username: 'admin',
                    password: hashPassword('admin'), // SHA-256 de "admin"
                    email: 'admin@sistema.com',
                    role: 'admin',
                    ativo: true,
                    criadoEm: new Date().toISOString(),
                    ultimoLogin: null
                }
            ]
        };
        
        // Garante que o diretório existe
        await fs.ensureDir(path.dirname(USERS_FILE));
        
        // Salva novo arquivo
        await fs.writeJson(USERS_FILE, novoAdmin, { spaces: 2 });
        
        console.log('\n✅ Usuário admin resetado com sucesso!\n');
        console.log('📋 Credenciais:');
        console.log('   Usuário: admin');
        console.log('   Senha: admin');
        console.log('   Tipo: SHA-256');
        console.log('   Hash:', novoAdmin.usuarios[0].password);
        console.log('\n════════════════════════════════════════');
        console.log('\n🚀 Próximos passos:');
        console.log('   1. Feche COMPLETAMENTE o aplicativo Electron');
        console.log('   2. Execute: npm start');
        console.log('   3. Tente logar com: admin/admin');
        console.log();
        
        // Testa se a senha está correta
        const validacao = require('./src/aplicacao/validacao-credenciais');
        console.log('🧪 Testando credenciais...');
        const resultado = await validacao.validarCredenciais('admin', 'admin');
        
        if (resultado) {
            console.log('✅ TESTE PASSOU! Login funcionando!\n');
        } else {
            console.log('❌ TESTE FALHOU! Algo está errado.\n');
        }
        
    } catch (error) {
        console.error('❌ Erro ao resetar admin:', error.message);
        console.error(error.stack);
    }
}

resetarAdmin();
