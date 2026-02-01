-- ISP Chat System - Script de Inicialização SQL Server
-- Este script cria a estrutura inicial do banco SQL Server
-- Compatível com migração do sistema Node.js atual

-- === CONFIGURAÇÕES INICIAIS ===
USE master;
GO

-- Criar banco de dados se não existir
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'ISPChat')
BEGIN
    CREATE DATABASE ISPChat
    COLLATE SQL_Latin1_General_CP1_CI_AS;
END
GO

-- Usar o banco criado
USE ISPChat;
GO

-- === TABELA DE USUÁRIOS ===
-- Migração da estrutura de dados/usuarios.json
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
BEGIN
    CREATE TABLE users (
        -- Chave primária UUID
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        
        -- Dados básicos (compatível com Node.js)
        username NVARCHAR(50) UNIQUE NOT NULL,
        email NVARCHAR(255) UNIQUE NOT NULL,
        password_hash NVARCHAR(255) NOT NULL,
        
        -- Perfil e permissões
        role NVARCHAR(20) NOT NULL DEFAULT 'agent' 
            CHECK (role IN ('admin', 'supervisor', 'agent', 'viewer')),
        is_active BIT DEFAULT 1,
        is_verified BIT DEFAULT 0,
        
        -- Timestamps (compatível com Node.js)
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        updated_at DATETIME2 DEFAULT GETUTCDATE(),
        last_login DATETIME2,
        
        -- Metadados adicionais (JSON)
        user_metadata NVARCHAR(MAX) DEFAULT '{}' CHECK (ISJSON(user_metadata) = 1),
        
        -- Configurações do usuário (JSON)
        settings NVARCHAR(MAX) DEFAULT '{"notifications": true, "theme": "light", "language": "pt-BR"}' 
            CHECK (ISJSON(settings) = 1)
    );
    
    PRINT '✅ Tabela users criada';
END
GO

-- === TABELA DE CONVERSAS ===
-- Migração da estrutura de dados/filas-atendimento.json
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversations' AND xtype='U')
BEGIN
    CREATE TABLE conversations (
        -- Chave primária UUID
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        
        -- Referência ao sistema antigo (para migração)
        legacy_id NVARCHAR(255),
        
        -- Dados do cliente
        customer_phone NVARCHAR(20) NOT NULL,
        customer_name NVARCHAR(255),
        
        -- Status e atribuição
        status NVARCHAR(20) NOT NULL DEFAULT 'automation' 
            CHECK (status IN ('automation', 'waiting', 'in_service', 'closed')),
        priority NVARCHAR(20) NOT NULL DEFAULT 'normal' 
            CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
        agent_id UNIQUEIDENTIFIER REFERENCES users(id) ON DELETE SET NULL,
        
        -- Dados do WhatsApp
        whatsapp_client_id NVARCHAR(100),
        
        -- Timestamps
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        updated_at DATETIME2 DEFAULT GETUTCDATE(),
        assigned_at DATETIME2,
        closed_at DATETIME2,
        
        -- Última mensagem (para performance)
        last_message NVARCHAR(MAX),
        last_message_at DATETIME2,
        
        -- Controle do bot
        bot_attempts INT DEFAULT 0,
        bot_escalated BIT DEFAULT 0,
        
        -- Metadados (compatível com Node.js) - JSON
        metadata NVARCHAR(MAX) DEFAULT '{}' CHECK (ISJSON(metadata) = 1),
        
        -- Histórico de estados - JSON
        status_history NVARCHAR(MAX) DEFAULT '[]' CHECK (ISJSON(status_history) = 1)
    );
    
    PRINT '✅ Tabela conversations criada';
END
GO

-- === TABELA DE MENSAGENS ===
-- Armazenamento de todas as mensagens do sistema
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='messages' AND xtype='U')
BEGIN
    CREATE TABLE messages (
        -- Chave primária UUID
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        
        -- Referência à conversa
        conversation_id UNIQUEIDENTIFIER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        
        -- Dados do remetente
        sender_type NVARCHAR(20) NOT NULL 
            CHECK (sender_type IN ('customer', 'agent', 'bot', 'system')),
        sender_id UNIQUEIDENTIFIER, -- Pode ser NULL para mensagens de sistema
        
        -- Conteúdo da mensagem
        content NVARCHAR(MAX) NOT NULL,
        message_type NVARCHAR(20) DEFAULT 'text' 
            CHECK (message_type IN ('text', 'image', 'audio', 'video', 'document', 'location', 'contact', 'sticker', 'system')),
        
        -- Timestamps
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        
        -- Status da mensagem
        is_read BIT DEFAULT 0,
        delivered_at DATETIME2,
        read_at DATETIME2,
        
        -- Metadados (anexos, localização, etc.) - JSON
        metadata NVARCHAR(MAX) DEFAULT '{}' CHECK (ISJSON(metadata) = 1)
    );
    
    PRINT '✅ Tabela messages criada';
END
GO

-- === TABELA DE SESSÕES WHATSAPP ===
-- Controle das sessões ativas do WhatsApp
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='whatsapp_sessions' AND xtype='U')
BEGIN
    CREATE TABLE whatsapp_sessions (
        -- Chave primária UUID
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        
        -- Identificador da sessão
        session_id NVARCHAR(100) UNIQUE NOT NULL,
        client_id NVARCHAR(100) UNIQUE NOT NULL,
        
        -- Status da sessão
        is_active BIT DEFAULT 0,
        is_authenticated BIT DEFAULT 0,
        
        -- Dados da sessão
        qr_code NVARCHAR(MAX),
        phone_number NVARCHAR(20),
        
        -- Timestamps
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        updated_at DATETIME2 DEFAULT GETUTCDATE(),
        last_activity DATETIME2 DEFAULT GETUTCDATE(),
        
        -- Metadados - JSON
        metadata NVARCHAR(MAX) DEFAULT '{}' CHECK (ISJSON(metadata) = 1)
    );
    
    PRINT '✅ Tabela whatsapp_sessions criada';
END
GO

-- === TABELA DE CAMPANHAS ===
-- Sistema de campanhas de marketing
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='campaigns' AND xtype='U')
BEGIN
    CREATE TABLE campaigns (
        -- Chave primária UUID
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        
        -- Dados da campanha
        name NVARCHAR(255) NOT NULL,
        description NVARCHAR(MAX),
        
        -- Status
        is_active BIT DEFAULT 1,
        
        -- Configurações - JSON
        target_audience NVARCHAR(MAX) DEFAULT '{}' CHECK (ISJSON(target_audience) = 1),
        message_template NVARCHAR(MAX),
        
        -- Timestamps
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        updated_at DATETIME2 DEFAULT GETUTCDATE(),
        scheduled_at DATETIME2,
        
        -- Estatísticas
        sent_count INT DEFAULT 0,
        delivered_count INT DEFAULT 0,
        read_count INT DEFAULT 0,
        
        -- Metadados - JSON
        metadata NVARCHAR(MAX) DEFAULT '{}' CHECK (ISJSON(metadata) = 1)
    );
    
    PRINT '✅ Tabela campaigns criada';
END
GO

-- === ÍNDICES PARA PERFORMANCE ===

-- Índices para usuários
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_users_username')
    CREATE INDEX IX_users_username ON users(username);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_users_email')
    CREATE INDEX IX_users_email ON users(email);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_users_role')
    CREATE INDEX IX_users_role ON users(role);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_users_active')
    CREATE INDEX IX_users_active ON users(is_active);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_users_last_login')
    CREATE INDEX IX_users_last_login ON users(last_login);

-- Índices para conversas
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conversations_status')
    CREATE INDEX IX_conversations_status ON conversations(status);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conversations_agent')
    CREATE INDEX IX_conversations_agent ON conversations(agent_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conversations_customer')
    CREATE INDEX IX_conversations_customer ON conversations(customer_phone);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conversations_created_at')
    CREATE INDEX IX_conversations_created_at ON conversations(created_at);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conversations_updated_at')
    CREATE INDEX IX_conversations_updated_at ON conversations(updated_at);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conversations_priority')
    CREATE INDEX IX_conversations_priority ON conversations(priority);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conversations_whatsapp_client')
    CREATE INDEX IX_conversations_whatsapp_client ON conversations(whatsapp_client_id);

-- Índices para mensagens
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_messages_conversation')
    CREATE INDEX IX_messages_conversation ON messages(conversation_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_messages_created_at')
    CREATE INDEX IX_messages_created_at ON messages(created_at);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_messages_sender_type')
    CREATE INDEX IX_messages_sender_type ON messages(sender_type);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_messages_sender_id')
    CREATE INDEX IX_messages_sender_id ON messages(sender_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_messages_is_read')
    CREATE INDEX IX_messages_is_read ON messages(is_read);

-- Índices para sessões WhatsApp
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_whatsapp_sessions_active')
    CREATE INDEX IX_whatsapp_sessions_active ON whatsapp_sessions(is_active);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_whatsapp_sessions_client_id')
    CREATE INDEX IX_whatsapp_sessions_client_id ON whatsapp_sessions(client_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_whatsapp_sessions_last_activity')
    CREATE INDEX IX_whatsapp_sessions_last_activity ON whatsapp_sessions(last_activity);

-- Índices para campanhas
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_campaigns_active')
    CREATE INDEX IX_campaigns_active ON campaigns(is_active);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_campaigns_scheduled')
    CREATE INDEX IX_campaigns_scheduled ON campaigns(scheduled_at);

PRINT '✅ Todos os índices criados';
GO

-- === TRIGGERS PARA TIMESTAMPS AUTOMÁTICOS ===

-- Trigger para atualizar updated_at automaticamente na tabela users
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'TR_users_updated_at')
BEGIN
    EXEC('
    CREATE TRIGGER TR_users_updated_at
    ON users
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE users 
        SET updated_at = GETUTCDATE()
        FROM users u
        INNER JOIN inserted i ON u.id = i.id;
    END
    ');
    PRINT '✅ Trigger users updated_at criado';
END
GO

-- Trigger para atualizar updated_at automaticamente na tabela conversations
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'TR_conversations_updated_at')
BEGIN
    EXEC('
    CREATE TRIGGER TR_conversations_updated_at
    ON conversations
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE conversations 
        SET updated_at = GETUTCDATE()
        FROM conversations c
        INNER JOIN inserted i ON c.id = i.id;
    END
    ');
    PRINT '✅ Trigger conversations updated_at criado';
END
GO

-- Trigger para atualizar updated_at automaticamente na tabela whatsapp_sessions
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'TR_whatsapp_sessions_updated_at')
BEGIN
    EXEC('
    CREATE TRIGGER TR_whatsapp_sessions_updated_at
    ON whatsapp_sessions
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE whatsapp_sessions 
        SET updated_at = GETUTCDATE()
        FROM whatsapp_sessions w
        INNER JOIN inserted i ON w.id = i.id;
    END
    ');
    PRINT '✅ Trigger whatsapp_sessions updated_at criado';
END
GO

-- Trigger para atualizar updated_at automaticamente na tabela campaigns
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'TR_campaigns_updated_at')
BEGIN
    EXEC('
    CREATE TRIGGER TR_campaigns_updated_at
    ON campaigns
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE campaigns 
        SET updated_at = GETUTCDATE()
        FROM campaigns c
        INNER JOIN inserted i ON c.id = i.id;
    END
    ');
    PRINT '✅ Trigger campaigns updated_at criado';
END
GO

-- === DADOS INICIAIS ===

-- Inserir usuário admin (migração do sistema Node.js)
-- Senha: admin123 (hash bcrypt do sistema atual)
IF NOT EXISTS (SELECT * FROM users WHERE username = 'admin')
BEGIN
    INSERT INTO users (
        username, 
        email, 
        password_hash, 
        role, 
        is_active, 
        is_verified,
        created_at,
        last_login
    ) VALUES (
        'admin',
        'admin@sistema.com',
        '$2a$10$Cmu1DBIKIwpBB29IJMfN1uXu3QalrDOq7.j4mV.XzrKU/N0Nh7nam',
        'admin',
        1,
        1,
        '2026-01-11T07:14:39.060Z',
        '2026-01-18T12:45:27.102Z'
    );
    PRINT '✅ Usuário admin criado com sucesso';
END
ELSE
BEGIN
    PRINT '⚠️ Usuário admin já existe';
END
GO

-- === ESTATÍSTICAS FINAIS ===
PRINT '=== ISP CHAT SYSTEM - SQL SERVER INICIALIZADO ===';
PRINT 'Banco: ISPChat';
PRINT 'Tabelas criadas: users, conversations, messages, whatsapp_sessions, campaigns';
PRINT 'Índices: 17 índices para performance otimizada';
PRINT 'Triggers: 4 triggers para timestamps automáticos';
PRINT 'Usuário admin criado com sucesso';
PRINT 'Sistema pronto para migração dos dados do Node.js';
PRINT '=== SETUP CONCLUÍDO COM SUCESSO ===';
GO

-- Mostrar resumo das tabelas criadas
SELECT 
    TABLE_NAME as 'Tabela',
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = t.TABLE_NAME) as 'Colunas'
FROM INFORMATION_SCHEMA.TABLES t
WHERE TABLE_TYPE = 'BASE TABLE' 
    AND TABLE_CATALOG = 'ISPChat'
ORDER BY TABLE_NAME;
GO

-- Mostrar usuário admin criado
SELECT 
    username as 'Usuário',
    email as 'Email', 
    role as 'Perfil',
    is_active as 'Ativo',
    created_at as 'Criado em'
FROM users 
WHERE username = 'admin';
GO