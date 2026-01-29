#!/usr/bin/env node
// =========================================================================
// SCRIPT PARA TRADUZIR INTERFACE PARA PORTUGUÊS
// =========================================================================

const fs = require('fs-extra');
const path = require('path');

console.log('🇧🇷 TRADUZINDO INTERFACE PARA PORTUGUÊS...\n');

// Mapeamento de traduções
const TRADUCOES = {
    // Textos em inglês -> português
    'Loading...': 'Carregando...',
    'Please wait...': 'Aguarde...',
    'Error': 'Erro',
    'Success': 'Sucesso',
    'Failed': 'Falhou',
    'Connected': 'Conectado',
    'Disconnected': 'Desconectado',
    'Online': 'Online',
    'Offline': 'Offline',
    'Ready': 'Pronto',
    'Connecting...': 'Conectando...',
    'Reconnecting...': 'Reconectando...',
    'Authentication failed': 'Falha na autenticação',
    'Connection lost': 'Conexão perdida',
    'Session expired': 'Sessão expirada',
    'Invalid credentials': 'Credenciais inválidas',
    'User not found': 'Usuário não encontrado',
    'Access denied': 'Acesso negado',
    'Operation not allowed': 'Operação não permitida',
    'File too large': 'Arquivo muito grande',
    'Invalid format': 'Formato inválido',
    'Upload failed': 'Falha no upload',
    'Download failed': 'Falha no download',
    'Save': 'Salvar',
    'Cancel': 'Cancelar',
    'Delete': 'Excluir',
    'Edit': 'Editar',
    'Add': 'Adicionar',
    'Remove': 'Remover',
    'Update': 'Atualizar',
    'Refresh': 'Atualizar',
    'Search': 'Buscar',
    'Filter': 'Filtrar',
    'Clear': 'Limpar',
    'Close': 'Fechar',
    'Back': 'Voltar',
    'Next': 'Próximo',
    'Previous': 'Anterior',
    'Confirm': 'Confirmar',
    'Yes': 'Sim',
    'No': 'Não',
    'OK': 'OK',
    'Username': 'Usuário',
    'Password': 'Senha',
    'Email': 'E-mail',
    'Name': 'Nome',
    'Phone': 'Telefone',
    'Message': 'Mensagem',
    'Send': 'Enviar',
    'Receive': 'Receber',
    'Sent': 'Enviado',
    'Received': 'Recebido',
    'Typing...': 'Digitando...',
    'Last seen': 'Visto por último',
    'Active': 'Ativo',
    'Inactive': 'Inativo',
    'Available': 'Disponível',
    'Busy': 'Ocupado',
    'Away': 'Ausente',
    'Settings': 'Configurações',
    'Profile': 'Perfil',
    'Account': 'Conta',
    'Logout': 'Sair',
    'Login': 'Entrar',
    'Register': 'Cadastrar',
    'Dashboard': 'Painel',
    'Reports': 'Relatórios',
    'Users': 'Usuários',
    'Campaigns': 'Campanhas',
    'Chat': 'Chat',
    'Chatbot': 'Chatbot',
    'Help': 'Ajuda',
    'About': 'Sobre',
    'Version': 'Versão',
    'Theme': 'Tema',
    'Light': 'Claro',
    'Dark': 'Escuro',
    'Language': 'Idioma',
    'Notifications': 'Notificações',
    'Privacy': 'Privacidade',
    'Security': 'Segurança',
    'Backup': 'Backup',
    'Export': 'Exportar',
    'Import': 'Importar',
    'File': 'Arquivo',
    'Folder': 'Pasta',
    'Size': 'Tamanho',
    'Date': 'Data',
    'Time': 'Hora',
    'Status': 'Status',
    'Type': 'Tipo',
    'Category': 'Categoria',
    'Priority': 'Prioridade',
    'High': 'Alta',
    'Medium': 'Média',
    'Low': 'Baixa',
    'New': 'Novo',
    'Open': 'Abrir',
    'Closed': 'Fechado',
    'Pending': 'Pendente',
    'Approved': 'Aprovado',
    'Rejected': 'Rejeitado',
    'Draft': 'Rascunho',
    'Published': 'Publicado',
    'Archived': 'Arquivado',
    'Deleted': 'Excluído',
    'Created': 'Criado',
    'Modified': 'Modificado',
    'Author': 'Autor',
    'Owner': 'Proprietário',
    'Admin': 'Administrador',
    'User': 'Usuário',
    'Guest': 'Convidado',
    'Member': 'Membro',
    'Moderator': 'Moderador',
    'Manager': 'Gerente',
    'Supervisor': 'Supervisor',
    'Agent': 'Agente',
    'Customer': 'Cliente',
    'Contact': 'Contato',
    'Group': 'Grupo',
    'Channel': 'Canal',
    'Broadcast': 'Transmissão',
    'List': 'Lista',
    'Grid': 'Grade',
    'Table': 'Tabela',
    'Chart': 'Gráfico',
    'Graph': 'Gráfico',
    'Statistics': 'Estatísticas',
    'Analytics': 'Análises',
    'Metrics': 'Métricas',
    'Performance': 'Desempenho',
    'Quality': 'Qualidade',
    'Rating': 'Avaliação',
    'Review': 'Revisão',
    'Feedback': 'Feedback',
    'Comment': 'Comentário',
    'Reply': 'Responder',
    'Forward': 'Encaminhar',
    'Share': 'Compartilhar',
    'Copy': 'Copiar',
    'Paste': 'Colar',
    'Cut': 'Recortar',
    'Undo': 'Desfazer',
    'Redo': 'Refazer',
    'Select': 'Selecionar',
    'Select All': 'Selecionar Tudo',
    'Deselect': 'Desmarcar',
    'Check': 'Marcar',
    'Uncheck': 'Desmarcar',
    'Enable': 'Habilitar',
    'Disable': 'Desabilitar',
    'Show': 'Mostrar',
    'Hide': 'Ocultar',
    'Expand': 'Expandir',
    'Collapse': 'Recolher',
    'Minimize': 'Minimizar',
    'Maximize': 'Maximizar',
    'Restore': 'Restaurar',
    'Resize': 'Redimensionar',
    'Move': 'Mover',
    'Drag': 'Arrastar',
    'Drop': 'Soltar',
    'Upload': 'Enviar',
    'Download': 'Baixar',
    'Install': 'Instalar',
    'Uninstall': 'Desinstalar',
    'Update': 'Atualizar',
    'Upgrade': 'Atualizar',
    'Downgrade': 'Reverter',
    'Restart': 'Reiniciar',
    'Shutdown': 'Desligar',
    'Start': 'Iniciar',
    'Stop': 'Parar',
    'Pause': 'Pausar',
    'Resume': 'Continuar',
    'Play': 'Reproduzir',
    'Record': 'Gravar',
    'Mute': 'Silenciar',
    'Unmute': 'Ativar som',
    'Volume': 'Volume',
    'Quality': 'Qualidade',
    'Speed': 'Velocidade',
    'Duration': 'Duração',
    'Progress': 'Progresso',
    'Complete': 'Completo',
    'Incomplete': 'Incompleto',
    'Total': 'Total',
    'Count': 'Contagem',
    'Amount': 'Quantidade',
    'Price': 'Preço',
    'Cost': 'Custo',
    'Value': 'Valor',
    'Currency': 'Moeda',
    'Tax': 'Imposto',
    'Discount': 'Desconto',
    'Subtotal': 'Subtotal',
    'Grand Total': 'Total Geral'
};

// Função para traduzir conteúdo de arquivo
function traduzirConteudo(conteudo) {
    let conteudoTraduzido = conteudo;
    
    Object.entries(TRADUCOES).forEach(([ingles, portugues]) => {
        // Traduzir em strings (entre aspas)
        const regexString = new RegExp(`(['"\`])${ingles.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\1`, 'gi');
        conteudoTraduzido = conteudoTraduzido.replace(regexString, `$1${portugues}$1`);
        
        // Traduzir em comentários
        const regexComment = new RegExp(`(//.*?)${ingles.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'gi');
        conteudoTraduzido = conteudoTraduzido.replace(regexComment, `$1${portugues}`);
        
        // Traduzir em textos HTML
        const regexHtml = new RegExp(`(>)${ingles.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(<)`, 'gi');
        conteudoTraduzido = conteudoTraduzido.replace(regexHtml, `$1${portugues}$2`);
    });
    
    return conteudoTraduzido;
}

// Função para processar arquivo
async function processarArquivo(caminhoArquivo) {
    try {
        const conteudo = await fs.readFile(caminhoArquivo, 'utf8');
        const conteudoTraduzido = traduzirConteudo(conteudo);
        
        if (conteudo !== conteudoTraduzido) {
            await fs.writeFile(caminhoArquivo, conteudoTraduzido, 'utf8');
            console.log(`✅ Traduzido: ${path.relative(process.cwd(), caminhoArquivo)}`);
            return true;
        } else {
            console.log(`⏭️  Sem alterações: ${path.relative(process.cwd(), caminhoArquivo)}`);
            return false;
        }
    } catch (erro) {
        console.error(`❌ Erro ao processar ${caminhoArquivo}:`, erro.message);
        return false;
    }
}

// Função principal
async function traduzirInterface() {
    try {
        const pastaInterfaces = path.join(__dirname, '../src/interfaces');
        const arquivos = await fs.readdir(pastaInterfaces);
        
        let totalArquivos = 0;
        let arquivosTraduzidos = 0;
        
        for (const arquivo of arquivos) {
            if (arquivo.endsWith('.html') || arquivo.endsWith('.js')) {
                const caminhoCompleto = path.join(pastaInterfaces, arquivo);
                const stat = await fs.stat(caminhoCompleto);
                
                if (stat.isFile()) {
                    totalArquivos++;
                    const traduzido = await processarArquivo(caminhoCompleto);
                    if (traduzido) {
                        arquivosTraduzidos++;
                    }
                }
            }
        }
        
        console.log('\n📊 RELATÓRIO DE TRADUÇÃO:');
        console.log(`Total de arquivos processados: ${totalArquivos}`);
        console.log(`Arquivos traduzidos: ${arquivosTraduzidos}`);
        console.log(`Arquivos sem alterações: ${totalArquivos - arquivosTraduzidos}`);
        
        if (arquivosTraduzidos > 0) {
            console.log('\n🎉 TRADUÇÃO CONCLUÍDA COM SUCESSO!');
        } else {
            console.log('\n✨ INTERFACE JÁ ESTÁ TRADUZIDA!');
        }
        
    } catch (erro) {
        console.error('❌ ERRO NA TRADUÇÃO:', erro.message);
        process.exit(1);
    }
}

// Executar se chamado diretamente
if (require.main === module) {
    traduzirInterface();
}

module.exports = { traduzirInterface, traduzirConteudo };