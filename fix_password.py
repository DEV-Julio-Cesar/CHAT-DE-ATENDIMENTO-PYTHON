"""Script para gerar o hash de uma senha usando bcrypt"""
import bcrypt

password = b'Vi@13051987'
hash = bcrypt.hashpw(password, bcrypt.gensalt())
print(hash.decode())
# Apenas gera e imprime o hash da senha
