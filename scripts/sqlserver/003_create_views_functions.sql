-- =============================================================================
-- MIGRATION: Views e funções para relatórios
-- =============================================================================
-- Versão: 2.2.0
-- Data: 2026
-- =============================================================================

USE isp_support;
GO

PRINT '[MIGRATION] Iniciando migração 003 - Views e funções para relatórios';
GO

-- =============================================================================
-- 1. VIEW: Dashboard de Atendentes Online
-- =============================================================================

CREATE OR ALTER VIEW vw_agents_online
AS
SELECT 
    u.id,
    u.nome,
    u.email,
    u.role,
    u.is_online,
    u.last_activity,
    u.current_conversations,
    u.max_concurrent_conversations,
    u.avg_response_time,
    u.avg_satisfaction,
    CASE 
        WHEN u.current_conversations >= u.max_concurrent_conversations THEN 'busy'
        WHEN u.is_online = 1 THEN 'available'
        ELSE 'offline'
    END AS availability_status,
    u.max_concurrent_conversations - u.current_conversations AS available_slots
FROM usuarios u
WHERE u.is_active = 1 
  AND u.deleted_at IS NULL
  AND u.role IN ('admin', 'supervisor', 'atendente');
GO

PRINT '[OK] View vw_agents_online criada';
GO

-- =============================================================================
-- 2. VIEW: Resumo de Conversas Ativas
-- =============================================================================

CREATE OR ALTER VIEW vw_active_conversations
AS
SELECT 
    c.id,
    c.conversation_id,
    c.state,
    c.priority,
    c.category,
    c.started_at,
    c.assigned_at,
    c.last_message_at,
    c.message_count,
    DATEDIFF(MINUTE, c.started_at, GETDATE()) AS duration_minutes,
    DATEDIFF(MINUTE, c.last_message_at, GETDATE()) AS idle_minutes,
    
    -- Cliente
    wc.wa_id AS client_phone,
    wc.name AS client_name,
    wc.customer_code,
    wc.plan_name,
    
    -- Atendente
    u.id AS agent_id,
    u.nome AS agent_name,
    
    -- Posição na fila (se aplicável)
    qe.position AS queue_position,
    qe.entered_at AS queue_entered_at,
    DATEDIFF(MINUTE, qe.entered_at, GETDATE()) AS wait_minutes

FROM conversations c
INNER JOIN whatsapp_clients wc ON c.client_id = wc.id
LEFT JOIN usuarios u ON c.agent_id = u.id
LEFT JOIN queue_entries qe ON qe.conversation_id = c.id AND qe.status = 'waiting'
WHERE c.closed_at IS NULL;
GO

PRINT '[OK] View vw_active_conversations criada';
GO

-- =============================================================================
-- 3. VIEW: Métricas do Dia
-- =============================================================================

CREATE OR ALTER VIEW vw_today_metrics
AS
SELECT 
    -- Conversas
    COUNT(CASE WHEN c.started_at >= CAST(GETDATE() AS DATE) THEN 1 END) AS conversations_today,
    COUNT(CASE WHEN c.resolved_at >= CAST(GETDATE() AS DATE) THEN 1 END) AS resolved_today,
    COUNT(CASE WHEN c.state = 'queue' THEN 1 END) AS in_queue,
    COUNT(CASE WHEN c.state = 'human' THEN 1 END) AS in_progress,
    COUNT(CASE WHEN c.state = 'bot' THEN 1 END) AS with_bot,
    
    -- Tempo médio
    AVG(CASE 
        WHEN c.resolved_at >= CAST(GETDATE() AS DATE) 
        THEN DATEDIFF(SECOND, c.started_at, c.resolved_at) 
    END) AS avg_resolution_time_seconds,
    
    AVG(CASE 
        WHEN c.assigned_at >= CAST(GETDATE() AS DATE) 
        THEN DATEDIFF(SECOND, c.started_at, c.assigned_at) 
    END) AS avg_first_response_seconds,
    
    -- Satisfação
    AVG(CASE 
        WHEN c.resolved_at >= CAST(GETDATE() AS DATE) AND c.satisfaction_score IS NOT NULL
        THEN CAST(c.satisfaction_score AS DECIMAL(3,2))
    END) AS avg_satisfaction,
    
    -- Atendentes
    (SELECT COUNT(*) FROM usuarios WHERE is_online = 1 AND is_active = 1) AS agents_online
    
FROM conversations c
WHERE c.started_at >= DATEADD(DAY, -1, CAST(GETDATE() AS DATE));
GO

PRINT '[OK] View vw_today_metrics criada';
GO

-- =============================================================================
-- 4. VIEW: Ranking de Atendentes
-- =============================================================================

CREATE OR ALTER VIEW vw_agent_ranking
AS
SELECT 
    u.id,
    u.nome,
    u.role,
    
    -- Métricas do mês
    ISNULL(SUM(am.conversations_resolved), 0) AS total_resolved,
    ISNULL(SUM(am.messages_sent), 0) AS total_messages,
    
    -- Médias
    CASE 
        WHEN SUM(am.conversations_resolved) > 0 
        THEN SUM(am.total_response_time) / SUM(am.conversations_resolved)
        ELSE NULL 
    END AS avg_response_time,
    
    CASE 
        WHEN SUM(am.satisfaction_count) > 0 
        THEN CAST(SUM(am.satisfaction_sum) AS DECIMAL(10,2)) / SUM(am.satisfaction_count)
        ELSE NULL 
    END AS avg_satisfaction,
    
    -- Online time
    ISNULL(SUM(am.online_minutes), 0) AS total_online_minutes,
    
    -- Eficiência
    CASE 
        WHEN SUM(am.online_minutes) > 0 
        THEN CAST(SUM(am.conversations_resolved) AS DECIMAL(10,2)) / (SUM(am.online_minutes) / 60.0)
        ELSE NULL 
    END AS conversations_per_hour

FROM usuarios u
LEFT JOIN agent_metrics am ON u.id = am.agent_id 
    AND am.metric_date >= DATEADD(DAY, -30, CAST(GETDATE() AS DATE))
WHERE u.is_active = 1 AND u.role IN ('admin', 'supervisor', 'atendente')
GROUP BY u.id, u.nome, u.role;
GO

PRINT '[OK] View vw_agent_ranking criada';
GO

-- =============================================================================
-- 5. VIEW: Histórico de Conversas com Detalhes
-- =============================================================================

CREATE OR ALTER VIEW vw_conversation_history
AS
SELECT 
    c.id,
    c.conversation_id,
    c.state,
    c.priority,
    c.category,
    c.subcategory,
    c.message_count,
    c.satisfaction_score,
    c.satisfaction_comment,
    
    -- Tempos
    c.started_at,
    c.assigned_at,
    c.resolved_at,
    c.closed_at,
    c.first_response_time,
    c.resolution_time,
    c.wait_time,
    
    -- Cliente
    wc.id AS client_id,
    wc.wa_id AS client_phone,
    wc.name AS client_name,
    wc.customer_code,
    wc.plan_name,
    
    -- Atendente
    u.id AS agent_id,
    u.nome AS agent_name,
    
    -- Tags (concatenadas)
    STUFF((
        SELECT ', ' + ct.name
        FROM conversation_tag_rel ctr
        INNER JOIN conversation_tags ct ON ctr.tag_id = ct.id
        WHERE ctr.conversation_id = c.id
        FOR XML PATH(''), TYPE
    ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS tags

FROM conversations c
INNER JOIN whatsapp_clients wc ON c.client_id = wc.id
LEFT JOIN usuarios u ON c.agent_id = u.id;
GO

PRINT '[OK] View vw_conversation_history criada';
GO

-- =============================================================================
-- 6. FUNÇÃO: Calcular posição na fila
-- =============================================================================

CREATE OR ALTER FUNCTION fn_get_queue_position
(
    @conversation_id INT
)
RETURNS INT
AS
BEGIN
    DECLARE @position INT;
    DECLARE @queue_name NVARCHAR(100);
    DECLARE @entered_at DATETIME2;
    DECLARE @priority INT;
    
    -- Obter dados da entrada na fila
    SELECT 
        @queue_name = queue_name,
        @entered_at = entered_at,
        @priority = priority
    FROM queue_entries
    WHERE conversation_id = @conversation_id AND status = 'waiting';
    
    IF @queue_name IS NULL
        RETURN NULL;
    
    -- Calcular posição
    SELECT @position = COUNT(*) + 1
    FROM queue_entries
    WHERE queue_name = @queue_name
      AND status = 'waiting'
      AND (priority > @priority OR (priority = @priority AND entered_at < @entered_at));
    
    RETURN @position;
END
GO

PRINT '[OK] Função fn_get_queue_position criada';
GO

-- =============================================================================
-- 7. FUNÇÃO: Estimar tempo de espera
-- =============================================================================

CREATE OR ALTER FUNCTION fn_estimate_wait_time
(
    @queue_name NVARCHAR(100),
    @position INT
)
RETURNS INT
AS
BEGIN
    DECLARE @avg_resolution_time INT;
    DECLARE @agents_available INT;
    DECLARE @estimated_minutes INT;
    
    -- Calcular tempo médio de resolução (últimos 7 dias)
    SELECT @avg_resolution_time = AVG(DATEDIFF(MINUTE, assigned_at, resolved_at))
    FROM conversations
    WHERE resolved_at >= DATEADD(DAY, -7, GETDATE())
      AND assigned_at IS NOT NULL
      AND resolved_at IS NOT NULL;
    
    -- Contar agentes disponíveis
    SELECT @agents_available = COUNT(*)
    FROM usuarios
    WHERE is_online = 1 
      AND is_active = 1 
      AND current_conversations < max_concurrent_conversations;
    
    -- Estimar tempo
    IF @agents_available > 0 AND @avg_resolution_time IS NOT NULL
    BEGIN
        SET @estimated_minutes = (@position * ISNULL(@avg_resolution_time, 10)) / @agents_available;
    END
    ELSE
    BEGIN
        SET @estimated_minutes = @position * 15; -- Padrão: 15 min por posição
    END
    
    RETURN @estimated_minutes;
END
GO

PRINT '[OK] Função fn_estimate_wait_time criada';
GO

-- =============================================================================
-- 8. STORED PROCEDURE: Relatório diário
-- =============================================================================

CREATE OR ALTER PROCEDURE sp_generate_daily_report
    @report_date DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @report_date IS NULL SET @report_date = DATEADD(DAY, -1, CAST(GETDATE() AS DATE));
    
    DECLARE @next_date DATE = DATEADD(DAY, 1, @report_date);
    
    -- Métricas gerais
    SELECT 
        @report_date AS report_date,
        
        -- Volume
        COUNT(CASE WHEN started_at >= @report_date AND started_at < @next_date THEN 1 END) AS conversations_started,
        COUNT(CASE WHEN resolved_at >= @report_date AND resolved_at < @next_date THEN 1 END) AS conversations_resolved,
        
        -- Por estado final
        COUNT(CASE WHEN resolved_at >= @report_date AND resolved_at < @next_date AND state = 'resolved' THEN 1 END) AS resolved_by_human,
        COUNT(CASE WHEN resolved_at >= @report_date AND resolved_at < @next_date AND bot_message_count > 0 AND human_message_count = 0 THEN 1 END) AS resolved_by_bot,
        
        -- Tempos médios
        AVG(CASE WHEN resolved_at >= @report_date AND resolved_at < @next_date THEN first_response_time END) AS avg_first_response,
        AVG(CASE WHEN resolved_at >= @report_date AND resolved_at < @next_date THEN resolution_time END) AS avg_resolution_time,
        AVG(CASE WHEN resolved_at >= @report_date AND resolved_at < @next_date THEN wait_time END) AS avg_wait_time,
        
        -- Satisfação
        AVG(CASE WHEN resolved_at >= @report_date AND resolved_at < @next_date AND satisfaction_score IS NOT NULL 
            THEN CAST(satisfaction_score AS DECIMAL(3,2)) END) AS avg_satisfaction,
        
        -- Mensagens
        SUM(CASE WHEN started_at >= @report_date AND started_at < @next_date THEN message_count ELSE 0 END) AS total_messages
        
    FROM conversations;
    
    -- Métricas por atendente
    SELECT 
        u.id AS agent_id,
        u.nome AS agent_name,
        COUNT(CASE WHEN c.resolved_at >= @report_date AND c.resolved_at < @next_date THEN 1 END) AS resolved,
        AVG(CASE WHEN c.resolved_at >= @report_date AND c.resolved_at < @next_date THEN c.resolution_time END) AS avg_resolution,
        AVG(CASE WHEN c.resolved_at >= @report_date AND c.resolved_at < @next_date AND c.satisfaction_score IS NOT NULL 
            THEN CAST(c.satisfaction_score AS DECIMAL(3,2)) END) AS avg_satisfaction
    FROM usuarios u
    LEFT JOIN conversations c ON u.id = c.agent_id
    WHERE u.role IN ('admin', 'supervisor', 'atendente') AND u.is_active = 1
    GROUP BY u.id, u.nome
    ORDER BY resolved DESC;
    
    -- Métricas por categoria
    SELECT 
        ISNULL(category, 'Sem categoria') AS category,
        COUNT(*) AS total,
        AVG(resolution_time) AS avg_resolution_time,
        AVG(CAST(satisfaction_score AS DECIMAL(3,2))) AS avg_satisfaction
    FROM conversations
    WHERE resolved_at >= @report_date AND resolved_at < @next_date
    GROUP BY category
    ORDER BY total DESC;
    
    -- Métricas por hora
    SELECT 
        DATEPART(HOUR, started_at) AS hour_of_day,
        COUNT(*) AS conversations
    FROM conversations
    WHERE started_at >= @report_date AND started_at < @next_date
    GROUP BY DATEPART(HOUR, started_at)
    ORDER BY hour_of_day;
END
GO

PRINT '[OK] Procedure sp_generate_daily_report criada';
GO

-- =============================================================================
-- 9. STORED PROCEDURE: Atualizar posições da fila
-- =============================================================================

CREATE OR ALTER PROCEDURE sp_update_queue_positions
    @queue_name NVARCHAR(100) = 'default'
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Atualizar posições baseado em prioridade e ordem de chegada
    ;WITH RankedQueue AS (
        SELECT 
            id,
            ROW_NUMBER() OVER (ORDER BY priority DESC, entered_at ASC) AS new_position
        FROM queue_entries
        WHERE queue_name = @queue_name AND status = 'waiting'
    )
    UPDATE qe
    SET 
        position = rq.new_position,
        estimated_wait_minutes = dbo.fn_estimate_wait_time(@queue_name, rq.new_position)
    FROM queue_entries qe
    INNER JOIN RankedQueue rq ON qe.id = rq.id;
    
    SELECT @@ROWCOUNT AS updated_entries;
END
GO

PRINT '[OK] Procedure sp_update_queue_positions criada';
GO

-- =============================================================================
-- 10. ÍNDICES PARA PERFORMANCE DE RELATÓRIOS
-- =============================================================================

-- Índice para relatórios por data
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_conv_report_date')
BEGIN
    CREATE NONCLUSTERED INDEX IX_conv_report_date 
    ON conversations(started_at, resolved_at) 
    INCLUDE (state, category, satisfaction_score, message_count, first_response_time, resolution_time);
    PRINT '[OK] Índice IX_conv_report_date criado';
END
GO

-- Índice para busca de mensagens recentes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_msg_recent')
BEGIN
    CREATE NONCLUSTERED INDEX IX_msg_recent
    ON messages(conversation_id, created_at DESC)
    INCLUDE (message_type, content, sender_type);
    PRINT '[OK] Índice IX_msg_recent criado';
END
GO

PRINT '';
PRINT '=============================================================================';
PRINT ' MIGRATION 003 CONCLUÍDA COM SUCESSO!';
PRINT '=============================================================================';
GO
