#!/usr/bin/env python3
"""
Teste de diferentes senhas
"""
import bcrypt

# Hash do sistema atual
hash_atual = "$2a$10$Cmu1DBIKIwpBB29IJMfN1uXu3QalrDOq7.j4mV.XzrKU/N0Nh7nam"

# Senhas para testar
senhas = ["admin", "admin123", "123456", "password", ""]

print("🔍 Testando diferentes senhas com o hash atual...")
print(f"Hash: {hash_atual}")
print()

for senha in senhas:
    try:
        result = bcrypt.checkpw(senha.encode('utf-8'), hash_atual.encode('utf-8'))
        status = "✅ CORRETA" if result else "❌ Incorreta"
        print(f"Senha '{senha}': {status}")
    except Exception as e:
        print(f"Senha '{senha}': ❌ Erro - {e}")

print("\n🔍 Testando com passlib...")
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

for senha in senhas:
    try:
        # Truncar senha para 72 bytes se necessário
        senha_truncada = senha[:72] if len(senha.encode('utf-8')) > 72 else senha
        result = pwd_context.verify(senha_truncada, hash_atual)
        status = "✅ CORRETA" if result else "❌ Incorreta"
        print(f"Senha '{senha}' (passlib): {status}")
    except Exception as e:
        print(f"Senha '{senha}' (passlib): ❌ Erro - {e}")