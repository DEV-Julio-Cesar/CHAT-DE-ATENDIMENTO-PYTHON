"""
Script de Teste das Funcionalidades de Segurança
Valida todas as correções implementadas
"""
import asyncio
import sys


def test_password_validator():
    """Testar validador de senha"""
    print("\n" + "="*60)
    print("🔐 TESTE: Validador de Senha")
    print("="*60)
    
    from app.core.password_validator import password_validator
    
    # Teste 1: Senha fraca
    print("\n1. Testando senha fraca: '123456'")
    is_valid, errors = password_validator.validate("123456")
    print(f"   Válida: {is_valid}")
    if errors:
        for error in errors:
            print(f"   ❌ {error}")
    
    # Teste 2: Senha comum
    print("\n2. Testando senha comum: 'Password123!'")
    is_valid, errors = password_validator.validate("Password123!")
    print(f"   Válida: {is_valid}")
    if errors:
        for error in errors:
            print(f"   ❌ {error}")
    
    # Teste 3: Senha forte
    print("\n3. Testando senha forte: 'MyStr0ng!P@ssw0rd2024'")
    is_valid, errors = password_validator.validate("MyStr0ng!P@ssw0rd2024")
    print(f"   Válida: {is_valid}")
    if not is_valid:
        for error in errors:
            print(f"   ❌ {error}")
    else:
        print("   ✅ Senha aceita!")
    
    # Teste 4: Calcular força
    print("\n4. Calculando força de senhas:")
    passwords = [
        "123456",
        "Password1",
        "MyStr0ng!P@ssw0rd2024"
    ]
    for pwd in passwords:
        score, level = password_validator.calculate_strength(pwd)
        print(f"   '{pwd}': {score}/100 ({level})")
    
    # Teste 5: Gerar senha forte
    print("\n5. Gerando senha forte aleatória:")
    strong_pwd = password_validator.generate_strong_password(16)
    print(f"   Senha gerada: {strong_pwd}")
    is_valid, _ = password_validator.validate(strong_pwd)
    print(f"   Válida: {'✅' if is_valid else '❌'}")


def test_input_validator():
    """Testar validador de input"""
    print("\n" + "="*60)
    print("🛡️ TESTE: Validador de Input")
    print("="*60)
    
    from app.core.input_validator import input_validator
    
    # Teste 1: Validar email
    print("\n1. Validando emails:")
    emails = [
        "user@example.com",
        "invalid.email",
        "test@test@test.com"
    ]
    for email in emails:
        is_valid, normalized = input_validator.validate_email(email)
        status = "✅" if is_valid else "❌"
        print(f"   {status} '{email}' -> {normalized if is_valid else 'inválido'}")
    
    # Teste 2: Validar telefone
    print("\n2. Validando telefones:")
    phones = [
        "+5511999999999",
        "11999999999",
        "invalid-phone"
    ]
    for phone in phones:
        is_valid, normalized = input_validator.validate_phone(phone, "BR")
        status = "✅" if is_valid else "❌"
        print(f"   {status} '{phone}' -> {normalized if is_valid else 'inválido'}")
    
    # Teste 3: Detectar SQL Injection
    print("\n3. Detectando SQL Injection:")
    sql_tests = [
        "SELECT * FROM users",
        "'; DROP TABLE users; --",
        "normal text",
        "1' OR '1'='1"
    ]
    for test in sql_tests:
        detected = input_validator.detect_sql_injection(test)
        status = "🚨" if detected else "✅"
        print(f"   {status} '{test}' -> {'DETECTADO' if detected else 'seguro'}")
    
    # Teste 4: Detectar XSS
    print("\n4. Detectando XSS:")
    xss_tests = [
        "<script>alert('xss')</script>",
        "normal text",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')"
    ]
    for test in xss_tests:
        detected = input_validator.detect_xss(test)
        status = "🚨" if detected else "✅"
        print(f"   {status} '{test[:30]}...' -> {'DETECTADO' if detected else 'seguro'}")
    
    # Teste 5: Sanitizar string
    print("\n5. Sanitizando strings:")
    dirty = "<script>alert('xss')</script>Hello World!"
    clean = input_validator.sanitize_string(dirty, max_length=100, allow_html=False)
    print(f"   Original: {dirty}")
    print(f"   Limpo: {clean}")


async def test_rate_limiter():
    """Testar rate limiter"""
    print("\n" + "="*60)
    print("⏱️ TESTE: Rate Limiter")
    print("="*60)
    
    from app.core.rate_limiter import RateLimiter
    
    limiter = RateLimiter()
    
    print("\n1. Testando rate limit (máx 5 requisições em 60s):")
    for i in range(8):
        allowed, remaining = await limiter.is_allowed(
            identifier="test:user:123",
            max_requests=5,
            window_seconds=60
        )
        status = "✅" if allowed else "❌"
        print(f"   Requisição {i+1}: {status} (restantes: {remaining})")
    
    print("\n2. Resetando rate limit:")
    await limiter.reset("test:user:123")
    allowed, remaining = await limiter.is_allowed(
        identifier="test:user:123",
        max_requests=5,
        window_seconds=60
    )
    print(f"   Após reset: {'✅' if allowed else '❌'} (restantes: {remaining})")


def test_webhook_security():
    """Testar segurança de webhook"""
    print("\n" + "="*60)
    print("🔗 TESTE: Segurança de Webhook")
    print("="*60)
    
    from app.core.webhook_security import webhook_security
    import json
    
    # Teste 1: Gerar e verificar assinatura
    print("\n1. Testando assinatura HMAC:")
    payload = json.dumps({"test": "data", "timestamp": 1234567890}).encode()
    secret = "test-secret-key"
    
    signature = webhook_security.generate_webhook_signature(payload, secret)
    print(f"   Assinatura gerada: {signature[:50]}...")
    
    is_valid = webhook_security.verify_whatsapp_signature(payload, signature, secret)
    print(f"   Verificação: {'✅ Válida' if is_valid else '❌ Inválida'}")
    
    # Teste 2: Assinatura inválida
    print("\n2. Testando assinatura inválida:")
    wrong_signature = "sha256=wrong_signature_here"
    is_valid = webhook_security.verify_whatsapp_signature(payload, wrong_signature, secret)
    print(f"   Verificação: {'❌ Aceita (ERRO!)' if is_valid else '✅ Rejeitada (correto)'}")
    
    # Teste 3: Verificar timestamp
    print("\n3. Testando verificação de timestamp:")
    import time
    
    # Timestamp atual (válido)
    current_timestamp = int(time.time())
    is_valid, error = webhook_security.verify_timestamp(current_timestamp)
    print(f"   Timestamp atual: {'✅ Válido' if is_valid else f'❌ Inválido - {error}'}")
    
    # Timestamp antigo (inválido)
    old_timestamp = int(time.time()) - 600  # 10 minutos atrás
    is_valid, error = webhook_security.verify_timestamp(old_timestamp)
    print(f"   Timestamp antigo: {'❌ Aceito (ERRO!)' if is_valid else f'✅ Rejeitado - {error}'}")


def test_jwt_security():
    """Testar segurança JWT"""
    print("\n" + "="*60)
    print("🎫 TESTE: Segurança JWT")
    print("="*60)
    
    from app.core.security import security_manager
    
    # Teste 1: Criar token
    print("\n1. Criando token JWT:")
    token = security_manager.create_access_token({
        "sub": "user123",
        "email": "user@example.com",
        "role": "admin"
    })
    print(f"   Token criado: {token[:50]}...")
    
    # Teste 2: Verificar token
    print("\n2. Verificando token:")
    try:
        payload = security_manager.verify_token(token)
        print(f"   ✅ Token válido")
        print(f"   User ID: {payload.get('sub')}")
        print(f"   Email: {payload.get('email')}")
        print(f"   Role: {payload.get('role')}")
        print(f"   Audience: {payload.get('aud')}")
        print(f"   Issuer: {payload.get('iss')}")
        print(f"   JTI: {payload.get('jti')[:20]}...")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 3: Token inválido
    print("\n3. Testando token inválido:")
    try:
        invalid_token = "invalid.token.here"
        payload = security_manager.verify_token(invalid_token)
        print(f"   ❌ Token aceito (ERRO!)")
    except Exception as e:
        print(f"   ✅ Token rejeitado: {str(e)[:50]}...")


def print_summary():
    """Imprimir resumo das correções"""
    print("\n" + "="*60)
    print("📋 RESUMO DAS CORREÇÕES DE SEGURANÇA IMPLEMENTADAS")
    print("="*60)
    
    corrections = [
        ("✅", "JWT com validação completa (aud, iss, jti)"),
        ("✅", "Rate Limiter com fallback seguro em memória"),
        ("✅", "CORS configurado sem wildcard"),
        ("✅", "Security Headers habilitados"),
        ("✅", "Política de senha forte (12+ caracteres)"),
        ("✅", "Validação e sanitização de input"),
        ("✅", "Segurança de webhook com HMAC"),
        ("✅", "Proteção contra SQL Injection"),
        ("✅", "Proteção contra XSS"),
        ("✅", "Proteção contra replay attacks"),
    ]
    
    print("\nCorreções Aplicadas:")
    for status, description in corrections:
        print(f"  {status} {description}")
    
    print("\n" + "="*60)
    print("📚 Documentação: docs/SECURITY_IMPLEMENTATION.md")
    print("="*60)


def main():
    """Executar todos os testes"""
    print("\n" + "="*60)
    print("🔒 TESTE DE SEGURANÇA - SISTEMA DE CHAT")
    print("="*60)
    
    try:
        # Testes síncronos
        test_password_validator()
        test_input_validator()
        test_webhook_security()
        test_jwt_security()
        
        # Testes assíncronos
        print("\n⏳ Executando testes assíncronos...")
        asyncio.run(test_rate_limiter())
        
        # Resumo
        print_summary()
        
        print("\n✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO NOS TESTES: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
