import json
import asyncio
import asyncpg
from datetime import datetime
import os

async def migrate_users():
    """Migrar usuários do dados/usuarios.json para PostgreSQL"""
    
    # Caminho para o sistema Node.js atual
    nodejs_path = "../dados/usuarios.json"
    
    if not os.path.exists(nodejs_path):
        print("❌ Arquivo usuarios.json não encontrado!")
        return False
    
    # Ler dados do Node.js
    with open(nodejs_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Conectar PostgreSQL
    conn = await asyncpg.connect('postgresql://postgres:postgres123@localhost:5432/isp_chat')
    
    try:
        # Limpar tabela (apenas para desenvolvimento)
        await conn.execute("DELETE FROM users WHERE username != 'admin'")
        
        migrated = 0
        for user in data['usuarios']:
            try:
                await conn.execute("""
                    INSERT INTO users (username, email, password_hash, role, is_active, created_at, last_login)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (username) DO UPDATE SET
                        email = EXCLUDED.email,
                        password_hash = EXCLUDED.password_hash,
                        role = EXCLUDED.role,
                        is_active = EXCLUDED.is_active,
                        last_login = EXCLUDED.last_login
                """, 
                user['username'], 
                user['email'], 
                user['password'], 
                user['role'], 
                user['ativo'], 
                datetime.fromisoformat(user['criadoEm'].replace('Z', '+00:00')),
                datetime.fromisoformat(user['ultimoLogin'].replace('Z', '+00:00')) if user.get('ultimoLogin') else None
                )
                migrated += 1
                print(f"✅ Usuário migrado: {user['username']}")
            except Exception as e:
                print(f"❌ Erro ao migrar usuário {user['username']}: {e}")
        
        print(f"🎉 {migrated} usuários migrados com sucesso!")
        return True
        
    finally:
        await conn.close()

async def migrate_conversations():
    """Migrar conversas do dados/filas-atendimento.json para PostgreSQL"""
    
    nodejs_path = "../dados/filas-atendimento.json"
    
    if not os.path.exists(nodejs_path):
        print("❌ Arquivo filas-atendimento.json não encontrado!")
        return False
    
    with open(nodejs_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    conn = await asyncpg.connect('postgresql://postgres:postgres123@localhost:5432/isp_chat')
    
    try:
        # Limpar tabela
        await conn.execute("DELETE FROM conversations")
        
        migrated = 0
        for conv in data['conversas']:
            try:
                # Mapear estados
                status_map = {
                    'automacao': 'automation',
                    'espera': 'waiting',
                    'atendimento': 'in_service',
                    'encerrado': 'closed'
                }
                
                await conn.execute("""
                    INSERT INTO conversations (
                        legacy_id, customer_phone, customer_name, status, 
                        whatsapp_client_id, created_at, updated_at, 
                        last_message, bot_attempts, metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                conv['id'],
                conv['chatId'],
                conv['metadata'].get('nomeContato'),
                status_map.get(conv['estado'], 'automation'),
                conv['clientId'],
                datetime.fromisoformat(conv['criadoEm'].replace('Z', '+00:00')),
                datetime.fromisoformat(conv['atualizadoEm'].replace('Z', '+00:00')),
                conv['metadata'].get('ultimaMensagem'),
                conv['tentativasBot'],
                json.dumps(conv['metadata'])
                )
                migrated += 1
                print(f"✅ Conversa migrada: {conv['chatId']}")
            except Exception as e:
                print(f"❌ Erro ao migrar conversa {conv['id']}: {e}")
        
        print(f"🎉 {migrated} conversas migradas com sucesso!")
        return True
        
    finally:
        await conn.close()

async def validate_migration():
    """Validar integridade da migração"""
    conn = await asyncpg.connect('postgresql://postgres:postgres123@localhost:5432/isp_chat')
    
    try:
        # Contar registros
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        conversations_count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        
        print(f"📊 Usuários migrados: {users_count}")
        print(f"📊 Conversas migradas: {conversations_count}")
        
        # Testar consultas básicas
        admin_user = await conn.fetchrow("SELECT * FROM users WHERE username = 'admin'")
        if admin_user:
            print("✅ Usuário admin encontrado")
        else:
            print("❌ Usuário admin não encontrado!")
        
        return True
        
    finally:
        await conn.close()

async def main():
    print("🚀 Iniciando migração de dados do Node.js para Python...")
    
    # Migrar usuários
    print("\n1️⃣ Migrando usuários...")
    await migrate_users()
    
    # Migrar conversas
    print("\n2️⃣ Migrando conversas...")
    await migrate_conversations()
    
    # Validar migração
    print("\n3️⃣ Validando migração...")
    await validate_migration()
    
    print("\n🎉 Migração concluída!")

if __name__ == "__main__":
    asyncio.run(main())