#!/usr/bin/env node

/**
 * Teste Específico: poolWhatsApp.createClient is not a function
 * 
 * Objetivo: Validar que o singleton foi registrado corretamente
 * e que a rota consegue criar clientes sem erros de função não definida
 */

const fetch = require('node-fetch');

const API_URL = 'http://localhost:3333';
const TIMEOUT = 120000;

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    console.log('\n' + '='.repeat(70));
    console.log('🔍 TESTE ESPECÍFICO: poolWhatsApp.createClient Resolution');
    console.log('='.repeat(70));

    // Aguardar API ficar pronta
    let apiReady = false;
    let attempts = 0;
    process.stdout.write('\n⏳ Aguardando API...');
    
    while (!apiReady && attempts < 30) {
        try {
            const response = await fetch(`${API_URL}/api/health`, { timeout: 5000 });
            if (response.status < 500) {
                apiReady = true;
                process.stdout.write(' ✅\n');
            }
        } catch (e) {
            attempts++;
            process.stdout.write('.');
            await sleep(1000);
        }
    }

    if (!apiReady) {
        console.error('\n❌ API não respondeu em tempo hábil\n');
        process.exit(1);
    }

    console.log('\n📋 Validações:\n');

    // 1. Verificar arquivo de singleton
    console.log('1️⃣  Validando módulo singleton (instancia-pool.js)...');
    try {
        const path = require('path');
        const fs = require('fs');
        const poolFile = path.join(__dirname, 'src', 'services', 'instancia-pool.js');
        
        if (!fs.existsSync(poolFile)) {
            throw new Error('Arquivo não existe');
        }
        
        const content = fs.readFileSync(poolFile, 'utf-8');
        const hasObterPool = content.includes('function obterPool()');
        const hasDefinirPool = content.includes('function definirPool(pool)');
        const hasTemPool = content.includes('function temPool()');
        
        if (!hasObterPool || !hasDefinirPool || !hasTemPool) {
            throw new Error('Funções não encontradas');
        }
        
        console.log('   ✅ Singleton correto\n');
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}\n`);
        process.exit(1);
    }

    // 2. Verificar rota
    console.log('2️⃣  Validando rota (rotasWhatsAppSincronizacao.js)...');
    try {
        const path = require('path');
        const fs = require('fs');
        const routeFile = path.join(__dirname, 'src', 'rotas', 'rotasWhatsAppSincronizacao.js');
        
        if (!fs.existsSync(routeFile)) {
            throw new Error('Arquivo não existe');
        }
        
        const content = fs.readFileSync(routeFile, 'utf-8');
        const hasPoolImport = content.includes("require('../services/instancia-pool')");
        const hasGetPoolValidado = content.includes('function getPoolValidado()');
        const usesGetPool = content.includes('getPoolValidado()');
        
        if (!hasPoolImport) {
            throw new Error('Não importa instancia-pool');
        }
        if (!hasGetPoolValidado) {
            throw new Error('getPoolValidado não está definida');
        }
        if (!usesGetPool) {
            throw new Error('getPoolValidado não é utilizada');
        }
        
        console.log('   ✅ Rota corretamente configurada\n');
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}\n`);
        process.exit(1);
    }

    // 3. Verificar main.js
    console.log('3️⃣  Validando inicialização (main.js)...');
    try {
        const path = require('path');
        const fs = require('fs');
        const mainFile = path.join(__dirname, 'main.js');
        
        if (!fs.existsSync(mainFile)) {
            throw new Error('main.js não existe');
        }
        
        const content = fs.readFileSync(mainFile, 'utf-8');
        const hasDefinirPoolImport = content.includes("require('./src/services/instancia-pool')");
        const hasDefinirPoolCall = content.includes('definirPool(poolWhatsApp)');
        
        if (!hasDefinirPoolImport) {
            throw new Error('definirPool não foi importado');
        }
        if (!hasDefinirPoolCall) {
            throw new Error('definirPool(poolWhatsApp) não foi chamado');
        }
        
        console.log('   ✅ Inicialização correta\n');
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}\n`);
        process.exit(1);
    }

    // 4. Teste de API
    console.log('4️⃣  Testando endpoint /api/whatsapp/conectar-por-numero...');
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        try {
            const response = await fetch(`${API_URL}/api/whatsapp/conectar-por-numero`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phoneNumber: '5500000000000' }),
                signal: controller.signal
            });
            
            const responseText = await response.text();
            
            // Verificar se há o erro específico
            if (responseText.includes('poolWhatsApp.createClient is not a function')) {
                throw new Error('ERRO CRÍTICO ENCONTRADO: poolWhatsApp.createClient is not a function');
            }
            
            // Qualquer outra resposta é aceitável (sucesso, erro de validação, etc)
            console.log(`   ✅ Endpoint respondeu corretamente (status ${response.status})\n`);
            
        } finally {
            clearTimeout(timeoutId);
        }
    } catch (error) {
        console.log(`   ❌ Erro: ${error.message}\n`);
        process.exit(1);
    }

    // Resumo final
    console.log('='.repeat(70));
    console.log('\n✅ TESTE APROVADO!\n');
    console.log('📊 Resumo de Validações:\n');
    console.log('  ✓ Singleton instancia-pool.js implementado');
    console.log('  ✓ Rota usa getPoolValidado() para acessar pool');
    console.log('  ✓ main.js chama definirPool(poolWhatsApp)');
    console.log('  ✓ Endpoint respondeu sem erro "is not a function"\n');
    console.log('🎉 Correção v2.0.3 validada com sucesso!\n');
    console.log('='.repeat(70) + '\n');
    
    process.exit(0);
}

main().catch(error => {
    console.error('\n❌ ERRO CRÍTICO:', error.message, '\n');
    process.exit(1);
});
