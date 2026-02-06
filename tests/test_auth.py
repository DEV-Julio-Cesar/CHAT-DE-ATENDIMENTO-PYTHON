"""Teste completo de autenticação SQL Server"""
import sys
sys.path.insert(0, '.')
from app.core.sqlserver_db import SQLServerManager

sql = SQLServerManager()
print('=== TESTE COMPLETO DE AUTENTICACAO ===')
print()

# Testar conexao
if sql.test_connection():
    print('[OK] Conexao com SQL Server')
else:
    print('[ERRO] Falha na conexao')
    exit(1)

# Testar busca de usuario
user = sql.get_user_by_email('admin@sistema.local')
if user:
    print(f'[OK] Usuario encontrado: {user["email"]} (role: {user["role"]})')
else:
    print('[ERRO] Usuario nao encontrado')
    exit(1)

# Testar verificacao de senha (usando plain_password e hashed_password)
if sql.verify_password('Admin@123', user["password_hash"]):
    print('[OK] Verificacao de senha direta OK')
else:
    print('[ERRO] Verificacao de senha direta falhou')
    exit(1)

# Testar authenticate_user (metodo completo)
auth_user = sql.authenticate_user('admin@sistema.local', 'Admin@123')
if auth_user:
    print(f'[OK] authenticate_user bem-sucedido!')
    print(f'    - Email: {auth_user["email"]}')
    print(f'    - Nome: {auth_user["nome"]}')
    print(f'    - Role: {auth_user["role"]}')
    print(f'    - password_hash no retorno: {"SIM (ERRO!)" if "password_hash" in auth_user else "NAO (correto)"}')
else:
    print('[ERRO] authenticate_user falhou')
    exit(1)

# Testar senha errada
auth_wrong = sql.authenticate_user('admin@sistema.local', 'SenhaErrada123')
if auth_wrong is None:
    print('[OK] Senha errada corretamente rejeitada')
else:
    print('[ERRO] Senha errada foi aceita!')
    exit(1)

print()
print('=== TODOS OS TESTES PASSARAM! ===')
