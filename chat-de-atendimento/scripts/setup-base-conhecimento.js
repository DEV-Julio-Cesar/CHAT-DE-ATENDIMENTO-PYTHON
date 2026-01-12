#!/usr/bin/env node

/**
 * Script de Setup Inicial - Base de Conhecimento do Robô
 * 
 * Cria comandos padrões e configurações iniciais
 */

const fs = require('fs-extra');
const path = require('path');

const caminhoBase = path.join(__dirname, '..', '..', 'dados', 'base-conhecimento-robo.json');

const baseInicial = {
    comandos: [
        {
            id: 'saudacao_oi',
            palavras_chave: ['oi', 'olá', 'opa', 'e aí', 'oie', 'salve'],
            tipo: 'saudacao',
            resposta: 'Olá! 👋 Bem-vindo! Como posso ajudá-lo?',
            prioridade: 10,
            ativo: true,
            criado_em: new Date().toISOString(),
            atualizado_em: new Date().toISOString()
        },
        {
            id: 'horario_funcionamento',
            palavras_chave: ['horário', 'funcionamento', 'que horas', 'aberto', 'open', 'está aberto'],
            tipo: 'informacao',
            resposta: '📅 Funcionamos de segunda a sexta, das 9h às 18h. Sábado e domingo oferecemos suporte limitado das 10h às 14h.',
            prioridade: 8,
            ativo: true,
            criado_em: new Date().toISOString(),
            atualizado_em: new Date().toISOString()
        },
        {
            id: 'preco_valores',
            palavras_chave: ['preço', 'valor', 'quanto custa', 'caro', 'valores', 'tabela de preços'],
            tipo: 'informacao',
            resposta: '💰 Nossos planos começam em R$ 99/mês. Quer conhecer nossas opções completas?',
            prioridade: 7,
            ativo: true,
            criado_em: new Date().toISOString(),
            atualizado_em: new Date().toISOString()
        },
        {
            id: 'obrigado',
            palavras_chave: ['obrigado', 'valeu', 'obrigada', 'vlw', 'brigadão', 'brigado'],
            tipo: 'resposta_gentil',
            resposta: 'De nada! 😊 Fico feliz em ajudar. Precisa de mais alguma coisa?',
            prioridade: 5,
            ativo: true,
            criado_em: new Date().toISOString(),
            atualizado_em: new Date().toISOString()
        }
    ],
    configuracoes: {
        usar_base_conhecimento: true,
        usar_ia_gemini: true,
        fazer_fallback_ia: true,
        minimo_confianca: 70,
        tempo_resposta_segundos: 15,
        resposta_padrao_nao_entendi: 'Desculpe, não entendi. Poderia reformular sua pergunta? 🤔'
    }
};

async function setup() {
    try {
        console.log('🤖 Setup Inicial - Base de Conhecimento do Robô\n');

        // Criar diretório se não existir
        await fs.ensureDir(path.dirname(caminhoBase));

        // Verificar se arquivo já existe
        const existe = await fs.pathExists(caminhoBase);

        if (existe) {
            console.log('✅ Base de conhecimento já existe em:', caminhoBase);
            console.log('\n📊 Conteúdo atual:');
            
            const dados = await fs.readJson(caminhoBase);
            console.log(`   - Comandos: ${dados.comandos ? dados.comandos.length : 0}`);
            console.log(`   - Configurações: ${dados.configuracoes ? 'Sim' : 'Não'}`);
        } else {
            console.log('📝 Criando base de conhecimento inicial...');
            await fs.writeJson(caminhoBase, baseInicial, { spaces: 2 });
            
            console.log('✅ Base de conhecimento criada com sucesso!');
            console.log('\n📊 Conteúdo inicial:');
            console.log(`   - Comandos: ${baseInicial.comandos.length}`);
            console.log(`   - Configurações: Sim`);
            
            console.log('\n📋 Comandos padrão:');
            baseInicial.comandos.forEach(cmd => {
                console.log(`   ✓ ${cmd.id} (${cmd.tipo}) - Prioridade: ${cmd.prioridade}`);
            });
        }

        console.log('\n🌐 Próximas etapas:');
        console.log('   1. Inicie o servidor: npm start');
        console.log('   2. Acesse: http://localhost:3333/gerenciador-comandos.html');
        console.log('   3. Crie seus primeiros comandos!');
        
        console.log('\n📚 Documentação:');
        console.log('   - Guia Rápido: docs/GUIA-RAPIDO-COMANDOS.md');
        console.log('   - Documentação Completa: docs/GERENCIADOR-COMANDOS.md');
        
        console.log('\n✅ Setup concluído!\n');
    } catch (erro) {
        console.error('❌ Erro durante setup:', erro.message);
        process.exit(1);
    }
}

// Executar setup
setup();
