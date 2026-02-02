"""Script para corrigir o hash de senha do admin"""
import pyodbc
import bcrypt

# Conexão
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost;'
    'DATABASE=isp_support;'
    'Trusted_Connection=Yes;'
    'TrustServerCertificate=Yes'
)
cursor = conn.cursor()

# Gerar novo hash
password = "Admin@123"
salt = bcrypt.gensalt(rounds=12)
password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

print(f"Nova senha: {password}")
print(f"Novo hash: {password_hash}")
print(f"Tamanho do hash: {len(password_hash)}")

# Atualizar no banco
cursor.execute(
    "UPDATE usuarios SET password_hash = ? WHERE email = ?",
    (password_hash, 'admin@sistema.local')
)
conn.commit()

# Verificar
cursor.execute("SELECT password_hash FROM usuarios WHERE email = ?", ('admin@sistema.local',))
row = cursor.fetchone()
stored_hash = row[0]

print(f"\nHash armazenado: {stored_hash}")
print(f"Tamanho armazenado: {len(stored_hash)}")

# Testar verificação
test_result = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
print(f"\nVerificação: {'OK!' if test_result else 'FALHOU!'}")

conn.close()
