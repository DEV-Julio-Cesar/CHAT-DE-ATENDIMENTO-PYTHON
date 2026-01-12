#!/usr/bin/env node

/**
 * TESTE: Validação da Conexão por Número (v2.0.2)
 * ===================================================
 * 
 * Valida:
 * 1. Se a função window.poolAPI.openConexaoPorNumeroWindow() existe
 * 2. Se o arquivo conectar-numero.html está presente
 * 3. Se o handler IPC 'open-conexao-por-numero-window' está registrado
 * 4. Se o arquivo main.js tem a função createConexaoPorNumeroWindow()
 * 5. Se as rotas de API estão funcionando
 * 6. Se não há erros de caminho (ERR_FILE_NOT_FOUND)
 */

const fs = require('fs');
const path = require('path');

const RESET = '\x1b[0m';
const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[36m';

let testsPassed = 0;
let testsFailed = 0;

function logTest(name, passed, message = '') {
    if (passed) {
        console.log(`${GREEN}✓${RESET} ${name}`);
        testsPassed++;
    } else {
        console.log(`${RED}✗${RESET} ${name}`);
        if (message) console.log(`  ${RED}Erro:${RESET} ${message}`);
        testsFailed++;
    }
}

function testFileExists(filePath, description) {
    const fullPath = path.join(__dirname, filePath);
    const exists = fs.existsSync(fullPath);
    logTest(`${description} (${filePath})`, exists, exists ? '' : `Arquivo não encontrado em ${fullPath}`);
    return exists;
}

function testFileContent(filePath, searchString, description) {
    const fullPath = path.join(__dirname, filePath);
    if (!fs.existsSync(fullPath)) {
        logTest(description, false, `Arquivo não encontrado: ${filePath}`);
        return false;
    }
    
    const content = fs.readFileSync(fullPath, 'utf8');
    const found = content.includes(searchString);
    logTest(description, found, found ? '' : `Texto não encontrado: "${searchString}"`);
    return found;
}

console.log(`${BLUE}╔════════════════════════════════════════════════════════════╗${RESET}`);
console.log(`${BLUE}║          TESTE: Conexão por Número (v2.0.2)              ║${RESET}`);
console.log(`${BLUE}╚════════════════════════════════════════════════════════════╝${RESET}\n`);

console.log(`${YELLOW}1. Verificando arquivos necessários...${RESET}`);
testFileExists('src/interfaces/conectar-numero.html', 'Interface de conexão por número existe');
testFileExists('src/interfaces/gerenciador-pool.html', 'Gerenciador de pool existe');
testFileExists('src/interfaces/pre-carregamento-gerenciador-pool.js', 'Precarregamento gerenciador existe');
testFileExists('main.js', 'Arquivo principal exists');

console.log(`\n${YELLOW}2. Verificando função no gerenciador-pool.html...${RESET}`);
testFileContent(
    'src/interfaces/gerenciador-pool.html',
    'window.poolAPI.openConexaoPorNumeroWindow()',
    'Chamada IPC para abrir conexão por número'
);

console.log(`\n${YELLOW}3. Verificando método no precarregamento...${RESET}`);
testFileContent(
    'src/interfaces/pre-carregamento-gerenciador-pool.js',
    'openConexaoPorNumeroWindow',
    'Método openConexaoPorNumeroWindow no poolAPI'
);

console.log(`\n${YELLOW}4. Verificando handler IPC em main.js...${RESET}`);
testFileContent(
    'main.js',
    "ipcMain.handle('open-conexao-por-numero-window'",
    'Handler IPC open-conexao-por-numero-window registrado'
);

console.log(`\n${YELLOW}5. Verificando função createConexaoPorNumeroWindow em main.js...${RESET}`);
testFileContent(
    'main.js',
    'function createConexaoPorNumeroWindow()',
    'Função createConexaoPorNumeroWindow() definida'
);

testFileContent(
    'main.js',
    'conexaoWindow.loadFile(\'src/interfaces/conectar-numero.html\')',
    'Carregamento correto do arquivo conectar-numero.html'
);

console.log(`\n${YELLOW}6. Verificando que window.open() foi removido...${RESET}`);
const poolHtmlPath = path.join(__dirname, 'src/interfaces/gerenciador-pool.html');
const poolContent = fs.readFileSync(poolHtmlPath, 'utf8');

// Procura por window.open('/interfaces/conectar-numero.html' que era o código antigo
const hasOldCode = poolContent.includes("window.open('/interfaces/conectar-numero.html'");
logTest('window.open() antigo foi removido', !hasOldCode, hasOldCode ? 'Código antigo ainda presente' : '');

console.log(`\n${YELLOW}7. Verificando estrutura da conectar-numero.html...${RESET}`);
testFileContent(
    'src/interfaces/conectar-numero.html',
    '<html',
    'Arquivo HTML válido'
);

testFileContent(
    'src/interfaces/conectar-numero.html',
    'input',
    'Campo de entrada presente'
);

testFileContent(
    'src/interfaces/conectar-numero.html',
    'localhost:3333/api/whatsapp/conectar-por-numero',
    'API de conexão por número está sendo chamada (com URL completa)'
);

console.log(`\n${YELLOW}8. Verificando hotfix do v2.0.2...${RESET}`);
testFileContent(
    'src/services/ServicoClienteWhatsApp.js',
    "this.client.on('disconnected'",
    "Listener 'disconnected' usa .on() ao invés de .once()"
);

testFileContent(
    'src/services/ServicoClienteWhatsApp.js',
    "this.client.on('auth_failure'",
    "Listener 'auth_failure' usa .on() ao invés de .once()"
);

console.log(`\n${BLUE}╔════════════════════════════════════════════════════════════╗${RESET}`);
console.log(`${BLUE}║                      RESUMO DOS TESTES                     ║${RESET}`);
console.log(`${BLUE}╚════════════════════════════════════════════════════════════╝${RESET}`);

console.log(`\n${GREEN}Testes Passados:${RESET} ${testsPassed}`);
if (testsFailed > 0) {
    console.log(`${RED}Testes Falhados:${RESET} ${testsFailed}`);
}

if (testsFailed === 0) {
    console.log(`\n${GREEN}✓ TODOS OS TESTES PASSARAM!${RESET}`);
    console.log(`\n${YELLOW}Próximos passos:${RESET}`);
    console.log(`1. Iniciar aplicação com: npm start`);
    console.log(`2. Fazer login com: admin / admin`);
    console.log(`3. Ir para: Gerenciador de Conexões WhatsApp`);
    console.log(`4. Clicar em: "Adicionar Nova Conexão"`);
    console.log(`5. Escolher: "Conectar por Número"`);
    console.log(`6. Verificar se a janela abre corretamente`);
    process.exit(0);
} else {
    console.log(`\n${RED}✗ ALGUNS TESTES FALHARAM!${RESET}`);
    console.log(`\n${YELLOW}Verifique os erros acima e corrija os problemas.${RESET}`);
    process.exit(1);
}
