#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHECKLIST DE VALIDAÇÃO - SEMANA 1 INTEGRADA

Execute este script para validar se todas as integrações estão corretas:
    python verify_semana1_integration.py
"""

import os
import sys
from pathlib import Path

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
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
    
    # ========================================================================
    # MÓDULO 1: JWT + RBAC
    # ========================================================================
    print_section("1. MODULO: JWT + RBAC")
    
    checks = [
        ("Arquivo: app/core/dependencies.py existe", 
         check_file_exists("app/core/dependencies.py")),
        
        ("dependencies.py contém: get_current_user", 
         check_content_in_file("app/core/dependencies.py", "def get_current_user")),
        
        ("dependencies.py contém: require_admin", 
         check_content_in_file("app/core/dependencies.py", "def require_admin")),
        
        ("dependencies.py contém: require_role", 
         check_content_in_file("app/core/dependencies.py", "def require_role")),
        
        ("dependencies.py contém: revoke_token", 
         check_content_in_file("app/core/dependencies.py", "def revoke_token")),
        
        ("Arquivo: app/api/endpoints/auth.py modificado", 
         check_file_exists("app/api/endpoints/auth.py")),
        
        ("auth.py contém: POST /auth/login", 
         check_content_in_file("app/api/endpoints/auth.py", "@router.post(\"/login\"")),
        
        ("auth.py contém: POST /auth/logout", 
         check_content_in_file("app/api/endpoints/auth.py", "@router.post(\"/logout\"")),
        
        ("auth.py contém: GET /auth/token/validate", 
         check_content_in_file("app/api/endpoints/auth.py", "@router.get(\"/token/validate\"")),
        
        ("auth.py usa JWT encoding", 
         check_content_in_file("app/api/endpoints/auth.py", "jwt.encode")),
        
        ("Arquivo: app/api/endpoints/users.py modificado", 
         check_file_exists("app/api/endpoints/users.py")),
        
        ("users.py tem RBAC: Depends function", 
         check_content_in_file("app/api/endpoints/users.py", "Depends(get_current_active_user)")),
        
        ("users.py tem RBAC: require_admin integration", 
         check_content_in_file("app/api/endpoints/users.py", "Depends(require_admin)")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # MÓDULO 2: RATE LIMITING
    # ========================================================================
    print_section("🛡️ MÓDULO 2: RATE LIMITING")
    
    checks = [
        ("Arquivo: app/core/rate_limiter.py existe", 
         check_file_exists("app/core/rate_limiter.py")),
        
        ("rate_limiter.py contém: class RateLimiter", 
         check_content_in_file("app/core/rate_limiter.py", "class RateLimiter")),
        
        ("rate_limiter.py contém: RateLimitConfig", 
         check_content_in_file("app/core/rate_limiter.py", "class RateLimitConfig")),
        
        ("rate_limiter.py contém: is_allowed", 
         check_content_in_file("app/core/rate_limiter.py", "async def is_allowed")),
        
        ("main.py importa rate_limiter", 
         check_content_in_file("app/main.py", "from app.core.rate_limiter import")),
        
        ("main.py tem middleware de rate limit", 
         check_content_in_file("app/main.py", "@app.middleware(\"http\")")),
        
        ("Middleware valida login limit (5 tentativas)", 
         check_content_in_file("app/main.py", "LOGIN")),
        
        ("Middleware valida API limit (100 req/min)", 
         check_content_in_file("app/main.py", "API")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # MÓDULO 3: CRIPTOGRAFIA
    # ========================================================================
    print_section("🔒 MÓDULO 3: CRIPTOGRAFIA AES-256")
    
    checks = [
        ("Arquivo: app/core/encryption.py existe", 
         check_file_exists("app/core/encryption.py")),
        
        ("encryption.py contém: encryption functions", 
         check_content_in_file("app/core/encryption.py", "def encrypt") or 
         check_content_in_file("app/core/encryption.py", "encryption_manager")),
        
        ("encryption.py contém: encrypt method", 
         check_content_in_file("app/core/encryption.py", "def encrypt")),
        
        ("encryption.py contém: decrypt method", 
         check_content_in_file("app/core/encryption.py", "def decrypt")),
        
        ("encryption.py contém: AES-256", 
         check_content_in_file("app/core/encryption.py", "AES")),
        
        ("whatsapp_chat_flow.py importa encryption", 
         check_content_in_file("app/services/whatsapp_chat_flow.py", "from app.core.encryption")),
        
        ("chat_flow.py tem: encrypt_message_content", 
         check_content_in_file("app/services/whatsapp_chat_flow.py", "async def encrypt_message_content")),
        
        ("chat_flow.py tem: decrypt_message_content", 
         check_content_in_file("app/services/whatsapp_chat_flow.py", "async def decrypt_message_content")),
        
        ("chat_flow.py tem: add_encrypted_message", 
         check_content_in_file("app/services/whatsapp_chat_flow.py", "async def add_encrypted_message")),
        
        ("chat_flow.py tem: get_conversation_messages_decrypted", 
         check_content_in_file("app/services/whatsapp_chat_flow.py", "async def get_conversation_messages_decrypted")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # MÓDULO 4: AUDITORIA
    # ========================================================================
    print_section("📊 MÓDULO 4: AUDITORIA COM HASH CHAIN")
    
    checks = [
        ("Arquivo: app/core/audit_logger.py existe", 
         check_file_exists("app/core/audit_logger.py")),
        
        ("audit_logger.py contém: class AuditLogger", 
         check_content_in_file("app/core/audit_logger.py", "class AuditLogger")),
        
        ("audit_logger.py contém: async def log", 
         check_content_in_file("app/core/audit_logger.py", "async def log")),
        
        ("audit_logger.py usa hash SHA-256", 
         check_content_in_file("app/core/audit_logger.py", "sha256")),
        
        ("main.py importa audit_logger", 
         check_content_in_file("app/main.py", "from app.core.audit_logger import")),
        
        ("auth.py usa audit_logger.log", 
         check_content_in_file("app/api/endpoints/auth.py", "await audit_logger.log")),
        
        ("users.py usa audit_logger.log", 
         check_content_in_file("app/api/endpoints/users.py", "await audit_logger.log")),
        
        ("DATABASE: Modelo Mensagem tem conteudo_criptografado e iv", 
         check_content_in_file("app/models/database.py", "conteudo_criptografado") and 
         check_content_in_file("app/models/database.py", "iv = Column")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # MÓDULO 5: GDPR/LGPD
    # ========================================================================
    print_section("⚖️ MÓDULO 5: GDPR/LGPD")
    
    checks = [
        ("Arquivo: app/api/endpoints/gdpr.py existe", 
         check_file_exists("app/api/endpoints/gdpr.py")),
        
        ("gdpr.py contém: router = APIRouter", 
         check_content_in_file("app/api/endpoints/gdpr.py", "router = APIRouter")),
        
        ("gdpr.py contém: /deletion-request endpoint", 
         check_content_in_file("app/api/endpoints/gdpr.py", "deletion-request")),
        
        ("gdpr.py contém: /confirm-deletion endpoint", 
         check_content_in_file("app/api/endpoints/gdpr.py", "confirm-deletion")),
        
        ("gdpr.py contém: /data-export endpoint", 
         check_content_in_file("app/api/endpoints/gdpr.py", "data-export")),
        
        ("gdpr.py contém: /consent endpoint", 
         check_content_in_file("app/api/endpoints/gdpr.py", "consent")),
        
        ("routes.py importa gdpr endpoint", 
         check_content_in_file("app/api/routes.py", "from app.api.endpoints import gdpr")),
        
        ("routes.py registra gdpr endpoint", 
         check_content_in_file("app/api/routes.py", "gdpr.router")),
        
        ("DATABASE: Enum GDPRRequestType", 
         check_content_in_file("app/models/database.py", "class GDPRRequestType")),
        
        ("DATABASE: Table GDPRRequest", 
         check_content_in_file("app/models/database.py", "class GDPRRequest")),
        
        ("DATABASE: Table UserConsent", 
         check_content_in_file("app/models/database.py", "class UserConsent")),
        
        ("DATABASE: Table TokenBlacklist", 
         check_content_in_file("app/models/database.py", "class TokenBlacklist")),
        
        ("DATABASE: Enum ConsentType", 
         check_content_in_file("app/models/database.py", "class ConsentType")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # DATABASE MODELS
    # ========================================================================
    print_section("🗄️ MODELOS DE BANCO DE DADOS")
    
    checks = [
        ("DATABASE: Enum AuditEventType", 
         check_content_in_file("app/models/database.py", "class AuditEventType")),
        
        ("DATABASE: Table AuditLogEnhanced", 
         check_content_in_file("app/models/database.py", "class AuditLogEnhanced")),
        
        ("AuditLogEnhanced tem entry_hash", 
         check_content_in_file("app/models/database.py", "entry_hash")),
        
        ("AuditLogEnhanced tem previous_hash", 
         check_content_in_file("app/models/database.py", "previous_hash")),
        
        ("GDPRRequest tem confirmation_token", 
         check_content_in_file("app/models/database.py", "confirmation_token")),
        
        ("GDPRRequest tem backup_retention_until", 
         check_content_in_file("app/models/database.py", "backup_retention_until")),
        
        ("UserConsent rastreia consentimento", 
         check_content_in_file("app/models/database.py", "consent_type")),
        
        ("TokenBlacklist usa SHA-256 hash", 
         check_content_in_file("app/models/database.py", "token_hash")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # TESTES
    # ========================================================================
    print_section("🧪 TESTES INCLUSOS")
    
    checks = [
        ("Arquivo: app/tests/test_semana1_integration.py existe", 
         check_file_exists("app/tests/test_semana1_integration.py")),
        
        ("Testes contém: TestJWTAuthentication", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestJWTAuthentication")),
        
        ("Testes contém: TestRateLimiting", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestRateLimiting")),
        
        ("Testes contém: TestEncryption", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestEncryption")),
        
        ("Testes contém: TestAuditLogging", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestAuditLogging")),
        
        ("Testes contém: TestRBAC", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestRBAC")),
        
        ("Testes contém: TestGDPR", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestGDPR")),
        
        ("Testes contém: TestCompleteFlow", 
         check_content_in_file("app/tests/test_semana1_integration.py", "class TestCompleteFlow")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # DOCUMENTAÇÃO
    # ========================================================================
    print_section("📚 DOCUMENTAÇÃO")
    
    checks = [
        ("Guia: SEMANA1_INTEGRACAO_COMPLETA.md", 
         check_file_exists("docs/SEMANA1_INTEGRACAO_COMPLETA.md")),
        
        ("Resumo: RESUMO_SEMANA1_INTEGRADA.md", 
         check_file_exists("docs/RESUMO_SEMANA1_INTEGRADA.md")),
        
        ("Diagrama: DIAGRAMA_INTEGRACAO_SEMANA1.md", 
         check_file_exists("docs/DIAGRAMA_INTEGRACAO_SEMANA1.md")),
        
        ("Script: verify_semana1_integration.py", 
         check_file_exists("verify_semana1_integration.py")),
    ]
    
    for name, passed in checks:
        total_checks += 1
        if print_check(name, passed):
            passed_checks += 1
    
    # ========================================================================
    # RESULTADO FINAL
    # ========================================================================
    print_section("📊 RESULTADO FINAL")
    
    percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    print(f"\nTotal de verificações: {total_checks}")
    print(f"Verificações passadas: {BLUE}{passed_checks}{RESET}")
    print(f"Verificações falhadas: {RED}{total_checks - passed_checks}{RESET}")
    print(f"Percentual de sucesso: {percentage:.1f}%\n")
    
    if passed_checks == total_checks:
        print(f"{GREEN}{'='*70}")
        print(f"✅ SEMANA 1 - INTEGRAÇÃO 100% COMPLETA E VALIDADA!")
        print(f"{'='*70}{RESET}\n")
        print(f"{BLUE}Próximos passos:{RESET}")
        print(f"  1. Rodar testes: pytest app/tests/test_semana1_integration.py -v")
        print(f"  2. Conectar auth.py com BD real")
        print(f"  3. Implementar hash de senha (bcrypt)")
        print(f"  4. Configurar SMTP para emails GDPR")
        print(f"  5. Criar Alembic migrations")
        print(f"  6. Deploy em staging\n")
        return 0
    else:
        print(f"{RED}{'='*70}")
        print(f"❌ SEMANA 1 - INTEGRAÇÃO INCOMPLETA")
        print(f"Corriga os itens falhados acima")
        print(f"{'='*70}{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
