#!/usr/bin/env python3
"""
Debug do Auth Service
"""
from passlib.context import CryptContext

# Testar se a senha está correta
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash do sistema atual
password_hash = "$2a$10$Cmu1DBIKIwpBB29IJMfN1uXu3QalrDOq7.j4mV.XzrKU/N0Nh7nam"
password = "admin123"

print("🔍 Testando verificação de senha...")
print(f"Hash: {password_hash}")
print(f"Senha: {password}")

try:
    result = pwd_context.verify(password, password_hash)
    print(f"✅ Verificação: {result}")
except Exception as e:
    print(f"❌ Erro na verificação: {e}")

# Testar JWT
import jwt
from datetime import datetime, timedelta

JWT_SECRET = "your-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"

print("\n🔍 Testando JWT...")
try:
    token_data = {
        "sub": "admin",
        "user_id": "admin-id",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    print(f"✅ Token gerado: {token[:20]}...")
    
    # Verificar token
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    print(f"✅ Token verificado: {payload}")
except Exception as e:
    print(f"❌ Erro no JWT: {e}")