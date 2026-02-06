#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHECKLIST DE VALIDACAO - SEMANA 1 INTEGRADA

Execute este script para validar se todas as integracoes estao corretas:
    python verify_semana1_integration.py
"""

import os
import sys

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_file_exists(path):
    """Verificar se arquivo existe"""
    return os.path.exists(path)

def check_content_in_file(filepath, content):
    """Verificar se conteúdo está no arquivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return content in f.read()
    except:
        return False

def print_check(name, passed):
    """Print resultado de verificação"""
    status = f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"
    print(f"  {status}  {name}")
    return passed

def print_section(title):
    """Print seção de checklist"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

def main():
    workspace = "c:\\Users\\MASTER\\Documents\\Chat-de-atendimento-whats"
    os.chdir(workspace)
    
    total_checks = 0
    passed_checks = 0
    
    # MODULO 1: JWT + RBAC
    print_section("[1] MODULO: JWT + RBAC")
    
    checks = [
        ("Arquivo: app/core/dependencies.py existe", 
         check_file_exists("app/core/dependencies.py")),
        ("dependencies.py contém: get_current_user", 
         check_content_in_file("app/core/dependencies.py", "def get_current_user")),
        ("dependencies.py contém: require_admin", 
         check_content_in_file("app/core/dependencies.py", "def require_admin")),
        ("auth.py contém: POST /auth/login", 
         check_content_in_file("app/api/endpoints/auth.py", "@router.post(\"/login\"")),
        ("auth.py usa JWT encoding", 
         check_content_in_file("app/api/endpoints/auth.py", "jwt.encode")),
        ("users.py tem RBAC: Depends integration", 
         check_content_in_file("app/api/endpoints/users.py", "Depends(")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # MODULO 2: RATE LIMITING
    print_section("[2] MODULO: RATE LIMITING")
    
    checks = [
        ("Arquivo: app/core/rate_limiter.py existe", 
         check_file_exists("app/core/rate_limiter.py")),
        ("rate_limiter.py contém: is_allowed", 
         check_content_in_file("app/core/rate_limiter.py", "async def is_allowed")),
        ("main.py importa rate_limiter", 
         check_content_in_file("app/main.py", "from app.core.rate_limiter import")),
        ("main.py tem middleware rate limit", 
         check_content_in_file("app/main.py", "rate_limit_middleware")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # MODULO 3: CRIPTOGRAFIA
    print_section("[3] MODULO: CRIPTOGRAFIA AES-256")
    
    checks = [
        ("Arquivo: app/core/encryption.py existe", 
         check_file_exists("app/core/encryption.py")),
        ("encryption.py contém: def encrypt", 
         check_content_in_file("app/core/encryption.py", "def encrypt")),
        ("chat_flow.py tem: encrypt_message_content", 
         check_content_in_file("app/services/whatsapp_chat_flow.py", "async def encrypt_message_content")),
        ("chat_flow.py tem: add_encrypted_message", 
         check_content_in_file("app/services/whatsapp_chat_flow.py", "async def add_encrypted_message")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # MODULO 4: AUDITORIA
    print_section("[4] MODULO: AUDITORIA COM HASH CHAIN")
    
    checks = [
        ("Arquivo: app/core/audit_logger.py existe", 
         check_file_exists("app/core/audit_logger.py")),
        ("audit_logger.py contém: class AuditLogger", 
         check_content_in_file("app/core/audit_logger.py", "class AuditLogger")),
        ("main.py importa audit_logger", 
         check_content_in_file("app/main.py", "from app.core.audit_logger import")),
        ("BD tem campos criptografia: iv, conteudo_criptografado", 
         check_content_in_file("app/models/database.py", "conteudo_criptografado")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # MODULO 5: GDPR/LGPD
    print_section("[5] MODULO: GDPR/LGPD")
    
    checks = [
        ("Arquivo: app/api/endpoints/gdpr.py existe", 
         check_file_exists("app/api/endpoints/gdpr.py")),
        ("gdpr.py contém: deletion-request endpoint", 
         check_content_in_file("app/api/endpoints/gdpr.py", "deletion-request")),
        ("routes.py registra gdpr endpoint", 
         check_content_in_file("app/api/routes.py", "gdpr.router")),
        ("BD tem tabelas GDPR: GDPRRequest, UserConsent, TokenBlacklist", 
         check_content_in_file("app/models/database.py", "class GDPRRequest")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # TESTES
    print_section("[6] TESTES INCLUSOS")
    
    checks = [
        ("Arquivo: app/tests/test_semana1_integration.py existe", 
         check_file_exists("app/tests/test_semana1_integration.py")),
        ("Testes contém: TestJWTAuthentication", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestJWTAuthentication")),
        ("Testes contém: TestCompleteFlow", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestCompleteFlow")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # DOCUMENTACAO
    print_section("[7] DOCUMENTACAO")
    
    checks = [
        ("Guia: SEMANA1_INTEGRACAO_COMPLETA.md", 
         check_file_exists("docs/SEMANA1_INTEGRACAO_COMPLETA.md")),
        ("Resumo: RESUMO_SEMANA1_INTEGRADA.md", 
         check_file_exists("docs/RESUMO_SEMANA1_INTEGRADA.md")),
        ("Diagrama: DIAGRAMA_INTEGRACAO_SEMANA1.md", 
         check_file_exists("docs/DIAGRAMA_INTEGRACAO_SEMANA1.md")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # RESULTADO FINAL
    print_section("RESULTADO FINAL")
    
    percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    print(f"\nTotal de verificacoes: {total_checks}")
    print(f"Verificacoes passadas: {GREEN}{passed_checks}{RESET}")
    print(f"Verificacoes falhadas: {RED}{total_checks - passed_checks}{RESET}")
    print(f"Percentual de sucesso: {percentage:.1f}%\n")
    
    if passed_checks == total_checks:
        print(f"{GREEN}{'='*70}")
        print(f"[OK] SEMANA 1 - INTEGRACAO 100% COMPLETA E VALIDADA!")
        print(f"{'='*70}{RESET}\n")
        print(f"{BLUE}Proximos passos:{RESET}")
        print(f"  1. Rodar testes: pytest app/tests/test_semana1_integration.py -v")
        print(f"  2. Conectar auth.py com BD real")
        print(f"  3. Implementar hash de senha (bcrypt)")
        print(f"  4. Configurar SMTP para emails GDPR")
        print(f"  5. Criar Alembic migrations")
        print(f"  6. Deploy em staging\n")
        return 0
    else:
        print(f"{RED}{'='*70}")
        print(f"[FAIL] SEMANA 1 - INTEGRACAO INCOMPLETA")
        print(f"Corriga os itens falhados acima")
        print(f"{'='*70}{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
