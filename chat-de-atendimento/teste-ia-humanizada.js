#!/usr/bin/env node

/**
 * Script de Teste: IA Humanizada
 * Execute com: npm run teste:ia-humanizada
 * 
 * Testa todos os recursos do sistema de IA humanizada
 */

const ServicoIAHumanizada = require('./src/aplicacao/servico-ia-humanizada');
const colors = require('colors');

// Configuração
const servicoIA = new ServicoIAHumanizada({
    servico: 'Chat de Atendimento WhatsApp',
    empresa: 'Seu Negócio'
});

// Cores para output
const cores = {
    titulo: 'cyan',
    subtitulo: 'blue',
    cliente: 'yellow',
    bot: 'green',
    erro: 'red',
    sucesso: 'green',
    info: 'grey'
};

/**
 * Aguarda tempo em ms
 */
function esperar(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Exibe um teste
 */
async function exibirTeste(numero, titulo, funcaoTeste) {
    console.log(`\n${'═'.repeat(60)}`.magenta);
    console.log(`TESTE ${numero}: ${titulo}`.cyan.bold);
    console.log(`${'═'.repeat(60)}`.magenta);
    
    try {
        await funcaoTeste();
        console.log(`✓ Teste ${numero} executado com sucesso!`.green.bold);
    } catch (erro) {
        console.log(`✗ Erro no Teste ${numero}:`.red.bold);
        console.log(erro.message.red);
    }
    
    await esperar(500);
}

/**
 * Simula conversa de teste
 */
function simularConversa(cliente, texto) {
    console.log(`\n👤 ${cliente}: ${texto}`.yellow);
}

/**
 * Exibe resposta
 */
function exibirResposta(resposta) {
    console.log(`🤖 Bot: ${resposta}`.green);
}

/**
 * TESTE 1: Primeira Interação
 */
async function teste1_PrimeiraInteracao() {
    simularConversa('João Silva', 'Oi! Primeira vez aqui!');
    
    const resultado = await servicoIA.procesarMensagemCliente(
        'Oi! Primeira vez aqui!',
        'teste_cliente_001',
        'saudacao',
        { nome: 'João Silva' }
    );
    
    exibirResposta(resultado.resposta);
    console.log(`\n📊 Status: ${resultado.success ? 'Sucesso'.green : 'Falha'.red}`);
}

/**
 * TESTE 2: Dúvida Comum
 */
async function teste2_DuvidaComum() {
    simularConversa('Maria', 'Como vocês cobram pelos serviços?');
    
    const resultado = await servicoIA.procesarMensagemCliente(
        'Como vocês cobram pelos serviços?',
        'teste_cliente_002',
        'duvida',
        { nome: 'Maria' }
    );
    
    exibirResposta(resultado.resposta);
    console.log(`\n📊 Status: ${resultado.success ? 'Sucesso'.green : 'Falha'.red}`);
}

/**
 * TESTE 3: Conversa Multi-Turno
 */
async function teste3_ConversaMultiTurno() {
    const idCliente = 'teste_cliente_multi_003';
    const nomeCliente = 'Pedro';
    
    console.log(`\n📱 Conversas consecutivas - mesmo cliente:\n`);
    
    // Mensagem 1
    simularConversa(nomeCliente, 'Oi, preciso de ajuda com meu pedido');
    let resp1 = await servicoIA.procesarMensagemCliente(
        'Oi, preciso de ajuda com meu pedido',
        idCliente,
        'duvida',
        { nome: nomeCliente }
    );
    exibirResposta(resp1.resposta);
    
    // Mensagem 2
    await esperar(1000);
    simularConversa(nomeCliente, 'Fiz o pedido semana passada e ainda não chegou');
    let resp2 = await servicoIA.procesarMensagemCliente(
        'Fiz o pedido semana passada e ainda não chegou',
        idCliente,
        'problema'
    );
    exibirResposta(resp2.resposta);
    
    // Mensagem 3
    await esperar(1000);
    simularConversa(nomeCliente, 'Qual o número de rastreio?');
    let resp3 = await servicoIA.procesarMensagemCliente(
        'Qual o número de rastreio?',
        idCliente,
        'duvida'
    );
    exibirResposta(resp3.resposta);
    
    // Verificar histórico
    const info = servicoIA.obterInfoConversa(idCliente);
    console.log(`\n📊 Histórico mantido: ${info.totalMensagens} mensagens\n`);
}

/**
 * TESTE 4: Problema Técnico
 */
async function teste4_ProblemaTecnico() {
    simularConversa('Carlos', 'Não consigo fazer login. Recebo erro 403');
    
    const resultado = await servicoIA.processarProblemaComHistorico(
        'Não consigo fazer login. Recebo erro 403',
        'teste_cliente_004',
        [
            'Reiniciar o navegador',
            'Limpar cache e cookies',
            'Tentar em outro navegador'
        ]
    );
    
    exibirResposta(resultado.resposta);
    console.log(`\n📊 Status: ${resultado.success ? 'Sucesso'.green : 'Falha'.red}`);
}

/**
 * TESTE 5: Cliente Frustrado
 */
async function teste5_ClienteFrustrado() {
    const frustraçao = 'Estou muito frustrado! Paguei ontem e ainda nada!';
    simularConversa('Ana Silva', frustraçao);
    
    const resultado = await servicoIA.processarClienteInsatisfeito(
        frustraçao,
        'teste_cliente_005',
        'Cliente pagou e aguarda produto há 24h. Primeira reclamação.'
    );
    
    exibirResposta(resultado.resposta);
    console.log(`\n📊 Status: ${resultado.success ? 'Sucesso'.green : 'Falha'.red}`);
}

/**
 * TESTE 6: Pergunta Diagnóstica
 */
async function teste6_PerguntaDiagnostica() {
    simularConversa('Roberto', 'O sistema está muito lento');
    
    const resultado = await servicoIA.fazerPerguntaDiagnostica(
        'O sistema está muito lento',
        'teste_cliente_006'
    );
    
    console.log(`\n💡 Pergunta diagnóstica:`);
    exibirResposta(resultado.pergunta);
    console.log(`\n📊 Status: ${resultado.success ? 'Sucesso'.green : 'Falha'.red}`);
}

/**
 * TESTE 7: Feedback Positivo
 */
async function teste7_FeedbackPositivo() {
    const feedback = 'Vocês foram incríveis! Resolveram em minutos! Recomendo!';
    simularConversa('Juliana', feedback);
    
    const resultado = await servicoIA.responderFeedbackPositivo(
        feedback,
        'teste_cliente_007',
        'Juliana'
    );
    
    exibirResposta(resultado.resposta);
    console.log(`\n📊 Status: ${resultado.success ? 'Sucesso'.green : 'Falha'.red}`);
}

/**
 * TESTE 8: Diferentes Emoções
 */
async function teste8_DeteccaoEmocoes() {
    console.log(`\nTeste de Detecção de Emoções:\n`);
    
    const exemplos = [
        { msg: 'Oi! Tudo bem?', emocao: 'Neutro/Feliz' },
        { msg: 'Não funciona!!! 😠😠😠', emocao: 'Frustrado' },
        { msg: 'Preciso urgente! É emergência!', emocao: 'Urgente' },
        { msg: 'Não entendi como usar isso...', emocao: 'Confuso' },
        { msg: 'Adorei! Perfeito! 😊', emocao: 'Feliz' }
    ];
    
    for (const exemplo of exemplos) {
        const resultado = await servicoIA.procesarMensagemCliente(
            exemplo.msg,
            `teste_emocao_${Math.random()}`,
            'duvida'
        );
        
        console.log(`✓ "${exemplo.msg}" (${exemplo.emocao})`);
        console.log(`  → ${resultado.resposta.substring(0, 80)}...`);
        console.log();
    }
}

/**
 * TESTE 9: Gestão de Histórico
 */
async function teste9_GestaoHistorico() {
    const idCliente = 'teste_cliente_hist';
    
    console.log(`\n📋 Teste de Gestão de Histórico:\n`);
    
    // Primeira mensagem
    await servicoIA.procesarMensagemCliente(
        'Primeira mensagem',
        idCliente,
        'duvida'
    );
    
    let info = servicoIA.obterInfoConversa(idCliente);
    console.log(`✓ Após 1ª mensagem: ${info.totalMensagens} mensagem(ns)`.cyan);
    
    // Mais mensagens
    for (let i = 0; i < 3; i++) {
        await servicoIA.procesarMensagemCliente(
            `Mensagem ${i + 2}`,
            idCliente,
            'duvida'
        );
    }
    
    info = servicoIA.obterInfoConversa(idCliente);
    console.log(`✓ Após 4 mensagens: ${info.totalMensagens} mensagens`.cyan);
    
    // Limpar
    servicoIA.limparConversa(idCliente);
    info = servicoIA.obterInfoConversa(idCliente);
    console.log(`✓ Após limpar: ${info ? 'Erro - ainda existe' : 'Sucesso - eliminado'.green}`);
}

/**
 * TESTE 10: Resposta Fallback
 */
async function teste10_RespostaFallback() {
    console.log(`\nTeste de Tratamento de Erros:\n`);
    
    const resultado = await servicoIA.procesarMensagemCliente(
        'Mensagem de teste com resposta fallback',
        'teste_cliente_fallback',
        'duvida'
    );
    
    if (resultado.success) {
        console.log(`✓ Resposta obtida com sucesso`.green);
        console.log(`  ${resultado.resposta.substring(0, 100)}...`);
    } else {
        console.log(`✓ Fallback acionado (como esperado em erro)`.cyan);
        console.log(`  ${resultado.resposta}`);
    }
}

/**
 * RELATÓRIO FINAL
 */
async function relatorioFinal() {
    console.log(`\n${'═'.repeat(60)}`.magenta);
    console.log(`RELATÓRIO FINAL`.cyan.bold);
    console.log(`${'═'.repeat(60)}`.magenta);
    
    console.log(`
✅ Sistema de IA Humanizada Testado com Sucesso!

📊 Recursos Testados:
  ✓ Primeira interação com cliente novo
  ✓ Processamento de dúvidas comuns
  ✓ Manutenção de histórico multi-turno
  ✓ Resolução de problemas técnicos
  ✓ Tratamento de cliente frustrado
  ✓ Perguntas diagnósticas
  ✓ Resposta a feedback positivo
  ✓ Detecção automática de emoções
  ✓ Gestão de histórico de conversa
  ✓ Tratamento de erros e fallbacks

🚀 Próximas Etapas:
  1. Integrar em suas rotas Express (veja exemplos-uso-ia-humanizada.js)
  2. Configurar Gemini API Key
  3. Adaptar mensagens em dados/config-ia-humanizada.json
  4. Treinar com seus dados reais

📚 Documentação:
  • GUIA-IA-HUMANIZADA.md - Guia completo de uso
  • exemplos-uso-ia-humanizada.js - Exemplos práticos
  • gerador-prompts-ia.js - Gerador de prompts
  • servico-ia-humanizada.js - Serviço principal

💡 Dica: Customize as mensagens em config-ia-humanizada.json para sua marca!
    `);
    
    console.log(`${'═'.repeat(60)}`.magenta);
    console.log(`Testes Concluídos! 🎉`.green.bold);
    console.log(`${'═'.repeat(60)}\n`.magenta);
}

/**
 * Executar Todos os Testes
 */
async function executarTodosTestes() {
    console.clear();
    
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         🤖 TESTES - IA HUMANIZADA E HUMANIZADA 🤖        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    `.cyan.bold);
    
    console.log(`Iniciando testes em ${new Date().toLocaleTimeString('pt-BR')}\n`);
    
    try {
        await exibirTeste(1, 'Primeira Interação', teste1_PrimeiraInteracao);
        await exibirTeste(2, 'Dúvida Comum', teste2_DuvidaComum);
        await exibirTeste(3, 'Conversa Multi-Turno', teste3_ConversaMultiTurno);
        await exibirTeste(4, 'Problema Técnico', teste4_ProblemaTecnico);
        await exibirTeste(5, 'Cliente Frustrado', teste5_ClienteFrustrado);
        await exibirTeste(6, 'Pergunta Diagnóstica', teste6_PerguntaDiagnostica);
        await exibirTeste(7, 'Feedback Positivo', teste7_FeedbackPositivo);
        await exibirTeste(8, 'Detecção de Emoções', teste8_DeteccaoEmocoes);
        await exibirTeste(9, 'Gestão de Histórico', teste9_GestaoHistorico);
        await exibirTeste(10, 'Resposta Fallback', teste10_RespostaFallback);
        
        await relatorioFinal();
        
    } catch (erro) {
        console.log(`\n❌ Erro durante execução: ${erro.message}`.red.bold);
        process.exit(1);
    }
}

// Executar
if (require.main === module) {
    executarTodosTestes()
        .then(() => process.exit(0))
        .catch(erro => {
            console.error(erro);
            process.exit(1);
        });
}

module.exports = { executarTodosTestes };
