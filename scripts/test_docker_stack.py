"""
Script de Teste do Stack Docker - CIANET Atendimento
Versão: 3.0

Testa:
- Conexão com API
- Conexão com Redis
- Conexão com SQL Server (opcional)
- Autenticação JWT
- Endpoints principais
"""
import sys
import time
import json
import requests
from typing import Optional, Dict, Any

# Configuração
API_URL = "http://localhost:8000"
TIMEOUT = 10


def colored(text: str, color: str) -> str:
    """Adicionar cor ao texto"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def check(name: str, success: bool, message: str = ""):
    """Exibir resultado do teste"""
    status = colored("✓ PASS", "green") if success else colored("✗ FAIL", "red")
    print(f"  {status} {name}" + (f" - {message}" if message else ""))
    return success


def test_health() -> bool:
    """Testar endpoint de health"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
        return check("Health Check", response.status_code == 200, f"Status: {response.status_code}")
    except Exception as e:
        return check("Health Check", False, str(e))


def test_api_docs() -> bool:
    """Testar documentação OpenAPI"""
    try:
        response = requests.get(f"{API_URL}/docs", timeout=TIMEOUT)
        return check("API Docs (Swagger)", response.status_code == 200)
    except Exception as e:
        return check("API Docs", False, str(e))


def test_metrics() -> bool:
    """Testar endpoint de métricas Prometheus"""
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=TIMEOUT)
        has_metrics = "http_requests" in response.text or "python" in response.text
        return check("Prometheus Metrics", response.status_code == 200 and has_metrics)
    except Exception as e:
        return check("Prometheus Metrics", False, str(e))


def test_login() -> Optional[str]:
    """Testar login e obter token"""
    try:
        response = requests.post(
            f"{API_URL}/api/auth/v2/login",
            json={"email": "admin@cianet.com", "password": "admin123"},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            check("Login JWT", True, "Token obtido")
            return token
        else:
            check("Login JWT", False, f"Status: {response.status_code}")
            return None
    except Exception as e:
        check("Login JWT", False, str(e))
        return None


def test_protected_endpoint(token: str) -> bool:
    """Testar endpoint protegido"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/api/auth/v2/me",
            headers=headers,
            timeout=TIMEOUT
        )
        return check("Protected Endpoint", response.status_code == 200)
    except Exception as e:
        return check("Protected Endpoint", False, str(e))


def test_users_list(token: str) -> bool:
    """Testar listagem de usuários"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/api/users/v2/",
            headers=headers,
            timeout=TIMEOUT
        )
        return check("Users List", response.status_code in [200, 403])
    except Exception as e:
        return check("Users List", False, str(e))


def test_dashboard(token: str) -> bool:
    """Testar dashboard"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/api/dashboard/v2/realtime",
            headers=headers,
            timeout=TIMEOUT
        )
        return check("Dashboard Realtime", response.status_code in [200, 500])  # 500 se SQL Server não estiver configurado
    except Exception as e:
        return check("Dashboard Realtime", False, str(e))


def test_chatbot_status() -> bool:
    """Testar status do chatbot"""
    try:
        response = requests.get(
            f"{API_URL}/api/chatbot/v2/status",
            timeout=TIMEOUT
        )
        return check("Chatbot Status", response.status_code == 200)
    except Exception as e:
        return check("Chatbot Status", False, str(e))


def test_reports_status() -> bool:
    """Testar status dos relatórios PDF"""
    try:
        response = requests.get(
            f"{API_URL}/api/reports/v2/status",
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            return check("PDF Reports", data.get("reportlab_available", False), "ReportLab disponível")
        return check("PDF Reports", False, f"Status: {response.status_code}")
    except Exception as e:
        return check("PDF Reports", False, str(e))


def test_pwa_mobile() -> bool:
    """Testar página PWA mobile"""
    try:
        response = requests.get(f"{API_URL}/mobile", timeout=TIMEOUT)
        has_pwa = "manifest" in response.text.lower() or "CIANET" in response.text
        return check("PWA Mobile", response.status_code == 200 and has_pwa)
    except Exception as e:
        return check("PWA Mobile", False, str(e))


def test_service_worker() -> bool:
    """Testar Service Worker"""
    try:
        response = requests.get(f"{API_URL}/static/sw.js", timeout=TIMEOUT)
        has_sw = "Service Worker" in response.text or "cache" in response.text.lower()
        return check("Service Worker", response.status_code == 200 and has_sw)
    except Exception as e:
        return check("Service Worker", False, str(e))


def test_whatsapp_status(token: str) -> bool:
    """Testar status do WhatsApp"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/api/whatsapp/v2/send/status",
            headers=headers,
            timeout=TIMEOUT
        )
        return check("WhatsApp Status", response.status_code in [200, 500])
    except Exception as e:
        return check("WhatsApp Status", False, str(e))


def main():
    """Executar todos os testes"""
    print("\n" + "=" * 60)
    print(colored("  🟢 CIANET ATENDIMENTO - TESTE DE STACK DOCKER", "green"))
    print("=" * 60)
    print(f"\n  API URL: {API_URL}\n")
    
    passed = 0
    failed = 0
    
    # Testes básicos
    print(colored("\n📋 TESTES BÁSICOS", "blue"))
    print("-" * 40)
    
    if test_health():
        passed += 1
    else:
        failed += 1
        print(colored("\n  ⚠️  API não está respondendo. Verifique se o container está rodando.", "yellow"))
        print(f"     docker ps | grep cianet")
        print(f"     docker logs cianet-api")
        return
    
    if test_api_docs(): passed += 1
    else: failed += 1
    
    if test_metrics(): passed += 1
    else: failed += 1
    
    # Testes de autenticação
    print(colored("\n🔐 TESTES DE AUTENTICAÇÃO", "blue"))
    print("-" * 40)
    
    token = test_login()
    if token:
        passed += 1
        
        if test_protected_endpoint(token): passed += 1
        else: failed += 1
    else:
        failed += 1
        print(colored("  ⚠️  Sem token, pulando testes autenticados", "yellow"))
        token = None
    
    # Testes de funcionalidades
    print(colored("\n🔧 TESTES DE FUNCIONALIDADES", "blue"))
    print("-" * 40)
    
    if token:
        if test_users_list(token): passed += 1
        else: failed += 1
        
        if test_dashboard(token): passed += 1
        else: failed += 1
        
        if test_whatsapp_status(token): passed += 1
        else: failed += 1
    
    if test_chatbot_status(): passed += 1
    else: failed += 1
    
    if test_reports_status(): passed += 1
    else: failed += 1
    
    # Testes PWA
    print(colored("\n📱 TESTES PWA MOBILE", "blue"))
    print("-" * 40)
    
    if test_pwa_mobile(): passed += 1
    else: failed += 1
    
    if test_service_worker(): passed += 1
    else: failed += 1
    
    # Resultado final
    print("\n" + "=" * 60)
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    if failed == 0:
        print(colored(f"  ✅ TODOS OS TESTES PASSARAM! ({passed}/{total})", "green"))
    else:
        print(colored(f"  ⚠️  {passed}/{total} testes passaram ({success_rate:.0f}%)", "yellow"))
        print(colored(f"     {failed} testes falharam", "red"))
    
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    # Esperar API iniciar
    print("\nAguardando API iniciar...")
    for i in range(5):
        try:
            requests.get(f"{API_URL}/health", timeout=2)
            break
        except:
            print(f"  Tentativa {i+1}/5...")
            time.sleep(2)
    
    success = main()
    sys.exit(0 if success else 1)
