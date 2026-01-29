-- Inicialização do banco de dados PostgreSQL

-- Criar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Criar tipos enum
CREATE TYPE user_role AS ENUM ('admin', 'supervisor', 'atendente');
CREATE TYPE client_status AS ENUM ('ativo', 'inativo', 'suspenso');
CREATE TYPE conversation_state AS ENUM ('automacao', 'espera', 'atendimento', 'encerrado');
CREATE TYPE message_type AS ENUM ('texto', 'imagem', 'documento', 'audio', 'video');
CREATE TYPE sender_type AS ENUM ('cliente', 'atendente', 'bot', 'sistema');

-- Configurações de performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Configurações de logging
ALTER SYSTEM SET log_destination = 'stderr';
ALTER SYSTEM SET logging_collector = on;
ALTER SYSTEM SET log_directory = 'pg_log';
ALTER SYSTEM SET log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log';
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Criar usuário para a aplicação (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'isp_app') THEN
        CREATE ROLE isp_app WITH LOGIN PASSWORD 'app_password';
    END IF;
END
$$;

-- Conceder permissões
GRANT CONNECT ON DATABASE isp_support TO isp_app;
GRANT USAGE ON SCHEMA public TO isp_app;
GRANT CREATE ON SCHEMA public TO isp_app;

-- Criar função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Inserir usuário admin padrão (será criado pela aplicação)
-- Password: admin123 (hash será gerado pela aplicação)
INSERT INTO usuarios (id, username, email, password_hash, role, ativo, created_at)
VALUES (
    uuid_generate_v4(),
    'admin',
    'admin@sistema.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.',  -- admin123
    'admin',
    true,
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- Inserir configurações padrão do sistema
INSERT INTO configuracoes_sistema (id, chave, valor, descricao, categoria, created_at)
VALUES 
    (uuid_generate_v4(), 'max_whatsapp_clients', '10000', 'Máximo de clientes WhatsApp simultâneos', 'whatsapp', NOW()),
    (uuid_generate_v4(), 'max_bot_attempts', '3', 'Máximo de tentativas do bot antes de escalar', 'chatbot', NOW()),
    (uuid_generate_v4(), 'business_hours_start', '8', 'Hora de início do atendimento', 'horario', NOW()),
    (uuid_generate_v4(), 'business_hours_end', '18', 'Hora de fim do atendimento', 'horario', NOW()),
    (uuid_generate_v4(), 'rate_limit_per_minute', '100', 'Limite de requests por minuto', 'seguranca', NOW()),
    (uuid_generate_v4(), 'session_timeout_minutes', '1440', 'Timeout de sessão em minutos', 'seguranca', NOW()),
    (uuid_generate_v4(), 'backup_enabled', 'true', 'Backup automático habilitado', 'backup', NOW()),
    (uuid_generate_v4(), 'backup_retention_days', '30', 'Dias de retenção de backup', 'backup', NOW())
ON CONFLICT (chave) DO NOTHING;

-- Criar índices adicionais para performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usuarios_email_ativo ON usuarios(email, ativo);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usuarios_role_ativo ON usuarios(role, ativo);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clientes_status_servidor ON clientes_whatsapp(status, servidor_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversas_estado_created ON conversas(estado, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mensagens_created_at ON mensagens(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campanhas_status_created ON campanhas(status, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_envios_status_created ON envios_campanha(status, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_auditoria_created_at ON logs_auditoria(created_at);

-- Criar partições para tabelas grandes (mensagens por mês)
-- Exemplo para 2024
CREATE TABLE IF NOT EXISTS mensagens_2024_01 PARTITION OF mensagens
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_02 PARTITION OF mensagens
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_03 PARTITION OF mensagens
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_04 PARTITION OF mensagens
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_05 PARTITION OF mensagens
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_06 PARTITION OF mensagens
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_07 PARTITION OF mensagens
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_08 PARTITION OF mensagens
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_09 PARTITION OF mensagens
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_10 PARTITION OF mensagens
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_11 PARTITION OF mensagens
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE IF NOT EXISTS mensagens_2024_12 PARTITION OF mensagens
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- Função para criar partições automaticamente
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Criar função para limpeza automática de dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Limpar logs de auditoria com mais de 1 ano
    DELETE FROM logs_auditoria WHERE created_at < NOW() - INTERVAL '1 year';
    
    -- Limpar mensagens com mais de 2 anos (manter apenas metadados)
    DELETE FROM mensagens WHERE created_at < NOW() - INTERVAL '2 years';
    
    -- Limpar conversas encerradas com mais de 1 ano
    DELETE FROM conversas WHERE estado = 'encerrado' AND encerrada_em < NOW() - INTERVAL '1 year';
    
    -- Limpar campanhas finalizadas com mais de 6 meses
    DELETE FROM campanhas WHERE status = 'finalizada' AND finalizada_em < NOW() - INTERVAL '6 months';
END;
$$ LANGUAGE plpgsql;

-- Criar job de limpeza (requer pg_cron extension)
-- SELECT cron.schedule('cleanup-old-data', '0 2 * * 0', 'SELECT cleanup_old_data();');

-- Estatísticas iniciais
ANALYZE;