#!/usr/bin/env python3
"""
Teste do bcrypt
"""
import bcrypt

# Testar se conseguimos criar um hash
password = "admin123"
print(f"🔍 Testando bcrypt com senha: {password}")

try:
    # Criar um novo hash
    salt = bcrypt.gensalt()
    new_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    print(f"✅ Novo hash criado: {new_hash.decode('utf-8')}")
    
    # Verificar o novo hash
    result = bcrypt.checkpw(password.encode('utf-8'), new_hash)
    print(f"✅ Verificação do novo hash: {result}")
    
    # Testar o hash do sistema atual
    old_hash = "$2a$10$Cmu1DBIKIwpBB29IJMfN1uXu3QalrDOq7.j4mV.XzrKU/N0Nh7nam"
    print(f"\n🔍 Testando hash do sistema atual: {old_hash}")
    
    result = bcrypt.checkpw(password.encode('utf-8'), old_hash.encode('utf-8'))
    print(f"✅ Verificação do hash atual: {result}")
    
except Exception as e:
    print(f"❌ Erro no bcrypt: {e}")