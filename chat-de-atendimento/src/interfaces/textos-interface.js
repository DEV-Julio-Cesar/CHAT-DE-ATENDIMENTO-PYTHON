// =========================================================================
// TEXTOS DA INTERFACE EM PORTUGUÊS
// =========================================================================

const TEXTOS_INTERFACE = {
    // Títulos de páginas
    TITULOS: {
        LOGIN: 'Login - Sistema de Atendimento',
        PRINCIPAL: 'Sistema de Atendimento WhatsApp',
        CADASTRO: 'Cadastro de Usuário',
        CHAT: 'Chat WhatsApp',
        USUARIOS: 'Gerenciar Usuários',
        CAMPANHAS: 'Campanhas de Marketing',
        CHATBOT: 'Configurar Chatbot',
        DASHBOARD: 'Painel de Controle',
        RELATORIOS: 'Relatórios',
        CONFIGURACOES: 'Configurações'
    },

    // Botões
    BOTOES: {
        ENTRAR: 'Entrar',
        SAIR: 'Sair',
        CADASTRAR: 'Cadastrar',
        SALVAR: 'Salvar',
        CANCELAR: 'Cancelar',
        EDITAR: 'Editar',
        REMOVER: 'Remover',
        ADICIONAR: 'Adicionar',
        BUSCAR: 'Buscar',
        FILTRAR: 'Filtrar',
        LIMPAR: 'Limpar',
        ATUALIZAR: 'Atualizar',
        CONECTAR: 'Conectar',
        DESCONECTAR: 'Desconectar',
        ENVIAR: 'Enviar',
        ANEXAR: 'Anexar',
        DOWNLOAD: 'Baixar',
        UPLOAD: 'Enviar Arquivo',
        CONFIRMAR: 'Confirmar',
        FECHAR: 'Fechar',
        VOLTAR: 'Voltar',
        PROXIMO: 'Próximo',
        ANTERIOR: 'Anterior'
    },

    // Labels de formulários
    LABELS: {
        USUARIO: 'Usuário',
        SENHA: 'Senha',
        EMAIL: 'E-mail',
        NOME: 'Nome',
        TELEFONE: 'Telefone',
        PERFIL: 'Perfil',
        STATUS: 'Status',
        DATA_CRIACAO: 'Data de Criação',
        ULTIMO_LOGIN: 'Último Login',
        ATIVO: 'Ativo',
        INATIVO: 'Inativo',
        MENSAGEM: 'Mensagem',
        DESTINATARIO: 'Destinatário',
        ASSUNTO: 'Assunto',
        CONTEUDO: 'Conteúdo',
        ARQUIVO: 'Arquivo',
        TEMA: 'Tema'
    },

    // Placeholders
    PLACEHOLDERS: {
        DIGITE_USUARIO: 'Digite seu usuário',
        DIGITE_SENHA: 'Digite sua senha',
        DIGITE_EMAIL: 'Digite o e-mail',
        DIGITE_NOME: 'Digite o nome',
        DIGITE_TELEFONE: 'Digite o telefone',
        DIGITE_MENSAGEM: 'Digite sua mensagem...',
        BUSCAR: 'Buscar...',
        SELECIONE: 'Selecione uma opção'
    },

    // Mensagens de Status
    STATUS: {
        ONLINE: 'Online',
        OFFLINE: 'Offline',
        CONECTADO: 'Conectado',
        DESCONECTADO: 'Desconectado',
        CARREGANDO: 'Carregando...',
        PROCESSANDO: 'Processando...',
        ENVIANDO: 'Enviando...',
        SALVANDO: 'Salvando...',
        AGUARDE: 'Aguarde...',
        CONCLUIDO: 'Concluído',
        ERRO: 'Erro',
        SUCESSO: 'Sucesso'
    },

    // Mensagens de Confirmaração
    CONFIRMACOES: {
        REMOVER_USUARIO: 'Tem certeza que deseja remover este usuário?',
        REMOVER_CAMPANHA: 'Tem certeza que deseja remover esta campanha?',
        DESCONECTAR_WHATSAPP: 'Tem certeza que deseja desconectar o WhatsApp?',
        LIMPAR_CHAT: 'Tem certeza que deseja limpar o histórico do chat?',
        SAIR_SISTEMA: 'Tem certeza que deseja sair do sistema?',
        CANCELAR_OPERACAO: 'Tem certeza que deseja cancelar esta operação?',
        PERDER_ALTERACOES: 'Você perderá as alterações não salvas. Continuar?'
    },

    // Mensagens de erro
    ERROS: {
        CAMPOS_OBRIGATORIOS: 'Por favor, preencha todos os campos obrigatórios',
        USUARIO_SENHA_INVALIDOS: 'Usuário ou senha inválidos',
        EMAIL_INVALIDO: 'E-mail inválido',
        SENHA_MUITO_CURTA: 'A senha deve ter pelo menos 6 caracteres',
        TELEFONE_INVALIDO: 'Número de telefone inválido',
        ARQUIVO_MUITO_GRANDE: 'Arquivo muito grande (máximo 10MB)',
        FORMATO_NAO_SUPORTADO: 'Formato de arquivo não suportado',
        CONEXAO_PERDIDA: 'Conexão perdida. Tentando reconectar...',
        ERRO_SERVIDOR: 'Erro no servidor. Tente novamente',
        SESSAO_EXPIRADA: 'Sua sessão expirou. Faça login novamente',
        PERMISSAO_NEGADA: 'Você não tem permissão para esta ação',
        OPERACAO_NAO_PERMITIDA: 'Operação não permitida'
    },

    // Mensagens de sucesso
    SUCESSOS: {
        LOGIN_REALIZADO: 'Login realizado com sucesso!',
        USUARIO_CADASTRADO: 'Usuário cadastrado com sucesso!',
        USUARIO_ATUALIZADO: 'Usuário atualizado com sucesso!',
        USUARIO_REMOVIDO: 'Usuário removido com sucesso!',
        MENSAGEM_ENVIADA: 'Mensagem enviada com sucesso!',
        ARQUIVO_ENVIADO: 'Arquivo enviado com sucesso!',
        CONFIGURACAO_SALVA: 'Configuração salva com sucesso!',
        CAMPANHA_CRIADA: 'Campanha criada com sucesso!',
        BACKUP_CRIADO: 'Backup criado com sucesso!',
        DADOS_EXPORTADOS: 'Dados exportados com sucesso!'
    },

    // Informações
    INFOS: {
        BEM_VINDO: 'Bem-vindo ao Sistema de Atendimento WhatsApp!',
        PRIMEIRO_ACESSO: 'Use "admin/admin" para primeiro acesso',
        NENHUM_RESULTADO: 'Nenhum resultado encontrado',
        LISTA_VAZIA: 'Lista vazia',
        SELECIONE_ITEM: 'Selecione um item da lista',
        DADOS_ATUALIZADOS: 'Dados atualizados automaticamente',
        SISTEMA_ATUALIZADO: 'Sistema atualizado para a versão mais recente',
        BACKUP_AUTOMATICO: 'Backup automático realizado',
        MANUTENCAO: 'Sistema em manutenção. Voltamos em breve'
    },

    // Menu/Navegação
    MENU: {
        INICIO: 'Início',
        CHAT_INTELIGENTE: 'Chat Inteligente',
        CONFIGURAR_IA: 'Configurar IA',
        USUARIOS: 'Usuários',
        CAMPANHAS: 'Campanhas',
        RELATORIOS: 'Relatórios',
        CONFIGURACOES: 'Configurações',
        AJUDA: 'Ajuda',
        SOBRE: 'Sobre',
        SAIR: 'Sair'
    },

    // WhatsApp específico
    WHATSAPP: {
        CONECTAR_WHATSAPP: 'Conectar WhatsApp',
        ESCANEAR_QR: 'Escaneie o QR Code com seu WhatsApp',
        QR_INSTRUCOES: '📱 Escaneie este código com o WhatsApp do seu celular para conectar',
        AGUARDANDO_QR: 'Aguardando leitura do QR Code...',
        CONECTADO_SUCESSO: 'WhatsApp conectado com sucesso!',
        DESCONECTADO: 'WhatsApp desconectado',
        ERRO_CONEXAO: 'Erro na conexão com WhatsApp',
        NENHUM_CLIENTE: 'Nenhum cliente WhatsApp conectado',
        GERENCIAR_CONEXOES: 'Gerenciar Conexões',
        NOVA_CONEXAO: 'Nova Conexão',
        RECONECTANDO: 'Reconectando...',
        SESSAO_EXPIRADA: 'Sessão WhatsApp expirada'
    },

    // Chat
    CHAT: {
        NOVA_MENSAGEM: 'Nova mensagem',
        DIGITANDO: 'digitando...',
        ONLINE: 'Online',
        ULTIMA_VEZ: 'visto por último',
        ANEXAR_ARQUIVO: 'Anexar arquivo',
        ENVIAR_MENSAGEM: 'Enviar mensagem',
        BUSCAR_CONVERSA: 'Buscar conversa',
        LIMPAR_HISTORICO: 'Limpar histórico',
        BLOQUEAR_CONTATO: 'Bloquear contato',
        DESBLOQUEAR_CONTATO: 'Desbloquear contato',
        ARQUIVAR_CONVERSA: 'Arquivar conversa',
        MARCAR_LIDA: 'Marcar como lida',
        MARCAR_NAO_LIDA: 'Marcar como não lida'
    },

    // Filas
    FILAS: {
        AUTOMACAO: 'Automação',
        ESPERA: 'Aguardando Atendimento',
        ATENDIMENTO: 'Em Atendimento',
        ENCERRADO: 'Encerrado',
        ASSUMIR_CONVERSA: 'Assumir Conversa',
        LIBERAR_CONVERSA: 'Liberar Conversa',
        TRANSFERIR_CONVERSA: 'Transferir Conversa',
        ENCERRAR_ATENDIMENTO: 'Encerrar Atendimento',
        TEMPO_ESPERA: 'Tempo de Espera',
        ATENDENTE: 'Atendente'
    }
};

// Função para obter texto
function obterTexto(categoria, chave) {
    try {
        const texto = TEXTOS_INTERFACE[categoria]?.[chave];
        if (!texto) {
            console.warn(`[TEXTOS] Texto não encontrado: ${categoria}.${chave}`);
            return `${categoria}.${chave}`;
        }
        return texto;
    } catch (erro) {
        console.error('[TEXTOS] Erro ao obter texto:', erro);
        return `${categoria}.${chave}`;
    }
}

// Função de conveniência
const txt = {
    titulo: (chave) => obterTexto('TITULOS', chave),
    botao: (chave) => obterTexto('BOTOES', chave),
    label: (chave) => obterTexto('LABELS', chave),
    placeholder: (chave) => obterTexto('PLACEHOLDERS', chave),
    status: (chave) => obterTexto('Status', chave),
    confirmacao: (chave) => obterTexto('CONFIRMACOES', chave),
    erro: (chave) => obterTexto('ERROS', chave),
    sucesso: (chave) => obterTexto('SUCESSOS', chave),
    info: (chave) => obterTexto('INFOS', chave),
    menu: (chave) => obterTexto('MENU', chave),
    whatsapp: (chave) => obterTexto('WHATSAPP', chave),
    chat: (chave) => obterTexto('Chat', chave),
    fila: (chave) => obterTexto('FILAS', chave)
};

// Disponibilizar globalmente se estiver Não browser
if (typeof window !== 'undefined') {
    window.TEXTOS_INTERFACE = TEXTOS_INTERFACE;
    window.obterTexto = obterTexto;
    window.txt = txt;
}

// Exportarar para Nãode.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        TEXTOS_INTERFACE,
        obterTexto,
        txt
    };
}