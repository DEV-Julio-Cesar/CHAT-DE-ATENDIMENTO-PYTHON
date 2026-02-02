-- =============================================================================
-- SCRIPT SQL SERVER - ISP CUSTOMER SUPPORT
-- Sistema de Chat WhatsApp para Telecomunicações
-- =============================================================================
-- Autor: Sistema
-- Data: 2026
-- Versão: 2.0.0
-- =============================================================================

USE master;
GO

-- =============================================================================
-- 1. CRIAR BANCO DE DADOS
-- =============================================================================
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'isp_support')
BEGIN
    CREATE DATABASE isp_support
    ON PRIMARY (
        NAME = 'isp_support_data',
        FILENAME = 'C:\SQLData\isp_support_data.mdf',
        SIZE = 100MB,
        MAXSIZE = UNLIMITED,
        FILEGROWTH = 100MB
    )
    LOG ON (
        NAME = 'isp_support_log',
        FILENAME = 'C:\SQLData\isp_support_log.ldf',
        SIZE = 50MB,
        MAXSIZE = 2GB,
        FILEGROWTH = 50MB
    );
    PRINT '[OK] Banco de dados isp_support criado com sucesso';
END
ELSE
BEGIN
    PRINT '[INFO] Banco de dados isp_support já existe';
END
GO

USE isp_support;
GO

-- =============================================================================
-- 2. TABELA DE USUÁRIOS (AUTENTICAÇÃO)
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='usuarios' AND xtype='U')
BEGIN
    CREATE TABLE usuarios (
        id INT IDENTITY(1,1) PRIMARY KEY,
        
        -- Identificação
        email NVARCHAR(255) NOT NULL,
        username NVARCHAR(100) NULL,
        password_hash NVARCHAR(255) NOT NULL,
        
        -- Dados pessoais
        nome NVARCHAR(255) NOT NULL,
        sobrenome NVARCHAR(255) NULL,
        telefone NVARCHAR(20) NULL,
        avatar_url NVARCHAR(500) NULL,
        
        -- Controle de acesso
        role NVARCHAR(50) NOT NULL DEFAULT 'atendente',
        permissions NVARCHAR(MAX) NULL,  -- JSON com permissões específicas
        
        -- Status
        is_active BIT NOT NULL DEFAULT 1,
        is_verified BIT NOT NULL DEFAULT 0,
        is_online BIT NOT NULL DEFAULT 0,
        
        -- Segurança
        failed_login_attempts INT NOT NULL DEFAULT 0,
        locked_until DATETIME2 NULL,
        password_changed_at DATETIME2 NULL,
        must_change_password BIT NOT NULL DEFAULT 0,
        
        -- 2FA
        two_factor_enabled BIT NOT NULL DEFAULT 0,
        two_factor_secret NVARCHAR(100) NULL,
        backup_codes NVARCHAR(MAX) NULL,  -- JSON array
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        last_login DATETIME2 NULL,
        last_activity DATETIME2 NULL,
        
        -- Soft delete
        deleted_at DATETIME2 NULL,
        deleted_by INT NULL,
        
        -- Constraints
        CONSTRAINT UQ_usuarios_email UNIQUE (email),
        CONSTRAINT UQ_usuarios_username UNIQUE (username),
        CONSTRAINT CK_usuarios_role CHECK (role IN ('admin', 'supervisor', 'atendente', 'viewer'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_usuarios_email ON usuarios(email) WHERE deleted_at IS NULL;
    CREATE NONCLUSTERED INDEX IX_usuarios_role ON usuarios(role) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_usuarios_is_online ON usuarios(is_online) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_usuarios_last_activity ON usuarios(last_activity DESC);
    
    PRINT '[OK] Tabela usuarios criada';
END
GO

-- =============================================================================
-- 3. TABELA DE SESSÕES
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_sessions' AND xtype='U')
BEGIN
    CREATE TABLE user_sessions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        session_id NVARCHAR(100) NOT NULL,
        user_id INT NOT NULL,
        
        -- Token info
        access_token_hash NVARCHAR(64) NOT NULL,
        refresh_token_hash NVARCHAR(64) NULL,
        
        -- Dispositivo/Localização
        ip_address NVARCHAR(45) NOT NULL,
        user_agent NVARCHAR(500) NULL,
        device_type NVARCHAR(50) NULL,
        device_name NVARCHAR(255) NULL,
        browser NVARCHAR(100) NULL,
        os NVARCHAR(100) NULL,
        location_country NVARCHAR(100) NULL,
        location_city NVARCHAR(100) NULL,
        
        -- Status
        is_active BIT NOT NULL DEFAULT 1,
        is_current BIT NOT NULL DEFAULT 0,
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        expires_at DATETIME2 NOT NULL,
        last_used_at DATETIME2 NULL,
        revoked_at DATETIME2 NULL,
        revoke_reason NVARCHAR(255) NULL,
        
        -- Foreign keys
        CONSTRAINT FK_sessions_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        CONSTRAINT UQ_session_id UNIQUE (session_id)
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_sessions_user ON user_sessions(user_id) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_sessions_token ON user_sessions(access_token_hash);
    CREATE NONCLUSTERED INDEX IX_sessions_expires ON user_sessions(expires_at) WHERE is_active = 1;
    
    PRINT '[OK] Tabela user_sessions criada';
END
GO

-- =============================================================================
-- 4. TABELA DE TOKENS REVOGADOS (BLACKLIST)
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='token_blacklist' AND xtype='U')
BEGIN
    CREATE TABLE token_blacklist (
        id INT IDENTITY(1,1) PRIMARY KEY,
        token_hash NVARCHAR(64) NOT NULL,
        token_type NVARCHAR(20) NOT NULL DEFAULT 'access',
        user_id INT NULL,
        
        -- Metadados
        revoked_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        revoked_by INT NULL,
        expires_at DATETIME2 NOT NULL,
        reason NVARCHAR(255) NULL,
        
        -- Constraints
        CONSTRAINT UQ_token_hash UNIQUE (token_hash),
        CONSTRAINT CK_token_type CHECK (token_type IN ('access', 'refresh', 'api_key'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_blacklist_token ON token_blacklist(token_hash);
    CREATE NONCLUSTERED INDEX IX_blacklist_expires ON token_blacklist(expires_at);
    
    PRINT '[OK] Tabela token_blacklist criada';
END
GO

-- =============================================================================
-- 5. TABELA DE LOGS DE AUDITORIA
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='audit_logs' AND xtype='U')
BEGIN
    CREATE TABLE audit_logs (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Evento
        event_type NVARCHAR(100) NOT NULL,
        action NVARCHAR(255) NOT NULL,
        severity NVARCHAR(20) NOT NULL DEFAULT 'INFO',
        
        -- Recurso
        resource_type NVARCHAR(100) NULL,
        resource_id NVARCHAR(100) NULL,
        
        -- Usuário
        user_id INT NULL,
        user_email NVARCHAR(255) NULL,
        session_id NVARCHAR(100) NULL,
        
        -- Request info
        ip_address NVARCHAR(45) NULL,
        user_agent NVARCHAR(500) NULL,
        request_method NVARCHAR(10) NULL,
        request_path NVARCHAR(500) NULL,
        request_id NVARCHAR(100) NULL,
        
        -- Dados
        old_values NVARCHAR(MAX) NULL,  -- JSON
        new_values NVARCHAR(MAX) NULL,  -- JSON
        details NVARCHAR(MAX) NULL,     -- JSON
        
        -- Resultado
        status NVARCHAR(50) NOT NULL DEFAULT 'success',
        error_message NVARCHAR(MAX) NULL,
        
        -- Integridade (blockchain-style)
        entry_hash NVARCHAR(64) NOT NULL,
        previous_hash NVARCHAR(64) NULL,
        
        -- Timestamp
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        -- Constraints
        CONSTRAINT CK_audit_severity CHECK (severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
        CONSTRAINT CK_audit_status CHECK (status IN ('success', 'failure', 'partial', 'pending'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_audit_event_type ON audit_logs(event_type);
    CREATE NONCLUSTERED INDEX IX_audit_user ON audit_logs(user_id);
    CREATE NONCLUSTERED INDEX IX_audit_created ON audit_logs(created_at DESC);
    CREATE NONCLUSTERED INDEX IX_audit_resource ON audit_logs(resource_type, resource_id);
    CREATE NONCLUSTERED INDEX IX_audit_request_id ON audit_logs(request_id);
    
    PRINT '[OK] Tabela audit_logs criada';
END
GO

-- =============================================================================
-- 6. TABELA DE CONSENTIMENTOS (LGPD/GDPR)
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_consents' AND xtype='U')
BEGIN
    CREATE TABLE user_consents (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        
        -- Tipo de consentimento
        consent_type NVARCHAR(50) NOT NULL,
        consent_version NVARCHAR(20) NOT NULL DEFAULT '1.0',
        
        -- Status
        granted BIT NOT NULL DEFAULT 0,
        
        -- Timestamps
        granted_at DATETIME2 NULL,
        revoked_at DATETIME2 NULL,
        expires_at DATETIME2 NULL,
        
        -- Metadados
        ip_address NVARCHAR(45) NULL,
        user_agent NVARCHAR(500) NULL,
        consent_text NVARCHAR(MAX) NULL,
        
        -- Foreign keys
        CONSTRAINT FK_consent_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        
        -- Constraints
        CONSTRAINT CK_consent_type CHECK (consent_type IN (
            'terms_of_service',
            'privacy_policy',
            'marketing',
            'data_processing',
            'third_party_sharing',
            'cookies',
            'analytics'
        ))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_consent_user ON user_consents(user_id);
    CREATE NONCLUSTERED INDEX IX_consent_type ON user_consents(consent_type, granted);
    
    -- Unique constraint para evitar duplicatas
    CREATE UNIQUE NONCLUSTERED INDEX IX_consent_unique 
    ON user_consents(user_id, consent_type) WHERE revoked_at IS NULL;
    
    PRINT '[OK] Tabela user_consents criada';
END
GO

-- =============================================================================
-- 7. TABELA DE API KEYS
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='api_keys' AND xtype='U')
BEGIN
    CREATE TABLE api_keys (
        id INT IDENTITY(1,1) PRIMARY KEY,
        key_hash NVARCHAR(64) NOT NULL,
        key_prefix NVARCHAR(10) NOT NULL,  -- Para identificação (ex: "isp_live_")
        
        -- Proprietário
        user_id INT NULL,
        name NVARCHAR(255) NOT NULL,
        description NVARCHAR(500) NULL,
        
        -- Permissões
        scopes NVARCHAR(MAX) NULL,  -- JSON array de escopos permitidos
        
        -- Rate limiting
        rate_limit_per_minute INT NOT NULL DEFAULT 60,
        rate_limit_per_day INT NOT NULL DEFAULT 10000,
        
        -- Status
        is_active BIT NOT NULL DEFAULT 1,
        
        -- Uso
        last_used_at DATETIME2 NULL,
        last_used_ip NVARCHAR(45) NULL,
        total_requests BIGINT NOT NULL DEFAULT 0,
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        expires_at DATETIME2 NULL,
        revoked_at DATETIME2 NULL,
        revoked_by INT NULL,
        revoke_reason NVARCHAR(255) NULL,
        
        -- Constraints
        CONSTRAINT UQ_api_key_hash UNIQUE (key_hash),
        CONSTRAINT FK_apikey_user FOREIGN KEY (user_id) REFERENCES usuarios(id)
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_apikey_hash ON api_keys(key_hash) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_apikey_user ON api_keys(user_id);
    CREATE NONCLUSTERED INDEX IX_apikey_prefix ON api_keys(key_prefix);
    
    PRINT '[OK] Tabela api_keys criada';
END
GO

-- =============================================================================
-- 8. TABELA DE RATE LIMITING
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rate_limit_records' AND xtype='U')
BEGIN
    CREATE TABLE rate_limit_records (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Identificação
        identifier NVARCHAR(255) NOT NULL,
        identifier_type NVARCHAR(50) NOT NULL,  -- ip, user_id, api_key
        
        -- Dados
        request_count INT NOT NULL DEFAULT 1,
        window_start DATETIME2 NOT NULL,
        window_end DATETIME2 NOT NULL,
        
        -- Metadados
        endpoint NVARCHAR(255) NULL,
        
        -- Constraints
        CONSTRAINT CK_identifier_type CHECK (identifier_type IN ('ip', 'user_id', 'api_key', 'phone'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_ratelimit_lookup 
    ON rate_limit_records(identifier, identifier_type, window_start);
    
    CREATE NONCLUSTERED INDEX IX_ratelimit_cleanup 
    ON rate_limit_records(window_end);
    
    PRINT '[OK] Tabela rate_limit_records criada';
END
GO

-- =============================================================================
-- 9. TABELA DE CONFIGURAÇÕES DO SISTEMA
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='system_config' AND xtype='U')
BEGIN
    CREATE TABLE system_config (
        id INT IDENTITY(1,1) PRIMARY KEY,
        config_key NVARCHAR(100) NOT NULL,
        config_value NVARCHAR(MAX) NOT NULL,
        value_type NVARCHAR(20) NOT NULL DEFAULT 'string',
        
        -- Metadados
        category NVARCHAR(50) NULL,
        description NVARCHAR(500) NULL,
        is_sensitive BIT NOT NULL DEFAULT 0,
        is_editable BIT NOT NULL DEFAULT 1,
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_by INT NULL,
        
        -- Constraints
        CONSTRAINT UQ_config_key UNIQUE (config_key),
        CONSTRAINT CK_value_type CHECK (value_type IN ('string', 'int', 'float', 'bool', 'json'))
    );
    
    PRINT '[OK] Tabela system_config criada';
END
GO

-- =============================================================================
-- 10. TABELA DE CLIENTES WHATSAPP
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='whatsapp_clients' AND xtype='U')
BEGIN
    CREATE TABLE whatsapp_clients (
        id INT IDENTITY(1,1) PRIMARY KEY,
        
        -- Identificação WhatsApp
        wa_id NVARCHAR(20) NOT NULL,           -- Número formatado WhatsApp
        phone_number NVARCHAR(20) NOT NULL,    -- Número original
        profile_name NVARCHAR(255) NULL,
        
        -- Dados do cliente
        customer_code NVARCHAR(50) NULL,       -- Código no sistema de billing
        name NVARCHAR(255) NULL,
        email NVARCHAR(255) NULL,
        cpf_cnpj NVARCHAR(20) NULL,
        
        -- Plano/Serviço
        plan_name NVARCHAR(100) NULL,
        plan_value DECIMAL(10,2) NULL,
        due_date INT NULL,                     -- Dia do vencimento
        
        -- Status
        status NVARCHAR(50) NOT NULL DEFAULT 'active',
        opt_in_marketing BIT NOT NULL DEFAULT 0,
        opt_in_notifications BIT NOT NULL DEFAULT 1,
        
        -- Sessão atual
        current_session_id NVARCHAR(100) NULL,
        session_state NVARCHAR(50) NULL,
        last_message_at DATETIME2 NULL,
        
        -- Atendimento
        assigned_agent_id INT NULL,
        queue_position INT NULL,
        
        -- Timestamps
        first_contact_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        -- Constraints
        CONSTRAINT UQ_wa_id UNIQUE (wa_id),
        CONSTRAINT FK_client_agent FOREIGN KEY (assigned_agent_id) REFERENCES usuarios(id),
        CONSTRAINT CK_client_status CHECK (status IN ('active', 'inactive', 'blocked', 'pending'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_waclient_phone ON whatsapp_clients(phone_number);
    CREATE NONCLUSTERED INDEX IX_waclient_customer ON whatsapp_clients(customer_code);
    CREATE NONCLUSTERED INDEX IX_waclient_session ON whatsapp_clients(current_session_id) WHERE current_session_id IS NOT NULL;
    CREATE NONCLUSTERED INDEX IX_waclient_agent ON whatsapp_clients(assigned_agent_id) WHERE assigned_agent_id IS NOT NULL;
    
    PRINT '[OK] Tabela whatsapp_clients criada';
END
GO

-- =============================================================================
-- 11. TABELA DE CONVERSAS
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversations' AND xtype='U')
BEGIN
    CREATE TABLE conversations (
        id INT IDENTITY(1,1) PRIMARY KEY,
        conversation_id NVARCHAR(100) NOT NULL,
        
        -- Participantes
        client_id INT NOT NULL,
        agent_id INT NULL,
        
        -- Estado
        state NVARCHAR(50) NOT NULL DEFAULT 'bot',
        priority NVARCHAR(20) NOT NULL DEFAULT 'normal',
        
        -- Categorização
        category NVARCHAR(100) NULL,
        subcategory NVARCHAR(100) NULL,
        tags NVARCHAR(MAX) NULL,  -- JSON array
        
        -- Métricas
        message_count INT NOT NULL DEFAULT 0,
        bot_message_count INT NOT NULL DEFAULT 0,
        human_message_count INT NOT NULL DEFAULT 0,
        
        -- Tempos
        first_response_time INT NULL,  -- segundos
        resolution_time INT NULL,      -- segundos
        wait_time INT NULL,            -- segundos em fila
        
        -- Satisfação
        satisfaction_score INT NULL,   -- 1-5
        satisfaction_comment NVARCHAR(500) NULL,
        
        -- Timestamps
        started_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        assigned_at DATETIME2 NULL,
        resolved_at DATETIME2 NULL,
        closed_at DATETIME2 NULL,
        last_message_at DATETIME2 NULL,
        
        -- Constraints
        CONSTRAINT UQ_conversation_id UNIQUE (conversation_id),
        CONSTRAINT FK_conv_client FOREIGN KEY (client_id) REFERENCES whatsapp_clients(id),
        CONSTRAINT FK_conv_agent FOREIGN KEY (agent_id) REFERENCES usuarios(id),
        CONSTRAINT CK_conv_state CHECK (state IN ('bot', 'queue', 'human', 'resolved', 'closed')),
        CONSTRAINT CK_conv_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_conv_state ON conversations(state) WHERE closed_at IS NULL;
    CREATE NONCLUSTERED INDEX IX_conv_agent ON conversations(agent_id) WHERE agent_id IS NOT NULL;
    CREATE NONCLUSTERED INDEX IX_conv_client ON conversations(client_id);
    CREATE NONCLUSTERED INDEX IX_conv_started ON conversations(started_at DESC);
    
    PRINT '[OK] Tabela conversations criada';
END
GO

-- =============================================================================
-- 12. TABELA DE MENSAGENS
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='messages' AND xtype='U')
BEGIN
    CREATE TABLE messages (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        message_id NVARCHAR(100) NOT NULL,
        
        -- Relacionamentos
        conversation_id INT NOT NULL,
        
        -- Direção
        direction NVARCHAR(10) NOT NULL,  -- 'inbound' ou 'outbound'
        sender_type NVARCHAR(20) NOT NULL,  -- 'client', 'agent', 'bot', 'system'
        sender_id INT NULL,
        
        -- Conteúdo
        message_type NVARCHAR(30) NOT NULL DEFAULT 'text',
        content NVARCHAR(MAX) NULL,
        media_url NVARCHAR(500) NULL,
        media_type NVARCHAR(100) NULL,
        media_id NVARCHAR(100) NULL,
        
        -- Template (se aplicável)
        template_name NVARCHAR(100) NULL,
        template_params NVARCHAR(MAX) NULL,  -- JSON
        
        -- Status de entrega
        status NVARCHAR(30) NOT NULL DEFAULT 'pending',
        error_code NVARCHAR(50) NULL,
        error_message NVARCHAR(500) NULL,
        
        -- Timestamps WhatsApp
        wa_timestamp DATETIME2 NULL,
        sent_at DATETIME2 NULL,
        delivered_at DATETIME2 NULL,
        read_at DATETIME2 NULL,
        
        -- Metadados
        metadata NVARCHAR(MAX) NULL,  -- JSON
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        -- Constraints
        CONSTRAINT UQ_message_id UNIQUE (message_id),
        CONSTRAINT FK_msg_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        CONSTRAINT CK_msg_direction CHECK (direction IN ('inbound', 'outbound')),
        CONSTRAINT CK_msg_sender_type CHECK (sender_type IN ('client', 'agent', 'bot', 'system')),
        CONSTRAINT CK_msg_type CHECK (message_type IN ('text', 'image', 'document', 'audio', 'video', 'location', 'contacts', 'sticker', 'template', 'interactive', 'reaction')),
        CONSTRAINT CK_msg_status CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_msg_conv ON messages(conversation_id);
    CREATE NONCLUSTERED INDEX IX_msg_created ON messages(created_at DESC);
    CREATE NONCLUSTERED INDEX IX_msg_status ON messages(status) WHERE status IN ('pending', 'sent');
    
    PRINT '[OK] Tabela messages criada';
END
GO

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Trigger para atualizar updated_at automaticamente
CREATE OR ALTER TRIGGER TR_usuarios_updated
ON usuarios
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE usuarios
    SET updated_at = GETDATE()
    FROM usuarios u
    INNER JOIN inserted i ON u.id = i.id;
END
GO

CREATE OR ALTER TRIGGER TR_whatsapp_clients_updated
ON whatsapp_clients
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE whatsapp_clients
    SET updated_at = GETDATE()
    FROM whatsapp_clients w
    INNER JOIN inserted i ON w.id = i.id;
END
GO

PRINT '[OK] Triggers criados';
GO

-- =============================================================================
-- STORED PROCEDURES
-- =============================================================================

-- Procedure para autenticar usuário
CREATE OR ALTER PROCEDURE sp_authenticate_user
    @email NVARCHAR(255),
    @ip_address NVARCHAR(45) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @user_id INT;
    DECLARE @is_locked BIT = 0;
    DECLARE @locked_until DATETIME2;
    
    -- Buscar usuário
    SELECT 
        @user_id = id,
        @locked_until = locked_until
    FROM usuarios 
    WHERE email = @email AND is_active = 1 AND deleted_at IS NULL;
    
    -- Verificar se existe
    IF @user_id IS NULL
    BEGIN
        -- Log tentativa com email inválido
        INSERT INTO audit_logs (event_type, action, ip_address, status, entry_hash, details)
        VALUES ('AUTH', 'login_attempt', @ip_address, 'failure', 
                CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), @email)), 2),
                '{"reason": "user_not_found"}');
        
        SELECT 0 AS success, 'Invalid credentials' AS message;
        RETURN;
    END
    
    -- Verificar se está bloqueado
    IF @locked_until IS NOT NULL AND @locked_until > GETDATE()
    BEGIN
        SELECT 0 AS success, 'Account temporarily locked' AS message, @locked_until AS locked_until;
        RETURN;
    END
    
    -- Retornar dados do usuário para validação de senha
    SELECT 
        1 AS success,
        id,
        email,
        password_hash,
        nome,
        role,
        two_factor_enabled,
        failed_login_attempts
    FROM usuarios
    WHERE id = @user_id;
END
GO

-- Procedure para registrar login bem-sucedido
CREATE OR ALTER PROCEDURE sp_login_success
    @user_id INT,
    @session_id NVARCHAR(100),
    @access_token_hash NVARCHAR(64),
    @ip_address NVARCHAR(45),
    @user_agent NVARCHAR(500),
    @expires_at DATETIME2
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Atualizar usuário
    UPDATE usuarios
    SET 
        last_login = GETDATE(),
        last_activity = GETDATE(),
        is_online = 1,
        failed_login_attempts = 0,
        locked_until = NULL
    WHERE id = @user_id;
    
    -- Criar sessão
    INSERT INTO user_sessions (
        session_id, user_id, access_token_hash, 
        ip_address, user_agent, is_active, is_current,
        created_at, expires_at
    )
    VALUES (
        @session_id, @user_id, @access_token_hash,
        @ip_address, @user_agent, 1, 1,
        GETDATE(), @expires_at
    );
    
    -- Marcar outras sessões como não atuais
    UPDATE user_sessions
    SET is_current = 0
    WHERE user_id = @user_id AND session_id != @session_id;
    
    -- Log de auditoria
    INSERT INTO audit_logs (
        event_type, action, user_id, ip_address, user_agent, 
        status, entry_hash, details
    )
    VALUES (
        'AUTH', 'login', @user_id, @ip_address, @user_agent,
        'success', 
        CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), @user_id)), 2),
        CONCAT('{"session_id": "', @session_id, '"}')
    );
    
    SELECT 1 AS success;
END
GO

-- Procedure para registrar falha de login
CREATE OR ALTER PROCEDURE sp_login_failure
    @email NVARCHAR(255),
    @ip_address NVARCHAR(45),
    @reason NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @user_id INT;
    DECLARE @attempts INT;
    DECLARE @max_attempts INT = 5;
    DECLARE @lockout_minutes INT = 15;
    
    -- Buscar usuário
    SELECT @user_id = id, @attempts = failed_login_attempts
    FROM usuarios
    WHERE email = @email;
    
    IF @user_id IS NOT NULL
    BEGIN
        SET @attempts = @attempts + 1;
        
        -- Atualizar tentativas
        UPDATE usuarios
        SET 
            failed_login_attempts = @attempts,
            locked_until = CASE 
                WHEN @attempts >= @max_attempts 
                THEN DATEADD(MINUTE, @lockout_minutes, GETDATE())
                ELSE locked_until
            END
        WHERE id = @user_id;
    END
    
    -- Log de auditoria
    INSERT INTO audit_logs (
        event_type, action, user_id, ip_address,
        status, entry_hash, details
    )
    VALUES (
        'AUTH', 'login_attempt', @user_id, @ip_address,
        'failure',
        CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), @email)), 2),
        CONCAT('{"reason": "', @reason, '", "attempts": ', ISNULL(@attempts, 0), '}')
    );
    
    SELECT @attempts AS failed_attempts, @max_attempts AS max_attempts;
END
GO

-- Procedure para logout
CREATE OR ALTER PROCEDURE sp_logout
    @user_id INT,
    @session_id NVARCHAR(100),
    @token_hash NVARCHAR(64)
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Revogar sessão
    UPDATE user_sessions
    SET 
        is_active = 0,
        revoked_at = GETDATE(),
        revoke_reason = 'logout'
    WHERE user_id = @user_id AND session_id = @session_id;
    
    -- Adicionar token à blacklist
    INSERT INTO token_blacklist (token_hash, user_id, expires_at, reason)
    SELECT @token_hash, @user_id, expires_at, 'logout'
    FROM user_sessions
    WHERE session_id = @session_id;
    
    -- Atualizar status online se não há mais sessões ativas
    IF NOT EXISTS (SELECT 1 FROM user_sessions WHERE user_id = @user_id AND is_active = 1)
    BEGIN
        UPDATE usuarios SET is_online = 0 WHERE id = @user_id;
    END
    
    -- Log
    INSERT INTO audit_logs (event_type, action, user_id, status, entry_hash)
    VALUES ('AUTH', 'logout', @user_id, 'success',
            CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), @user_id)), 2));
    
    SELECT 1 AS success;
END
GO

-- Procedure para limpar tokens expirados
CREATE OR ALTER PROCEDURE sp_cleanup_expired_tokens
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @deleted_sessions INT;
    DECLARE @deleted_tokens INT;
    DECLARE @deleted_ratelimits INT;
    
    -- Limpar sessões expiradas
    DELETE FROM user_sessions
    WHERE expires_at < GETDATE() OR (is_active = 0 AND revoked_at < DATEADD(DAY, -7, GETDATE()));
    SET @deleted_sessions = @@ROWCOUNT;
    
    -- Limpar tokens da blacklist expirados
    DELETE FROM token_blacklist
    WHERE expires_at < DATEADD(DAY, -1, GETDATE());
    SET @deleted_tokens = @@ROWCOUNT;
    
    -- Limpar registros de rate limit antigos
    DELETE FROM rate_limit_records
    WHERE window_end < DATEADD(HOUR, -1, GETDATE());
    SET @deleted_ratelimits = @@ROWCOUNT;
    
    -- Log
    INSERT INTO audit_logs (event_type, action, status, entry_hash, details)
    VALUES ('SYSTEM', 'cleanup', 'success',
            CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), 'cleanup')), 2),
            CONCAT('{"sessions": ', @deleted_sessions, ', "tokens": ', @deleted_tokens, ', "ratelimits": ', @deleted_ratelimits, '}'));
    
    SELECT @deleted_sessions AS sessions_deleted, 
           @deleted_tokens AS tokens_deleted,
           @deleted_ratelimits AS ratelimits_deleted;
END
GO

PRINT '[OK] Stored Procedures criados';
GO

-- =============================================================================
-- DADOS INICIAIS
-- =============================================================================

-- Inserir configurações do sistema
IF NOT EXISTS (SELECT 1 FROM system_config WHERE config_key = 'max_whatsapp_clients')
BEGIN
    INSERT INTO system_config (config_key, config_value, value_type, category, description)
    VALUES 
        ('max_whatsapp_clients', '10000', 'int', 'whatsapp', 'Máximo de clientes WhatsApp simultâneos'),
        ('max_bot_attempts', '3', 'int', 'chatbot', 'Tentativas do bot antes de escalar'),
        ('business_hours_start', '8', 'int', 'schedule', 'Hora de início do atendimento'),
        ('business_hours_end', '18', 'int', 'schedule', 'Hora de fim do atendimento'),
        ('rate_limit_per_minute', '100', 'int', 'security', 'Limite de requests por minuto'),
        ('session_timeout_minutes', '1440', 'int', 'security', 'Timeout de sessão (minutos)'),
        ('whatsapp_session_hours', '24', 'int', 'whatsapp', 'Duração da sessão WhatsApp (horas)'),
        ('max_queue_size', '100', 'int', 'queue', 'Tamanho máximo da fila de espera');
    
    PRINT '[OK] Configurações iniciais inseridas';
END
GO

-- Inserir usuário admin padrão (senha: Admin@123)
IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'admin@sistema.local')
BEGIN
    INSERT INTO usuarios (
        email, username, password_hash, nome, role, 
        is_active, is_verified, created_at
    )
    VALUES (
        'admin@sistema.local',
        'admin',
        -- Hash bcrypt de 'Admin@123'
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.',
        'Administrador',
        'admin',
        1, 1, GETDATE()
    );
    
    PRINT '[OK] Usuário admin criado (email: admin@sistema.local, senha: Admin@123)';
END
GO

-- =============================================================================
-- JOBS DE MANUTENÇÃO (SQL Server Agent)
-- =============================================================================

-- Nota: Execute estes comandos se tiver SQL Server Agent disponível
/*
-- Job para limpeza de tokens expirados (executa a cada hora)
USE msdb;
GO

EXEC sp_add_job 
    @job_name = N'ISP_Cleanup_Expired_Tokens',
    @enabled = 1,
    @description = N'Limpa tokens e sessões expirados';
GO

EXEC sp_add_jobstep
    @job_name = N'ISP_Cleanup_Expired_Tokens',
    @step_name = N'Execute Cleanup',
    @subsystem = N'TSQL',
    @command = N'EXEC isp_support.dbo.sp_cleanup_expired_tokens',
    @database_name = N'isp_support';
GO

EXEC sp_add_schedule
    @schedule_name = N'Hourly',
    @freq_type = 4,
    @freq_interval = 1,
    @freq_subday_type = 8,
    @freq_subday_interval = 1;
GO

EXEC sp_attach_schedule
    @job_name = N'ISP_Cleanup_Expired_Tokens',
    @schedule_name = N'Hourly';
GO

EXEC sp_add_jobserver
    @job_name = N'ISP_Cleanup_Expired_Tokens';
GO
*/

PRINT '';
PRINT '=============================================================================';
PRINT ' SETUP SQL SERVER CONCLUÍDO COM SUCESSO!';
PRINT '=============================================================================';
PRINT '';
PRINT ' Tabelas criadas:';
PRINT '   - usuarios';
PRINT '   - user_sessions';
PRINT '   - token_blacklist';
PRINT '   - audit_logs';
PRINT '   - user_consents';
PRINT '   - api_keys';
PRINT '   - rate_limit_records';
PRINT '   - system_config';
PRINT '   - whatsapp_clients';
PRINT '   - conversations';
PRINT '   - messages';
PRINT '';
PRINT ' Stored Procedures:';
PRINT '   - sp_authenticate_user';
PRINT '   - sp_login_success';
PRINT '   - sp_login_failure';
PRINT '   - sp_logout';
PRINT '   - sp_cleanup_expired_tokens';
PRINT '';
PRINT ' Usuário admin padrão:';
PRINT '   Email: admin@sistema.local';
PRINT '   Senha: Admin@123';
PRINT '';
PRINT '=============================================================================';
GO
