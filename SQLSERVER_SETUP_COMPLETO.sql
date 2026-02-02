-- =============================================================================
-- SCRIPT COMPLETO SQL SERVER - ISP CUSTOMER SUPPORT
-- Sistema de Chat WhatsApp para Telecomunicações
-- =============================================================================
-- Autor: Sistema
-- Data: 2026
-- Versão: 2.0.0
-- =============================================================================
-- 
-- INSTRUÇÕES DE USO:
-- 1. Abra o SQL Server Management Studio (SSMS)
-- 2. Conecte ao servidor SQL Server
-- 3. Execute este script completo (F5)
-- 4. Verifique as mensagens de saída para confirmar sucesso
--
-- REQUISITOS:
-- - SQL Server 2016 ou superior
-- - Permissões de sysadmin ou db_creator
-- - Pasta C:\SQLData deve existir (ou altere os paths abaixo)
--
-- =============================================================================

USE master;
GO

-- =============================================================================
-- 1. CRIAR BANCO DE DADOS
-- =============================================================================
PRINT '=============================================================================';
PRINT ' INICIANDO SETUP DO BANCO DE DADOS ISP_SUPPORT';
PRINT '=============================================================================';
PRINT '';

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'isp_support')
BEGIN
    -- Verificar se pasta existe, senão usar path padrão
    DECLARE @dataPath NVARCHAR(500) = 'C:\SQLData\';
    
    -- Se C:\SQLData não existir, usar pasta padrão do SQL Server
    IF NOT EXISTS (SELECT 1 FROM sys.dm_os_file_exists(@dataPath + 'test.txt') WHERE file_exists = 1)
    BEGIN
        SELECT @dataPath = CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS NVARCHAR(500));
    END
    
    EXEC('
    CREATE DATABASE isp_support
    ON PRIMARY (
        NAME = ''isp_support_data'',
        FILENAME = ''' + @dataPath + 'isp_support_data.mdf'',
        SIZE = 100MB,
        MAXSIZE = UNLIMITED,
        FILEGROWTH = 100MB
    )
    LOG ON (
        NAME = ''isp_support_log'',
        FILENAME = ''' + @dataPath + 'isp_support_log.ldf'',
        SIZE = 50MB,
        MAXSIZE = 2GB,
        FILEGROWTH = 50MB
    )');
    
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
        permissions NVARCHAR(MAX) NULL,
        
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
        backup_codes NVARCHAR(MAX) NULL,
        
        -- Métricas de atendente
        avg_response_time INT NULL,
        total_conversations INT NOT NULL DEFAULT 0,
        avg_satisfaction DECIMAL(3,2) NULL,
        current_conversations INT NOT NULL DEFAULT 0,
        max_concurrent_conversations INT NOT NULL DEFAULT 5,
        
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
    
    CREATE NONCLUSTERED INDEX IX_usuarios_email ON usuarios(email) WHERE deleted_at IS NULL;
    CREATE NONCLUSTERED INDEX IX_usuarios_role ON usuarios(role) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_usuarios_is_online ON usuarios(is_online) WHERE is_active = 1;
    
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
        
        access_token_hash NVARCHAR(64) NOT NULL,
        refresh_token_hash NVARCHAR(64) NULL,
        
        ip_address NVARCHAR(45) NOT NULL,
        user_agent NVARCHAR(500) NULL,
        device_type NVARCHAR(50) NULL,
        device_name NVARCHAR(255) NULL,
        browser NVARCHAR(100) NULL,
        os NVARCHAR(100) NULL,
        location_country NVARCHAR(100) NULL,
        location_city NVARCHAR(100) NULL,
        
        is_active BIT NOT NULL DEFAULT 1,
        is_current BIT NOT NULL DEFAULT 0,
        
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        expires_at DATETIME2 NOT NULL,
        last_used_at DATETIME2 NULL,
        revoked_at DATETIME2 NULL,
        revoke_reason NVARCHAR(255) NULL,
        
        CONSTRAINT FK_sessions_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        CONSTRAINT UQ_session_id UNIQUE (session_id)
    );
    
    CREATE NONCLUSTERED INDEX IX_sessions_user ON user_sessions(user_id) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_sessions_token ON user_sessions(access_token_hash);
    
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
        
        revoked_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        revoked_by INT NULL,
        expires_at DATETIME2 NOT NULL,
        reason NVARCHAR(255) NULL,
        
        CONSTRAINT UQ_token_hash UNIQUE (token_hash),
        CONSTRAINT CK_token_type CHECK (token_type IN ('access', 'refresh', 'api_key'))
    );
    
    CREATE NONCLUSTERED INDEX IX_blacklist_token ON token_blacklist(token_hash);
    
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
        
        event_type NVARCHAR(100) NOT NULL,
        action NVARCHAR(255) NOT NULL,
        severity NVARCHAR(20) NOT NULL DEFAULT 'INFO',
        
        resource_type NVARCHAR(100) NULL,
        resource_id NVARCHAR(100) NULL,
        
        user_id INT NULL,
        user_email NVARCHAR(255) NULL,
        session_id NVARCHAR(100) NULL,
        
        ip_address NVARCHAR(45) NULL,
        user_agent NVARCHAR(500) NULL,
        request_method NVARCHAR(10) NULL,
        request_path NVARCHAR(500) NULL,
        request_id NVARCHAR(100) NULL,
        
        old_values NVARCHAR(MAX) NULL,
        new_values NVARCHAR(MAX) NULL,
        details NVARCHAR(MAX) NULL,
        
        status NVARCHAR(50) NOT NULL DEFAULT 'success',
        error_message NVARCHAR(MAX) NULL,
        
        entry_hash NVARCHAR(64) NOT NULL,
        previous_hash NVARCHAR(64) NULL,
        
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT CK_audit_severity CHECK (severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
        CONSTRAINT CK_audit_status CHECK (status IN ('success', 'failure', 'partial', 'pending'))
    );
    
    CREATE NONCLUSTERED INDEX IX_audit_event_type ON audit_logs(event_type);
    CREATE NONCLUSTERED INDEX IX_audit_user ON audit_logs(user_id);
    CREATE NONCLUSTERED INDEX IX_audit_created ON audit_logs(created_at DESC);
    
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
        
        consent_type NVARCHAR(50) NOT NULL,
        consent_version NVARCHAR(20) NOT NULL DEFAULT '1.0',
        
        granted BIT NOT NULL DEFAULT 0,
        
        granted_at DATETIME2 NULL,
        revoked_at DATETIME2 NULL,
        expires_at DATETIME2 NULL,
        
        ip_address NVARCHAR(45) NULL,
        user_agent NVARCHAR(500) NULL,
        consent_text NVARCHAR(MAX) NULL,
        
        CONSTRAINT FK_consent_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        CONSTRAINT CK_consent_type CHECK (consent_type IN (
            'terms_of_service', 'privacy_policy', 'marketing',
            'data_processing', 'third_party_sharing', 'cookies', 'analytics'
        ))
    );
    
    CREATE NONCLUSTERED INDEX IX_consent_user ON user_consents(user_id);
    
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
        key_prefix NVARCHAR(10) NOT NULL,
        
        user_id INT NULL,
        name NVARCHAR(255) NOT NULL,
        description NVARCHAR(500) NULL,
        
        scopes NVARCHAR(MAX) NULL,
        
        rate_limit_per_minute INT NOT NULL DEFAULT 60,
        rate_limit_per_day INT NOT NULL DEFAULT 10000,
        
        is_active BIT NOT NULL DEFAULT 1,
        
        last_used_at DATETIME2 NULL,
        last_used_ip NVARCHAR(45) NULL,
        total_requests BIGINT NOT NULL DEFAULT 0,
        
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        expires_at DATETIME2 NULL,
        revoked_at DATETIME2 NULL,
        
        CONSTRAINT UQ_api_key_hash UNIQUE (key_hash),
        CONSTRAINT FK_apikey_user FOREIGN KEY (user_id) REFERENCES usuarios(id)
    );
    
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
        
        identifier NVARCHAR(255) NOT NULL,
        identifier_type NVARCHAR(50) NOT NULL,
        
        request_count INT NOT NULL DEFAULT 1,
        window_start DATETIME2 NOT NULL,
        window_end DATETIME2 NOT NULL,
        
        endpoint NVARCHAR(255) NULL,
        
        CONSTRAINT CK_identifier_type CHECK (identifier_type IN ('ip', 'user_id', 'api_key', 'phone'))
    );
    
    CREATE NONCLUSTERED INDEX IX_ratelimit_lookup 
    ON rate_limit_records(identifier, identifier_type, window_start);
    
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
        
        category NVARCHAR(50) NULL,
        description NVARCHAR(500) NULL,
        is_sensitive BIT NOT NULL DEFAULT 0,
        is_editable BIT NOT NULL DEFAULT 1,
        
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_by INT NULL,
        
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
        
        wa_id NVARCHAR(20) NOT NULL,
        phone_number NVARCHAR(20) NOT NULL,
        profile_name NVARCHAR(255) NULL,
        
        customer_code NVARCHAR(50) NULL,
        name NVARCHAR(255) NULL,
        email NVARCHAR(255) NULL,
        cpf_cnpj NVARCHAR(20) NULL,
        
        plan_name NVARCHAR(100) NULL,
        plan_value DECIMAL(10,2) NULL,
        due_date INT NULL,
        
        status NVARCHAR(50) NOT NULL DEFAULT 'active',
        opt_in_marketing BIT NOT NULL DEFAULT 0,
        opt_in_notifications BIT NOT NULL DEFAULT 1,
        
        current_session_id NVARCHAR(100) NULL,
        session_state NVARCHAR(50) NULL,
        last_message_at DATETIME2 NULL,
        
        assigned_agent_id INT NULL,
        queue_position INT NULL,
        
        first_contact_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT UQ_wa_id UNIQUE (wa_id),
        CONSTRAINT FK_client_agent FOREIGN KEY (assigned_agent_id) REFERENCES usuarios(id),
        CONSTRAINT CK_client_status CHECK (status IN ('active', 'inactive', 'blocked', 'pending'))
    );
    
    CREATE NONCLUSTERED INDEX IX_waclient_phone ON whatsapp_clients(phone_number);
    CREATE NONCLUSTERED INDEX IX_waclient_customer ON whatsapp_clients(customer_code);
    
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
        
        client_id INT NOT NULL,
        agent_id INT NULL,
        
        state NVARCHAR(50) NOT NULL DEFAULT 'bot',
        priority NVARCHAR(20) NOT NULL DEFAULT 'normal',
        
        category NVARCHAR(100) NULL,
        subcategory NVARCHAR(100) NULL,
        tags NVARCHAR(MAX) NULL,
        
        message_count INT NOT NULL DEFAULT 0,
        bot_message_count INT NOT NULL DEFAULT 0,
        human_message_count INT NOT NULL DEFAULT 0,
        
        first_response_time INT NULL,
        resolution_time INT NULL,
        wait_time INT NULL,
        
        satisfaction_score INT NULL,
        satisfaction_comment NVARCHAR(500) NULL,
        
        started_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        assigned_at DATETIME2 NULL,
        resolved_at DATETIME2 NULL,
        closed_at DATETIME2 NULL,
        last_message_at DATETIME2 NULL,
        
        CONSTRAINT UQ_conversation_id UNIQUE (conversation_id),
        CONSTRAINT FK_conv_client FOREIGN KEY (client_id) REFERENCES whatsapp_clients(id),
        CONSTRAINT FK_conv_agent FOREIGN KEY (agent_id) REFERENCES usuarios(id),
        CONSTRAINT CK_conv_state CHECK (state IN ('bot', 'queue', 'human', 'resolved', 'closed')),
        CONSTRAINT CK_conv_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
    );
    
    CREATE NONCLUSTERED INDEX IX_conv_state ON conversations(state) WHERE closed_at IS NULL;
    CREATE NONCLUSTERED INDEX IX_conv_agent ON conversations(agent_id) WHERE agent_id IS NOT NULL;
    
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
        
        conversation_id INT NOT NULL,
        
        direction NVARCHAR(10) NOT NULL,
        sender_type NVARCHAR(20) NOT NULL,
        sender_id INT NULL,
        
        message_type NVARCHAR(30) NOT NULL DEFAULT 'text',
        content NVARCHAR(MAX) NULL,
        media_url NVARCHAR(500) NULL,
        media_type NVARCHAR(100) NULL,
        media_id NVARCHAR(100) NULL,
        
        template_name NVARCHAR(100) NULL,
        template_params NVARCHAR(MAX) NULL,
        
        status NVARCHAR(30) NOT NULL DEFAULT 'pending',
        error_code NVARCHAR(50) NULL,
        error_message NVARCHAR(500) NULL,
        
        wa_timestamp DATETIME2 NULL,
        sent_at DATETIME2 NULL,
        delivered_at DATETIME2 NULL,
        read_at DATETIME2 NULL,
        
        metadata NVARCHAR(MAX) NULL,
        
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT UQ_message_id UNIQUE (message_id),
        CONSTRAINT FK_msg_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        CONSTRAINT CK_msg_direction CHECK (direction IN ('inbound', 'outbound')),
        CONSTRAINT CK_msg_sender_type CHECK (sender_type IN ('client', 'agent', 'bot', 'system')),
        CONSTRAINT CK_msg_type CHECK (message_type IN ('text', 'image', 'document', 'audio', 'video', 'location', 'contacts', 'sticker', 'template', 'interactive', 'reaction')),
        CONSTRAINT CK_msg_status CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed'))
    );
    
    CREATE NONCLUSTERED INDEX IX_msg_conv ON messages(conversation_id);
    CREATE NONCLUSTERED INDEX IX_msg_created ON messages(created_at DESC);
    
    PRINT '[OK] Tabela messages criada';
END
GO

-- =============================================================================
-- 13. TABELA DE MÉTRICAS DE ATENDENTES
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='agent_metrics' AND xtype='U')
BEGIN
    CREATE TABLE agent_metrics (
        id INT IDENTITY(1,1) PRIMARY KEY,
        agent_id INT NOT NULL,
        
        metric_date DATE NOT NULL,
        hour_of_day INT NULL,
        
        conversations_started INT NOT NULL DEFAULT 0,
        conversations_resolved INT NOT NULL DEFAULT 0,
        conversations_transferred INT NOT NULL DEFAULT 0,
        messages_sent INT NOT NULL DEFAULT 0,
        messages_received INT NOT NULL DEFAULT 0,
        
        total_response_time INT NOT NULL DEFAULT 0,
        avg_response_time INT NULL,
        min_response_time INT NULL,
        max_response_time INT NULL,
        total_resolution_time INT NOT NULL DEFAULT 0,
        avg_resolution_time INT NULL,
        
        satisfaction_sum INT NOT NULL DEFAULT 0,
        satisfaction_count INT NOT NULL DEFAULT 0,
        avg_satisfaction DECIMAL(3,2) NULL,
        
        online_minutes INT NOT NULL DEFAULT 0,
        
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT FK_metrics_agent FOREIGN KEY (agent_id) REFERENCES usuarios(id),
        CONSTRAINT UQ_agent_metrics UNIQUE (agent_id, metric_date, hour_of_day)
    );
    
    PRINT '[OK] Tabela agent_metrics criada';
END
GO

-- =============================================================================
-- 14. TABELA DE TEMPLATES DE RESPOSTA RÁPIDA
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='quick_replies' AND xtype='U')
BEGIN
    CREATE TABLE quick_replies (
        id INT IDENTITY(1,1) PRIMARY KEY,
        
        shortcut NVARCHAR(50) NOT NULL,
        title NVARCHAR(255) NOT NULL,
        content NVARCHAR(MAX) NOT NULL,
        
        category NVARCHAR(100) NULL,
        tags NVARCHAR(MAX) NULL,
        
        owner_id INT NULL,
        is_global BIT NOT NULL DEFAULT 0,
        
        use_count INT NOT NULL DEFAULT 0,
        last_used_at DATETIME2 NULL,
        
        is_active BIT NOT NULL DEFAULT 1,
        
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        created_by INT NULL,
        
        CONSTRAINT FK_quickreply_owner FOREIGN KEY (owner_id) REFERENCES usuarios(id),
        CONSTRAINT FK_quickreply_creator FOREIGN KEY (created_by) REFERENCES usuarios(id)
    );
    
    PRINT '[OK] Tabela quick_replies criada';
END
GO

-- =============================================================================
-- TRIGGERS
-- =============================================================================

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
    DECLARE @locked_until DATETIME2;
    
    SELECT 
        @user_id = id,
        @locked_until = locked_until
    FROM usuarios 
    WHERE email = @email AND is_active = 1 AND deleted_at IS NULL;
    
    IF @user_id IS NULL
    BEGIN
        INSERT INTO audit_logs (event_type, action, ip_address, status, entry_hash, details)
        VALUES ('AUTH', 'login_attempt', @ip_address, 'failure', 
                CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), @email)), 2),
                '{"reason": "user_not_found"}');
        
        SELECT 0 AS success, 'Invalid credentials' AS message;
        RETURN;
    END
    
    IF @locked_until IS NOT NULL AND @locked_until > GETDATE()
    BEGIN
        SELECT 0 AS success, 'Account temporarily locked' AS message, @locked_until AS locked_until;
        RETURN;
    END
    
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
    
    UPDATE usuarios
    SET 
        last_login = GETDATE(),
        last_activity = GETDATE(),
        is_online = 1,
        failed_login_attempts = 0,
        locked_until = NULL
    WHERE id = @user_id;
    
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
    
    UPDATE user_sessions
    SET is_current = 0
    WHERE user_id = @user_id AND session_id != @session_id;
    
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
    
    SELECT @user_id = id, @attempts = failed_login_attempts
    FROM usuarios
    WHERE email = @email;
    
    IF @user_id IS NOT NULL
    BEGIN
        SET @attempts = @attempts + 1;
        
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
    
    UPDATE user_sessions
    SET 
        is_active = 0,
        revoked_at = GETDATE(),
        revoke_reason = 'logout'
    WHERE user_id = @user_id AND session_id = @session_id;
    
    INSERT INTO token_blacklist (token_hash, user_id, expires_at, reason)
    SELECT @token_hash, @user_id, expires_at, 'logout'
    FROM user_sessions
    WHERE session_id = @session_id;
    
    IF NOT EXISTS (SELECT 1 FROM user_sessions WHERE user_id = @user_id AND is_active = 1)
    BEGIN
        UPDATE usuarios SET is_online = 0 WHERE id = @user_id;
    END
    
    INSERT INTO audit_logs (event_type, action, user_id, status, entry_hash)
    VALUES ('AUTH', 'logout', @user_id, 'success',
            CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), @user_id)), 2));
    
    SELECT 1 AS success;
END
GO

-- Procedure para validar sessão
CREATE OR ALTER PROCEDURE sp_validate_session
    @session_id NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        s.id,
        s.session_id,
        s.user_id,
        s.is_active,
        s.expires_at,
        u.email,
        u.nome,
        u.role,
        u.is_active AS user_active
    FROM user_sessions s
    INNER JOIN usuarios u ON s.user_id = u.id
    WHERE s.session_id = @session_id
      AND s.is_active = 1
      AND s.expires_at > GETDATE()
      AND u.is_active = 1
      AND u.deleted_at IS NULL;
    
    -- Atualizar último uso
    UPDATE user_sessions 
    SET last_used_at = GETDATE()
    WHERE session_id = @session_id;
    
    UPDATE usuarios 
    SET last_activity = GETDATE()
    FROM usuarios u
    INNER JOIN user_sessions s ON u.id = s.user_id
    WHERE s.session_id = @session_id;
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
    
    DELETE FROM user_sessions
    WHERE expires_at < GETDATE() OR (is_active = 0 AND revoked_at < DATEADD(DAY, -7, GETDATE()));
    SET @deleted_sessions = @@ROWCOUNT;
    
    DELETE FROM token_blacklist
    WHERE expires_at < DATEADD(DAY, -1, GETDATE());
    SET @deleted_tokens = @@ROWCOUNT;
    
    DELETE FROM rate_limit_records
    WHERE window_end < DATEADD(HOUR, -1, GETDATE());
    SET @deleted_ratelimits = @@ROWCOUNT;
    
    INSERT INTO audit_logs (event_type, action, status, entry_hash, details)
    VALUES ('SYSTEM', 'cleanup', 'success',
            CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CONCAT(GETDATE(), 'cleanup')), 2),
            CONCAT('{"sessions": ', @deleted_sessions, ', "tokens": ', @deleted_tokens, ', "ratelimits": ', @deleted_ratelimits, '}'));
    
    SELECT @deleted_sessions AS sessions_deleted, 
           @deleted_tokens AS tokens_deleted,
           @deleted_ratelimits AS ratelimits_deleted;
END
GO

-- Procedure para métricas do dashboard
CREATE OR ALTER PROCEDURE sp_get_dashboard_metrics
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Atendentes online
    SELECT 
        COUNT(*) AS total_agents,
        SUM(CASE WHEN is_online = 1 THEN 1 ELSE 0 END) AS online_agents,
        SUM(current_conversations) AS total_active_conversations
    FROM usuarios
    WHERE role IN ('admin', 'supervisor', 'atendente') AND is_active = 1;
    
    -- Conversas por estado
    SELECT 
        state,
        COUNT(*) AS count
    FROM conversations
    WHERE closed_at IS NULL
    GROUP BY state;
    
    -- Métricas do dia
    SELECT 
        COUNT(*) AS conversations_today,
        AVG(first_response_time) AS avg_first_response,
        AVG(resolution_time) AS avg_resolution,
        AVG(CAST(satisfaction_score AS FLOAT)) AS avg_satisfaction
    FROM conversations
    WHERE CAST(started_at AS DATE) = CAST(GETDATE() AS DATE);
END
GO

PRINT '[OK] Stored Procedures criados';
GO

-- =============================================================================
-- VIEWS
-- =============================================================================

-- View de atendentes online
CREATE OR ALTER VIEW vw_online_agents AS
SELECT 
    id,
    nome,
    email,
    role,
    current_conversations,
    max_concurrent_conversations,
    avg_response_time,
    avg_satisfaction,
    last_activity
FROM usuarios
WHERE is_active = 1 
  AND is_online = 1 
  AND role IN ('admin', 'supervisor', 'atendente')
  AND deleted_at IS NULL;
GO

-- View de fila de espera
CREATE OR ALTER VIEW vw_queue AS
SELECT 
    c.id,
    c.conversation_id,
    wc.phone_number,
    wc.name AS customer_name,
    c.priority,
    c.started_at,
    DATEDIFF(MINUTE, c.started_at, GETDATE()) AS waiting_minutes
FROM conversations c
INNER JOIN whatsapp_clients wc ON c.client_id = wc.id
WHERE c.state = 'queue'
  AND c.closed_at IS NULL;
GO

-- View de métricas diárias
CREATE OR ALTER VIEW vw_daily_metrics AS
SELECT 
    CAST(started_at AS DATE) AS metric_date,
    COUNT(*) AS total_conversations,
    SUM(CASE WHEN state = 'resolved' THEN 1 ELSE 0 END) AS resolved_conversations,
    AVG(first_response_time) AS avg_first_response_time,
    AVG(resolution_time) AS avg_resolution_time,
    AVG(CAST(satisfaction_score AS FLOAT)) AS avg_satisfaction
FROM conversations
WHERE started_at >= DATEADD(DAY, -30, GETDATE())
GROUP BY CAST(started_at AS DATE);
GO

PRINT '[OK] Views criadas';
GO

-- =============================================================================
-- DADOS INICIAIS
-- =============================================================================

-- Configurações do sistema
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

-- Usuário admin padrão (senha: Admin@123)
IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'admin@sistema.local')
BEGIN
    INSERT INTO usuarios (
        email, username, password_hash, nome, role, 
        is_active, is_verified, created_at
    )
    VALUES (
        'admin@sistema.local',
        'admin',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.',
        'Administrador',
        'admin',
        1, 1, GETDATE()
    );
    
    PRINT '[OK] Usuario admin criado';
END
GO

-- Respostas rápidas de exemplo
IF NOT EXISTS (SELECT 1 FROM quick_replies WHERE shortcut = '/ola')
BEGIN
    INSERT INTO quick_replies (shortcut, title, content, category, is_global, created_by)
    VALUES 
        ('/ola', 'Saudação inicial', 'Olá! Bem-vindo ao suporte da TechISP. Como posso ajudar você hoje?', 'saudacao', 1, 1),
        ('/aguarde', 'Pedir para aguardar', 'Um momento, por favor. Estou verificando isso para você.', 'geral', 1, 1),
        ('/internet', 'Problema de internet', 'Entendo que está tendo problemas com sua internet. Pode me informar se o problema é em todos os dispositivos ou apenas em um específico?', 'suporte', 1, 1),
        ('/reiniciar', 'Instrução para reiniciar modem', 'Por favor, reinicie seu modem: 1) Desligue da tomada 2) Aguarde 30 segundos 3) Ligue novamente 4) Aguarde 2 minutos para estabilizar', 'suporte', 1, 1),
        ('/boleto', 'Enviar 2ª via', 'Estou gerando a 2ª via do seu boleto. Em instantes enviarei o link para pagamento.', 'financeiro', 1, 1),
        ('/obrigado', 'Agradecimento final', 'Obrigado pelo contato! Se precisar de mais alguma coisa, estamos à disposição. Tenha um ótimo dia! 😊', 'encerramento', 1, 1);
    
    PRINT '[OK] Respostas rapidas de exemplo inseridas';
END
GO

-- =============================================================================
-- FINALIZAÇÃO
-- =============================================================================

PRINT '';
PRINT '=============================================================================';
PRINT ' SETUP SQL SERVER CONCLUIDO COM SUCESSO!';
PRINT '=============================================================================';
PRINT '';
PRINT ' TABELAS CRIADAS:';
PRINT '   - usuarios (autenticacao)';
PRINT '   - user_sessions (sessoes JWT)';
PRINT '   - token_blacklist (tokens revogados)';
PRINT '   - audit_logs (auditoria)';
PRINT '   - user_consents (LGPD)';
PRINT '   - api_keys (chaves de API)';
PRINT '   - rate_limit_records (rate limiting)';
PRINT '   - system_config (configuracoes)';
PRINT '   - whatsapp_clients (clientes WhatsApp)';
PRINT '   - conversations (conversas)';
PRINT '   - messages (mensagens)';
PRINT '   - agent_metrics (metricas de atendentes)';
PRINT '   - quick_replies (respostas rapidas)';
PRINT '';
PRINT ' STORED PROCEDURES:';
PRINT '   - sp_authenticate_user';
PRINT '   - sp_login_success';
PRINT '   - sp_login_failure';
PRINT '   - sp_logout';
PRINT '   - sp_validate_session';
PRINT '   - sp_cleanup_expired_tokens';
PRINT '   - sp_get_dashboard_metrics';
PRINT '';
PRINT ' VIEWS:';
PRINT '   - vw_online_agents';
PRINT '   - vw_queue';
PRINT '   - vw_daily_metrics';
PRINT '';
PRINT ' USUARIO ADMIN PADRAO:';
PRINT '   Email: admin@sistema.local';
PRINT '   Senha: Admin@123';
PRINT '';
PRINT '=============================================================================';
GO
