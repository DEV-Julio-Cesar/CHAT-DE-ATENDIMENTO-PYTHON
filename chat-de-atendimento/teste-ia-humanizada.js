#!/usr/bin/env node
// =========================================================================
// TESTE DE IA HUMANIZADA E INTEGRAÇÃO GEMINI
// =========================================================================

const fs = require('fs-extra');

console.log('🤖 TESTANDO SISTEMA DE IA HUMANIZADA...\n');

async function testarIA() {
    try {
        // Verificar se os módulos de IA carregam
        console.log('🔄 Carregando módulos de IA...');
        
        const iaGemini = require('./src/aplicacao/ia-gemini');
        console.log('✅ Módulo IA Gemini carregado');
        
        const servicoIA = require('./src/aplicacao/servico-ia-humanizada');
        console.log('✅ Serviço IA Humanizada carregado');
        
        const automacaoConfig = require('./src/aplicacao/automacao-config');
        console.log('✅ Configuração de automação carregada');
        
        // Verificar configurações
        console.log('\n🔄 Verificando configurações...');
        
        const configIA = fs.existsSync('dados/config-ia-humanizada.json');
        if (configIA) {
            console.log('✅ Arquivo de configuração IA encontrado');
            const config = fs.readJsonSync('dados/config-ia-humanizada.json');
            console.log(`📝 Configurações carregadas: ${Object.keys(config).length} itens`);
        } else {
            console.log('⚠️  Arquivo de configuração IA não encontrado');
        }
        
        const automacaoConfigFile = fs.existsSync('dados/automacao-config.json');
        if (automacaoConfigFile) {
            console.log('✅ Arquivo de configuração de automação encontrado');
        } else {
            console.log('⚠️  Arquivo de configuração de automação não encontrado');
        }
        
        // Testar geração de prompt
        console.log('\n🔄 Testando geração de prompts...');
        
        try {
            const promptTeste = await automacaoConfig.gerarPromptPreview({
                instrucoesAdicionais: 'Responda de forma amigável e profissional',
                destaques: ['Teste de funcionamento', 'Sistema operacional']
            });
            
            if (promptTeste && promptTeste.success) {
                console.log('✅ Geração de prompt funcionando');
                console.log(`📝 Prompt gerado (${promptTeste.prompt.length} caracteres)`);
            } else {
                console.log('⚠️  Geração de prompt retornou resultado vazio');
            }
        } catch (erro) {
            console.log(`⚠️  Erro na geração de prompt: ${erro.message}`);
        }
        
        // Verificar API Key do Gemini
        console.log('\n🔄 Verificando integração Gemini...');
        
        const geminiKey = process.env.GEMINI_API_KEY;
        if (geminiKey && !geminiKey.startsWith('SUA_CHAVE_')) {
            console.log('✅ Chave API Gemini configurada');
            
            // Teste básico do Gemini (sem fazer chamada real)
            console.log('💡 Para testar completamente, execute uma pergunta via interface');
        } else {
            console.log('⚠️  Chave API Gemini não configurada');
            console.log('💡 Configure GEMINI_API_KEY para habilitar IA');
        }
        
        // Verificar base de conhecimento
        console.log('\n🔄 Verificando base de conhecimento...');
        
        const baseConhecimento = fs.existsSync('dados/base-conhecimento-robo.json');
        if (baseConhecimento) {
            console.log('✅ Base de conhecimento encontrada');
            const base = fs.readJsonSync('dados/base-conhecimento-robo.json');
            console.log(`📚 Itens na base: ${base.length || 0}`);
        } else {
            console.log('⚠️  Base de conhecimento não encontrada');
        }
        
        // Verificar regras do chatbot
        const chatbotRules = fs.existsSync('dados/chatbot-rules.json');
        if (chatbotRules) {
            console.log('✅ Regras do chatbot encontradas');
            const regras = fs.readJsonSync('dados/chatbot-rules.json');
            console.log(`🤖 Regras configuradas: ${regras.length || 0}`);
        } else {
            console.log('⚠️  Regras do chatbot não encontradas');
        }
        
        console.log('\n🎉 TESTE DE IA HUMANIZADA CONCLUÍDO');
        console.log('\n💡 DICAS:');
        console.log('- Configure GEMINI_API_KEY para habilitar IA completa');
        console.log('- Verifique dados/config-ia-humanizada.json para ajustes');
        console.log('- Use a interface para testar respostas em tempo real');
        
    } catch (erro) {
        console.error('❌ ERRO NO TESTE DE IA:', erro.message);
        process.exit(1);
    }
}

testarIA();