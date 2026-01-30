-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tipos enumerados
CREATE TYPE user_role AS ENUM ('admin', 'supervisor', 'agent', 'viewer');
CREATE TYPE conversation_status AS ENUM ('automation', 'waiting', 'in_service', 'closed');

-- Tabela de usuários (migração do dados/usuarios.json)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'agent',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Migrar usuário admin do sistema atual
INSERT INTO users (username, email, password_hash, role, is_active, last_login)
VALUES ('admin', 'admin@sistema.com', '$2a$10$Cmu1DBIKIwpBB29IJMfN1uXu3QalrDOq7.j4mV.XzrKU/N0Nh7nam', 'admin', true, '2026-01-18T12:45:27.102Z');

-- Tabela de conversas (migração do dados/filas-atendimento.json)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legacy_id VARCHAR(255), -- Para manter referência ao sistema antigo
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),
    status conversation_status NOT NULL DEFAULT 'automation',
    agent_id UUID REFERENCES users(id),
    whatsapp_client_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message TEXT,
    bot_attempts INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- Índices para performance
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_agent ON conversations(agent_id);
CREATE INDEX idx_conversations_customer ON conversations(customer_phone);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

-- Tabela de mensagens
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL, -- 'customer', 'agent', 'bot', 'system'
    sender_id UUID,
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);