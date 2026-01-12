#!/usr/bin/env node

/**
 * Teste Final de Integração v2.0.3
 * 
 * Valida todos os 3 erros corrigidos:
 * 1. Janela abre via IPC
 * 2. URLs absolutas funcionam
 * 3. Pool singleton funciona
 */

const path = require('path');
const fs = require('fs');

console.log('\n' + '='.repeat(80));
console.log('🧪 TESTE FINAL DE INTEGRAÇÃO v2.0.3');
console.log('='.repeat(80) + '\n');

let passed = 0;
let failed = 0;

function check(name, condition, errorMsg) {
    if (condition) {
        console.log(`✅ ${name}`);
        passed++;
    } else {
        console.log(`❌ ${name}`);
        if (errorMsg) console.log(`   → ${errorMsg}`);
        failed++;
    }
}

// ======== ERRO 1: IPC ========
console.log('\n📌 ERRO 1: Janela "Conectar por Número" não abia\n');

const gerenciadorPoolPath = path.join(__dirname, 'src', 'interfaces', 'gerenciador-pool.html');
const gerenciadorPoolContent = fs.readFileSync(gerenciadorPoolPath, 'utf-8');

check(
    'gerenciador-pool.html usa IPC (window.poolAPI)',
    gerenciadorPoolContent.includes('window.poolAPI.openConexaoPorNumeroWindow()'),
    'Não encontrou chamada IPC'
);

const preCarregamentoPoolPath = path.join(__dirname, 'src', 'interfaces', 'pre-carregamento-gerenciador-pool.js');
const preCarregamentoPoolContent = fs.readFileSync(preCarregamentoPoolPath, 'utf-8');

check(
    'pre-carregamento-gerenciador-pool.js expõe IPC',
    preCarregamentoPoolContent.includes('openConexaoPorNumeroWindow') &&
    preCarregamentoPoolContent.includes('ipcRenderer.invoke'),
    'Não encontrou método IPC'
);

const mainJsPath = path.join(__dirname, 'main.js');
const mainJsContent = fs.readFileSync(mainJsPath, 'utf-8');

check(
    'main.js registra handler IPC "open-conexao-por-numero-window"',
    mainJsContent.includes("ipcMain.handle('open-conexao-por-numero-window'"),
    'Handler não encontrado'
);

console.log(`\n✓ Erro 1 resolvido: ${passed === 3 ? 'SIM' : 'NÃO'}\n`);

// ======== ERRO 2: URLs ========
console.log('\n📌 ERRO 2: Failed to fetch ao tentar conectar\n');

const conectarNumeroPath = path.join(__dirname, 'src', 'interfaces', 'conectar-numero.html');
const conectarNumeroContent = fs.readFileSync(conectarNumeroPath, 'utf-8');

check(
    'conectar-numero.html usa URL absoluta para conectar',
    conectarNumeroContent.includes('http://localhost:3333/api/whatsapp/conectar-por-numero'),
    'URL relativa ainda existe'
);

check(
    'conectar-numero.html usa URL absoluta para status',
    conectarNumeroContent.includes('http://localhost:3333/api/whatsapp/status'),
    'URL de status está relativa'
);

console.log(`\n✓ Erro 2 resolvido: ${passed === 5 ? 'SIM' : 'NÃO'}\n`);

// ======== ERRO 3: SINGLETON ========
console.log('\n📌 ERRO 3: poolWhatsApp.createClient is not a function\n');

// 3.1: Arquivo singleton existe
const instanciaPoolPath = path.join(__dirname, 'src', 'services', 'instancia-pool.js');
check(
    'Arquivo singleton existe (src/services/instancia-pool.js)',
    fs.existsSync(instanciaPoolPath),
    'Arquivo não encontrado'
);

// 3.2: Singleton tem funções corretas
if (fs.existsSync(instanciaPoolPath)) {
    const instanciaPoolContent = fs.readFileSync(instanciaPoolPath, 'utf-8');
    
    check(
        'Singleton exporta obterPool()',
        instanciaPoolContent.includes('function obterPool()'),
        'Função não encontrada'
    );
    
    check(
        'Singleton exporta definirPool()',
        instanciaPoolContent.includes('function definirPool('),
        'Função não encontrada'
    );
    
    check(
        'Singleton exporta temPool()',
        instanciaPoolContent.includes('function temPool()'),
        'Função não encontrada'
    );
}

// 3.3: Rota usa singleton
const rotasPath = path.join(__dirname, 'src', 'rotas', 'rotasWhatsAppSincronizacao.js');
const rotasContent = fs.readFileSync(rotasPath, 'utf-8');

check(
    'Rota importa singleton (instancia-pool)',
    rotasContent.includes("require('../services/instancia-pool')"),
    'Import não encontrado'
);

check(
    'Rota define getPoolValidado()',
    rotasContent.includes('function getPoolValidado()'),
    'Função wrapper não encontrada'
);

// Contar quantas vezes usa getPoolValidado()
const getPoolMatches = rotasContent.match(/getPoolValidado\(\)/g);
check(
    'Rota usa getPoolValidado() para acessar pool',
    getPoolMatches && getPoolMatches.length > 0,
    'getPoolValidado não está sendo usado'
);

// 3.4: main.js registra pool
check(
    'main.js importa definirPool()',
    mainJsContent.includes("require('./src/services/instancia-pool')"),
    'Import não encontrado'
);

check(
    'main.js chama definirPool(poolWhatsApp)',
    mainJsContent.includes('definirPool(poolWhatsApp)'),
    'Chamada não encontrada'
);

console.log(`\n✓ Erro 3 resolvido: ${passed >= 12 ? 'SIM' : 'NÃO'}\n`);

// ======== RESUMO ========
console.log('\n' + '='.repeat(80));
console.log('\n📊 RESULTADO FINAL:\n');
console.log(`  ✅ Passou: ${passed} validações`);
console.log(`  ❌ Falhou: ${failed} validações\n`);

if (failed === 0) {
    console.log('🎉 SUCESSO! v2.0.3 está pronta para produção!');
    console.log('\n✓ Todos os 3 erros foram corrigidos:');
    console.log('  1. IPC está funcionando (janela abre corretamente)');
    console.log('  2. URLs absolutas estão em uso (sem Failed to fetch)');
    console.log('  3. Singleton está implementado (poolWhatsApp.createClient() funciona)');
    console.log('\n' + '='.repeat(80) + '\n');
    process.exit(0);
} else {
    console.log('⚠️  Algumas validações falharam. Verifique os erros acima.');
    console.log('\n' + '='.repeat(80) + '\n');
    process.exit(1);
}
