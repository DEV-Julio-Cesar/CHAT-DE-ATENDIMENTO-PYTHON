-- =============================================================================
-- MIGRATION: Adicionar campos de performance e análise
-- =============================================================================
-- Versão: 2.1.0
-- Data: 2026
-- =============================================================================

USE isp_support;
GO

PRINT '[MIGRATION] Iniciando migração 002 - Campos de performance e análise';
GO

-- =============================================================================
-- 1. ADICIONAR CAMPOS NA TABELA USUARIOS
-- =============================================================================

-- Campo para métricas de atendente
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('usuarios') AND name = 'avg_response_time')
BEGIN
    ALTER TABLE usuarios ADD avg_response_time INT NULL;  -- segundos
    PRINT '[OK] Campo avg_response_time adicionado em usuarios';
END
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('usuarios') AND name = 'total_conversations')
BEGIN
    ALTER TABLE usuarios ADD total_conversations INT NOT NULL DEFAULT 0;
    PRINT '[OK] Campo total_conversations adicionado em usuarios';
END
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('usuarios') AND name = 'avg_satisfaction')
BEGIN
    ALTER TABLE usuarios ADD avg_satisfaction DECIMAL(3,2) NULL;  -- 1.00 a 5.00
    PRINT '[OK] Campo avg_satisfaction adicionado em usuarios';
END
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('usuarios') AND name = 'current_conversations')
BEGIN
    ALTER TABLE usuarios ADD current_conversations INT NOT NULL DEFAULT 0;
    PRINT '[OK] Campo current_conversations adicionado em usuarios';
END
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('usuarios') AND name = 'max_concurrent_conversations')
BEGIN
    ALTER TABLE usuarios ADD max_concurrent_conversations INT NOT NULL DEFAULT 5;
    PRINT '[OK] Campo max_concurrent_conversations adicionado em usuarios';
END
GO

-- =============================================================================
-- 2. TABELA DE MÉTRICAS DE ATENDENTES
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='agent_metrics' AND xtype='U')
BEGIN
    CREATE TABLE agent_metrics (
        id INT IDENTITY(1,1) PRIMARY KEY,
        agent_id INT NOT NULL,
        
        -- Período
        metric_date DATE NOT NULL,
        hour_of_day INT NULL,  -- 0-23, NULL para métricas diárias
        
        -- Métricas de volume
        conversations_started INT NOT NULL DEFAULT 0,
        conversations_resolved INT NOT NULL DEFAULT 0,
        conversations_transferred INT NOT NULL DEFAULT 0,
        messages_sent INT NOT NULL DEFAULT 0,
        messages_received INT NOT NULL DEFAULT 0,
        
        -- Métricas de tempo (em segundos)
        total_response_time INT NOT NULL DEFAULT 0,
        avg_response_time INT NULL,
        min_response_time INT NULL,
        max_response_time INT NULL,
        total_resolution_time INT NOT NULL DEFAULT 0,
        avg_resolution_time INT NULL,
        
        -- Métricas de qualidade
        satisfaction_sum INT NOT NULL DEFAULT 0,
        satisfaction_count INT NOT NULL DEFAULT 0,
        avg_satisfaction DECIMAL(3,2) NULL,
        
        -- Online time
        online_minutes INT NOT NULL DEFAULT 0,
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        
        -- Constraints
        CONSTRAINT FK_metrics_agent FOREIGN KEY (agent_id) REFERENCES usuarios(id),
        CONSTRAINT UQ_agent_metrics UNIQUE (agent_id, metric_date, hour_of_day)
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_metrics_agent_date ON agent_metrics(agent_id, metric_date);
    CREATE NONCLUSTERED INDEX IX_metrics_date ON agent_metrics(metric_date);
    
    PRINT '[OK] Tabela agent_metrics criada';
END
GO

-- =============================================================================
-- 3. TABELA DE TEMPLATES DE RESPOSTA RÁPIDA
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='quick_replies' AND xtype='U')
BEGIN
    CREATE TABLE quick_replies (
        id INT IDENTITY(1,1) PRIMARY KEY,
        
        -- Identificação
        shortcut NVARCHAR(50) NOT NULL,
        title NVARCHAR(255) NOT NULL,
        content NVARCHAR(MAX) NOT NULL,
        
        -- Categorização
        category NVARCHAR(100) NULL,
        tags NVARCHAR(MAX) NULL,  -- JSON array
        
        -- Propriedade
        owner_id INT NULL,        -- NULL = global
        is_global BIT NOT NULL DEFAULT 0,
        
        -- Estatísticas
        use_count INT NOT NULL DEFAULT 0,
        last_used_at DATETIME2 NULL,
        
        -- Status
        is_active BIT NOT NULL DEFAULT 1,
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        created_by INT NULL,
        
        -- Constraints
        CONSTRAINT FK_quickreply_owner FOREIGN KEY (owner_id) REFERENCES usuarios(id),
        CONSTRAINT FK_quickreply_creator FOREIGN KEY (created_by) REFERENCES usuarios(id)
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_quickreply_shortcut ON quick_replies(shortcut) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_quickreply_owner ON quick_replies(owner_id) WHERE is_active = 1;
    CREATE NONCLUSTERED INDEX IX_quickreply_category ON quick_replies(category);
    
    PRINT '[OK] Tabela quick_replies criada';
END
GO

-- =============================================================================
-- 4. TABELA DE TAGS DE CONVERSA
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversation_tags' AND xtype='U')
BEGIN
    CREATE TABLE conversation_tags (
        id INT IDENTITY(1,1) PRIMARY KEY,
        
        -- Tag info
        name NVARCHAR(100) NOT NULL,
        color NVARCHAR(7) NOT NULL DEFAULT '#6B7280',  -- Hex color
        description NVARCHAR(255) NULL,
        
        -- Estatísticas
        use_count INT NOT NULL DEFAULT 0,
        
        -- Status
        is_active BIT NOT NULL DEFAULT 1,
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        created_by INT NULL,
        
        -- Constraints
        CONSTRAINT UQ_tag_name UNIQUE (name),
        CONSTRAINT FK_tag_creator FOREIGN KEY (created_by) REFERENCES usuarios(id)
    );
    
    PRINT '[OK] Tabela conversation_tags criada';
END
GO

-- =============================================================================
-- 5. TABELA DE RELAÇÃO CONVERSA-TAG
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversation_tag_rel' AND xtype='U')
BEGIN
    CREATE TABLE conversation_tag_rel (
        conversation_id INT NOT NULL,
        tag_id INT NOT NULL,
        added_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        added_by INT NULL,
        
        CONSTRAINT PK_conv_tag PRIMARY KEY (conversation_id, tag_id),
        CONSTRAINT FK_convtag_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        CONSTRAINT FK_convtag_tag FOREIGN KEY (tag_id) REFERENCES conversation_tags(id),
        CONSTRAINT FK_convtag_user FOREIGN KEY (added_by) REFERENCES usuarios(id)
    );
    
    PRINT '[OK] Tabela conversation_tag_rel criada';
END
GO

-- =============================================================================
-- 6. TABELA DE NOTAS INTERNAS
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversation_notes' AND xtype='U')
BEGIN
    CREATE TABLE conversation_notes (
        id INT IDENTITY(1,1) PRIMARY KEY,
        conversation_id INT NOT NULL,
        
        -- Conteúdo
        content NVARCHAR(MAX) NOT NULL,
        
        -- Autor
        author_id INT NOT NULL,
        
        -- Tipo
        note_type NVARCHAR(50) NOT NULL DEFAULT 'note',  -- note, warning, important
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NULL,
        
        -- Constraints
        CONSTRAINT FK_note_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        CONSTRAINT FK_note_author FOREIGN KEY (author_id) REFERENCES usuarios(id),
        CONSTRAINT CK_note_type CHECK (note_type IN ('note', 'warning', 'important', 'transfer'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_note_conv ON conversation_notes(conversation_id);
    
    PRINT '[OK] Tabela conversation_notes criada';
END
GO

-- =============================================================================
-- 7. TABELA DE TRANSFERÊNCIAS
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversation_transfers' AND xtype='U')
BEGIN
    CREATE TABLE conversation_transfers (
        id INT IDENTITY(1,1) PRIMARY KEY,
        conversation_id INT NOT NULL,
        
        -- De/Para
        from_agent_id INT NULL,
        to_agent_id INT NULL,
        to_queue NVARCHAR(100) NULL,
        
        -- Motivo
        reason NVARCHAR(500) NULL,
        transfer_type NVARCHAR(50) NOT NULL,  -- 'agent', 'queue', 'department'
        
        -- Status
        status NVARCHAR(50) NOT NULL DEFAULT 'pending',
        
        -- Timestamps
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        accepted_at DATETIME2 NULL,
        rejected_at DATETIME2 NULL,
        
        -- Constraints
        CONSTRAINT FK_transfer_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        CONSTRAINT FK_transfer_from FOREIGN KEY (from_agent_id) REFERENCES usuarios(id),
        CONSTRAINT FK_transfer_to FOREIGN KEY (to_agent_id) REFERENCES usuarios(id),
        CONSTRAINT CK_transfer_type CHECK (transfer_type IN ('agent', 'queue', 'department', 'bot')),
        CONSTRAINT CK_transfer_status CHECK (status IN ('pending', 'accepted', 'rejected', 'cancelled', 'timeout'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_transfer_conv ON conversation_transfers(conversation_id);
    CREATE NONCLUSTERED INDEX IX_transfer_to ON conversation_transfers(to_agent_id) WHERE status = 'pending';
    
    PRINT '[OK] Tabela conversation_transfers criada';
END
GO

-- =============================================================================
-- 8. TABELA DE FILA DE ATENDIMENTO
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='queue_entries' AND xtype='U')
BEGIN
    CREATE TABLE queue_entries (
        id INT IDENTITY(1,1) PRIMARY KEY,
        
        -- Conversa
        conversation_id INT NOT NULL,
        client_id INT NOT NULL,
        
        -- Fila
        queue_name NVARCHAR(100) NOT NULL DEFAULT 'default',
        priority INT NOT NULL DEFAULT 0,  -- Maior = mais prioritário
        
        -- Posição e tempo
        position INT NULL,
        estimated_wait_minutes INT NULL,
        
        -- Status
        status NVARCHAR(50) NOT NULL DEFAULT 'waiting',
        
        -- Timestamps
        entered_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        assigned_at DATETIME2 NULL,
        abandoned_at DATETIME2 NULL,
        
        -- Atribuição
        assigned_to INT NULL,
        
        -- Constraints
        CONSTRAINT FK_queue_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        CONSTRAINT FK_queue_client FOREIGN KEY (client_id) REFERENCES whatsapp_clients(id),
        CONSTRAINT FK_queue_agent FOREIGN KEY (assigned_to) REFERENCES usuarios(id),
        CONSTRAINT CK_queue_status CHECK (status IN ('waiting', 'assigned', 'abandoned', 'timeout'))
    );
    
    -- Índices
    CREATE NONCLUSTERED INDEX IX_queue_status ON queue_entries(queue_name, status, priority DESC, entered_at);
    CREATE NONCLUSTERED INDEX IX_queue_conv ON queue_entries(conversation_id);
    
    PRINT '[OK] Tabela queue_entries criada';
END
GO

-- =============================================================================
-- 9. STORED PROCEDURES ADICIONAIS
-- =============================================================================

-- Procedure para atualizar métricas de atendente
CREATE OR ALTER PROCEDURE sp_update_agent_metrics
    @agent_id INT,
    @metric_date DATE = NULL,
    @conversations_started INT = 0,
    @conversations_resolved INT = 0,
    @messages_sent INT = 0,
    @response_time INT = NULL,
    @resolution_time INT = NULL,
    @satisfaction_score INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @metric_date IS NULL SET @metric_date = CAST(GETDATE() AS DATE);
    
    -- Inserir ou atualizar métricas
    MERGE agent_metrics AS target
    USING (SELECT @agent_id AS agent_id, @metric_date AS metric_date, NULL AS hour_of_day) AS source
    ON target.agent_id = source.agent_id 
       AND target.metric_date = source.metric_date 
       AND target.hour_of_day IS NULL
    WHEN MATCHED THEN
        UPDATE SET
            conversations_started = conversations_started + @conversations_started,
            conversations_resolved = conversations_resolved + @conversations_resolved,
            messages_sent = messages_sent + @messages_sent,
            total_response_time = total_response_time + ISNULL(@response_time, 0),
            total_resolution_time = total_resolution_time + ISNULL(@resolution_time, 0),
            satisfaction_sum = satisfaction_sum + ISNULL(@satisfaction_score, 0),
            satisfaction_count = satisfaction_count + CASE WHEN @satisfaction_score IS NOT NULL THEN 1 ELSE 0 END,
            updated_at = GETDATE()
    WHEN NOT MATCHED THEN
        INSERT (agent_id, metric_date, hour_of_day, 
                conversations_started, conversations_resolved, messages_sent,
                total_response_time, total_resolution_time,
                satisfaction_sum, satisfaction_count)
        VALUES (@agent_id, @metric_date, NULL,
                @conversations_started, @conversations_resolved, @messages_sent,
                ISNULL(@response_time, 0), ISNULL(@resolution_time, 0),
                ISNULL(@satisfaction_score, 0), CASE WHEN @satisfaction_score IS NOT NULL THEN 1 ELSE 0 END);
    
    -- Recalcular médias
    UPDATE agent_metrics
    SET 
        avg_response_time = CASE WHEN conversations_resolved > 0 THEN total_response_time / conversations_resolved ELSE NULL END,
        avg_resolution_time = CASE WHEN conversations_resolved > 0 THEN total_resolution_time / conversations_resolved ELSE NULL END,
        avg_satisfaction = CASE WHEN satisfaction_count > 0 THEN CAST(satisfaction_sum AS DECIMAL(10,2)) / satisfaction_count ELSE NULL END
    WHERE agent_id = @agent_id AND metric_date = @metric_date AND hour_of_day IS NULL;
    
    SELECT 1 AS success;
END
GO

-- Procedure para obter próximo da fila
CREATE OR ALTER PROCEDURE sp_get_next_from_queue
    @agent_id INT,
    @queue_name NVARCHAR(100) = 'default'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @conversation_id INT;
    DECLARE @queue_id INT;
    
    -- Buscar próximo da fila (maior prioridade, mais antigo)
    SELECT TOP 1 
        @queue_id = id,
        @conversation_id = conversation_id
    FROM queue_entries
    WHERE queue_name = @queue_name 
      AND status = 'waiting'
    ORDER BY priority DESC, entered_at ASC;
    
    IF @queue_id IS NOT NULL
    BEGIN
        -- Atribuir ao agente
        UPDATE queue_entries
        SET 
            status = 'assigned',
            assigned_to = @agent_id,
            assigned_at = GETDATE()
        WHERE id = @queue_id;
        
        -- Atualizar conversa
        UPDATE conversations
        SET 
            agent_id = @agent_id,
            state = 'human',
            assigned_at = GETDATE()
        WHERE id = @conversation_id;
        
        -- Atualizar contador do agente
        UPDATE usuarios
        SET current_conversations = current_conversations + 1
        WHERE id = @agent_id;
        
        -- Retornar dados
        SELECT 
            c.id AS conversation_id,
            c.conversation_id AS external_id,
            wc.wa_id,
            wc.name AS client_name,
            wc.phone_number,
            c.started_at,
            qe.entered_at AS queue_entered_at,
            DATEDIFF(SECOND, qe.entered_at, GETDATE()) AS wait_seconds
        FROM conversations c
        INNER JOIN whatsapp_clients wc ON c.client_id = wc.id
        INNER JOIN queue_entries qe ON qe.id = @queue_id
        WHERE c.id = @conversation_id;
    END
    ELSE
    BEGIN
        SELECT NULL AS conversation_id, 'Queue empty' AS message;
    END
END
GO

PRINT '[OK] Stored Procedures adicionais criados';
GO

-- =============================================================================
-- 10. INSERIR QUICK REPLIES PADRÃO
-- =============================================================================

IF NOT EXISTS (SELECT 1 FROM quick_replies WHERE shortcut = '/ola')
BEGIN
    INSERT INTO quick_replies (shortcut, title, content, category, is_global, is_active)
    VALUES 
        ('/ola', 'Saudação', 'Olá! Meu nome é {agent_name}, como posso ajudar você hoje?', 'Saudações', 1, 1),
        ('/tchau', 'Despedida', 'Foi um prazer ajudar! Se precisar de mais alguma coisa, estou à disposição. Tenha um ótimo dia!', 'Saudações', 1, 1),
        ('/aguarde', 'Aguardar', 'Por favor, aguarde um momento enquanto verifico essa informação para você.', 'Geral', 1, 1),
        ('/fatura', 'Fatura', 'Para enviar a 2ª via da sua fatura, preciso confirmar alguns dados. Poderia me informar o CPF do titular?', 'Financeiro', 1, 1),
        ('/codigo', 'Código de barras', 'Aqui está o código de barras da sua fatura:\n\n{barcode}\n\nVocê pode copiar e pagar pelo app do seu banco.', 'Financeiro', 1, 1),
        ('/tecnico', 'Visita técnica', 'Vou verificar a disponibilidade para agendar uma visita técnica. Qual período seria melhor para você: manhã (8h às 12h) ou tarde (13h às 18h)?', 'Suporte', 1, 1),
        ('/conexao', 'Problema de conexão', 'Entendo que você está com problemas de conexão. Vamos fazer alguns testes. Primeiro, poderia reiniciar o roteador desligando-o por 30 segundos?', 'Suporte', 1, 1),
        ('/planos', 'Upgrade de plano', 'Temos ótimas opções de upgrade! Nossos planos disponíveis são:\n\n📶 100 Mbps - R$ 99,90\n📶 200 Mbps - R$ 129,90\n📶 400 Mbps - R$ 179,90\n\nQual te interessa?', 'Comercial', 1, 1);
    
    PRINT '[OK] Quick replies padrão inseridas';
END
GO

-- =============================================================================
-- 11. INSERIR TAGS PADRÃO
-- =============================================================================

IF NOT EXISTS (SELECT 1 FROM conversation_tags WHERE name = 'Urgente')
BEGIN
    INSERT INTO conversation_tags (name, color, description, is_active)
    VALUES 
        ('Urgente', '#EF4444', 'Problema crítico que precisa de atenção imediata', 1),
        ('VIP', '#F59E0B', 'Cliente VIP ou plano premium', 1),
        ('Financeiro', '#10B981', 'Assuntos relacionados a pagamentos e faturas', 1),
        ('Técnico', '#3B82F6', 'Problemas técnicos de conexão ou equipamento', 1),
        ('Comercial', '#8B5CF6', 'Vendas, upgrades e novos serviços', 1),
        ('Reclamação', '#EC4899', 'Cliente insatisfeito ou reclamando', 1),
        ('Cancelamento', '#6B7280', 'Solicitação de cancelamento', 1),
        ('Follow-up', '#06B6D4', 'Precisa de acompanhamento posterior', 1);
    
    PRINT '[OK] Tags padrão inseridas';
END
GO

PRINT '';
PRINT '=============================================================================';
PRINT ' MIGRATION 002 CONCLUÍDA COM SUCESSO!';
PRINT '=============================================================================';
GO
