"""Script para verificar usuários no banco de dados"""
import asyncio
from app.core.database import db_manager
from app.models.database import Usuario
from sqlalchemy import select

async def check_users():
    """Verificar usuários cadastrados"""
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        result = await session.execute(select(Usuario))
        users = result.scalars().all()
        
        if not users:
            print("❌ Nenhum usuário cadastrado no banco!")
            print("\nVou criar o usuário admin...")
            
            # Criar usuário admin
            from app.core.security import get_password_hash
            
            admin = Usuario(
                email="admin@empresa.com.br",
                nome="Administrador",
                senha_hash=get_password_hash("Admin@123"),
                role="admin",
                ativo=True
            )
            
            session.add(admin)
            await session.commit()
            print("✅ Usuário admin criado com sucesso!")
            print(f"   Email: admin@empresa.com.br")
            print(f"   Senha: Admin@123")
        else:
            print(f"✅ {len(users)} usuário(s) encontrado(s):\n")
            for user in users:
                print(f"📧 Email: {user.email}")
                print(f"   Nome: {user.nome}")
                print(f"   Role: {user.role}")
                print(f"   Ativo: {user.ativo}")
                print()
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_users())
