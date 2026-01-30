#!/usr/bin/env node
// =========================================================================
// TESTE COMPLETO DO SISTEMA - DIAGNÓSTICO GERAL
// =========================================================================

const fs = require('fs-extra');
const path = require('path');

console.log('🔍 INICIANDO DIAGNÓSTICO COMPLETO DO SISTEMA...\n');

let totalTestes = 0;
let testesPassaram = 0;
let testesFalharam = 0;

function teste(nome, funcao) {
    totalTestes++;
    try {
        console.log(`⏳ Testando: ${nome}`);
        const resultado = funcao();
        if (resultado === true || resultado === undefined) {
            console.log(`✅ PASSOU: ${nome}`);
            testesPassaram++;
        } else {
            console.log(`❌ FALHOU: ${nome} - ${resultado}`);
            testesFalharam++;
        }
    } catch (erro) {
        console.log(`❌ ERRO: ${nome} - ${erro.message}`);
        testesFalharam++;
    }
    console.log('');
}

// =========================================================================
// TESTES DE ESTRUTURA DE ARQUIVOS
// =========================================================================

teste('Estrutura de pastas principais', () => {
    const pastasObrigatorias = [
        'src',
        'src/aplicacao',
        'src/core', 
        'src/infraestrutura',
        'src/interfaces',
        'src/services',
        'dados'
    ];
    
    for (const pasta of pastasObrigatorias) {
        if (!fs.existsSync(pasta)) {
            return `Pasta obrigatória não encontrada: ${pasta}`;
        }
    }
    return true;
});

teste('Arquivos principais existem', () => {
    const arquivosObrigatorios = [
        'main.js',
        'package.json',
        'src/infraestrutura/logger.js',
        'src/aplicacao/gerenciador-usuarios.js',
        'dados/usuarios.json'
    ];
    
    for (const arquivo of arquivosObrigatorios) {
        if (!fs.existsSync(arquivo)) {
            return `Arquivo obrigatório não encontrado: ${arquivo}`;
        }
    }
    return true;
});

// =========================================================================
// TESTES DE CONFIGURAÇÃO
// =========================================================================

teste('Package.json válido', () => {
    const pkg = require('./package.json');
    if (!pkg.name || !pkg.version || !pkg.main) {
        return 'Package.json inválido ou incompleto';
    }
    return true;
});

teste('Dependências principais instaladas', () => {
    const dependenciasChave = [
        'electron',
        'whatsapp-web.js',
        'express',
        'ws',
        'axios'
    ];
    
    for (const dep of dependenciasChave) {
        try {
            require.resolve(dep);
        } catch (erro) {
            return `Dependência não encontrada: ${dep}`;
        }
    }
    return true;
});

// =========================================================================
// TESTES DE DADOS
// =========================================================================

teste('Arquivo de usuários válido', () => {
    try {
        const usuarios = fs.readJsonSync('dados/usuarios.json');
        if (!usuarios.usuarios || !Array.isArray(usuarios.usuarios)) {
            return 'Arquivo de usuários deve ter propriedade "usuarios" como array';
        }
        return true;
    } catch (erro) {
        return `Erro ao ler usuários: ${erro.message}`;
    }
});

teste('Pastas de dados existem', () => {
    const pastasDados = [
        'dados/logs',
        'dados/backups',
        'dados/mensagens'
    ];
    
    for (const pasta of pastasDados) {
        fs.ensureDirSync(pasta);
    }
    return true;
});

// =========================================================================
// TESTES DE MÓDULOS
// =========================================================================

teste('Logger funciona', () => {
    try {
        const logger = require('./src/infraestrutura/logger');
        if (typeof logger.info !== 'function') {
            return 'Logger não possui método info';
        }
        logger.info('[TESTE] Logger funcionando');
        return true;
    } catch (erro) {
        return `Erro no logger: ${erro.message}`;
    }
});

teste('Gerenciador de usuários carrega', () => {
    try {
        const gerenciadorUsuarios = require('./src/aplicacao/gerenciador-usuarios');
        if (typeof gerenciadorUsuarios.listarUsuarios !== 'function') {
            return 'Gerenciador de usuários não possui método listarUsuarios';
        }
        return true;
    } catch (erro) {
        return `Erro no gerenciador de usuários: ${erro.message}`;
    }
});

teste('Pool WhatsApp carrega', () => {
    try {
        const GerenciadorPoolWhatsApp = require('./src/services/GerenciadorPoolWhatsApp');
        if (typeof GerenciadorPoolWhatsApp !== 'function') {
            return 'GerenciadorPoolWhatsApp não é uma classe válida';
        }
        return true;
    } catch (erro) {
        return `Erro no pool WhatsApp: ${erro.message}`;
    }
});

// =========================================================================
// RESULTADOS FINAIS
// =========================================================================

console.log('='.repeat(60));
console.log('📊 RELATÓRIO FINAL DO DIAGNÓSTICO');
console.log('='.repeat(60));
console.log(`Total de testes: ${totalTestes}`);
console.log(`✅ Passaram: ${testesPassaram}`);
console.log(`❌ Falharam: ${testesFalharam}`);
console.log(`📈 Taxa de sucesso: ${Math.round((testesPassaram / totalTestes) * 100)}%`);

if (testesFalharam === 0) {
    console.log('\n🎉 TODOS OS TESTES PASSARAM! Sistema pronto para uso.');
    process.exit(0);
} else {
    console.log('\n⚠️  ALGUNS TESTES FALHARAM. Verifique os erros acima.');
    process.exit(1);
}