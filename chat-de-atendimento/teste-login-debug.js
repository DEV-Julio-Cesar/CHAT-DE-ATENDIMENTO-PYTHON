/**
 * Script de Teste - Validação de Login
 * Testa o login do usuário admin
 */

const crypto = require('crypto');
const bcrypt = require('bcryptjs');
const fs = require('fs-extra');
const path = require('path');

const USERS_FILE = path.join(__dirname, 'dados', 'usuarios.json');

function hashPassword(password) {
    return crypto.createHash('sha256').update(password).digest('hex');
}

async function testarLogin() {
    console.log('🔐 Testando Login do Administrador\n');
    
    try {
        // Carrega usuários
        const dados = await fs.readJson(USERS_FILE);
        const admin = dados.usuarios.find(u => u.username === 'admin');
        
        if (!admin) {
            console.log('❌ Usuário admin não encontrado!\n');
            return;
        }
        
        console.log('📋 Dados do Admin:');
        console.log('   Username:', admin.username);
        console.log('   Email:', admin.email);
        console.log('   Role:', admin.role);
        console.log('   Ativo:', admin.ativo);
        console.log('   Password (hash):', admin.password.substring(0, 50) + '...');
        console.log('   Tipo de hash:', admin.password.startsWith('$2') ? 'bcrypt' : 'SHA-256');
        console.log();
        
        // Testa senhas comuns
        const senhasTeste = ['admin', 'Admin', 'admin123', 'password', '123456'];
        
        console.log('🧪 Testando senhas comuns:\n');
        
        for (const senha of senhasTeste) {
            console.log(`   Testando: "${senha}"`);
            
            // Testa bcrypt
            if (admin.password.startsWith('$2')) {
                try {
                    const bcryptOk = await bcrypt.compare(senha, admin.password);
                    if (bcryptOk) {
                        console.log(`   ✅ SENHA CORRETA com bcrypt: "${senha}"\n`);
                        console.log(`📝 Para logar, use:`);
                        console.log(`   Usuário: admin`);
                        console.log(`   Senha: ${senha}`);
                        return;
                    }
                } catch (e) {
                    // Ignora erro e tenta SHA-256
                }
            }
            
            // Testa SHA-256
            const sha256Hash = hashPassword(senha);
            if (admin.password === sha256Hash) {
                console.log(`   ✅ SENHA CORRETA com SHA-256: "${senha}"\n`);
                console.log(`📝 Para logar, use:`);
                console.log(`   Usuário: admin`);
                console.log(`   Senha: ${senha}`);
                return;
            }
        }
        
        console.log('\n❌ Nenhuma senha comum funcionou!\n');
        console.log('💡 Soluções:');
        console.log('   1. Execute: npm run seed:admin');
        console.log('   2. Isso vai redefinir o admin com senha "admin"');
        console.log('   3. Ou delete o arquivo: dados/usuarios.json');
        console.log('   4. E reinicie o sistema\n');
        
    } catch (error) {
        console.error('❌ Erro:', error.message);
    }
}

testarLogin();
