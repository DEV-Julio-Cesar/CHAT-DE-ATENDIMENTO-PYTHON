#!/usr/bin/env node
// =========================================================================
// SCRIPT PARA INICIALIZAR APLICAÇÃO WEB COMPLETA
// =========================================================================

const { spawn } = require('child_process');
const fs = require('fs-extra');
const path = require('path');

console.log('🌐 INICIANDO APLICAÇÃO WEB COMPLETA...\n');

async function verificarPreRequisitos() {
    console.log('🔍 Verificando pré-requisitos...');
    
    // Verificar se as pastas existem
    const pastasNecessarias = [
        'dados',
        'dados/logs',
        'src/interfaces',
        '.wwebjs_auth'
    ];
    
    for (const pasta of pastasNecessarias) {
        await fs.ensureDir(pasta);
        console.log(`✅ Pasta ${pasta} verificada`);
    }
    
    // Verificar se o usuário admin existe
    try {
        const { spawn: spawnSync } = require('child_process');
        const seedProcess = spawnSync('node', ['scripts/seed-admin.js'], { stdio: 'inherit' });
        
        seedProcess.on('close', (code) => {
            if (code === 0) {
                console.log('✅ Usuário admin verificado');
            }
        });
    } catch (error) {
        console.log('⚠️  Erro ao verificar usuário admin:', error.message);
    }
    
    console.log('✅ Pré-requisitos verificados\n');
}

function iniciarServidor() {
    console.log('🚀 Iniciando servidor web...');
    
    const servidor = spawn('node', ['server-web.js'], {
        stdio: 'inherit',
        env: { ...process.env, NODE_ENV: 'production' }
    });
    
    servidor.on('error', (error) => {
        console.error('❌ Erro ao iniciar servidor:', error.message);
        process.exit(1);
    });
    
    servidor.on('close', (code) => {
        console.log(`\n🛑 Servidor encerrado com código ${code}`);
        process.exit(code);
    });
    
    // Tratamento de sinais para encerramento gracioso
    process.on('SIGINT', () => {
        console.log('\n🛑 Encerrando aplicação...');
        servidor.kill('SIGINT');
    });
    
    process.on('SIGTERM', () => {
        console.log('\n🛑 Encerrando aplicação...');
        servidor.kill('SIGTERM');
    });
}

async function main() {
    try {
        await verificarPreRequisitos();
        iniciarServidor();
    } catch (error) {
        console.error('❌ Erro na inicialização:', error.message);
        process.exit(1);
    }
}

main();