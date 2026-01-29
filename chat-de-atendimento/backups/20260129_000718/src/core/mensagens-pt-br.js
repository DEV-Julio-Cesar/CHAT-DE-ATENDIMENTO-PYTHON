// =========================================================================
// MENSAGENS EM PORTUGUÊS BRASILEIRO
// =========================================================================

const MENSAGENS = {
    // Sistema
    SISTEMA: {
        ONLINE: 'Online',
        OFFLINE: 'Offline',
        CONECTANDO: 'Conectando...',
        DESCONECTADO: 'Desconectado',
        ERRO: 'Erro',
        SUCESSO: 'Sucesso',
        CARREGANDO: 'Carregando...',
        AGUARDE: 'Aguarde...',
        PROCESSANDO: 'Processando...',
        CONCLUIDO: 'Concluído',
        CANCELADO: 'Cancelado',
        TIMEOUT: 'Tempo esgotado',
        RECONECTANDO: 'Reconectando...',
        INICIALIZANDO: 'Inicializando...'
    },

    // WhatsApp
    WHATSAPP: {
        CONECTADO: 'WhatsApp conectado',
        DESCONECTADO: 'WhatsApp desconectado',
        AUTENTICADO: 'Autenticado com sucesso',
        QR_GERADO: 'QR Code gerado',
        QR_AGUARDANDO: 'Aguardando leitura do QR Code',
        CLIENTE_PRONTO: 'Cliente WhatsApp pronto',
        ERRO_CONEXAO: 'Erro na conexão WhatsApp',
        SESSAO_EXPIRADA: 'Sessão expirada',
        RECONECTANDO: 'Reconectando WhatsApp...',
        NENHUM_CLIENTE: 'Nenhum cliente WhatsApp conectado',
        CLIENTE_NAO_ENCONTRADO: 'Cliente não encontrado',
        MENSAGEM_ENVIADA: 'Mensagem enviada',
        ERRO_ENVIO: 'Erro ao enviar mensagem',
        CHAT_NAO_ENCONTRADO: 'Chat não encontrado'
    },

    // Login/Autenticação
    LOGIN: {
        BEM_VINDO: 'Bem-vindo ao Sistema',
        USUARIO_SENHA_OBRIGATORIOS: 'Usuário e senha são obrigatórios',
        CREDENCIAIS_INVALIDAS: 'Usuário ou senha inválidos',
        LOGIN_SUCESSO: 'Login realizado com sucesso',
        SESSAO_EXPIRADA: 'Sua sessão expirou. Faça login novamente',
        LOGOUT_SUCESSO: 'Logout realizado com sucesso',
        PRIMEIRO_ACESSO: 'Use "admin/admin" para primeiro acesso',
        PREENCHA_CAMPOS: 'Por favor, preencha todos os campos',
        ERRO_LOGIN: 'Erro ao realizar login'
    },

    // Usuários
    USUARIOS: {
        CADASTRADO_SUCESSO: 'Usuário cadastrado com sucesso',
        USUARIO_JA_EXISTE: 'Usuário já existe',
        USUARIO_NAO_ENCONTRADO: 'Usuário não encontrado',
        USUARIO_REMOVIDO: 'Usuário removido com sucesso',
        USUARIO_ATUALIZADO: 'Usuário atualizado com sucesso',
        USUARIO_ATIVADO: 'Usuário ativado',
        USUARIO_DESATIVADO: 'Usuário desativado',
        NAO_REMOVER_ADMIN: 'Não é possível remover o usuário admin',
        NAO_DESATIVAR_ADMIN: 'Não é possível desativar o usuário admin',
        ERRO_CADASTRO: 'Erro ao cadastrar usuário',
        ERRO_REMOCAO: 'Erro ao remover usuário',
        ERRO_ATUALIZACAO: 'Erro ao atualizar usuário'
    },

    // Chat/Mensagens
    CHAT: {
        NOVA_MENSAGEM: 'Nova mensagem recebida',
        MENSAGEM_ENVIADA: 'Mensagem enviada',
        ERRO_ENVIO: 'Erro ao enviar mensagem',
        CHAT_VAZIO: 'Nenhuma mensagem encontrada',
        DIGITANDO: 'digitando...',
        ONLINE: 'online',
        ULTIMA_VEZ: 'visto por último',
        ARQUIVO_ENVIADO: 'Arquivo enviado',
        ERRO_ARQUIVO: 'Erro ao enviar arquivo',
        MENSAGEM_MUITO_LONGA: 'Mensagem muito longa',
        CHAT_BLOQUEADO: 'Chat bloqueado'
    },

    // Filas de Atendimento
    FILAS: {
        AUTOMACAO: 'Automação',
        ESPERA: 'Aguardando Atendimento',
        ATENDIMENTO: 'Em Atendimento',
        ENCERRADO: 'Encerrado',
        CONVERSA_ASSUMIDA: 'Conversa assumida',
        CONVERSA_LIBERADA: 'Conversa liberada',
        JA_EM_ATENDIMENTO: 'Já em atendimento por outro usuário',
        ATENDIMENTO_NAO_ENCONTRADO: 'Atendimento não encontrado',
        ERRO_ASSUMIR: 'Erro ao assumir conversa',
        ERRO_LIBERAR: 'Erro ao liberar conversa'
    },

    // Campanhas
    CAMPANHAS: {
        CRIADA_SUCESSO: 'Campanha criada com sucesso',
        REMOVIDA_SUCESSO: 'Campanha removida com sucesso',
        CAMPANHA_NAO_ENCONTRADA: 'Campanha não encontrada',
        EXECUTANDO: 'Executando campanha...',
        CONCLUIDA: 'Campanha concluída',
        ERRO_EXECUCAO: 'Erro na execução da campanha',
        DESTINATARIOS_IMPORTADOS: 'Destinatários importados com sucesso',
        ERRO_IMPORTACAO: 'Erro ao importar destinatários',
        ARQUIVO_INVALIDO: 'Arquivo inválido',
        FORMATO_NAO_SUPORTADO: 'Formato não suportado'
    },

    // Chatbot/IA
    CHATBOT: {
        RESPOSTA_GERADA: 'Resposta gerada pela IA',
        ERRO_IA: 'Erro na IA',
        CONFIGURACAO_SALVA: 'Configuração salva',
        REGRAS_ATUALIZADAS: 'Regras atualizadas',
        PROMPT_GERADO: 'Prompt gerado com sucesso',
        ERRO_PROMPT: 'Erro ao gerar prompt',
        IA_INDISPONIVEL: 'IA temporariamente indisponível',
        CHAVE_API_NECESSARIA: 'Configure GEMINI_API_KEY para habilitar IA'
    },

    // Backup/Sistema
    BACKUP: {
        CRIADO_SUCESSO: 'Backup criado com sucesso',
        ERRO_BACKUP: 'Erro ao criar backup',
        RESTAURADO_SUCESSO: 'Backup restaurado com sucesso',
        ERRO_RESTAURACAO: 'Erro ao restaurar backup',
        ARQUIVO_NAO_ENCONTRADO: 'Arquivo de backup não encontrado',
        LIMPEZA_CONCLUIDA: 'Limpeza de arquivos antigos concluída'
    },

    // Validação
    VALIDACAO: {
        CAMPO_OBRIGATORIO: 'Campo obrigatório',
        EMAIL_INVALIDO: 'E-mail inválido',
        SENHA_MUITO_CURTA: 'Senha muito curta (mínimo 6 caracteres)',
        TELEFONE_INVALIDO: 'Número de telefone inválido',
        ARQUIVO_MUITO_GRANDE: 'Arquivo muito grande',
        FORMATO_INVALIDO: 'Formato inválido',
        DADOS_INVALIDOS: 'Dados inválidos'
    },

    // Interface
    INTERFACE: {
        CONFIRMAR: 'Confirmar',
        CANCELAR: 'Cancelar',
        SALVAR: 'Salvar',
        EDITAR: 'Editar',
        REMOVER: 'Remover',
        ADICIONAR: 'Adicionar',
        BUSCAR: 'Buscar',
        FILTRAR: 'Filtrar',
        EXPORTAR: 'Exportar',
        IMPORTAR: 'Importar',
        ATUALIZAR: 'Atualizar',
        FECHAR: 'Fechar',
        VOLTAR: 'Voltar',
        PROXIMO: 'Próximo',
        ANTERIOR: 'Anterior',
        SELECIONAR: 'Selecionar',
        LIMPAR: 'Limpar',
        COPIAR: 'Copiar',
        COLAR: 'Colar',
        DOWNLOAD: 'Download',
        UPLOAD: 'Upload'
    },

    // Status/Estados
    STATUS: {
        ATIVO: 'Ativo',
        INATIVO: 'Inativo',
        PENDENTE: 'Pendente',
        APROVADO: 'Aprovado',
        REJEITADO: 'Rejeitado',
        EM_ANDAMENTO: 'Em andamento',
        PAUSADO: 'Pausado',
        FINALIZADO: 'Finalizado',
        DISPONIVEL: 'Disponível',
        OCUPADO: 'Ocupado',
        AUSENTE: 'Ausente'
    },

    // Notificações
    NOTIFICACOES: {
        NOVA_MENSAGEM: 'Nova mensagem recebida',
        CLIENTE_CONECTADO: 'Cliente WhatsApp conectado',
        CLIENTE_DESCONECTADO: 'Cliente WhatsApp desconectado',
        SISTEMA_ATUALIZADO: 'Sistema atualizado',
        BACKUP_AUTOMATICO: 'Backup automático realizado',
        ERRO_SISTEMA: 'Erro no sistema',
        MANUTENCAO: 'Sistema em manutenção'
    }
};

// Função para obter mensagem
function obterMensagem(categoria, chave, parametros = {}) {
    try {
        const mensagem = MENSAGENS[categoria]?.[chave];
        if (!mensagem) {
            console.warn(`[MENSAGENS] Mensagem não encontrada: ${categoria}.${chave}`);
            return `${categoria}.${chave}`;
        }

        // Substituir parâmetros na mensagem se fornecidos
        let mensagemFinal = mensagem;
        Object.keys(parametros).forEach(param => {
            mensagemFinal = mensagemFinal.replace(`{${param}}`, parametros[param]);
        });

        return mensagemFinal;
    } catch (erro) {
        console.error('[MENSAGENS] Erro ao obter mensagem:', erro);
        return `${categoria}.${chave}`;
    }
}

// Função de conveniência para categorias específicas
const msg = {
    sistema: (chave, params) => obterMensagem('SISTEMA', chave, params),
    whatsapp: (chave, params) => obterMensagem('WHATSAPP', chave, params),
    login: (chave, params) => obterMensagem('LOGIN', chave, params),
    usuarios: (chave, params) => obterMensagem('USUARIOS', chave, params),
    chat: (chave, params) => obterMensagem('CHAT', chave, params),
    filas: (chave, params) => obterMensagem('FILAS', chave, params),
    campanhas: (chave, params) => obterMensagem('CAMPANHAS', chave, params),
    chatbot: (chave, params) => obterMensagem('CHATBOT', chave, params),
    backup: (chave, params) => obterMensagem('BACKUP', chave, params),
    validacao: (chave, params) => obterMensagem('VALIDACAO', chave, params),
    interface: (chave, params) => obterMensagem('INTERFACE', chave, params),
    status: (chave, params) => obterMensagem('STATUS', chave, params),
    notificacoes: (chave, params) => obterMensagem('NOTIFICACOES', chave, params)
};

module.exports = {
    MENSAGENS,
    obterMensagem,
    msg
};