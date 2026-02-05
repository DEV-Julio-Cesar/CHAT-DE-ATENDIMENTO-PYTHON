-- Script para criar todas as tabelas do sistema CIANET PROVEDOR no MariaDB/MySQL
-- Salve este arquivo e execute no seu banco usando um cliente MySQL/MariaDB

DATABASE_URL: str = "mysql+aiomysql://root:BemVindo!@localhost:3306/cianet_provedor"

-- Usuários
CREATE TABLE usuarios (
    id CHAR(36) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','atendente','supervisor') NOT NULL DEFAULT 'atendente',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ultimo_login DATETIME NULL
);

-- Clientes WhatsApp
CREATE TABLE clientes_whatsapp (
    id CHAR(36) PRIMARY KEY,
    client_id VARCHAR(100) NOT NULL UNIQUE,
    nome VARCHAR(255) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    status ENUM('ativo','inativo','suspenso') NOT NULL DEFAULT 'ativo',
    servidor_id VARCHAR(50),
    client_metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cliente_telefone_status (telefone, status),
    INDEX idx_cliente_servidor (servidor_id)
);

-- Conversas
CREATE TABLE conversas (
    id CHAR(36) PRIMARY KEY,
    cliente_id CHAR(36) NOT NULL,
    chat_id VARCHAR(255) NOT NULL,
    estado ENUM('automacao','espera','atendimento','encerrado') NOT NULL DEFAULT 'automacao',
    atendente_id CHAR(36),
    tentativas_bot INT NOT NULL DEFAULT 0,
    prioridade INT NOT NULL DEFAULT 0,
    tags JSON,
    conversation_metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    encerrada_em DATETIME,
    FOREIGN KEY (cliente_id) REFERENCES clientes_whatsapp(id),
    FOREIGN KEY (atendente_id) REFERENCES usuarios(id),
    INDEX idx_conversa_cliente_estado (cliente_id, estado),
    INDEX idx_conversa_atendente_ativo (atendente_id, estado),
    INDEX idx_conversa_chat_id (chat_id),
    INDEX idx_conversa_estado_prioridade (estado, prioridade),
    INDEX idx_conversa_created_at (created_at),
    INDEX idx_conversa_updated_at (updated_at)
);

-- Mensagens
CREATE TABLE mensagens (
    id CHAR(36) PRIMARY KEY,
    conversa_id CHAR(36) NOT NULL,
    whatsapp_message_id VARCHAR(255),
    remetente_tipo ENUM('cliente','atendente','bot','sistema') NOT NULL,
    remetente_id VARCHAR(255),
    conteudo TEXT,
    conteudo_criptografado TEXT,
    iv VARCHAR(255),
    tipo_criptografia VARCHAR(50) DEFAULT 'AES-256-CBC',
    tipo_mensagem ENUM('texto','imagem','documento','audio','video') NOT NULL DEFAULT 'texto',
    arquivo_url VARCHAR(500),
    message_metadata JSON,
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversa_id) REFERENCES conversas(id),
    INDEX idx_mensagem_conversa_data (conversa_id, created_at),
    INDEX idx_mensagem_whatsapp_id (whatsapp_message_id),
    INDEX idx_mensagem_remetente (remetente_tipo, remetente_id),
    INDEX idx_mensagem_tipo_data (tipo_mensagem, created_at),
    INDEX idx_mensagem_lida (lida, created_at)
);

-- Campanhas
CREATE TABLE campanhas (
    id CHAR(36) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    mensagem_template TEXT NOT NULL,
    criador_id CHAR(36) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'rascunho',
    agendada_para DATETIME,
    total_destinatarios INT NOT NULL DEFAULT 0,
    enviadas INT NOT NULL DEFAULT 0,
    falharam INT NOT NULL DEFAULT 0,
    campaign_metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    finalizada_em DATETIME,
    FOREIGN KEY (criador_id) REFERENCES usuarios(id)
);

-- Envios de Campanha
CREATE TABLE envios_campanha (
    id CHAR(36) PRIMARY KEY,
    campanha_id CHAR(36) NOT NULL,
    destinatario_telefone VARCHAR(20) NOT NULL,
    destinatario_nome VARCHAR(255),
    mensagem_personalizada TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pendente',
    whatsapp_message_id VARCHAR(255),
    erro_detalhes TEXT,
    enviado_em DATETIME,
    entregue_em DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campanha_id) REFERENCES campanhas(id),
    INDEX idx_envio_campanha_status (campanha_id, status),
    INDEX idx_envio_telefone (destinatario_telefone)
);

-- Configurações do Sistema
CREATE TABLE configuracoes_sistema (
    id CHAR(36) PRIMARY KEY,
    chave VARCHAR(100) NOT NULL UNIQUE,
    valor JSON NOT NULL,
    descricao TEXT,
    categoria VARCHAR(50) NOT NULL DEFAULT 'geral',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Logs de Auditoria
CREATE TABLE logs_auditoria (
    id CHAR(36) PRIMARY KEY,
    usuario_id CHAR(36),
    acao VARCHAR(100) NOT NULL,
    recurso VARCHAR(100) NOT NULL,
    recurso_id VARCHAR(255),
    detalhes JSON,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_auditoria_usuario_acao (usuario_id, acao),
    INDEX idx_auditoria_recurso (recurso, recurso_id),
    INDEX idx_auditoria_created_at (created_at)
);

-- AuditLogEnhanced (blockchain-like)
CREATE TABLE audit_logs_enhanced (
    id CHAR(36) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    user_id CHAR(36),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'success',
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details JSON,
    entry_hash VARCHAR(64) NOT NULL UNIQUE,
    previous_hash VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES usuarios(id),
    INDEX idx_audit_enhanced_event_type (event_type, created_at),
    INDEX idx_audit_enhanced_user_action (user_id, action),
    INDEX idx_audit_enhanced_resource (resource_type, resource_id),
    INDEX idx_audit_enhanced_hash_chain (entry_hash, previous_hash)
);

-- GDPR Requests
CREATE TABLE gdpr_requests (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    request_type ENUM('deletion','export','consent') NOT NULL,
    status ENUM('pending','confirmation_sent','in_progress','completed','cancelled','failed') DEFAULT 'pending',
    reason TEXT,
    confirmation_token VARCHAR(255) UNIQUE,
    confirmation_token_expires_at DATETIME,
    confirmed_at DATETIME,
    backup_id VARCHAR(255),
    backup_retention_until DATETIME,
    requested_by VARCHAR(255) NOT NULL,
    processed_by VARCHAR(255),
    details JSON,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES usuarios(id),
    INDEX idx_gdpr_user_status (user_id, status),
    INDEX idx_gdpr_request_type (request_type, created_at),
    INDEX idx_gdpr_confirmation_token (confirmation_token)
);

-- User Consent
CREATE TABLE user_consents (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    consent_type ENUM('marketing','analytics','data_processing','third_party') NOT NULL,
    granted BOOLEAN NOT NULL DEFAULT FALSE,
    version INT NOT NULL DEFAULT 1,
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_at DATETIME,
    withdrawn_at DATETIME,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    description TEXT,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES usuarios(id),
    INDEX idx_consent_user_type (user_id, consent_type),
    INDEX idx_consent_granted (granted, created_at),
    INDEX idx_consent_expires (expires_at)
);

-- Token Blacklist
CREATE TABLE token_blacklists (
    id CHAR(36) PRIMARY KEY,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    user_id CHAR(36),
    reason VARCHAR(100) DEFAULT 'logout',
    revoked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    FOREIGN KEY (user_id) REFERENCES usuarios(id),
    INDEX idx_token_blacklist_expires (expires_at),
    INDEX idx_token_blacklist_user (user_id, revoked_at)
);
