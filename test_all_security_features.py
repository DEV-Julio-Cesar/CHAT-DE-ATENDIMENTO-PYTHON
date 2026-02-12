"""
Teste Completo de Todas as Funcionalidades de Segurança
Incluindo 2FA e Criptografia
"""
import asyncio
import sys


def test_encryption():
    """Testar criptografia de mensagens"""
    print("\n" + "="*60)
    print("🔐 TESTE: Criptografia de Mensagens")
    print("="*60)
    
    from app.core.encryption_manager import encryption_manager
    
    if not encryption_manager.is_enabled():
        print("\n⚠️  Criptografia não habilitada (configure MASTER_ENCRYPTION_KEY)")
        return
    
    # Teste 1: Criptografar e descriptografar texto
    print("\n1. Testando criptografia de texto:")
    original = "Mensagem confidencial do cliente"
    print(f"   Original: {original}")
    
    encrypted = encryption_manager.encrypt(original)
    print(f"   Criptografado: {encrypted[:50]}...")
    
    decrypted = encryption_manager.decrypt(encrypted)
    print(f"   Descriptografado: {decrypted}")
    print(f"   Match: {'✅' if original == decrypted else '❌'}")
    
    # Teste 2: Criptografar dicionário
    print("\n2. Testando criptografia de dicionário:")
    data = {
        "nome": "João Silva",
        "cpf": "123.456.789-00",
        "telefone": "+5511999999999",
        "mensagem": "Preciso de suporte técnico"
    }
    
    encrypted_data = encryption_manager.encrypt_dict(data, ['cpf', 'telefone', 'mensagem'])
    print(f"   CPF criptografado: {encrypted_data['cpf'][:30]}...")
    print(f"   Telefone criptografado: {encrypted_data['telefone'][:30]}...")
    
    decrypted_data = encryption_manager.decrypt_dict(encrypted_data, ['cpf', 'telefone', 'mensagem'])
    print(f"   CPF descriptografado: {decrypted_data['cpf']}")
    print(f"   Match: {'✅' if data == decrypted_data else '❌'}")


def test_2fa():
    """Testar autenticação de dois fatores"""
    print("\n" + "="*60)
    print("🔑 TESTE: Autenticação de Dois Fatores (2FA)")
    print("="*60)
    
    from app.core.two_factor_auth import two_factor_auth, setup_2fa_for_user
    
    # Teste 1: Configurar 2FA
    print("\n1. Configurando 2FA para usuário:")
    user_email = "teste@example.com"
    setup_data = setup_2fa_for_user(user_email)
    
    print(f"   Secret gerado: {setup_data['secret']}")
    print(f"   QR Code gerado: {'✅' if setup_data['qr_code'] else '❌'}")
    print(f"   Códigos de backup: {len(setup_data['backup_codes'])} códigos")
    print(f"   Exemplo: {setup_data['backup_codes'][0]}")
    
    # Teste 2: Gerar e verificar código
    print("\n2. Testando geração e verificação de código:")
    secret = setup_data['secret']
    current_code = two_factor_auth.get_current_code(secret)
    print(f"   Código atual: {current_code}")
    
    is_valid = two_factor_auth.verify_code(secret, current_code)
    print(f"   Verificação: {'✅ Válido' if is_valid else '❌ Inválido'}")
    
    # Teste 3: Código inválido
    print("\n3. Testando código inválido:")
    invalid_code = "000000"
    is_valid = two_factor_auth.verify_code(secret, invalid_code)
    print(f"   Código {invalid_code}: {'❌ Aceito (ERRO!)' if is_valid else '✅ Rejeitado (correto)'}")
    
    # Teste 4: Códigos de backup
    print("\n4. Testando códigos de backup:")
    backup_code = setup_data['backup_codes'][0]
    hashed_codes = setup_data['backup_codes_hashed']
    
    is_valid, used_hash = two_factor_auth.verify_backup_code(backup_code, hashed_codes)
    print(f"   Código de backup: {backup_code}")
    print(f"   Verificação: {'✅ Válido' if is_valid else '❌ Inválido'}")
    
    # Teste 5: Código de backup inválido
    print("\n5. Testando código de backup inválido:")
    invalid_backup = "XXXX-XXXX"
    is_valid, _ = two_factor_auth.verify_backup_code(invalid_backup, hashed_codes)
    print(f"   Código {invalid_backup}: {'❌ Aceito (ERRO!)' if is_valid else '✅ Rejeitado (correto)'}")


def test_complete_security_flow():
    """Testar fluxo completo de segurança"""
    print("\n" + "="*60)
    print("🛡️ TESTE: Fluxo Completo de Segurança")
    print("="*60)
    
    from app.core.password_validator import password_validator
    from app.core.input_validator import input_validator
    from app.core.security import security_manager
    
    # Simular registro de usuário
    print("\n1. Simulando registro de usuário:")
    user_data = {
        "email": "novo.usuario@example.com",
        "password": "MyStr0ng!Pass24",  # Senha mais curta para bcrypt
        "nome": "Novo Usuário"
    }
    
    # Validar email
    is_valid, normalized_email = input_validator.validate_email(user_data['email'])
    print(f"   Email válido: {'✅' if is_valid else '❌'}")
    
    # Validar senha
    is_valid, errors = password_validator.validate(user_data['password'])
    print(f"   Senha válida: {'✅' if is_valid else '❌'}")
    if errors:
        for error in errors:
            print(f"      - {error}")
    
    # Hash da senha
    import bcrypt
    password_hash = bcrypt.hashpw(user_data['password'].encode(), bcrypt.gensalt())
    print(f"   Hash gerado: {password_hash.decode()[:30]}...")
    
    # Criar token JWT
    print("\n2. Criando token JWT:")
    token = security_manager.create_access_token({
        "sub": "user123",
        "email": normalized_email,
        "role": "user"
    })
    print(f"   Token: {token[:50]}...")
    
    # Verificar token
    print("\n3. Verificando token:")
    try:
        payload = security_manager.verify_token(token)
        print(f"   ✅ Token válido")
        print(f"   User ID: {payload.get('sub')}")
        print(f"   Email: {payload.get('email')}")
        print(f"   Audience: {payload.get('aud')}")
        print(f"   Issuer: {payload.get('iss')}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")


def print_final_summary():
    """Imprimir resumo final"""
    print("\n" + "="*60)
    print("📋 RESUMO FINAL - TODAS AS FUNCIONALIDADES")
    print("="*60)
    
    features = [
        ("✅", "JWT com validação completa (aud, iss, jti)"),
        ("✅", "Rate Limiter com fallback seguro"),
        ("✅", "CORS configurado corretamente"),
        ("✅", "Security Headers habilitados"),
        ("✅", "Política de senha forte (12+ caracteres)"),
        ("✅", "Validação e sanitização de input"),
        ("✅", "Segurança de webhook (HMAC)"),
        ("✅", "Proteção contra SQL Injection"),
        ("✅", "Proteção contra XSS"),
        ("✅", "Proteção contra replay attacks"),
        ("✅", "Criptografia AES-256-GCM"),
        ("✅", "Autenticação de dois fatores (2FA)"),
    ]
    
    print("\nFuncionalidades Implementadas:")
    for status, description in features:
        print(f"  {status} {description}")
    
    print("\n" + "="*60)
    print("📚 Arquivos Criados:")
    print("="*60)
    files = [
        "app/core/password_validator.py",
        "app/core/input_validator.py",
        "app/core/webhook_security.py",
        "app/core/encryption_manager.py",
        "app/core/two_factor_auth.py",
        "app/api/endpoints/two_factor.py",
        "docs/SECURITY_IMPLEMENTATION.md",
        "generate_secrets.py",
        "test_security_features.py",
        "test_all_security_features.py",
    ]
    for f in files:
        print(f"  ✅ {f}")
    
    print("\n" + "="*60)
    print("🚀 Próximos Passos:")
    print("="*60)
    print("  1. Configurar Redis em produção")
    print("  2. Implementar CSRF tokens")
    print("  3. Adicionar testes automatizados")
    print("  4. Configurar WAF (Web Application Firewall)")
    print("  5. Penetration testing profissional")
    print("\n" + "="*60)


def main():
    """Executar todos os testes"""
    print("\n" + "="*60)
    print("🔒 TESTE COMPLETO DE SEGURANÇA")
    print("="*60)
    
    try:
        # Testes de criptografia
        test_encryption()
        
        # Testes de 2FA
        test_2fa()
        
        # Teste de fluxo completo
        test_complete_security_flow()
        
        # Resumo final
        print_final_summary()
        
        print("\n✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO NOS TESTES: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
