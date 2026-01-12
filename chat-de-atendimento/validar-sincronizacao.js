#!/usr/bin/env node
/**
 * =========================================================================
 * VALIDADOR DE SINCRONIZAÇÃO WHATSAPP
 * =========================================================================
 * 
 * Verifica se todos os arquivos foram criados e integrados corretamente
 * 
 * Uso: node validar-sincronizacao.js
 * =========================================================================
 */

const fs = require('fs-extra');
const path = require('path');

// =========================================================================
// CONFIGURAÇÃO
// =========================================================================

const ARQUIVOS_REQUERIDOS = [
    {
        caminho: 'src/services/GerenciadorSessaoWhatsApp.js',
        tipo: 'classe',
        descricao: 'Gerenciador de Sessão'
    },
    {
        caminho: 'src/interfaces/validacao-whatsapp.html',
        tipo: 'interface',
        descricao: 'Interface HTML'
    },
    {
        caminho: 'src/rotas/rotasWhatsAppSincronizacao.js',
        tipo: 'rotas',
        descricao: 'Rotas API'
    }
];

const INTEGRAÇÕES_REQUERIDAS = [
    {
        arquivo: 'src/infraestrutura/api.js',
        contem: "require('../rotas/rotasWhatsAppSincronizacao')",
        descricao: 'Importação de rotas em api.js'
    },
    {
        arquivo: 'src/infraestrutura/api.js',
        contem: "app.use('/api/whatsapp', rotasWhatsAppSincronizacao)",
        descricao: 'Registro de rotas em api.js'
    },
    {
        arquivo: 'src/infraestrutura/api.js',
        contem: "express.static",
        descricao: 'Servindo arquivos estáticos em api.js'
    },
    {
        arquivo: 'main.js',
        contem: "require('./src/services/GerenciadorSessaoWhatsApp')",
        descricao: 'Importação do gerenciador em main.js'
    },
    {
        arquivo: 'main.js',
        contem: "GerenciadorSessaoWhatsApp.inicializar()",
        descricao: 'Inicialização do gerenciador em main.js'
    }
];

// =========================================================================
// CORES
// =========================================================================

const cores = {
    reset: '\x1b[0m',
    bold: '\x1b[1m',
    dim: '\x1b[2m',
    verde: '\x1b[32m',
    vermelho: '\x1b[31m',
    amarelo: '\x1b[33m',
    azul: '\x1b[36m'
};

function log(tipo, mensagem) {
    const icones = {
        OK: cores.verde + '✓' + cores.reset,
        ERRO: cores.vermelho + '✗' + cores.reset,
        AVISO: cores.amarelo + '⚠' + cores.reset,
        INFO: cores.azul + 'ℹ' + cores.reset
    };
    
    console.log(`${icones[tipo] || '•'} ${mensagem}`);
}

function secao(titulo) {
    console.log(`\n${cores.bold}${cores.azul}═══ ${titulo} ═══${cores.reset}\n`);
}

// =========================================================================
// VALIDAÇÕES
// =========================================================================

async function validarArquivos() {
    secao('VALIDAÇÃO DE ARQUIVOS');
    
    let todosPresentes = true;
    
    for (const arquivo of ARQUIVOS_REQUERIDOS) {
        const caminhoCompleto = path.join(__dirname, arquivo.caminho);
        const existe = await fs.pathExists(caminhoCompleto);
        
        if (existe) {
            const stats = await fs.stat(caminhoCompleto);
            const tamanho = (stats.size / 1024).toFixed(2);
            log('OK', `${arquivo.caminho} (${tamanho} KB) - ${arquivo.descricao}`);
        } else {
            log('ERRO', `${arquivo.caminho} - ARQUIVO NÃO ENCONTRADO`);
            todosPresentes = false;
        }
    }
    
    return todosPresentes;
}

async function validarIntegracoes() {
    secao('VALIDAÇÃO DE INTEGRAÇÕES');
    
    let todasIntegradas = true;
    
    for (const integracao of INTEGRAÇÕES_REQUERIDAS) {
        const caminhoCompleto = path.join(__dirname, integracao.arquivo);
        
        try {
            const conteudo = await fs.readFile(caminhoCompleto, 'utf-8');
            
            if (conteudo.includes(integracao.contem)) {
                log('OK', `${integracao.descricao}`);
            } else {
                log('ERRO', `${integracao.descricao} - NÃO ENCONTRADO`);
                todasIntegradas = false;
            }
        } catch (erro) {
            log('ERRO', `${integracao.arquivo} - ARQUIVO NÃO PODE SER LIDO`);
            todasIntegradas = false;
        }
    }
    
    return todasIntegradas;
}

async function validarDiretorio() {
    secao('VALIDAÇÃO DE DIRETÓRIOS');
    
    const diretorios = [
        'dados/sessoes-whatsapp',
        'dados/sessoes-whatsapp/logs',
        'src/services',
        'src/interfaces',
        'src/rotas'
    ];
    
    let todosExistem = true;
    
    for (const dir of diretorios) {
        const caminhoCompleto = path.join(__dirname, dir);
        const existe = await fs.pathExists(caminhoCompleto);
        
        if (existe) {
            log('OK', dir);
        } else {
            log('AVISO', `${dir} - criando...`);
            try {
                await fs.ensureDir(caminhoCompleto);
                log('OK', `${dir} - criado com sucesso`);
            } catch (erro) {
                log('ERRO', `${dir} - não foi possível criar`);
                todosExistem = false;
            }
        }
    }
    
    return todosExistem;
}

async function validarConteudo() {
    secao('VALIDAÇÃO DE CONTEÚDO');
    
    const validacoes = [
        {
            arquivo: 'src/services/GerenciadorSessaoWhatsApp.js',
            deve_conter: ['class GerenciadorSessaoWhatsApp', 'inicializar()', 'criarSessao', 'validarSessao'],
            descricao: 'Gerenciador de Sessão'
        },
        {
            arquivo: 'src/interfaces/validacao-whatsapp.html',
            deve_conter: ['<html', 'qr-code', 'validacao', 'sincronizar'],
            descricao: 'Interface HTML'
        },
        {
            arquivo: 'src/rotas/rotasWhatsAppSincronizacao.js',
            deve_conter: ['router.get', 'router.post', '/qr-code', '/validar', '/status'],
            descricao: 'Rotas API'
        }
    ];
    
    let tudoOk = true;
    
    for (const validacao of validacoes) {
        const caminhoCompleto = path.join(__dirname, validacao.arquivo);
        
        try {
            const conteudo = await fs.readFile(caminhoCompleto, 'utf-8');
            let arquivoOk = true;
            
            for (const texto of validacao.deve_conter) {
                if (!conteudo.includes(texto)) {
                    log('ERRO', `${validacao.descricao}: não contém "${texto}"`);
                    arquivoOk = false;
                    tudoOk = false;
                }
            }
            
            if (arquivoOk) {
                log('OK', `${validacao.descricao}: conteúdo válido`);
            }
        } catch (erro) {
            log('ERRO', `${validacao.arquivo}: não pode ser lido`);
            tudoOk = false;
        }
    }
    
    return tudoOk;
}

// =========================================================================
// RELATÓRIO FINAL
// =========================================================================

async function executarValidacao() {
    console.log(`\n${cores.bold}${cores.azul}╔════════════════════════════════════════╗${cores.reset}`);
    console.log(`${cores.bold}${cores.azul}║  VALIDADOR DE SINCRONIZAÇÃO WHATSAPP   ║${cores.reset}`);
    console.log(`${cores.bold}${cores.azul}╚════════════════════════════════════════╝${cores.reset}\n`);
    
    const resultado = {
        'Arquivos Requeridos': await validarArquivos(),
        'Diretórios': await validarDiretorio(),
        'Conteúdo dos Arquivos': await validarConteudo(),
        'Integrações': await validarIntegracoes()
    };
    
    secao('RESUMO FINAL');
    
    const sucessos = Object.values(resultado).filter(r => r).length;
    const total = Object.keys(resultado).length;
    const percentual = Math.round((sucessos / total) * 100);
    
    Object.entries(resultado).forEach(([teste, resultado]) => {
        const icone = resultado ? cores.verde + '✓' : cores.vermelho + '✗';
        console.log(`${icone} ${teste}${cores.reset}`);
    });
    
    console.log(`\n${cores.bold}Resultado: ${sucessos}/${total} (${percentual}%)${cores.reset}\n`);
    
    if (percentual === 100) {
        console.log(cores.verde + cores.bold + '✓ VALIDAÇÃO COMPLETA - TUDO PRONTO!' + cores.reset);
        console.log(`\n${cores.dim}Próximos passos:${cores.reset}`);
        console.log(`1. Inicie a aplicação: ${cores.bold}npm start${cores.reset}`);
        console.log(`2. Acesse: ${cores.bold}http://localhost:3333/validacao-whatsapp.html${cores.reset}`);
        console.log(`3. Siga o guia: ${cores.bold}GUIA-SINCRONIZACAO-PASSO-A-PASSO.md${cores.reset}\n`);
        process.exit(0);
    } else if (percentual >= 80) {
        console.log(cores.amarelo + cores.bold + '⚠ MAIORIA VALIDADA - VERIFIQUE AVISOS' + cores.reset + '\n');
        process.exit(1);
    } else {
        console.log(cores.vermelho + cores.bold + '✗ VALIDAÇÃO FALHOU - ERROS ENCONTRADOS' + cores.reset + '\n');
        process.exit(2);
    }
}

// =========================================================================
// EXECUTAR
// =========================================================================

executarValidacao().catch(erro => {
    console.error(cores.vermelho + `Erro: ${erro.message}` + cores.reset);
    process.exit(3);
});
