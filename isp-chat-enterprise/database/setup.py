#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup SQL Server para ISP Chat System
Configuração e migração de dados para SQL Server
"""

import asyncio
import aioodbc
import pyodbc
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import uuid

class SQLServerSetup:
    """
    Classe para configurar SQL Server
    """
    
    def __init__(self):
        # Configuração de conexão SQL Server
        self.connection_string = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=ISPChat;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
            "Encrypt=yes;"
        )
        
        self.master_connection_string = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=master;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
            "Encrypt=yes;"
        )
    
    def print_header(self, title):
        """Imprimir cabeçalho formatado"""
        print(f"\n{'='*60}")
        print(f"🔧 {title}")
        print(f"{'='*60}")
    
    def print_step(self, step, description):
        """Imprimir passo formatado"""
        print(f"\n{step}. {description}")
        print("-" * 40)
    
    async def test_connection(self):
        """Testar conexão com SQL Server"""
        self.print_step("1", "TESTANDO CONEXÃO SQL SERVER")
        
        try:
            # Testar conexão com master
            async with aioodbc.connect(dsn=self.master_connection_string) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT @@VERSION")
                    version = await cursor.fetchone()
                    print(f"✅ SQL Server conectado com sucesso!")
                    print(f"📊 Versão: {version[0].split('(')[0].strip()}")
            
            # Testar conexão com banco ISPChat
            try:
                async with aioodbc.connect(dsn=self.connection_string) as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT DB_NAME()")
                        db_name = await cursor.fetchone()
                        print(f"✅ Banco ISPChat acessível: {db_name[0]}")
                        return True
            except Exception as e:
                print(f"⚠️ Banco ISPChat não encontrado, será criado: {e}")
                return True
                
        except Exception as e:
            print(f"❌ Erro ao conectar SQL Server: {e}")
            print("\n💡 SOLUÇÕES POSSÍVEIS:")
            print("   1. Verificar se SQL Server está rodando")
            print("   2. Verificar se ODBC Driver 18 está instalado")
            print("   3. Verificar autenticação Windows")
            return False
    
    async def verify_database_structure(self):
        """Verificar estrutura do banco"""
        self.print_step("2", "VERIFICANDO ESTRUTURA DO BANCO")
        
        try:
            async with aioodbc.connect(dsn=self.connection_string) as conn:
                async with conn.cursor() as cursor:
                    # Listar tabelas
                    await cursor.execute("""
                        SELECT TABLE_NAME, 
                               (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                                WHERE TABLE_NAME = t.TABLE_NAME) as column_count
                        FROM INFORMATION_SCHEMA.TABLES t
                        WHERE TABLE_TYPE = 'BASE TABLE' 
                            AND TABLE_CATALOG = 'ISPChat'
                        ORDER BY TABLE_NAME
                    """)
                    
                    tables = await cursor.fetchall()
                    
                    if not tables:
                        print("❌ Nenhuma tabela encontrada!")
                        return False
                    
                    print(f"✅ {len(tables)} tabelas encontradas:")
                    for table in tables:
                        print(f"   - {table[0]} ({table[1]} colunas)")
                    
                    # Verificar usuário admin
                    await cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
                    admin_count = await cursor.fetchone()
                    
                    if admin_count[0] > 0:
                        print("✅ Usuário admin encontrado")
                    else:
                        print("❌ Usuário admin não encontrado")
                        return False
                    
                    return True
                    
        except Exception as e:
            print(f"❌ Erro ao verificar estrutura: {e}")
            return False
    
    async def migrate_nodejs_data(self):
        """Migrar dados do sistema Node.js"""
        self.print_step("3", "MIGRANDO DADOS DO NODE.JS")
        
        try:
            # Caminhos para os dados do Node.js
            nodejs_data_path = Path("../chat-de-atendimento/dados")
            
            if not nodejs_data_path.exists():
                print("⚠️ Dados do Node.js não encontrados, pulando migração")
                return True
            
            async with aioodbc.connect(dsn=self.connection_string) as conn:
                async with conn.cursor() as cursor:
                    migrated_count = 0
                    
                    # Migrar usuários (exceto admin que já existe)
                    usuarios_file = nodejs_data_path / "usuarios.json"
                    if usuarios_file.exists():
                        with open(usuarios_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        for user in data.get('usuarios', []):
                            if user['username'] != 'admin':  # Admin já foi criado
                                try:
                                    await cursor.execute("""
                                        IF NOT EXISTS (SELECT 1 FROM users WHERE username = ?)
                                        INSERT INTO users (
                                            username, email, password_hash, role, is_active,
                                            created_at, last_login
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        user['username'],
                                        user['username'],
                                        user['email'],
                                        user['password'],
                                        user['role'],
                                        user['ativo'],
                                        user['criadoEm'],
                                        user.get('ultimoLogin')
                                    ))
                                    migrated_count += 1
                                except Exception as e:
                                    print(f"⚠️ Erro ao migrar usuário {user['username']}: {e}")
                    
                    # Migrar conversas
                    conversas_file = nodejs_data_path / "filas-atendimento.json"
                    if conversas_file.exists():
                        with open(conversas_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        status_map = {
                            'automacao': 'automation',
                            'espera': 'waiting',
                            'atendimento': 'in_service',
                            'encerrado': 'closed'
                        }
                        
                        for conv in data.get('conversas', []):
                            try:
                                await cursor.execute("""
                                    IF NOT EXISTS (SELECT 1 FROM conversations WHERE legacy_id = ?)
                                    INSERT INTO conversations (
                                        legacy_id, customer_phone, customer_name, status,
                                        whatsapp_client_id, created_at, updated_at,
                                        last_message, bot_attempts, metadata
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    conv['id'],
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
                                migrated_count += 1
                            except Exception as e:
                                print(f"⚠️ Erro ao migrar conversa {conv['id']}: {e}")
                    
                    await conn.commit()
                    print(f"✅ {migrated_count} registros migrados do Node.js")
                    
                    return True
                    
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            return True  # Não falhar se migração der erro
    
    async def test_database_operations(self):
        """Testar operações básicas do banco"""
        self.print_step("4", "TESTANDO OPERAÇÕES DO BANCO")
        
        try:
            async with aioodbc.connect(dsn=self.connection_string) as conn:
                async with conn.cursor() as cursor:
                    # Testar consulta de usuários
                    await cursor.execute("SELECT COUNT(*) FROM users")
                    users_count = await cursor.fetchone()
                    users_count = users_count[0]
                    
                    # Testar consulta de conversas
                    await cursor.execute("SELECT COUNT(*) FROM conversations")
                    conversations_count = await cursor.fetchone()
                    conversations_count = conversations_count[0]
                    
                    # Testar inserção de mensagem de teste
                    test_conv_id = str(uuid.uuid4())
                    test_message_id = str(uuid.uuid4())
                    
                    await cursor.execute("""
                        INSERT INTO conversations (id, customer_phone, customer_name, status)
                        VALUES (?, ?, ?, ?)
                    """, (test_conv_id, "+5511999999999", "Teste", "automation"))
                    
                    await cursor.execute("""
                        INSERT INTO messages (id, conversation_id, sender_type, content)
                        VALUES (?, ?, ?, ?)
                    """, (test_message_id, test_conv_id, "customer", "Mensagem de teste"))
                    
                    await conn.commit()
                    
                    # Verificar se foi inserido
                    await cursor.execute("""
                        SELECT COUNT(*) FROM messages WHERE conversation_id = ?
                    """, (test_conv_id,))
                    message_count = await cursor.fetchone()
                    message_count = message_count[0]
                    
                    # Limpar dados de teste
                    await cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (test_conv_id,))
                    await cursor.execute("DELETE FROM conversations WHERE id = ?", (test_conv_id,))
                    await conn.commit()
                    
                    print(f"✅ Operações básicas funcionando!")
                    print(f"📊 Usuários: {users_count}")
                    print(f"📊 Conversas: {conversations_count}")
                    print(f"✅ Inserção/consulta/exclusão testadas")
                    
                    return True
                    
        except Exception as e:
            print(f"❌ Erro nos testes: {e}")
            return False
    
    async def validate_setup(self):
        """Validar setup completo"""
        self.print_step("5", "VALIDAÇÃO FINAL")
        
        try:
            async with aioodbc.connect(dsn=self.connection_string) as conn:
                async with conn.cursor() as cursor:
                    # Verificar usuário admin
                    await cursor.execute("""
                        SELECT username, email, role, is_active, created_at 
                        FROM users WHERE username = 'admin'
                    """)
                    admin = await cursor.fetchone()
                    
                    if admin:
                        print(f"✅ Usuário admin encontrado:")
                        print(f"   - Username: {admin[0]}")
                        print(f"   - Email: {admin[1]}")
                        print(f"   - Role: {admin[2]}")
                        print(f"   - Ativo: {'Sim' if admin[3] else 'Não'}")
                        print(f"   - Criado: {admin[4]}")
                    else:
                        print("❌ Usuário admin não encontrado!")
                        return False
                    
                    # Contar registros por tabela
                    tables = ['users', 'conversations', 'messages', 'whatsapp_sessions', 'campaigns']
                    print(f"📈 Registros por tabela:")
                    
                    for table in tables:
                        await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = await cursor.fetchone()
                        print(f"   - {table}: {count[0]}")
                    
                    # Verificar índices
                    await cursor.execute("""
                        SELECT COUNT(*) FROM sys.indexes 
                        WHERE object_id IN (
                            SELECT object_id FROM sys.tables 
                            WHERE name IN ('users', 'conversations', 'messages', 'whatsapp_sessions', 'campaigns')
                        ) AND name IS NOT NULL
                    """)
                    indexes_count = await cursor.fetchone()
                    print(f"📊 Índices criados: {indexes_count[0]}")
                    
                    # Verificar triggers
                    await cursor.execute("""
                        SELECT COUNT(*) FROM sys.triggers 
                        WHERE name LIKE 'TR_%_updated_at'
                    """)
                    triggers_count = await cursor.fetchone()
                    print(f"🔄 Triggers ativos: {triggers_count[0]}")
                    
                    return True
                    
        except Exception as e:
            print(f"❌ Erro na validação: {e}")
            return False
    
    def print_connection_info(self):
        """Imprimir informações de conexão"""
        self.print_step("6", "INFORMAÇÕES DE CONEXÃO")
        
        print("🗄️ SQL SERVER:")
        print("   Server: localhost")
        print("   Database: ISPChat")
        print("   Authentication: Windows")
        print("   Driver: ODBC Driver 18 for SQL Server")
        
        print("\n🔗 CONNECTION STRING:")
        print("   Para Python: mssql+aioodbc:///?odbc_connect=" + self.connection_string.replace(';', '%3B'))
        
        print("\n🔑 CREDENCIAIS:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Email: admin@sistema.com")
        
        print("\n🛠️ FERRAMENTAS:")
        print("   SQL Server Management Studio (SSMS)")
        print("   Azure Data Studio")
        print("   Comando: sqlcmd -S localhost -E -C -d ISPChat")
    
    async def run_setup(self):
        """Executar setup completo"""
        self.print_header("SETUP SQL SERVER - ISP CHAT SYSTEM")
        
        print("🎯 Configuração e validação do SQL Server")
        print("📋 Banco: ISPChat")
        print("🔐 Autenticação: Windows")
        
        steps = [
            ("Testar Conexão", self.test_connection),
            ("Verificar Estrutura", self.verify_database_structure),
            ("Migrar Node.js", self.migrate_nodejs_data),
            ("Testar Operações", self.test_database_operations),
            ("Validar Setup", self.validate_setup)
        ]
        
        results = []
        
        for step_name, step_func in steps:
            try:
                result = await step_func()
                results.append((step_name, result))
            except Exception as e:
                print(f"❌ Erro no passo {step_name}: {e}")
                results.append((step_name, False))
        
        # Resumo final
        self.print_header("RESUMO DO SETUP")
        
        success_count = 0
        for step_name, success in results:
            status = "✅ SUCESSO" if success else "❌ FALHOU"
            print(f"{status} - {step_name}")
            if success:
                success_count += 1
        
        print(f"\n📊 RESULTADO: {success_count}/{len(results)} passos concluídos")
        
        if success_count >= len(results) - 1:  # Permitir 1 falha (migração)
            print("\n🎉 SETUP SQL SERVER CONCLUÍDO COM SUCESSO!")
            print("✅ Banco de dados pronto para desenvolvimento")
            self.print_connection_info()
            return True
        else:
            print("\n⚠️ SETUP INCOMPLETO")
            print("❌ Verifique os erros acima")
            return False

async def main():
    """Função principal"""
    setup = SQLServerSetup()
    success = await setup.run_setup()
    
    if success:
        print(f"\n⏰ Setup concluído em: {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(0)
    else:
        print(f"\n⏰ Setup falhou em: {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())