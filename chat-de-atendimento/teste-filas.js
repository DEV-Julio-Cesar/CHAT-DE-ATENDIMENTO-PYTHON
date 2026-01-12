/**
 * Script de Teste - Gerenciador de Filas
 * Cria conversas de teste para validar operações em lote
 */

const fs = require('fs-extra');
const path = require('path');

const ARQUIVO_FILAS = path.join(__dirname, 'dados', 'atendimentos.json');

// IDs de clientes fictícios para teste
const CLIENTES_TESTE = [
    { clientId: 'teste-client-001', nome: 'João Silva', telefone: '5511999990001' },
    { clientId: 'teste-client-002', nome: 'Maria Santos', telefone: '5511999990002' },
    { clientId: 'teste-client-003', nome: 'Pedro Costa', telefone: '5511999990003' },
    { clientId: 'teste-client-004', nome: 'Ana Paula', telefone: '5511999990004' },
    { clientId: 'teste-client-005', nome: 'Carlos Eduardo', telefone: '5511999990005' },
    { clientId: 'teste-client-006', nome: 'Juliana Oliveira', telefone: '5511999990006' },
    { clientId: 'teste-client-007', nome: 'Roberto Lima', telefone: '5511999990007' },
    { clientId: 'teste-client-008', nome: 'Fernanda Souza', telefone: '5511999990008' }
];

const MENSAGENS_TESTE = [
    'Olá, preciso de ajuda com meu pedido',
    'Gostaria de informações sobre preços',
    'Qual o horário de funcionamento?',
    'Estou com problema na entrega',
    'Como faço para cancelar?',
    'Preciso falar com um atendente',
    'Obrigado pelo atendimento!',
    'Quando posso receber o produto?'
];

const ESTADOS = {
    AUTOMACAO: 'automacao',
    ESPERA: 'espera',
    ATENDIMENTO: 'atendimento',
    ENCERRADO: 'encerrado'
};

function gerarId(clientId, chatId) {
    return `${clientId}_${chatId}`;
}

function criarConversaTeste(cliente, estado, atendente = null) {
    const agora = new Date();
    const chatId = `${cliente.telefone}@c.us`;
    const id = gerarId(cliente.clientId, chatId);
    
    // Varia o tempo de criação para simular conversas em diferentes momentos
    const minutosAtras = Math.floor(Math.random() * 120); // 0 a 2 horas atrás
    const criadoEm = new Date(agora - minutosAtras * 60000).toISOString();
    
    const mensagemAleatoria = MENSAGENS_TESTE[Math.floor(Math.random() * MENSAGENS_TESTE.length)];
    
    const conversa = {
        id,
        clientId: cliente.clientId,
        chatId,
        estado,
        criadoEm,
        atualizadoEm: criadoEm,
        metadata: {
            nomeContato: cliente.nome,
            telefone: cliente.telefone,
            ultimaMensagem: mensagemAleatoria,
            timestampUltimaMensagem: criadoEm
        },
        tentativasBot: estado === ESTADOS.AUTOMACAO ? Math.floor(Math.random() * 3) : 0,
        historicoEstados: [
            {
                estado,
                timestamp: criadoEm,
                motivo: 'conversa_teste'
            }
        ]
    };
    
    if (atendente) {
        conversa.atendente = atendente;
        conversa.historicoEstados.push({
            estado,
            timestamp: criadoEm,
            atendente,
            motivo: 'teste_automatico'
        });
    }
    
    return conversa;
}

async function criarConversasTeste() {
    try {
        console.log('🧪 Criando conversas de teste...\n');
        
        // Carrega arquivo existente ou cria novo
        let data = { conversas: [] };
        if (await fs.pathExists(ARQUIVO_FILAS)) {
            try {
                data = await fs.readJson(ARQUIVO_FILAS);
                if (!data || !Array.isArray(data.conversas)) {
                    data = { conversas: [] };
                }
                console.log(`📁 Arquivo existente encontrado: ${data.conversas.length} conversas`);
                
                // Remove conversas de teste anteriores
                data.conversas = data.conversas.filter(c => !c.clientId || !c.clientId.startsWith('teste-client'));
                console.log(`🧹 Conversas de teste antigas removidas`);
            } catch (error) {
                console.log('⚠️  Erro ao ler arquivo, criando novo...');
                data = { conversas: [] };
            }
        } else {
            console.log('📝 Criando novo arquivo de conversas');
        }
        
        // Cria conversas em diferentes estados
        const novasConversas = [];
        
        // 3 conversas em AUTOMAÇÃO
        console.log('\n🤖 Criando 3 conversas em AUTOMAÇÃO...');
        for (let i = 0; i < 3; i++) {
            const conversa = criarConversaTeste(CLIENTES_TESTE[i], ESTADOS.AUTOMACAO);
            novasConversas.push(conversa);
            console.log(`   ✓ ${conversa.metadata.nomeContato} - "${conversa.metadata.ultimaMensagem}"`);
        }
        
        // 3 conversas em ESPERA
        console.log('\n⏳ Criando 3 conversas em ESPERA...');
        for (let i = 3; i < 6; i++) {
            const conversa = criarConversaTeste(CLIENTES_TESTE[i], ESTADOS.ESPERA);
            novasConversas.push(conversa);
            console.log(`   ✓ ${conversa.metadata.nomeContato} - "${conversa.metadata.ultimaMensagem}"`);
        }
        
        // 2 conversas em ATENDIMENTO (com diferentes atendentes)
        console.log('\n👤 Criando 2 conversas em ATENDIMENTO...');
        const conversa1 = criarConversaTeste(CLIENTES_TESTE[6], ESTADOS.ATENDIMENTO, 'admin');
        novasConversas.push(conversa1);
        console.log(`   ✓ ${conversa1.metadata.nomeContato} - Atendente: admin`);
        
        const conversa2 = criarConversaTeste(CLIENTES_TESTE[7], ESTADOS.ATENDIMENTO, 'Maria');
        novasConversas.push(conversa2);
        console.log(`   ✓ ${conversa2.metadata.nomeContato} - Atendente: Maria`);
        
        // Adiciona as novas conversas
        data.conversas.push(...novasConversas);
        
        // Garante que o diretório existe
        await fs.ensureDir(path.dirname(ARQUIVO_FILAS));
        
        // Salva arquivo
        await fs.writeJson(ARQUIVO_FILAS, data, { spaces: 2 });
        
        console.log('\n✅ Conversas de teste criadas com sucesso!');
        console.log(`\n📊 Resumo:`);
        console.log(`   Total de conversas: ${data.conversas.length}`);
        console.log(`   🤖 Automação: 3`);
        console.log(`   ⏳ Espera: 3`);
        console.log(`   👤 Atendimento: 2`);
        console.log(`\n🎯 Agora você pode testar:`);
        console.log(`   ✓ Selecionar múltiplas conversas (checkboxes)`);
        console.log(`   ✓ Atribuir em lote para um atendente`);
        console.log(`   ✓ Encerrar múltiplas conversas com mensagem`);
        console.log(`   ✓ Transferir conversas entre atendentes`);
        console.log(`   ✓ Escalar conversas da automação para espera`);
        console.log(`\n🌐 Acesse: http://localhost:3333/chat-filas.html`);
        
    } catch (error) {
        console.error('❌ Erro ao criar conversas de teste:', error);
        process.exit(1);
    }
}

// Executa
criarConversasTeste();
