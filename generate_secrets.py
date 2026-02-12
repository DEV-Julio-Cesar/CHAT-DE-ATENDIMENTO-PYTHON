"""
Gerador de Chaves Secretas Seguras
Gera todas as chaves necessárias para o sistema
"""
import secrets
import hashlib
import os


def generate_secret_key(length: int = 32) -> str:
    """Gerar chave secreta aleatória"""
    return secrets.token_urlsafe(length)


def generate_salt(length: int = 16) -> str:
    """Gerar salt para criptografia"""
    return secrets.token_urlsafe(length)


def generate_webhook_token(length: int = 32) -> str:
    """Gerar token de webhook"""
    return secrets.token_urlsafe(length)


def generate_api_key() -> str:
    """Gerar chave de API"""
    return f"isp_{secrets.token_urlsafe(32)}"


def main():
    print("=" * 70)
    print("🔐 GERADOR DE CHAVES SECRETAS SEGURAS")
    print("=" * 70)
    print("\nGerando chaves criptograficamente seguras...\n")
    
    # Gerar todas as chaves
    jwt_secret = generate_secret_key(32)
    encryption_key = generate_secret_key(32)
    encryption_salt = generate_salt(16)
    webhook_token = generate_webhook_token(32)
    api_key = generate_api_key()
    
    # Exibir chaves
    print("=" * 70)
    print("📋 CHAVES GERADAS - COPIE PARA SEU .env")
    print("=" * 70)
    print()
    
    print("# ============================================================================")
    print("# SEGURANÇA - JWT")
    print("# ============================================================================")
    print(f'SECRET_KEY="{jwt_secret}"')
    print('ALGORITHM="HS256"')
    print('ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1 hora')
    print()
    
    print("# ============================================================================")
    print("# SEGURANÇA - CRIPTOGRAFIA")
    print("# ============================================================================")
    print(f'MASTER_ENCRYPTION_KEY="{encryption_key}"')
    print(f'ENCRYPTION_SALT="{encryption_salt}"')
    print()
    
    print("# ============================================================================")
    print("# SEGURANÇA - WEBHOOK")
    print("# ============================================================================")
    print(f'WHATSAPP_WEBHOOK_VERIFY_TOKEN="{webhook_token}"')
    print()
    
    print("# ============================================================================")
    print("# SEGURANÇA - API KEY (OPCIONAL)")
    print("# ============================================================================")
    print(f'API_KEY="{api_key}"')
    print()
    
    print("=" * 70)
    print("⚠️  IMPORTANTE:")
    print("=" * 70)
    print("1. NUNCA compartilhe estas chaves")
    print("2. NUNCA commite o arquivo .env no Git")
    print("3. Use chaves diferentes para dev/staging/prod")
    print("4. Rotacione as chaves a cada 90 dias")
    print("5. Guarde backup das chaves em local seguro (ex: 1Password, LastPass)")
    print()
    
    # Salvar em arquivo temporário
    output_file = ".env.secrets"
    with open(output_file, "w") as f:
        f.write("# CHAVES SECRETAS GERADAS\n")
        f.write("# COPIE PARA SEU .env E DELETE ESTE ARQUIVO\n\n")
        f.write(f'SECRET_KEY="{jwt_secret}"\n')
        f.write('ALGORITHM="HS256"\n')
        f.write('ACCESS_TOKEN_EXPIRE_MINUTES=60\n\n')
        f.write(f'MASTER_ENCRYPTION_KEY="{encryption_key}"\n')
        f.write(f'ENCRYPTION_SALT="{encryption_salt}"\n\n')
        f.write(f'WHATSAPP_WEBHOOK_VERIFY_TOKEN="{webhook_token}"\n\n')
        f.write(f'API_KEY="{api_key}"\n')
    
    print(f"✅ Chaves salvas em: {output_file}")
    print("   Copie para seu .env e DELETE este arquivo!")
    print()
    
    # Calcular hashes para verificação
    print("=" * 70)
    print("🔍 HASHES PARA VERIFICAÇÃO (SHA-256)")
    print("=" * 70)
    print(f"SECRET_KEY: {hashlib.sha256(jwt_secret.encode()).hexdigest()[:16]}...")
    print(f"ENCRYPTION_KEY: {hashlib.sha256(encryption_key.encode()).hexdigest()[:16]}...")
    print()


if __name__ == "__main__":
    main()
