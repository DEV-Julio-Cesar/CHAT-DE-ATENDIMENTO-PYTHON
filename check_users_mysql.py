"""Script para verificar e criar usuários no MySQL"""
import asyncio
import aiomysql
from passlib.context import CryptContext

# Configurar hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def check_and_create_users():
    """Verificar e criar usuários"""
    # Conectar ao MySQL
    conn = await aiomysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='BemVindo!',
        db='cianet_provedor'
    )
    
    try:
        async with conn.cursor() as cursor:
            # Verificar usuários existentes
            await cursor.execute("SELECT email, username, role, ativo FROM usuarios")
            users = await cursor.fetchall()
            
            if not users:
                print("❌ Nenhum usuário cadastrado no banco!")
                print("\n🔧 Criando usuário admin...")
                
                # Hash da senha
                senha_hash = pwd_context.hash("Admin@123")
                
                # Inserir usuário admin
                import uuid
                user_id = str(uuid.uuid4())
                
                await cursor.execute("""
                    INSERT INTO usuarios (id, username, email, password_hash, role, ativo, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (user_id, 'admin', 'admin@empresa.com.br', senha_hash, 'admin', 1))
                
                await conn.commit()
                
                print("✅ Usuário admin criado com sucesso!")
                print(f"   📧 Email: admin@empresa.com.br")
                print(f"   🔑 Senha: Admin@123")
                print(f"   👤 Role: admin")
            else:
                print(f"✅ {len(users)} usuário(s) encontrado(s):\n")
                for user in users:
                    email, username, role, ativo = user
                    print(f"📧 Email: {email}")
                    print(f"   Username: {username}")
                    print(f"   Role: {role}")
                    print(f"   Ativo: {'Sim' if ativo else 'Não'}")
                    print()
                
                print("\n🔑 Credenciais padrão:")
                print("   Email: admin@empresa.com.br")
                print("   Senha: Admin@123")
    
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(check_and_create_users())
