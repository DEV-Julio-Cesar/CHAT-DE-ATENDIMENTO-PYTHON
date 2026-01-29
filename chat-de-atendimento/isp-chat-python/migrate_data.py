#!/usr/bin/env python3
"""
Migração de dados do sistema Node.js para Python
"""
import json
import sqlite3
import os
from datetime import datetime
import uuid

def create_sqlite_database():
    """Criar banco SQLite com schema básico"""
    conn = sqlite3.connect('isp_chat.db')
    cursor = conn.cursor()
    
    # Criar tabelas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'agent',
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            legacy_id TEXT,
            customer_phone TEXT NOT NULL,
            customer_name TEXT,
            status TEXT NOT NULL DEFAULT 'automation',
            agent_id TEXT,
            whatsapp_client_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_message TEXT,
            bot_attempts INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            sender_id TEXT,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    ''')
    
    conn.commit()
    return conn

def migrate_users(conn):
    """Migrar usuários do JSON para SQLite"""
    print("🔄 Migrando usuários...")
    
    # Caminho para dados do Node.js
    users_file = "../dados/usuarios.json"
    
    if not os.path.exists(users_file):
        print(f"❌ Arquivo não encontrado: {users_file}")
        return False
    
    with open(users_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cursor = conn.cursor()
    migrated = 0
    
    for user in data['usuarios']:
        try:
            user_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (id, username, email, password_hash, role, is_active, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                user['username'],
                user['email'],
                user['password'],
                user['role'],
                user['ativo'],
                user['criadoEm'],
                user.get('ultimoLogin')
            ))
            migrated += 1
            print(f"✅ Usuário migrado: {user['username']}")
        except Exception as e:
            print(f"❌ Erro ao migrar usuário {user['username']}: {e}")
    
    conn.commit()
    print(f"🎉 {migrated} usuários migrados!")
    return True

def migrate_conversations(conn):
    """Migrar conversas do JSON para SQLite"""
    print("\n🔄 Migrando conversas...")
    
    conversations_file = "../dados/filas-atendimento.json"
    
    if not os.path.exists(conversations_file):
        print(f"❌ Arquivo não encontrado: {conversations_file}")
        return False
    
    with open(conversations_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cursor = conn.cursor()
    migrated = 0
    
    # Mapear estados
    status_map = {
        'automacao': 'automation',
        'espera': 'waiting',
        'atendimento': 'in_service',
        'encerrado': 'closed'
    }
    
    for conv in data['conversas']:
        try:
            conv_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT OR REPLACE INTO conversations 
                (id, legacy_id, customer_phone, customer_name, status, 
                 whatsapp_client_id, created_at, updated_at, 
                 last_message, bot_attempts, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                conv_id,
                conv['id'],
                conv['chatId'],
                conv['metadata'].get('nomeContato'),
                status_map.get(conv['estado'], 'automation'),
                conv['clientId'],
                conv['criadoEm'],
                conv['atualizadoEm'],
                conv['metadata'].get('ultimaMensagem'),
                conv['tentativasBot'],
                json.dumps(conv['metadata'])
            ))
            migrated += 1
            print(f"✅ Conversa migrada: {conv['chatId']}")
        except Exception as e:
            print(f"❌ Erro ao migrar conversa {conv['id']}: {e}")
    
    conn.commit()
    print(f"🎉 {migrated} conversas migradas!")
    return True

def validate_migration(conn):
    """Validar migração"""
    print("\n🔍 Validando migração...")
    
    cursor = conn.cursor()
    
    # Contar registros
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversations")
    conversations_count = cursor.fetchone()[0]
    
    print(f"📊 Usuários: {users_count}")
    print(f"📊 Conversas: {conversations_count}")
    
    # Verificar usuário admin
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    
    if admin:
        print("✅ Usuário admin encontrado")
        print(f"   ID: {admin[0]}")
        print(f"   Email: {admin[2]}")
        print(f"   Role: {admin[4]}")
    else:
        print("❌ Usuário admin não encontrado!")
    
    return True

def main():
    """Função principal"""
    print("🚀 Iniciando migração de dados Node.js → Python")
    print("📁 Usando SQLite temporariamente (migraremos para PostgreSQL depois)")
    
    try:
        # Criar banco
        conn = create_sqlite_database()
        print("✅ Banco SQLite criado")
        
        # Migrar dados
        migrate_users(conn)
        migrate_conversations(conn)
        
        # Validar
        validate_migration(conn)
        
        conn.close()
        print("\n🎉 Migração concluída com sucesso!")
        print("📄 Banco criado: isp_chat.db")
        print("🔄 Próximo passo: Atualizar Auth Service para usar SQLite")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Migração bem-sucedida!")
    else:
        print("\n❌ Migração falhou!")