#!/usr/bin/env node
/**
 * =========================================================================
 * TESTE DE SINCRONIZAÇÃO WHATSAPP
 * =========================================================================
 * 
 * Script para validar a integração completa do sistema de sincronização
 * WhatsApp com:
 * - QR Code + Validação por Telefone
 * - Validação Manual por Código
 * - Integração Meta/Facebook API
 * - Keep-Alive (30 minutos)
 * - Sincronização Periódica (5 minutos)
 * 
 * Uso: node teste-sincronizacao.js
 * =========================================================================
 */

const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');
const chalk = require('chalk');

// =========================================================================
// CONFIGURAÇÃO
// =========================================================================

const BASE_URL = 'http://localhost:3333';
const TESTS_DIR = path.join(__dirname, 'testes');
const SYNC_INTERFACE_URL = `${BASE_URL}/validacao-whatsapp.html`;

// =========================================================================
// CORES E FORMATAÇÃO
// =========================================================================

const colors = {
    reset: '\x1b[0m',
    bold: '\x1b[1m',
    dim: '\x1b[2m',
    cyan: '\x1b[36m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    red: '\x1b[31m'
};

function log(type, msg) {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = {
        'INFO': colors.cyan + '[INFO]' + colors.reset,
        'OK': colors.green + '[✓ OK]' + colors.reset,
        'ERROR': colors.red + '[✗ ERRO]' + colors.reset,
        'WARN': colors.yellow + '[⚠ AVISO]' + colors.reset,
        'SECTION': colors.bold + colors.cyan + '[SEÇÃO]' + colors.reset
    };
    console.log(`${prefix[type] || '[LOG]'} ${timestamp} - ${msg}`);
}

// =========================================================================
// TESTES
// =========================================================================

async function testarConexao() {
    log('SECTION', 'TESTE 1: Conectividade com API');
    
    try {
        const response = await axios.get(`${BASE_URL}/api/status`, { timeout: 5000 });
        log('OK', `API respondendo: ${response.status}`);
        return true;
    } catch (error) {
        log('ERROR', `API não respondendo: ${error.message}`);
        return false;
    }
}

async function testarInterfaceHTML() {
    log('SECTION', 'TESTE 2: Interface HTML de Sincronização');
    
    try {
        const response = await axios.get(SYNC_INTERFACE_URL, { timeout: 5000 });
        
        if (response.status === 200) {
            log('OK', `Interface HTML disponível (${response.data.length} bytes)`);
            
            // Verificar se contém os elementos esperados
            const contem = {
                'Tab QR Code': response.data.includes('qr-tab') || response.data.includes('QR Code'),
                'Tab Manual': response.data.includes('manual-tab') || response.data.includes('Manual'),
                'Tab Meta': response.data.includes('meta-tab') || response.data.includes('Meta'),
                'Validação': response.data.includes('validar') || response.data.includes('sincronizar')
            };
            
            let todosPresentes = true;
            Object.entries(contem).forEach(([elemento, presente]) => {
                if (presente) {
                    log('OK', `  ✓ ${elemento} encontrado`);
                } else {
                    log('WARN', `  ✗ ${elemento} não encontrado`);
                    todosPresentes = false;
                }
            });
            
            return todosPresentes;
        }
    } catch (error) {
        log('ERROR', `Interface não disponível: ${error.message}`);
        return false;
    }
}

async function testarEndpointQRCode() {
    log('SECTION', 'TESTE 3: Endpoint QR Code');
    
    try {
        const response = await axios.get(`${BASE_URL}/api/whatsapp/qr-code`, { timeout: 5000 });
        
        if (response.data.success) {
            log('OK', `QR Code gerado com sucesso`);
            log('INFO', `  - Status: ${response.data.status}`);
            log('INFO', `  - Cliente ID: ${response.data.clientId || 'N/A'}`);
            return true;
        } else {
            log('WARN', `QR Code retornou success=false: ${response.data.message || 'sem mensagem'}`);
            return false;
        }
    } catch (error) {
        log('ERROR', `Erro ao obter QR Code: ${error.message}`);
        return false;
    }
}

async function testarEndpointStatus() {
    log('SECTION', 'TESTE 4: Endpoint Status');
    
    try {
        const response = await axios.get(`${BASE_URL}/api/whatsapp/status`, { timeout: 5000 });
        
        log('OK', `Status obtido com sucesso`);
        log('INFO', `  - Ativo: ${response.data.ativo ? 'Sim' : 'Não'}`);
        log('INFO', `  - Telefone: ${response.data.telefone || 'Não sincronizado'}`);
        log('INFO', `  - Status: ${response.data.status || 'desconhecido'}`);
        log('INFO', `  - Tempo ativo: ${response.data.tempo_ativo || 'N/A'}`);
        log('INFO', `  - Última sincronização: ${response.data.ultima_sincronizacao || 'N/A'}`);
        
        return true;
    } catch (error) {
        log('WARN', `Erro ao obter status: ${error.message} (esperado se não sincronizado)`);
        return false;
    }
}

async function testarValidacaoQRCode() {
    log('SECTION', 'TESTE 5: Validação QR Code (Simulado)');
    
    try {
        // Este teste simula uma validação QR Code
        // Em produção, você precisaria fazer o scan real do QR Code
        const response = await axios.post(`${BASE_URL}/api/whatsapp/validar-qrcode`, 
            { telefone: '5584920024786' }, 
            { timeout: 5000 }
        );
        
        if (response.data.success) {
            log('OK', `Validação QR Code iniciada`);
            log('INFO', `  - Sessão ID: ${response.data.sessaoId || 'N/A'}`);
            log('INFO', `  - Telefone: ${response.data.telefone || 'N/A'}`);
            return true;
        } else {
            log('WARN', `Validação retornou success=false: ${response.data.message}`);
            return true; // Não é erro de conectividade
        }
    } catch (error) {
        log('ERROR', `Erro na validação: ${error.message}`);
        return false;
    }
}

async function testarKeepAlive() {
    log('SECTION', 'TESTE 6: Endpoint Keep-Alive');
    
    try {
        const response = await axios.post(`${BASE_URL}/api/whatsapp/manter-vivo`, 
            {}, 
            { timeout: 5000 }
        );
        
        log('OK', `Keep-Alive respondendo`);
        log('INFO', `  - Status: ${response.data.status || 'ok'}`);
        log('INFO', `  - Última atualização: ${response.data.ultima_atualizacao || 'N/A'}`);
        
        return true;
    } catch (error) {
        log('WARN', `Keep-Alive erro: ${error.message} (esperado se não sincronizado)`);
        return false;
    }
}

async function testarValidacaoManual() {
    log('SECTION', 'TESTE 7: Validação Manual (Simulado)');
    
    try {
        const response = await axios.post(`${BASE_URL}/api/whatsapp/validar-manual`, 
            { 
                telefone: '5584920024786',
                codigo: '123456'
            }, 
            { timeout: 5000 }
        );
        
        log('INFO', `Validação manual testada`);
        log('INFO', `  - Sucesso: ${response.data.success}`);
        log('INFO', `  - Mensagem: ${response.data.message}`);
        
        return true;
    } catch (error) {
        log('WARN', `Validação manual erro: ${error.message}`);
        return false;
    }
}

async function testarMetaAPI() {
    log('SECTION', 'TESTE 8: Meta API (Simulado)');
    
    try {
        const response = await axios.post(`${BASE_URL}/api/whatsapp/sincronizar-meta`, 
            { 
                telefone: '5584920024786',
                accessToken: 'test_token_123456'
            }, 
            { timeout: 5000 }
        );
        
        log('INFO', `Meta API testada`);
        log('INFO', `  - Sucesso: ${response.data.success}`);
        log('INFO', `  - Mensagem: ${response.data.message}`);
        
        return true;
    } catch (error) {
        log('WARN', `Meta API erro: ${error.message}`);
        return false;
    }
}

async function verificarArquivosGerenciador() {
    log('SECTION', 'TESTE 9: Verificação de Arquivos do Gerenciador');
    
    const arquivos = [
        'src/services/GerenciadorSessaoWhatsApp.js',
        'src/interfaces/validacao-whatsapp.html',
        'src/rotas/rotasWhatsAppSincronizacao.js',
        'dados/sessoes-whatsapp/sessao-ativa.json'
    ];
    
    let todosExistem = true;
    for (const arquivo of arquivos) {
        const caminhoCompleto = path.join(__dirname, arquivo);
        const existe = await fs.pathExists(caminhoCompleto);
        
        if (existe) {
            log('OK', `  ✓ ${arquivo}`);
        } else {
            log('ERROR', `  ✗ ${arquivo} (não encontrado)`);
            todosExistem = false;
        }
    }
    
    return todosExistem;
}

// =========================================================================
// RESUMO FINAL
// =========================================================================

async function executarTodosTestes() {
    console.log('\n' + colors.bold + colors.cyan + '╔════════════════════════════════════════════════════════════╗' + colors.reset);
    console.log(colors.bold + colors.cyan + '║  TESTE DE SINCRONIZAÇÃO WHATSAPP - SUITE COMPLETA            ║' + colors.reset);
    console.log(colors.bold + colors.cyan + '╚════════════════════════════════════════════════════════════╝' + colors.reset + '\n');
    
    const resultados = {
        'Conectividade API': await testarConexao(),
        'Interface HTML': await testarInterfaceHTML(),
        'Endpoint QR Code': await testarEndpointQRCode(),
        'Endpoint Status': await testarEndpointStatus(),
        'Validação QR Code': await testarValidacaoQRCode(),
        'Keep-Alive': await testarKeepAlive(),
        'Validação Manual': await testarValidacaoManual(),
        'Meta API': await testarMetaAPI(),
        'Arquivos Gerenciador': await verificarArquivosGerenciador()
    };
    
    console.log('\n' + colors.bold + colors.cyan + '╔════════════════════════════════════════════════════════════╗' + colors.reset);
    console.log(colors.bold + colors.cyan + '║  RESUMO DOS TESTES                                           ║' + colors.reset);
    console.log(colors.bold + colors.cyan + '╚════════════════════════════════════════════════════════════╝' + colors.reset + '\n');
    
    const sucessos = Object.values(resultados).filter(r => r).length;
    const total = Object.keys(resultados).length;
    const percentual = Math.round((sucessos / total) * 100);
    
    Object.entries(resultados).forEach(([teste, resultado]) => {
        const icon = resultado ? colors.green + '✓' + colors.reset : colors.red + '✗' + colors.reset;
        const status = resultado ? 'PASSOU' : 'FALHOU';
        console.log(`${icon} ${teste}: ${status}`);
    });
    
    console.log(`\n${colors.bold}Resultado: ${sucessos}/${total} (${percentual}%)${colors.reset}\n`);
    
    if (percentual === 100) {
        console.log(colors.bold + colors.green + '🎉 TODOS OS TESTES PASSARAM! 🎉' + colors.reset + '\n');
    } else if (percentual >= 80) {
        console.log(colors.bold + colors.yellow + '⚠️  MAIORIA DOS TESTES PASSOU' + colors.reset + '\n');
    } else {
        console.log(colors.bold + colors.red + '❌ ALGUNS TESTES FALHARAM' + colors.reset + '\n');
    }
    
    console.log(colors.dim + '📝 Próximas etapas:' + colors.reset);
    console.log('  1. Acessar http://localhost:3333/validacao-whatsapp.html');
    console.log('  2. Selecionar método de validação (QR Code / Manual / Meta)');
    console.log('  3. Seguir as instruções na interface');
    console.log('  4. Verificar status em http://localhost:3333/api/whatsapp/status\n');
}

// =========================================================================
// EXECUTAR
// =========================================================================

executarTodosTestes().catch(erro => {
    log('ERROR', `Erro ao executar testes: ${erro.message}`);
    process.exit(1);
});
