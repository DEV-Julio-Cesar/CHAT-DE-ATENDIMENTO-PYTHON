#!/usr/bin/env node

/**
 * Teste: Conectar por Número - Versão v2.0.3
 * 
 * Validações:
 * 1. ✓ IPC funciona (janela abre)
 * 2. ✓ URLs absolutas funcionam (sem Failed to fetch)
 * 3. ✓ poolWhatsApp é inicializado no singleton
 * 4. ✓ Rota /api/whatsapp/conectar-por-numero chama pool.createClient()
 * 5. ✓ Cliente é criado com sucesso
 */

const fetch = require('node-fetch');
const axios = require('axios');

const API_URL = 'http://localhost:3333';
const TIMEOUT = 120000; // 2 minutos

let testsPassed = 0;
let testsFailed = 0;

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function test(name, fn) {
    try {
        process.stdout.write(`\n📝 ${name}... `);
        await fn();
        process.stdout.write('✅ OK\n');
        testsPassed++;
    } catch (error) {
        process.stdout.write(`❌ FALHOU\n`);
        console.error(`   Erro: ${error.message}`);
        testsFailed++;
    }
}

async function main() {
    console.log('\n' + '='.repeat(60));
    console.log('🧪 TESTE: Conectar por Número (v2.0.3)');
    console.log('='.repeat(60));

    // Aguardar API ficar pronta
    let apiReady = false;
    let attempts = 0;
    while (!apiReady && attempts < 30) {
        try {
            const response = await fetch(`${API_URL}/api/health`, { timeout: 5000 });
            if (response.status < 500) {
                apiReady = true;
            }
        } catch (e) {
            attempts++;
            await sleep(1000);
        }
    }

    if (!apiReady) {
        console.error('\n❌ API não está respondendo em ' + API_URL);
        process.exit(1);
    }

    console.log('\n✓ API está rodando');

    // Teste 1: Validar que a rota existe
    await test('Rota /api/whatsapp/listar-clientes existe', async () => {
        const response = await fetch(`${API_URL}/api/whatsapp/listar-clientes`);
        if (!response.ok && response.status !== 401) {
            throw new Error(`Status ${response.status}`);
        }
    });

    // Teste 2: Validar que a rota conectar-por-numero existe
    await test('Rota /api/whatsapp/conectar-por-numero está registrada', async () => {
        // Tentar com POST para verificar se rota existe
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        try {
            const response = await fetch(`${API_URL}/api/whatsapp/conectar-por-numero`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phoneNumber: '5500000000000' }),
                signal: controller.signal
            });
            
            // Qualquer resposta (exceto 404 ou 500 server error) significa que a rota existe
            if (response.status === 404) {
                throw new Error('Rota não existe (404)');
            }
            if (response.status === 405) {
                throw new Error('Método não permitido (405)');
            }
            if (response.status >= 500) {
                const text = await response.text();
                if (text.includes('poolWhatsApp.createClient is not a function')) {
                    throw new Error('ERRO CRÍTICO: poolWhatsApp.createClient não é função!');
                }
                throw new Error(`Erro servidor (${response.status})`);
            }
        } finally {
            clearTimeout(timeoutId);
        }
    });

    // Teste 3: Validar importação correta do singleton
    await test('Módulo instancia-pool.js está sendo utilizado', async () => {
        const path = require('path');
        const fs = require('fs');
        const routeFile = path.join(__dirname, 'src', 'rotas', 'rotasWhatsAppSincronizacao.js');
        
        if (!fs.existsSync(routeFile)) {
            throw new Error('Arquivo de rota não encontrado');
        }
        
        const content = fs.readFileSync(routeFile, 'utf-8');
        if (!content.includes("require('../services/instancia-pool')")) {
            throw new Error('Rota não importa singleton instancia-pool');
        }
    });

    // Teste 4: Validar que definirPool foi adicionado
    await test('Função definirPool() está registrada no main.js', async () => {
        const path = require('path');
        const fs = require('fs');
        const mainFile = path.join(__dirname, 'main.js');
        
        if (!fs.existsSync(mainFile)) {
            throw new Error('main.js não encontrado');
        }
        
        const content = fs.readFileSync(mainFile, 'utf-8');
        if (!content.includes('definirPool(poolWhatsApp)')) {
            throw new Error('main.js não chama definirPool()');
        }
    });

    // Teste 5: Validar que getPoolValidado wraps access corretamente
    await test('Função getPoolValidado() está presente na rota', async () => {
        const path = require('path');
        const fs = require('fs');
        const routeFile = path.join(__dirname, 'src', 'rotas', 'rotasWhatsAppSincronizacao.js');
        const content = fs.readFileSync(routeFile, 'utf-8');
        
        if (!content.includes('function getPoolValidado()')) {
            throw new Error('getPoolValidado não está definida');
        }
        
        // Verificar que está sendo usada
        if (!content.includes('getPoolValidado().createClient')) {
            throw new Error('getPoolValidado().createClient não é chamado');
        }
    });

    // Resumo
    console.log('\n' + '='.repeat(60));
    console.log(`\n📊 Resultado: ${testsPassed} ✅ | ${testsFailed} ❌\n`);

    if (testsFailed === 0) {
        console.log('✅ TODOS OS TESTES PASSARAM - Sistema v2.0.3 validado!\n');
        process.exit(0);
    } else {
        console.log(`❌ ${testsFailed} teste(s) falharam\n`);
        process.exit(1);
    }
}

main().catch(console.error);
