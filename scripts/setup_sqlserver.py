"""
Script para criar tabelas e usuário de teste no SQL Server
SEMANA 1 - Setup inicial do banco de dados

Execute: python scripts/setup_sqlserver.py
"""
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyodbc
import bcrypt
from app.core.config import settings


def get_connection_string():
    """Construir string de conexão"""
    trust_cert = "Yes" if settings.SQLSERVER_TRUST_CERT else "No"
    
    return (
        f"DRIVER={{{settings.SQLSERVER_DRIVER}}};"
        f"SERVER={settings.SQLSERVER_HOST},{settings.SQLSERVER_PORT};"
        f"DATABASE=master;"  # Conectar ao master primeiro
        f"UID={settings.SQLSERVER_USER};"
        f"PWD={settings.SQLSERVER_PASSWORD};"
        f"TrustServerCertificate={trust_cert};"
    )


def get_db_connection_string():
    """Construir string de conexão para o banco específico"""
    trust_cert = "Yes" if settings.SQLSERVER_TRUST_CERT else "No"
    
    return (
        f"DRIVER={{{settings.SQLSERVER_DRIVER}}};"
        f"SERVER={settings.SQLSERVER_HOST},{settings.SQLSERVER_PORT};"
        f"DATABASE={settings.SQLSERVER_DATABASE};"
        f"UID={settings.SQLSERVER_USER};"
        f"PWD={settings.SQLSERVER_PASSWORD};"
        f"TrustServerCertificate={trust_cert};"
    )


def create_database():
    """Criar banco de dados se não existir"""
    print(f"\n{'='*60}")
    print("SETUP SQL SERVER - Chat WhatsApp")
    print(f"{'='*60}")
    
    print(f"\nConectando ao SQL Server: {settings.SQLSERVER_HOST}:{settings.SQLSERVER_PORT}")
    
    try:
        conn = pyodbc.connect(get_connection_string(), autocommit=True)
        cursor = conn.cursor()
        
        # Verificar se banco existe
        cursor.execute(f"""
            SELECT name FROM sys.databases 
            WHERE name = '{settings.SQLSERVER_DATABASE}'
        """)
        
        if not cursor.fetchone():
            print(f"\nCriando banco de dados: {settings.SQLSERVER_DATABASE}")
            cursor.execute(f"CREATE DATABASE [{settings.SQLSERVER_DATABASE}]")
            print("[OK] Banco de dados criado com sucesso!")
        else:
            print(f"\n[OK] Banco de dados '{settings.SQLSERVER_DATABASE}' já existe")
        
        conn.close()
        return True
        
    except pyodbc.Error as e:
        print(f"\n[ERRO] Falha ao conectar: {e}")
        return False


def create_tables():
    """Criar tabelas necessárias"""
    print(f"\n{'='*60}")
    print("CRIANDO TABELAS")
    print(f"{'='*60}")
    
    try:
        conn = pyodbc.connect(get_db_connection_string())
        cursor = conn.cursor()
        
        # =====================================================================
        # TABELA: usuarios
        # =====================================================================
        print("\n[1/4] Criando tabela 'usuarios'...")
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='usuarios' AND xtype='U')
            CREATE TABLE usuarios (
                id INT IDENTITY(1,1) PRIMARY KEY,
                email NVARCHAR(255) NOT NULL UNIQUE,
                password_hash NVARCHAR(255) NOT NULL,
                nome NVARCHAR(255) NOT NULL,
                role NVARCHAR(50) NOT NULL DEFAULT 'user',
                is_active BIT NOT NULL DEFAULT 1,
                created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                last_login DATETIME2 NULL,
                
                INDEX idx_usuarios_email (email),
                INDEX idx_usuarios_role (role)
            )
        """)
        conn.commit()
        print("      [OK] Tabela 'usuarios' criada/verificada")
        
        # =====================================================================
        # TABELA: audit_logs
        # =====================================================================
        print("\n[2/4] Criando tabela 'audit_logs'...")
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='audit_logs' AND xtype='U')
            CREATE TABLE audit_logs (
                id INT IDENTITY(1,1) PRIMARY KEY,
                event_type NVARCHAR(100) NOT NULL,
                user_id NVARCHAR(50) NULL,
                action NVARCHAR(255) NOT NULL,
                resource_type NVARCHAR(100) NULL,
                resource_id NVARCHAR(100) NULL,
                ip_address NVARCHAR(45) NULL,
                user_agent NVARCHAR(500) NULL,
                status NVARCHAR(50) NULL,
                details NVARCHAR(MAX) NULL,
                entry_hash NVARCHAR(64) NOT NULL,
                previous_hash NVARCHAR(64) NULL,
                created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                
                INDEX idx_audit_event_type (event_type),
                INDEX idx_audit_user_id (user_id),
                INDEX idx_audit_created_at (created_at)
            )
        """)
        conn.commit()
        print("      [OK] Tabela 'audit_logs' criada/verificada")
        
        # =====================================================================
        # TABELA: token_blacklist
        # =====================================================================
        print("\n[3/4] Criando tabela 'token_blacklist'...")
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='token_blacklist' AND xtype='U')
            CREATE TABLE token_blacklist (
                id INT IDENTITY(1,1) PRIMARY KEY,
                token_hash NVARCHAR(64) NOT NULL UNIQUE,
                user_id NVARCHAR(50) NULL,
                revoked_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                expires_at DATETIME2 NOT NULL,
                reason NVARCHAR(255) NULL,
                
                INDEX idx_token_hash (token_hash),
                INDEX idx_token_expires (expires_at)
            )
        """)
        conn.commit()
        print("      [OK] Tabela 'token_blacklist' criada/verificada")
        
        # =====================================================================
        # TABELA: user_consents (LGPD)
        # =====================================================================
        print("\n[4/4] Criando tabela 'user_consents'...")
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_consents' AND xtype='U')
            CREATE TABLE user_consents (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT NOT NULL,
                consent_type NVARCHAR(50) NOT NULL,
                granted BIT NOT NULL DEFAULT 0,
                granted_at DATETIME2 NULL,
                revoked_at DATETIME2 NULL,
                ip_address NVARCHAR(45) NULL,
                
                FOREIGN KEY (user_id) REFERENCES usuarios(id),
                INDEX idx_consent_user (user_id),
                INDEX idx_consent_type (consent_type)
            )
        """)
        conn.commit()
        print("      [OK] Tabela 'user_consents' criada/verificada")
        
        conn.close()
        print(f"\n{'='*60}")
        print("[OK] TODAS AS TABELAS CRIADAS COM SUCESSO!")
        print(f"{'='*60}")
        return True
        
    except pyodbc.Error as e:
        print(f"\n[ERRO] Falha ao criar tabelas: {e}")
        return False


def create_test_user():
    """Criar usuário de teste"""
    print(f"\n{'='*60}")
    print("CRIANDO USUARIO DE TESTE")
    print(f"{'='*60}")
    
    try:
        conn = pyodbc.connect(get_db_connection_string())
        cursor = conn.cursor()
        
        # Dados do usuário teste
        email = "admin@chatwhatsapp.com"
        password = "Admin@123"
        nome = "Administrador"
        role = "admin"
        
        # Verificar se já existe
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"\n[INFO] Usuario '{email}' ja existe (ID: {existing[0]})")
        else:
            # Gerar hash da senha
            salt = bcrypt.gensalt(rounds=12)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            # Inserir usuário
            cursor.execute("""
                INSERT INTO usuarios (email, password_hash, nome, role)
                VALUES (?, ?, ?, ?)
            """, (email, password_hash, nome, role))
            conn.commit()
            
            print(f"\n[OK] Usuario de teste criado!")
        
        # Criar usuário normal também
        email2 = "user@chatwhatsapp.com"
        password2 = "User@123"
        
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email2,))
        if not cursor.fetchone():
            salt = bcrypt.gensalt(rounds=12)
            password_hash2 = bcrypt.hashpw(password2.encode('utf-8'), salt).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO usuarios (email, password_hash, nome, role)
                VALUES (?, ?, ?, ?)
            """, (email2, password_hash2, "Usuario Teste", "user"))
            conn.commit()
            print(f"[OK] Usuario normal criado!")
        
        conn.close()
        
        print(f"\n{'='*60}")
        print("CREDENCIAIS DE TESTE:")
        print(f"{'='*60}")
        print(f"\n  ADMIN:")
        print(f"    Email: admin@chatwhatsapp.com")
        print(f"    Senha: Admin@123")
        print(f"    Role:  admin")
        print(f"\n  USER:")
        print(f"    Email: user@chatwhatsapp.com")
        print(f"    Senha: User@123")
        print(f"    Role:  user")
        print(f"\n{'='*60}")
        
        return True
        
    except pyodbc.Error as e:
        print(f"\n[ERRO] Falha ao criar usuario: {e}")
        return False


def verify_setup():
    """Verificar se tudo foi configurado corretamente"""
    print(f"\n{'='*60}")
    print("VERIFICANDO SETUP")
    print(f"{'='*60}")
    
    try:
        conn = pyodbc.connect(get_db_connection_string())
        cursor = conn.cursor()
        
        # Verificar tabelas
        tables = ['usuarios', 'audit_logs', 'token_blacklist', 'user_consents']
        
        for table in tables:
            cursor.execute(f"""
                SELECT COUNT(*) FROM sysobjects 
                WHERE name='{table}' AND xtype='U'
            """)
            exists = cursor.fetchone()[0] > 0
            status = "[OK]" if exists else "[FALHA]"
            print(f"  {status} Tabela '{table}'")
        
        # Contar usuários
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        user_count = cursor.fetchone()[0]
        print(f"\n  Total de usuarios: {user_count}")
        
        conn.close()
        
        print(f"\n{'='*60}")
        print("[OK] SETUP COMPLETO!")
        print(f"{'='*60}")
        print("\nProximo passo: Testar login via API")
        print("  POST http://localhost:8000/auth/login")
        print('  {"email": "admin@chatwhatsapp.com", "password": "Admin@123"}')
        
        return True
        
    except pyodbc.Error as e:
        print(f"\n[ERRO] Verificacao falhou: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("     SETUP SQL SERVER - SISTEMA CHAT WHATSAPP")
    print("="*60)
    
    # Passo 1: Criar banco
    if not create_database():
        print("\n[ERRO] Falha ao criar banco. Verifique as configuracoes.")
        sys.exit(1)
    
    # Passo 2: Criar tabelas
    if not create_tables():
        print("\n[ERRO] Falha ao criar tabelas.")
        sys.exit(1)
    
    # Passo 3: Criar usuário teste
    if not create_test_user():
        print("\n[ERRO] Falha ao criar usuario teste.")
        sys.exit(1)
    
    # Passo 4: Verificar
    verify_setup()
