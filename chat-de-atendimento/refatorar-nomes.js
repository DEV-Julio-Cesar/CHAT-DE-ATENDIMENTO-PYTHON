// Script de Refatoração Automática - Renomeação para Português
// Execute este script para atualizar todas as referências nos arquivos

const fs = require('fs-extra');
const path = require('path');

// Mapeamento de arquivos renomeados
const mapeamentoArquivos = {
  // Interfaces
  'modal-confirmacao.js': 'modal-confirmacao.js',
  'estados-carregamento.js': 'estados-carregamento.js',
  'notificacoes-toast.js': 'notificacoes-toast.js',
  'api-navegacao.js': 'api-navegacao.js',
  'barra-navegacao.js': 'barra-navegacao.js',
  
  // Preloads
  'pre-carregamento.js': 'pre-carregamento.js',
  'pre-carregamento-cadastro.js': 'pre-carregamento-cadastro.js',
  'pre-carregamento-chat.js': 'pre-carregamento-chat.js',
  'pre-carregamento-chatbot.js': 'pre-carregamento-chatbot.js',
  'pre-carregamento-painel.js': 'pre-carregamento-painel.js',
  'pre-carregamento-saude.js': 'pre-carregamento-saude.js',
  'pre-carregamento-historico.js': 'pre-carregamento-historico.js',
  'pre-carregamento-login.js': 'pre-carregamento-login.js',
  'pre-carregamento-gerenciador-pool.js': 'pre-carregamento-gerenciador-pool.js',
  'pre-carregamento-principal.js': 'pre-carregamento-principal.js',
  'pre-carregamento-qr.js': 'pre-carregamento-qr.js',
  'pre-carregamento-usuarios.js': 'pre-carregamento-usuarios.js',
  
  // HTMLs
  'painel.html': 'painel.html',
  'saude.html': 'saude.html',
  'historico.html': 'historico.html',
  'gerenciador-pool.html': 'gerenciador-pool.html',
  'janela-qr.html': 'janela-qr.html',
  
  // Services
  'GerenciadorJanelas': 'GerenciadorJanelas',
  'GerenciadorPoolWhatsApp': 'GerenciadorPoolWhatsApp',
  'ServicoClienteWhatsApp': 'ServicoClienteWhatsApp',
  
  // Core
  'armazenamento-cache.js': 'armazenamento-armazenamento-cache.js',
  'disjuntor-circuito.js': 'disjuntor-circuito.js',
  'gerenciador-configuracoes.js': 'gerenciador-configuracoes.js',
  'injecao-dependencias.js': 'injecao-dependencias.js',
  'tratador-erros.js': 'tratador-erros.js',
  'sinalizadores-recursos.js': 'sinalizadores-recursos.js',
  'validador-entradas.js': 'validador-entradas.js',
  'fila-mensagens.js': 'fila-mensagens.js',
  'monitor-desempenho.js': 'monitor-desempenho.js',
  'metricas-prometheus.js': 'metricas-prometheus.js',
  'limitador-taxa.js': 'limitador-taxa.js',
  'politica-retentativas.js': 'politica-retentativas.js'
};

// Função recursiva para encontrar todos os arquivos .js e .html
async function encontrarArquivos(diretorio, extensoes = ['.js', '.html']) {
  const arquivos = [];
  const itens = await fs.readdir(diretorio);
  
  for (const item of itens) {
    const caminhoCompleto = path.join(diretorio, item);
    const stat = await fs.stat(caminhoCompleto);
    
    if (stat.isDirectory() && !item.startsWith('.') && item !== 'node_modules') {
      const subArquivos = await encontrarArquivos(caminhoCompleto, extensoes);
      arquivos.push(...subArquivos);
    } else if (stat.isFile() && extensoes.some(ext => item.endsWith(ext))) {
      arquivos.push(caminhoCompleto);
    }
  }
  
  return arquivos;
}

// Função para substituir referências em um arquivo
async function atualizarReferencias(caminhoArquivo) {
  try {
    let conteudo = await fs.readFile(caminhoArquivo, 'utf-8');
    let modificado = false;
    
    for (const [antigo, novo] of Object.entries(mapeamentoArquivos)) {
      if (conteudo.includes(antigo)) {
        const regex = new RegExp(antigo.replace(/\./g, '\\.'), 'g');
        conteudo = conteudo.replace(regex, novo);
        modificado = true;
      }
    }
    
    if (modificado) {
      await fs.writeFile(caminhoArquivo, conteudo, 'utf-8');
      console.log(`✅ Atualizado: ${caminhoArquivo}`);
      return true;
    }
    
    return false;
  } catch (erro) {
    console.error(`❌ Erro ao atualizar ${caminhoArquivo}:`, erro.message);
    return false;
  }
}

// Função principal
async function executarRefatoracao() {
  console.log('🚀 Iniciando refatoração automática...\n');
  
  const raiz = __dirname;
  const arquivos = await encontrarArquivos(raiz);
  
  console.log(`📁 Encontrados ${arquivos.length} arquivos para processar\n`);
  
  let contador = 0;
  for (const arquivo of arquivos) {
    const atualizado = await atualizarReferencias(arquivo);
    if (atualizado) contador++;
  }
  
  console.log(`\n✨ Refatoração concluída!`);
  console.log(`📊 Total de arquivos atualizados: ${contador} de ${arquivos.length}`);
}

// Executar
executarRefatoracao().catch(erro => {
  console.error('❌ Erro fatal:', erro);
  process.exit(1);
});
