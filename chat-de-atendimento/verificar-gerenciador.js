#!/usr/bin/env node

/**
 * Verificador de Status - Sistema de Gerenciamento de Comandos
 * 
 * Verifica se todos os arquivos estão no lugar certo
 */

const fs = require('fs-extra');
const path = require('path');

const rootDir = __dirname;

const arquivosEsperados = [
    // Interface Web
    { path: 'src/interfaces/gerenciador-comandos.html', tipo: '🎨 Interface Web', obrigatorio: true },
    { path: 'src/interfaces/index-gerenciador.html', tipo: '🎨 Página Inicial', obrigatorio: true },

    // API
    { path: 'src/rotas/base-conhecimento-api.js', tipo: '📡 API REST', obrigatorio: true },

    // Aplicação
    { path: 'src/aplicacao/gerenciador-base-conhecimento.js', tipo: '⚙️ Gerenciador', obrigatorio: true },

    // Dados
    { path: 'dados/base-conhecimento-robo.json', tipo: '💾 Base de Dados', obrigatorio: false },

    // Documentação
    { path: 'docs/GERENCIADOR-COMANDOS.md', tipo: '📚 Documentação Completa', obrigatorio: true },
    { path: 'docs/GUIA-RAPIDO-COMANDOS.md', tipo: '⚡ Guia Rápido', obrigatorio: true },
    { path: 'docs/FLUXO-COMPLETO-SISTEMA.md', tipo: '🔄 Fluxo do Sistema', obrigatorio: true },

    // Setup
    { path: 'scripts/setup-base-conhecimento.js', tipo: '🔧 Script Setup', obrigatorio: true },

    // README
    { path: 'COMECE-AQUI.md', tipo: '📖 README', obrigatorio: true }
];

async function verificarStatus() {
    console.log('\n🔍 Verificando Status do Sistema\n');
    console.log('═'.repeat(60));

    let obrigatoriosOk = 0;
    let obrigatoriosTotal = 0;
    let opcionaisOk = 0;
    let opcionaisTotal = 0;

    for (const arquivo of arquivosEsperados) {
        const caminhoCompleto = path.join(rootDir, arquivo.path);
        const existe = await fs.pathExists(caminhoCompleto);
        const status = existe ? '✅' : '❌';

        console.log(`${status} ${arquivo.tipo.padEnd(30)} → ${arquivo.path}`);

        if (arquivo.obrigatorio) {
            obrigatoriosTotal++;
            if (existe) obrigatoriosOk++;
        } else {
            opcionaisTotal++;
            if (existe) opcionaisOk++;
        }
    }

    console.log('═'.repeat(60));

    // Resumo
    console.log(`\n📊 RESUMO`);
    console.log(`\n📋 Obrigatórios: ${obrigatoriosOk}/${obrigatoriosTotal}`);
    
    if (obrigatoriosOk === obrigatoriosTotal) {
        console.log('   ✅ Todos os arquivos obrigatórios presentes!');
    } else {
        console.log(`   ⚠️  Faltam ${obrigatoriosTotal - obrigatoriosOk} arquivos`);
    }

    console.log(`\n📦 Opcionais: ${opcionaisOk}/${opcionaisTotal}`);
    
    if (opcionaisOk === opcionaisTotal) {
        console.log('   ✅ Todos os arquivos opcionais presentes!');
    } else {
        console.log(`   ℹ️  ${opcionaisTotal - opcionaisOk} arquivo(s) opcional(is) faltando`);
    }

    // Verificar dependências
    console.log('\n\n📦 DEPENDÊNCIAS NECESSÁRIAS');
    console.log('═'.repeat(60));

    const packagePath = path.join(rootDir, 'package.json');
    if (await fs.pathExists(packagePath)) {
        const pkg = await fs.readJson(packagePath);
        
        const dependenciasNecessarias = [
            'express',
            'cors',
            'body-parser',
            'fs-extra',
            'whatsapp-web.js',
            'axios'
        ];

        console.log('\n✅ Dependências obrigatórias:');
        dependenciasNecessarias.forEach(dep => {
            const existe = pkg.dependencies && pkg.dependencies[dep];
            const status = existe ? '✅' : '❌';
            console.log(`${status} ${dep}`);
        });
    }

    // Instruções de inicialização
    console.log('\n\n🚀 PRÓXIMAS ETAPAS');
    console.log('═'.repeat(60));

    if (obrigatoriosOk === obrigatoriosTotal) {
        console.log('\n1️⃣  Inicie o servidor:');
        console.log('   npm start\n');

        console.log('2️⃣  Acesse a interface:');
        console.log('   http://localhost:3333/gerenciador-comandos.html\n');

        console.log('3️⃣  Ou configure primeiro:');
        console.log('   npm run setup:base-conhecimento\n');

        console.log('4️⃣  Consulte a documentação:');
        console.log('   - Guia rápido: docs/GUIA-RAPIDO-COMANDOS.md');
        console.log('   - Documentação: docs/GERENCIADOR-COMANDOS.md');
        console.log('   - Como começar: COMECE-AQUI.md\n');

        console.log('✅ Sistema pronto para usar!\n');
    } else {
        console.log('\n⚠️  Alguns arquivos obrigatórios estão faltando.');
        console.log('    Verifique se todos foram criados corretamente.\n');
    }

    console.log('═'.repeat(60));
    console.log('');
}

// Executar verificação
verificarStatus().catch(erro => {
    console.error('❌ Erro ao verificar:', erro.message);
    process.exit(1);
});
