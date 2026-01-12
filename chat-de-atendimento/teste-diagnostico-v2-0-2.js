#!/usr/bin/env node

/**
 * TESTE DE DIAGNÓSTICO v2.0.2
 * Verifica se a feature "Conectar por Número" está funcionando corretamente
 */

const fs = require('fs-extra');
const path = require('path');

console.log('\n' + '='.repeat(60));
console.log('🔍 TESTE DE DIAGNÓSTICO - Conexão por Número v2.0.2');
console.log('='.repeat(60) + '\n');

const basePath = path.join(__dirname);

// ============================================================================
// TESTE 1: Verificar se arquivo HTML existe
// ============================================================================
console.log('📋 TESTE 1: Verificando arquivo conectar-numero.html');
console.log('-'.repeat(60));

const htmlPath = path.join(basePath, 'src', 'interfaces', 'conectar-numero.html');
const htmlExists = fs.existsSync(htmlPath);

if (htmlExists) {
    const stats = fs.statSync(htmlPath);
    const size = (stats.size / 1024).toFixed(2);
    console.log(`✅ ENCONTRADO: ${htmlPath}`);
    console.log(`   Tamanho: ${size} KB`);
} else {
    console.log(`❌ NÃO ENCONTRADO: ${htmlPath}`);
    console.log(`   PROBLEMA: Arquivo desapareceu ou foi movido!`);
}

// ============================================================================
// TESTE 2: Verificar se Pool Manager foi modificado
// ============================================================================
console.log('\n📋 TESTE 2: Verificando modificações em gerenciador-pool.html');
console.log('-'.repeat(60));

const poolPath = path.join(basePath, 'src', 'interfaces', 'gerenciador-pool.html');
const poolContent = fs.readFileSync(poolPath, 'utf8');

const testes = [
    {
        nome: 'Função conectarNovo()',
        regex: /async function conectarNovo\(\)/,
        critica: true
    },
    {
        nome: 'Função mostrarModalConexao()',
        regex: /function mostrarModalConexao\(\)/,
        critica: true
    },
    {
        nome: 'Função abrirConexaoPorNumero()',
        regex: /async function abrirConexaoPorNumero\(\)/,
        critica: true
    },
    {
        nome: 'Modal CSS (.modal-conexao)',
        regex: /\.modal-conexao\s*\{/,
        critica: true
    },
    {
        nome: 'Botão de escolha de método',
        regex: /onclick="abrirConexaoPorNumero\(\)"/,
        critica: true
    }
];

let todasAchadas = true;
testes.forEach(teste => {
    const encontrada = teste.regex.test(poolContent);
    const icone = encontrada ? '✅' : '❌';
    const status = encontrada ? 'OK' : 'FALTANDO';
    console.log(`${icone} ${teste.nome}: ${status}`);
    if (!encontrada && teste.critica) {
        todasAchadas = false;
    }
});

if (!todasAchadas) {
    console.log('\n⚠️  PROBLEMA: Código não foi adicionado corretamente ao gerenciador-pool.html');
}

// ============================================================================
// TESTE 3: Verificar se rotas foram criadas
// ============================================================================
console.log('\n📋 TESTE 3: Verificando novos endpoints da API');
console.log('-'.repeat(60));

const rotasPath = path.join(basePath, 'src', 'rotas', 'rotasWhatsAppSincronizacao.js');
const rotasContent = fs.readFileSync(rotasPath, 'utf8');

const rotasTestes = [
    {
        nome: 'POST /conectar-por-numero',
        regex: /router\.post\(['"]\/conectar-por-numero['"]|POST.*conectar-por-numero/,
        critica: true
    },
    {
        nome: 'GET /status/:clientId',
        regex: /router\.get\(['"]\/status\/:clientId['"]|GET.*status.*clientId/,
        critica: true
    },
    {
        nome: 'Validação de telefone (regex)',
        regex: /\^55\\d\{10,11\}\$|55.*\d.*10.*11/,
        critica: true
    }
];

let todasRotasAchadas = true;
rotasTestes.forEach(rota => {
    const encontrada = rota.regex.test(rotasContent);
    const icone = encontrada ? '✅' : '❌';
    const status = encontrada ? 'OK' : 'FALTANDO';
    console.log(`${icone} ${rota.nome}: ${status}`);
    if (!encontrada && rota.critica) {
        todasRotasAchadas = false;
    }
});

if (!todasRotasAchadas) {
    console.log('\n⚠️  PROBLEMA: Endpoints não foram adicionados corretamente');
}

// ============================================================================
// TESTE 4: Verificar hotfix de listeners
// ============================================================================
console.log('\n📋 TESTE 4: Verificando hotfix de listeners (v2.0.2)');
console.log('-'.repeat(60));

const servicePath = path.join(basePath, 'src', 'services', 'ServicoClienteWhatsApp.js');
const serviceContent = fs.readFileSync(servicePath, 'utf8');

const listenerTestes = [
    {
        nome: 'client.on("disconnected")',
        regex: /client\.on\s*\(\s*['"]disconnected['"]/,
        critica: true
    },
    {
        nome: 'client.on("auth_failure")',
        regex: /client\.on\s*\(\s*['"]auth_failure['"]/,
        critica: true
    }
];

let hotfixOk = true;
listenerTestes.forEach(listener => {
    const encontrada = listener.regex.test(serviceContent);
    const icone = encontrada ? '✅' : '❌';
    const status = encontrada ? 'OK' : 'FALTANDO (BUG!!)';
    console.log(`${icone} ${listener.nome}: ${status}`);
    if (!encontrada) {
        hotfixOk = false;
    }
});

// Verificar se ainda existe .once() (bug antigo)
const hasOnce = /client\.once\s*\(\s*['"]disconnected['"]|client\.once\s*\(\s*['"]auth_failure['"]/.test(serviceContent);
if (hasOnce) {
    console.log(`\n❌ PROBLEMA CRÍTICO: Ainda existem listeners com .once() (BUG ATIVO)!`);
    hotfixOk = false;
}

// ============================================================================
// TESTE 5: Estrutura de arquivos
// ============================================================================
console.log('\n📋 TESTE 5: Estrutura de arquivos');
console.log('-'.repeat(60));

const arquivosEsperados = [
    { caminho: 'src/interfaces/conectar-numero.html', tipo: 'Interface' },
    { caminho: 'src/interfaces/gerenciador-pool.html', tipo: 'Interface' },
    { caminho: 'src/rotas/rotasWhatsAppSincronizacao.js', tipo: 'API' },
    { caminho: 'src/services/ServicoClienteWhatsApp.js', tipo: 'Service' }
];

let estruturaOk = true;
arquivosEsperados.forEach(arquivo => {
    const fullPath = path.join(basePath, arquivo.caminho);
    const existe = fs.existsSync(fullPath);
    const icone = existe ? '✅' : '❌';
    console.log(`${icone} [${arquivo.tipo}] ${arquivo.caminho}`);
    if (!existe) estruturaOk = false;
});

// ============================================================================
// RESULTADO FINAL
// ============================================================================
console.log('\n' + '='.repeat(60));
console.log('📊 RESULTADO DO DIAGNÓSTICO');
console.log('='.repeat(60));

const resultados = [
    { nome: 'Arquivo HTML', ok: htmlExists },
    { nome: 'Pool Manager modificado', ok: todasAchadas },
    { nome: 'Endpoints da API', ok: todasRotasAchadas },
    { nome: 'Hotfix de listeners', ok: hotfixOk },
    { nome: 'Estrutura de arquivos', ok: estruturaOk }
];

let todosOk = true;
resultados.forEach(resultado => {
    const icone = resultado.ok ? '✅' : '❌';
    console.log(`${icone} ${resultado.nome}`);
    if (!resultado.ok) todosOk = false;
});

console.log('\n' + '='.repeat(60));

if (todosOk) {
    console.log('✅ DIAGNÓSTICO OK - Tudo foi implementado corretamente!');
    console.log('\nPróximo passo: Iniciar aplicação com "npm start"');
} else {
    console.log('❌ PROBLEMAS DETECTADOS - Veja acima os detalhes');
    console.log('\nProblemas encontrados:');
    if (!htmlExists) console.log('  • Arquivo conectar-numero.html não existe');
    if (!todasAchadas) console.log('  • Código não foi adicionado ao gerenciador-pool.html');
    if (!todasRotasAchadas) console.log('  • Endpoints não foram adicionados');
    if (!hotfixOk) console.log('  • Listeners não usam .on() corretamente');
    if (!estruturaOk) console.log('  • Estrutura de arquivos incompleta');
}

console.log('='.repeat(60) + '\n');

process.exit(todosOk ? 0 : 1);
