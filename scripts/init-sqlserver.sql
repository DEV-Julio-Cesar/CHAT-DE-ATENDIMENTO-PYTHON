-- ============================================================================
-- SCRIPT DE INICIALIZAÇÃO DO BANCO DE DADOS SQL SERVER
-- Sistema de Atendimento WhatsApp - CIANET PROVEDOR
-- Versão: 3.0 | Data: 2026
-- ============================================================================

USE master;
GO

-- Criar banco de dados se não existir
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'isp_support')
BEGIN
    CREATE DATABASE isp_support
    COLLATE Latin1_General_CI_AI;
    PRINT 'Banco de dados isp_support criado com sucesso.';
END
GO

USE isp_support;
GO

-- ============================================================================
-- TABELA DE USUÁRIOS (AUTENTICAÇÃO JWT)
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'usuarios') AND type = 'U')
BEGIN
    CREATE TABLE usuarios (
        id INT IDENTITY(1,1) PRIMARY KEY,
        email NVARCHAR(255) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        nome NVARCHAR(100) NOT NULL,
        role NVARCHAR(20) NOT NULL DEFAULT 'atendente'
            CHECK (role IN ('admin', 'supervisor', 'atendente')),
        is_active BIT NOT NULL DEFAULT 1,
        two_factor_enabled BIT NOT NULL DEFAULT 0,
        two_factor_secret NVARCHAR(100) NULL,
        failed_login_attempts INT NOT NULL DEFAULT 0,
        locked_until DATETIME NULL,
        password_changed_at DATETIME NULL,
        must_change_password BIT NOT NULL DEFAULT 0,
        avatar_url NVARCHAR(500) NULL,
        phone NVARCHAR(20) NULL,
        department NVARCHAR(100) NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE(),
        last_login DATETIME NULL,
        deleted_at DATETIME NULL,
        
        -- Índices
        INDEX IX_usuarios_email (email),
        INDEX IX_usuarios_role (role),
        INDEX IX_usuarios_active (is_active)
    );
    PRINT 'Tabela usuarios criada.';
END
GO

-- ============================================================================
-- TABELA DE REFRESH TOKENS
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'refresh_tokens') AND type = 'U')
BEGIN
    CREATE TABLE refresh_tokens (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL FOREIGN KEY REFERENCES usuarios(id) ON DELETE CASCADE,
        token_hash NVARCHAR(255) NOT NULL UNIQUE,
        device_info NVARCHAR(500) NULL,
        ip_address NVARCHAR(50) NULL,
        user_agent NVARCHAR(500) NULL,
        expires_at DATETIME NOT NULL,
        is_revoked BIT NOT NULL DEFAULT 0,
        revoked_at DATETIME NULL,
        revoked_reason NVARCHAR(255) NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        last_used_at DATETIME NULL,
        
        INDEX IX_refresh_tokens_user (user_id),
        INDEX IX_refresh_tokens_expires (expires_at),
        INDEX IX_refresh_tokens_revoked (is_revoked)
    );
    PRINT 'Tabela refresh_tokens criada.';
END
GO

-- ============================================================================
-- TABELA DE SESSÕES ATIVAS
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'user_sessions') AND type = 'U')
BEGIN
    CREATE TABLE user_sessions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL FOREIGN KEY REFERENCES usuarios(id) ON DELETE CASCADE,
        session_id NVARCHAR(100) NOT NULL UNIQUE,
        access_token_jti NVARCHAR(100) NULL,
        refresh_token_id INT NULL FOREIGN KEY REFERENCES refresh_tokens(id),
        device_name NVARCHAR(100) NULL,
        device_type NVARCHAR(50) NULL,
        browser NVARCHAR(100) NULL,
        os NVARCHAR(100) NULL,
        ip_address NVARCHAR(50) NULL,
        location NVARCHAR(255) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        last_activity DATETIME NOT NULL DEFAULT GETDATE(),
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        expires_at DATETIME NOT NULL,
        
        INDEX IX_sessions_user (user_id),
        INDEX IX_sessions_active (is_active),
        INDEX IX_sessions_expires (expires_at)
    );
    PRINT 'Tabela user_sessions criada.';
END
GO

-- ============================================================================
-- TABELA DE PERMISSÕES GRANULARES
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'permissions') AND type = 'U')
BEGIN
    CREATE TABLE permissions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        code NVARCHAR(100) NOT NULL UNIQUE,
        name NVARCHAR(100) NOT NULL,
        description NVARCHAR(500) NULL,
        category NVARCHAR(50) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Tabela permissions criada.';
END
GO

-- ============================================================================
-- TABELA DE PERMISSÕES POR ROLE
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'role_permissions') AND type = 'U')
BEGIN
    CREATE TABLE role_permissions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        role NVARCHAR(20) NOT NULL CHECK (role IN ('admin', 'supervisor', 'atendente')),
        permission_id INT NOT NULL FOREIGN KEY REFERENCES permissions(id) ON DELETE CASCADE,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT UQ_role_permission UNIQUE (role, permission_id)
    );
    PRINT 'Tabela role_permissions criada.';
END
GO

-- ============================================================================
-- TABELA DE CLIENTES WHATSAPP
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'clientes_whatsapp') AND type = 'U')
BEGIN
    CREATE TABLE clientes_whatsapp (
        id INT IDENTITY(1,1) PRIMARY KEY,
        phone NVARCHAR(20) NOT NULL UNIQUE,
        name NVARCHAR(200) NULL,
        email NVARCHAR(255) NULL,
        profile_pic_url NVARCHAR(500) NULL,
        status NVARCHAR(20) NOT NULL DEFAULT 'ativo'
            CHECK (status IN ('ativo', 'inativo', 'bloqueado')),
        tags NVARCHAR(500) NULL,
        notes NVARCHAR(MAX) NULL,
        crm_customer_id NVARCHAR(100) NULL,
        first_contact_at DATETIME NULL,
        last_contact_at DATETIME NULL,
        total_conversations INT NOT NULL DEFAULT 0,
        total_messages INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE(),
        
        INDEX IX_clientes_phone (phone),
        INDEX IX_clientes_status (status),
        INDEX IX_clientes_crm (crm_customer_id)
    );
    PRINT 'Tabela clientes_whatsapp criada.';
END
GO

-- ============================================================================
-- TABELA DE CONVERSAS
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'conversas') AND type = 'U')
BEGIN
    CREATE TABLE conversas (
        id INT IDENTITY(1,1) PRIMARY KEY,
        client_id INT NOT NULL FOREIGN KEY REFERENCES clientes_whatsapp(id),
        attendant_id INT NULL FOREIGN KEY REFERENCES usuarios(id),
        status NVARCHAR(30) NOT NULL DEFAULT 'waiting'
            CHECK (status IN ('waiting', 'in_progress', 'on_hold', 'resolved', 'closed')),
        priority NVARCHAR(20) NOT NULL DEFAULT 'normal'
            CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
        category NVARCHAR(100) NULL,
        subject NVARCHAR(500) NULL,
        queue_position INT NULL,
        rating INT NULL CHECK (rating BETWEEN 1 AND 5),
        feedback NVARCHAR(MAX) NULL,
        started_at DATETIME NOT NULL DEFAULT GETDATE(),
        first_response_at DATETIME NULL,
        resolved_at DATETIME NULL,
        closed_at DATETIME NULL,
        last_message_at DATETIME NULL,
        total_messages INT NOT NULL DEFAULT 0,
        bot_handled BIT NOT NULL DEFAULT 0,
        transferred_from INT NULL,
        transferred_to INT NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE(),
        
        INDEX IX_conversas_client (client_id),
        INDEX IX_conversas_attendant (attendant_id),
        INDEX IX_conversas_status (status),
        INDEX IX_conversas_created (created_at DESC)
    );
    PRINT 'Tabela conversas criada.';
END
GO

-- ============================================================================
-- TABELA DE MENSAGENS
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'mensagens') AND type = 'U')
BEGIN
    CREATE TABLE mensagens (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        conversation_id INT NOT NULL FOREIGN KEY REFERENCES conversas(id) ON DELETE CASCADE,
        sender_type NVARCHAR(20) NOT NULL
            CHECK (sender_type IN ('client', 'attendant', 'bot', 'system')),
        sender_id INT NULL,
        content NVARCHAR(MAX) NOT NULL,
        message_type NVARCHAR(20) NOT NULL DEFAULT 'text'
            CHECK (message_type IN ('text', 'image', 'audio', 'video', 'document', 'sticker', 'location')),
        media_url NVARCHAR(500) NULL,
        media_mime_type NVARCHAR(100) NULL,
        whatsapp_message_id NVARCHAR(100) NULL,
        status NVARCHAR(20) NOT NULL DEFAULT 'sent'
            CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed')),
        is_from_me BIT NOT NULL DEFAULT 0,
        quoted_message_id BIGINT NULL,
        metadata NVARCHAR(MAX) NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        delivered_at DATETIME NULL,
        read_at DATETIME NULL,
        
        INDEX IX_mensagens_conversation (conversation_id),
        INDEX IX_mensagens_created (created_at DESC),
        INDEX IX_mensagens_whatsapp_id (whatsapp_message_id)
    );
    PRINT 'Tabela mensagens criada.';
END
GO

-- ============================================================================
-- TABELA DE RESPOSTAS RÁPIDAS
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'quick_replies') AND type = 'U')
BEGIN
    CREATE TABLE quick_replies (
        id INT IDENTITY(1,1) PRIMARY KEY,
        shortcut NVARCHAR(50) NOT NULL UNIQUE,
        title NVARCHAR(100) NOT NULL,
        content NVARCHAR(MAX) NOT NULL,
        category NVARCHAR(50) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        usage_count INT NOT NULL DEFAULT 0,
        created_by INT NULL FOREIGN KEY REFERENCES usuarios(id),
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Tabela quick_replies criada.';
END
GO

-- ============================================================================
-- TABELA DE LOGS DE AUDITORIA
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'audit_logs') AND type = 'U')
BEGIN
    CREATE TABLE audit_logs (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NULL FOREIGN KEY REFERENCES usuarios(id),
        event_type NVARCHAR(50) NOT NULL,
        action NVARCHAR(100) NOT NULL,
        resource_type NVARCHAR(50) NULL,
        resource_id NVARCHAR(100) NULL,
        ip_address NVARCHAR(50) NULL,
        user_agent NVARCHAR(500) NULL,
        status NVARCHAR(20) NULL,
        details NVARCHAR(MAX) NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        
        INDEX IX_audit_user (user_id),
        INDEX IX_audit_event (event_type),
        INDEX IX_audit_created (created_at DESC)
    );
    PRINT 'Tabela audit_logs criada.';
END
GO

-- ============================================================================
-- TABELA DE MÉTRICAS DO DASHBOARD
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dashboard_metrics') AND type = 'U')
BEGIN
    CREATE TABLE dashboard_metrics (
        id INT IDENTITY(1,1) PRIMARY KEY,
        metric_date DATE NOT NULL,
        hour_of_day INT NULL,
        total_conversations INT NOT NULL DEFAULT 0,
        new_conversations INT NOT NULL DEFAULT 0,
        resolved_conversations INT NOT NULL DEFAULT 0,
        total_messages INT NOT NULL DEFAULT 0,
        avg_response_time_seconds INT NULL,
        avg_resolution_time_seconds INT NULL,
        total_clients INT NOT NULL DEFAULT 0,
        new_clients INT NOT NULL DEFAULT 0,
        active_attendants INT NOT NULL DEFAULT 0,
        avg_rating DECIMAL(3,2) NULL,
        bot_handled_count INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT UQ_metrics_date_hour UNIQUE (metric_date, hour_of_day),
        INDEX IX_metrics_date (metric_date DESC)
    );
    PRINT 'Tabela dashboard_metrics criada.';
END
GO

-- ============================================================================
-- TABELA DE FILAS DE ATENDIMENTO
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'queues') AND type = 'U')
BEGIN
    CREATE TABLE queues (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(100) NOT NULL UNIQUE,
        description NVARCHAR(500) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        max_size INT NULL,
        priority_weight INT NOT NULL DEFAULT 1,
        business_hours_start TIME NULL,
        business_hours_end TIME NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Tabela queues criada.';
END
GO

-- ============================================================================
-- TABELA DE ATENDENTES NAS FILAS
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'queue_attendants') AND type = 'U')
BEGIN
    CREATE TABLE queue_attendants (
        id INT IDENTITY(1,1) PRIMARY KEY,
        queue_id INT NOT NULL FOREIGN KEY REFERENCES queues(id) ON DELETE CASCADE,
        user_id INT NOT NULL FOREIGN KEY REFERENCES usuarios(id) ON DELETE CASCADE,
        is_active BIT NOT NULL DEFAULT 1,
        max_concurrent INT NOT NULL DEFAULT 5,
        current_count INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT UQ_queue_user UNIQUE (queue_id, user_id)
    );
    PRINT 'Tabela queue_attendants criada.';
END
GO

-- ============================================================================
-- TABELA DE CAMPANHAS
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'campaigns') AND type = 'U')
BEGIN
    CREATE TABLE campaigns (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(200) NOT NULL,
        description NVARCHAR(MAX) NULL,
        message_template NVARCHAR(MAX) NOT NULL,
        media_url NVARCHAR(500) NULL,
        status NVARCHAR(20) NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled')),
        target_filter NVARCHAR(MAX) NULL,
        total_recipients INT NOT NULL DEFAULT 0,
        sent_count INT NOT NULL DEFAULT 0,
        delivered_count INT NOT NULL DEFAULT 0,
        read_count INT NOT NULL DEFAULT 0,
        failed_count INT NOT NULL DEFAULT 0,
        scheduled_at DATETIME NULL,
        started_at DATETIME NULL,
        completed_at DATETIME NULL,
        created_by INT NOT NULL FOREIGN KEY REFERENCES usuarios(id),
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE(),
        
        INDEX IX_campaigns_status (status),
        INDEX IX_campaigns_scheduled (scheduled_at)
    );
    PRINT 'Tabela campaigns criada.';
END
GO

-- ============================================================================
-- INSERIR PERMISSÕES PADRÃO
-- ============================================================================
PRINT 'Inserindo permissões padrão...';

-- Permissões de Dashboard
IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'dashboard.view')
BEGIN
    INSERT INTO permissions (code, name, description, category) VALUES 
    ('dashboard.view', 'Ver Dashboard', 'Visualizar métricas e estatísticas', 'dashboard'),
    ('dashboard.export', 'Exportar Relatórios', 'Exportar dados do dashboard', 'dashboard');
END

-- Permissões de Conversas
IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'conversations.view')
BEGIN
    INSERT INTO permissions (code, name, description, category) VALUES 
    ('conversations.view', 'Ver Conversas', 'Visualizar conversas', 'conversations'),
    ('conversations.respond', 'Responder Conversas', 'Enviar mensagens', 'conversations'),
    ('conversations.transfer', 'Transferir Conversas', 'Transferir para outro atendente', 'conversations'),
    ('conversations.close', 'Encerrar Conversas', 'Fechar conversas', 'conversations'),
    ('conversations.delete', 'Excluir Conversas', 'Remover conversas', 'conversations');
END

-- Permissões de Clientes
IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'clients.view')
BEGIN
    INSERT INTO permissions (code, name, description, category) VALUES 
    ('clients.view', 'Ver Clientes', 'Visualizar lista de clientes', 'clients'),
    ('clients.edit', 'Editar Clientes', 'Modificar dados de clientes', 'clients'),
    ('clients.export', 'Exportar Clientes', 'Exportar lista de clientes', 'clients');
END

-- Permissões de Campanhas
IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'campaigns.view')
BEGIN
    INSERT INTO permissions (code, name, description, category) VALUES 
    ('campaigns.view', 'Ver Campanhas', 'Visualizar campanhas', 'campaigns'),
    ('campaigns.create', 'Criar Campanhas', 'Criar novas campanhas', 'campaigns'),
    ('campaigns.edit', 'Editar Campanhas', 'Modificar campanhas', 'campaigns'),
    ('campaigns.delete', 'Excluir Campanhas', 'Remover campanhas', 'campaigns'),
    ('campaigns.send', 'Enviar Campanhas', 'Iniciar envio de campanhas', 'campaigns');
END

-- Permissões de Usuários
IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'users.view')
BEGIN
    INSERT INTO permissions (code, name, description, category) VALUES 
    ('users.view', 'Ver Usuários', 'Visualizar lista de usuários', 'users'),
    ('users.create', 'Criar Usuários', 'Adicionar novos usuários', 'users'),
    ('users.edit', 'Editar Usuários', 'Modificar dados de usuários', 'users'),
    ('users.delete', 'Excluir Usuários', 'Remover usuários', 'users'),
    ('users.permissions', 'Gerenciar Permissões', 'Alterar permissões de usuários', 'users');
END

-- Permissões de Configurações
IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'settings.view')
BEGIN
    INSERT INTO permissions (code, name, description, category) VALUES 
    ('settings.view', 'Ver Configurações', 'Visualizar configurações do sistema', 'settings'),
    ('settings.edit', 'Editar Configurações', 'Modificar configurações do sistema', 'settings'),
    ('settings.whatsapp', 'Configurar WhatsApp', 'Gerenciar conexão WhatsApp', 'settings'),
    ('settings.integrations', 'Gerenciar Integrações', 'Configurar integrações externas', 'settings');
END

-- Permissões de Chatbot
IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'chatbot.view')
BEGIN
    INSERT INTO permissions (code, name, description, category) VALUES 
    ('chatbot.view', 'Ver Chatbot', 'Visualizar configurações do chatbot', 'chatbot'),
    ('chatbot.train', 'Treinar Chatbot', 'Adicionar conhecimento ao chatbot', 'chatbot'),
    ('chatbot.config', 'Configurar Chatbot', 'Modificar comportamento do chatbot', 'chatbot');
END

GO

-- ============================================================================
-- ATRIBUIR PERMISSÕES AOS ROLES
-- ============================================================================
PRINT 'Atribuindo permissões aos roles...';

-- Admin tem todas as permissões
INSERT INTO role_permissions (role, permission_id)
SELECT 'admin', id FROM permissions
WHERE NOT EXISTS (
    SELECT 1 FROM role_permissions WHERE role = 'admin' AND permission_id = permissions.id
);

-- Supervisor tem a maioria das permissões
INSERT INTO role_permissions (role, permission_id)
SELECT 'supervisor', id FROM permissions
WHERE code NOT IN ('users.delete', 'users.permissions', 'settings.edit', 'settings.integrations')
AND NOT EXISTS (
    SELECT 1 FROM role_permissions WHERE role = 'supervisor' AND permission_id = permissions.id
);

-- Atendente tem permissões básicas
INSERT INTO role_permissions (role, permission_id)
SELECT 'atendente', id FROM permissions
WHERE code IN (
    'dashboard.view', 
    'conversations.view', 'conversations.respond', 'conversations.transfer', 'conversations.close',
    'clients.view',
    'chatbot.view'
)
AND NOT EXISTS (
    SELECT 1 FROM role_permissions WHERE role = 'atendente' AND permission_id = permissions.id
);

GO

-- ============================================================================
-- INSERIR USUÁRIO ADMIN PADRÃO
-- ============================================================================
PRINT 'Criando usuário admin padrão...';

-- Password: Admin@123 (bcrypt hash)
IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'admin@empresa.com.br')
BEGIN
    INSERT INTO usuarios (email, password_hash, nome, role, is_active, created_at)
    VALUES (
        'admin@empresa.com.br',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X.wdBPj/RK.PmvlG.',
        'Administrador',
        'admin',
        1,
        GETDATE()
    );
    PRINT 'Usuário admin criado: admin@empresa.com.br / Admin@123';
END

-- Criar usuário supervisor de exemplo
IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'supervisor@empresa.com.br')
BEGIN
    INSERT INTO usuarios (email, password_hash, nome, role, is_active, created_at)
    VALUES (
        'supervisor@empresa.com.br',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X.wdBPj/RK.PmvlG.',
        'Supervisor',
        'supervisor',
        1,
        GETDATE()
    );
    PRINT 'Usuário supervisor criado: supervisor@empresa.com.br / Admin@123';
END

-- Criar usuário atendente de exemplo
IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'atendente@empresa.com.br')
BEGIN
    INSERT INTO usuarios (email, password_hash, nome, role, is_active, created_at)
    VALUES (
        'atendente@empresa.com.br',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X.wdBPj/RK.PmvlG.',
        'João Atendente',
        'atendente',
        1,
        GETDATE()
    );
    PRINT 'Usuário atendente criado: atendente@empresa.com.br / Admin@123';
END

GO

-- ============================================================================
-- INSERIR RESPOSTAS RÁPIDAS DE EXEMPLO
-- ============================================================================
PRINT 'Inserindo respostas rápidas...';

IF NOT EXISTS (SELECT 1 FROM quick_replies WHERE shortcut = '/ola')
BEGIN
    INSERT INTO quick_replies (shortcut, title, content, category, is_active) VALUES
    ('/ola', 'Saudação', 'Olá! Seja bem-vindo(a) ao atendimento da CIANET PROVEDOR. Meu nome é {attendant_name}. Como posso ajudá-lo(a)?', 'saudacao', 1),
    ('/aguarde', 'Aguardar', 'Um momento, por favor. Estou verificando as informações.', 'atendimento', 1),
    ('/fatura', 'Segunda via fatura', 'Para segunda via da fatura, acesse nosso app ou site: app.cianet.com.br. Posso ajudar com mais alguma coisa?', 'financeiro', 1),
    ('/suporte', 'Suporte técnico', 'Entendi! Vou abrir um chamado de suporte técnico para você. Nossa equipe entrará em contato em até 2 horas.', 'suporte', 1),
    ('/horario', 'Horário de atendimento', 'Nosso horário de atendimento é de segunda a sexta, das 8h às 18h, e aos sábados das 8h às 12h.', 'info', 1),
    ('/tchau', 'Despedida', 'Obrigado por entrar em contato com a CIANET PROVEDOR! Caso precise de mais ajuda, estamos à disposição. Tenha um ótimo dia!', 'despedida', 1),
    ('/planos', 'Informações de planos', 'Temos planos de internet a partir de R$ 79,90/mês. Qual velocidade você precisa? 100MB, 300MB ou 500MB?', 'comercial', 1),
    ('/velocidade', 'Teste de velocidade', 'Para testar sua velocidade, acesse: speedtest.cianet.com.br. Conecte-se pelo cabo de rede para melhor resultado.', 'suporte', 1);
    PRINT 'Respostas rápidas inseridas.';
END

GO

-- ============================================================================
-- INSERIR FILA PADRÃO
-- ============================================================================
PRINT 'Criando filas de atendimento...';

IF NOT EXISTS (SELECT 1 FROM queues WHERE name = 'Atendimento Geral')
BEGIN
    INSERT INTO queues (name, description, is_active, priority_weight, business_hours_start, business_hours_end) VALUES
    ('Atendimento Geral', 'Fila principal de atendimento ao cliente', 1, 1, '08:00', '18:00'),
    ('Suporte Técnico', 'Fila para problemas técnicos', 1, 2, '08:00', '22:00'),
    ('Financeiro', 'Fila para questões financeiras', 1, 1, '08:00', '18:00'),
    ('Comercial', 'Fila para vendas e novos planos', 1, 1, '08:00', '18:00');
    PRINT 'Filas criadas.';
END

GO

-- ============================================================================
-- STORED PROCEDURES
-- ============================================================================

-- Procedure para criar sessão
CREATE OR ALTER PROCEDURE sp_CreateUserSession
    @user_id INT,
    @session_id NVARCHAR(100),
    @access_token_jti NVARCHAR(100),
    @device_name NVARCHAR(100) = NULL,
    @device_type NVARCHAR(50) = NULL,
    @browser NVARCHAR(100) = NULL,
    @os NVARCHAR(100) = NULL,
    @ip_address NVARCHAR(50) = NULL,
    @expires_hours INT = 24
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO user_sessions (
        user_id, session_id, access_token_jti, device_name, device_type,
        browser, os, ip_address, is_active, last_activity, expires_at
    )
    VALUES (
        @user_id, @session_id, @access_token_jti, @device_name, @device_type,
        @browser, @os, @ip_address, 1, GETDATE(), DATEADD(hour, @expires_hours, GETDATE())
    );
    
    SELECT SCOPE_IDENTITY() AS session_db_id;
END
GO

-- Procedure para validar sessão
CREATE OR ALTER PROCEDURE sp_ValidateSession
    @session_id NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE user_sessions
    SET last_activity = GETDATE()
    WHERE session_id = @session_id 
      AND is_active = 1 
      AND expires_at > GETDATE();
    
    SELECT 
        s.id,
        s.user_id,
        s.session_id,
        s.device_name,
        s.ip_address,
        s.last_activity,
        s.expires_at,
        u.email,
        u.nome,
        u.role
    FROM user_sessions s
    INNER JOIN usuarios u ON s.user_id = u.id
    WHERE s.session_id = @session_id 
      AND s.is_active = 1 
      AND s.expires_at > GETDATE()
      AND u.is_active = 1;
END
GO

-- Procedure para obter permissões do usuário
CREATE OR ALTER PROCEDURE sp_GetUserPermissions
    @user_id INT
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT DISTINCT p.code, p.name, p.category
    FROM usuarios u
    INNER JOIN role_permissions rp ON u.role = rp.role
    INNER JOIN permissions p ON rp.permission_id = p.id
    WHERE u.id = @user_id AND u.is_active = 1;
END
GO

-- Procedure para métricas do dashboard
CREATE OR ALTER PROCEDURE sp_GetDashboardMetrics
    @start_date DATE = NULL,
    @end_date DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @start_date IS NULL SET @start_date = CAST(GETDATE() AS DATE);
    IF @end_date IS NULL SET @end_date = CAST(GETDATE() AS DATE);
    
    -- Métricas gerais
    SELECT
        (SELECT COUNT(*) FROM conversas WHERE CAST(created_at AS DATE) BETWEEN @start_date AND @end_date) AS total_conversations,
        (SELECT COUNT(*) FROM conversas WHERE status = 'waiting') AS waiting_conversations,
        (SELECT COUNT(*) FROM conversas WHERE status = 'in_progress') AS active_conversations,
        (SELECT COUNT(*) FROM conversas WHERE status IN ('resolved', 'closed') AND CAST(resolved_at AS DATE) BETWEEN @start_date AND @end_date) AS resolved_today,
        (SELECT COUNT(*) FROM mensagens WHERE CAST(created_at AS DATE) BETWEEN @start_date AND @end_date) AS total_messages,
        (SELECT COUNT(*) FROM clientes_whatsapp WHERE CAST(created_at AS DATE) BETWEEN @start_date AND @end_date) AS new_clients,
        (SELECT COUNT(*) FROM usuarios WHERE is_active = 1 AND role IN ('atendente', 'supervisor')) AS total_attendants,
        (SELECT AVG(CAST(rating AS FLOAT)) FROM conversas WHERE rating IS NOT NULL AND CAST(created_at AS DATE) BETWEEN @start_date AND @end_date) AS avg_rating;
END
GO

PRINT '============================================';
PRINT 'Banco de dados inicializado com sucesso!';
PRINT '============================================';
PRINT '';
PRINT 'Usuários criados:';
PRINT '  admin@empresa.com.br / Admin@123 (admin)';
PRINT '  supervisor@empresa.com.br / Admin@123 (supervisor)';
PRINT '  atendente@empresa.com.br / Admin@123 (atendente)';
PRINT '';
GO
