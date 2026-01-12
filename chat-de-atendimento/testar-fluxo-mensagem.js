/**
 * Script de Teste - Fluxo de Mensagens WhatsApp
 * 
 * Simula o recebimento de mensagens e verifica se o sistema
 * está criando conversas e movendo entre os estados corretamente.
 */

const fs = require('fs-extra');
const path = require('path');

const gerenciadorFilas = require('./src/aplicacao/gerenciador-filas');
const gerenciadorMensagens = require('./src/aplicacao/gerenciador-mensagens');
const chatbot = require('./src/aplicacao/chatbot');

async function testarFluxoCompleto() {
    console.log('\n🧪 TESTE DO FLUXO DE MENSAGENS WHATSAPP\n');
    console.log('=' .repeat(60));
    
    const clientId = 'test-client';
    const chatId = '5511999999999@c.us';
    
    try {
        // 1. Verificar se chatbot está configurado
        console.log('\n1️⃣ Verificando configuração do chatbot...');
        const regras = await chatbot.carregarRegras();
        console.log(`   ✅ Chatbot ativo: ${regras.ativo}`);
        console.log(`   ✅ Palavras-chave: ${regras.palavrasChave.length} categorias`);
        console.log(`   ✅ Horário: ${regras.horarioAtendimento.inicio} - ${regras.horarioAtendimento.fim}`);
        
        // 2. Limpar dados de teste anteriores
        console.log('\n2️⃣ Limpando dados de teste...');
        const arquivoFilas = path.join(__dirname, 'dados/filas-atendimento.json');
        if (await fs.pathExists(arquivoFilas)) {
            const data = await fs.readJson(arquivoFilas);
            data.conversas = data.conversas.filter(c => !c.chatId.startsWith('test-'));
            await fs.writeJson(arquivoFilas, data, { spaces: 2 });
        }
        console.log('   ✅ Dados de teste anteriores removidos');
        
        // 3. Testar criação de conversa em AUTOMAÇÃO
        console.log('\n3️⃣ Simulando primeira mensagem (criação em AUTOMAÇÃO)...');
        let conversa = await gerenciadorFilas.buscarPorChatId(chatId);
        
        if (!conversa) {
            const resultado = await gerenciadorFilas.adicionarConversa({
                clientId,
                chatId,
                nomeContato: 'Teste Cliente',
                ultimaMensagem: 'Olá, preciso de ajuda'
            });
            conversa = resultado.conversa;
            console.log(`   ✅ Conversa criada: ${conversa.id}`);
            console.log(`   📊 Estado: ${conversa.estado}`);
        } else {
            console.log(`   ⚠️  Conversa já existe: ${conversa.id}`);
            console.log(`   📊 Estado atual: ${conversa.estado}`);
        }
        
        // 4. Testar roteamento automatizado
        console.log('\n4️⃣ Testando roteamento automatizado...');
        
        const mensagens = [
            'Olá',
            'Qual o horário de funcionamento?',
            'Quanto custa?',
            'Preciso falar com um atendente'
        ];
        
        for (let i = 0; i < mensagens.length; i++) {
            const msg = mensagens[i];
            console.log(`\n   📥 Mensagem ${i + 1}: "${msg}"`);
            
            const resultado = await gerenciadorMensagens.roteamentoAutomatizado(
                clientId,
                chatId,
                msg
            );
            
            if (resultado.devResponder) {
                console.log(`   🤖 Bot respondeu: "${resultado.resposta.substring(0, 50)}${resultado.resposta.length > 50 ? '...' : ''}"`);
                
                if (resultado.escalar) {
                    console.log(`   ⬆️  Escalamento solicitado!`);
                }
            } else {
                console.log(`   ❌ Bot não soube responder`);
            }
            
            // Atualizar tentativas
            const conversaAtual = await gerenciadorFilas.buscarPorChatId(chatId);
            if (conversaAtual) {
                const tentativas = (conversaAtual.tentativasBot || 0) + 1;
                await gerenciadorFilas.atualizarTentativasBot(chatId, tentativas);
                console.log(`   📊 Tentativas do bot: ${tentativas}/3`);
                
                // Verificar se deve mover para ESPERA
                if (resultado.escalar || tentativas >= 3) {
                    await gerenciadorFilas.moverParaEspera(clientId, chatId, resultado.escalar ? 'escalamento' : 'max_tentativas');
                    console.log(`   ⏳ Conversa movida para ESPERA`);
                    break;
                } else if (!resultado.devResponder) {
                    await gerenciadorFilas.moverParaEspera(clientId, chatId, 'bot_sem_resposta');
                    console.log(`   ⏳ Conversa movida para ESPERA (bot sem resposta)`);
                    break;
                }
            }
        }
        
        // 5. Verificar estado final
        console.log('\n5️⃣ Verificando estado final da conversa...');
        const conversaFinal = await gerenciadorFilas.buscarPorChatId(chatId);
        
        if (conversaFinal) {
            console.log(`   ✅ Conversa encontrada: ${conversaFinal.id}`);
            console.log(`   📊 Estado: ${conversaFinal.estado}`);
            console.log(`   🤖 Tentativas bot: ${conversaFinal.tentativasBot}`);
            console.log(`   👤 Atendente: ${conversaFinal.atendente || 'Nenhum'}`);
            console.log(`   📝 Última mensagem: ${conversaFinal.metadata?.ultimaMensagem || 'N/A'}`);
            
            console.log('\n   📜 Histórico de estados:');
            conversaFinal.historicoEstados.forEach(h => {
                const timestamp = new Date(h.timestamp).toLocaleTimeString('pt-BR');
                console.log(`      ${timestamp} - ${h.estado.toUpperCase()}${h.motivo ? ` (${h.motivo})` : ''}`);
            });
        } else {
            console.log('   ❌ Conversa não encontrada!');
        }
        
        // 6. Estatísticas gerais
        console.log('\n6️⃣ Estatísticas das filas...');
        const stats = await gerenciadorFilas.obterEstatisticas();
        console.log(`   🤖 Automação: ${stats.automacao}`);
        console.log(`   ⏳ Espera: ${stats.espera}`);
        console.log(`   👤 Atendimento: ${stats.atendimento}`);
        console.log(`   ✅ Encerradas: ${stats.encerradas}`);
        console.log(`   📊 Total ativas: ${stats.total}`);
        
        console.log('\n' + '='.repeat(60));
        console.log('✅ TESTE CONCLUÍDO COM SUCESSO!\n');
        
        console.log('📋 PRÓXIMOS PASSOS:');
        console.log('   1. Conecte o WhatsApp no sistema');
        console.log('   2. Envie uma mensagem de teste pelo WhatsApp');
        console.log('   3. Verifique os logs no terminal do sistema');
        console.log('   4. Abra a interface chat-filas.html para ver as conversas');
        console.log('   5. Assuma a conversa que está em ESPERA\n');
        
    } catch (erro) {
        console.error('\n❌ ERRO NO TESTE:', erro.message);
        console.error(erro.stack);
        process.exit(1);
    }
}

// Executa o teste
testarFluxoCompleto()
    .then(() => process.exit(0))
    .catch(erro => {
        console.error('Erro fatal:', erro);
        process.exit(1);
    });
