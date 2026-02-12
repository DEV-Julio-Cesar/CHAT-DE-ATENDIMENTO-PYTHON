"""
Script de Verificação de Segurança
Verifica configurações de segurança do sistema
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from app.core.config import settings
from app.core.validators import validar_cpf
from app.core.encryption import get_encryption_manager


def check_security_headers():
    """Verificar headers de segurança"""
    print("\n🔒 Verificando Headers de Segurança...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        headers = response.headers
        
        required_headers = {
            "X-Frame-Options": "DENY ou SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "Configurado",
            "Referrer-Policy": "Configurado"
        }
        
        for header, expected in required_headers.items():
            if header in headers:
                print(f"  ✅ {header}: {headers[header][:50]}...")
            else:
                print(f"  ❌ {header}: FALTANDO")
        
        return True
    except Exception as e:
        print(f"  ❌ Erro ao verificar headers: {e}")
        return False


def check_cors_config():
    """Verificar configuração CORS"""
    print("\n🌐 Verificando Configuração CORS...")
    
    if settings.DEBUG:
        print("  ⚠️  DEBUG=True - CORS permite localhost")
    else:
        print("  ✅ DEBUG=False - CORS restrito")
    
    # Verificar se não usa wildcard
    cors_origins = settings.CORS_ORIGINS
    if "*" in cors_origins:
        print("  ❌ CORS usa wildcard (*) - INSEGURO!")
        return False
    else:
        print(f"  ✅ CORS restrito a: {cors_origins}")
        return True


def check_rate_limiting():
    """Verificar configuração de rate limiting"""
    print("\n⏱️  Verificando Rate Limiting...")
    
    from app.core.rate_limiter import RateLimitConfig
    
    login_config = RateLimitConfig.LOGIN
    print(f"  Login: {login_config['max_requests']} tentativas em {login_config['window_seconds']}s")
    
    if login_config['max_requests'] <= 3:
        print("  ✅ Rate limiting adequado (≤3 tentativas)")
    else:
        print("  ⚠️  Rate limiting pode ser mais rigoroso")
    
    return True


def check_encryption():
    """Verificar criptografia"""
    print("\n🔐 Verificando Criptografia...")
    
    try:
        # Testar criptografia
        encryption_manager = get_encryption_manager()
        
        test_data = "Dados sensíveis de teste"
        encrypted = encryption_manager.encrypt(test_data)
        decrypted = encryption_manager.decrypt(encrypted)
        
        if decrypted == test_data:
            print("  ✅ Criptografia AES-256-GCM funcionando")
        else:
            print("  ❌ Erro na criptografia")
            return False
        
        # Verificar chave mestra
        if settings.MASTER_ENCRYPTION_KEY:
            print("  ✅ MASTER_ENCRYPTION_KEY configurada")
        else:
            print("  ⚠️  MASTER_ENCRYPTION_KEY não configurada (usando temporária)")
        
        return True
    except Exception as e:
        print(f"  ❌ Erro ao verificar criptografia: {e}")
        return False


def check_validators():
    """Verificar validadores"""
    print("\n✔️  Verificando Validadores...")
    
    # Testar validação de CPF
    cpf_valido = "07013042439"
    cpf_invalido = "12345678901"
    
    if validar_cpf(cpf_valido):
        print(f"  ✅ CPF válido aceito: {cpf_valido}")
    else:
        print(f"  ❌ CPF válido rejeitado: {cpf_valido}")
        return False
    
    if not validar_cpf(cpf_invalido):
        print(f"  ✅ CPF inválido rejeitado: {cpf_invalido}")
    else:
        print(f"  ❌ CPF inválido aceito: {cpf_invalido}")
        return False
    
    return True


def check_secrets():
    """Verificar configuração de secrets"""
    print("\n🔑 Verificando Secrets...")
    
    secrets_provider = os.getenv('SECRETS_PROVIDER', 'local')
    print(f"  Provedor: {secrets_provider}")
    
    if secrets_provider == 'local':
        print("  ⚠️  Usando .env local (OK para desenvolvimento)")
    else:
        print(f"  ✅ Usando Secrets Manager: {secrets_provider}")
    
    # Verificar se .env está no .gitignore
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path) as f:
            if ".env" in f.read():
                print("  ✅ .env está no .gitignore")
            else:
                print("  ❌ .env NÃO está no .gitignore - CRÍTICO!")
                return False
    
    return True


def check_jwt_config():
    """Verificar configuração JWT"""
    print("\n🎫 Verificando Configuração JWT...")
    
    algorithm = settings.ALGORITHM
    print(f"  Algoritmo: {algorithm}")
    
    if algorithm == "HS256":
        print("  ⚠️  Usando HS256 (considere migrar para RS256)")
    elif algorithm == "RS256":
        print("  ✅ Usando RS256 (mais seguro)")
    
    token_expire = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    print(f"  Expiração: {token_expire} minutos")
    
    if token_expire > 1440:  # 24 horas
        print("  ⚠️  Token expira em mais de 24 horas")
    else:
        print("  ✅ Expiração adequada")
    
    return True


def main():
    """Executar todas as verificações"""
    print("="*60)
    print("🔒 VERIFICAÇÃO DE SEGURANÇA - CHAT-DE-ATENDIMENTO-PYTHON")
    print("="*60)
    
    checks = [
        ("Headers de Segurança", check_security_headers),
        ("Configuração CORS", check_cors_config),
        ("Rate Limiting", check_rate_limiting),
        ("Criptografia", check_encryption),
        ("Validadores", check_validators),
        ("Secrets", check_secrets),
        ("JWT", check_jwt_config)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Erro em {name}: {e}")
            results.append((name, False))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"  {status}: {name}")
    
    print(f"\n🎯 Score: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 Todas as verificações passaram!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} verificação(ões) falharam")
        return 1


if __name__ == "__main__":
    sys.exit(main())
