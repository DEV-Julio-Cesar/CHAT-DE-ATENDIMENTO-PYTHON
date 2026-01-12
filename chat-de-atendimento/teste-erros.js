#!/usr/bin/env node

/**
 * 🧪 Script de teste para validar o tratamento de erros melhorado
 * Este script simula os erros que ocorrem durante desconexão do WhatsApp
 */

const logger = require('./src/infraestrutura/logger');
const TratadorErros = require('./src/core/tratador-erros');

console.log('\n✅ Iniciando testes de tratamento de erros...\n');

// Simular diferentes tipos de rejeição
setTimeout(() => {
    console.log('📌 Teste 1: Simulando "Protocol error - Session closed"');
    
    // Simular rejeição de protocolo
    const protocolError = new Error('Protocol error (Runtime.callFunctionOn): Session closed. Most likely the page has been closed.');
    protocolError.category = 'internal';
    
    // Usar .catch() para capturar a rejeição
    const promise1 = Promise.reject(protocolError);
    promise1.catch(() => {
        // Caught intentionally
        console.log('   [Capturado pelo teste]');
    });
    
    // Simular rejeição não tratada depois de um tempo
    setTimeout(() => {
        const protocolError2 = new Error('Protocol error (Runtime.callFunctionOn): Session closed');
        protocolError2.category = 'internal';
        Promise.reject(protocolError2).catch(() => {});
    }, 100);
    
}, 1000);

// Teste 2: Error com stack trace contendo Runtime.callFunctionOn
setTimeout(() => {
    console.log('\n📌 Teste 2: Simulando erro com "Runtime.callFunctionOn" no stack trace');
    
    const err = new Error('Some operation failed');
    err.stack = `Error: Some operation failed
    at CDPSessionImpl.send (node_modules/puppeteer-core/lib/cjs/puppeteer/common/Connection.js:316:35)
    at ExecutionContext._ExecutionContext_evaluate (Runtime.callFunctionOn)`;
    
    const promise2 = Promise.reject(err);
    promise2.catch(() => {
        console.log('   [Capturado pelo teste]');
    });
    
}, 2000);

// Teste 3: Error "Browser closed"
setTimeout(() => {
    console.log('\n📌 Teste 3: Simulando erro "Browser closed"');
    
    const browserError = new Error('Browser closed unexpectedly');
    
    const promise3 = Promise.reject(browserError);
    promise3.catch(() => {
        console.log('   [Capturado pelo teste]');
    });
    
}, 3000);

// Teste 4: Error real que não é benigno
setTimeout(() => {
    console.log('\n📌 Teste 4: Simulando erro REAL (não benigno) - "Database Connection Failed"');
    
    const realError = new Error('Database Connection Failed - Unable to reach server');
    
    // NÃO capturar este erro - deixar ir para unhandledRejection
    Promise.reject(realError);
    
}, 4000);

// Aguardar e encerrar
setTimeout(() => {
    console.log('\n✅ Testes concluídos. Verifique os logs acima para validar o tratamento.\n');
    console.log('✅ Erros benignos devem aparecer como [INFO] ou ser filtrados');
    console.log('❌ Erros reais devem aparecer como [ERRO]');
    process.exit(0);
}, 5500);

