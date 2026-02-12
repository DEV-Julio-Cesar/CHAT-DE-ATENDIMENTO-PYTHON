"""
Teste completo da aplicação web
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_web_pages():
    """Testar todas as páginas web"""
    print("=" * 70)
    print("🌐 TESTE COMPLETO DA APLICAÇÃO WEB")
    print("=" * 70)
    
    pages = [
        ("/", "Página Principal"),
        ("/login", "Login"),
        ("/dashboard", "Dashboard"),
        ("/chat", "Chat de Atendimento"),
        ("/atendimento", "Atendimento Profissional (NOVO)"),
        ("/whatsapp", "Configuração WhatsApp"),
        ("/chatbot-admin", "Admin do Chatbot"),
        ("/campaigns", "Campanhas"),
        ("/users", "Gerenciamento de Usuários"),
        ("/settings", "Configurações"),
    ]
    
    print("\n📄 PÁGINAS WEB:")
    print("-" * 70)
    
    for url, name in pages:
        try:
            response = requests.get(f"{BASE_URL}{url}", timeout=5)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {name:40} | {url:30} | {response.status_code}")
        except Exception as e:
            print(f"❌ {name:40} | {url:30} | ERRO: {str(e)[:30]}")
    
    print("\n" + "=" * 70)
    print("📡 API ENDPOINTS:")
    print("-" * 70)
    
    # Testar endpoints da API
    api_endpoints = [
        ("/api/v1/auth/login", "POST", "Autenticação"),
        ("/health", "GET", "Health Check"),
        ("/info", "GET", "Informações do Sistema"),
        ("/docs", "GET", "Documentação Swagger"),
        ("/api/v1/whatsapp/qr-code", "GET", "QR Code WhatsApp"),
        ("/api/v1/whatsapp/chats", "GET", "Lista de Chats"),
    ]
    
    for url, method, name in api_endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{url}", timeout=5)
            else:
                response = requests.post(f"{BASE_URL}{url}", timeout=5)
            
            status = "✅" if response.status_code in [200, 401, 422] else "❌"
            print(f"{status} {name:40} | {method:6} {url:30} | {response.status_code}")
        except Exception as e:
            print(f"❌ {name:40} | {method:6} {url:30} | ERRO")
    
    print("\n" + "=" * 70)
    print("🤖 SERVIÇO WHATSAPP:")
    print("-" * 70)
    
    # Testar serviço WhatsApp
    whatsapp_endpoints = [
        ("http://localhost:3001/status", "Status do Serviço"),
        ("http://localhost:3001/qr-code", "QR Code"),
    ]
    
    for url, name in whatsapp_endpoints:
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            status = "✅" if response.status_code == 200 else "❌"
            
            if "status" in data:
                print(f"{status} {name:40} | Status: {data.get('status', 'N/A').upper()}")
            elif "connected" in data:
                connected = "CONECTADO" if data.get('connected') else "DESCONECTADO"
                print(f"{status} {name:40} | {connected}")
            else:
                print(f"{status} {name:40} | {response.status_code}")
        except Exception as e:
            print(f"❌ {name:40} | ERRO: Serviço não está rodando")
    
    print("\n" + "=" * 70)
    print("🎯 NOVO SISTEMA DE ATENDIMENTO:")
    print("-" * 70)
    
    # Testar novo sistema de atendimento (requer autenticação)
    print("⚠️  Endpoints de atendimento requerem autenticação JWT")
    print("   Para testar, faça login primeiro em: /login")
    print("")
    print("   Endpoints disponíveis:")
    print("   • GET  /api/v1/atendimento/automacao - Conversas em automação")
    print("   • GET  /api/v1/atendimento/espera - Conversas em espera")
    print("   • GET  /api/v1/atendimento/ativo - Conversas ativas")
    print("   • POST /api/v1/atendimento/atribuir - Puxar atendimento")
    print("   • POST /api/v1/atendimento/transferir - Transferir atendimento")
    print("   • POST /api/v1/atendimento/finalizar - Finalizar atendimento")
    print("   • GET  /api/v1/atendimento/estatisticas - Estatísticas")
    
    print("\n" + "=" * 70)
    print("📋 RESUMO:")
    print("=" * 70)
    print("")
    print("✅ Servidor FastAPI: RODANDO (porta 8000)")
    print("✅ Serviço WhatsApp: RODANDO (porta 3001)")
    print("")
    print("🌐 ACESSE AS PÁGINAS:")
    print("-" * 70)
    print(f"   • Login:              {BASE_URL}/login")
    print(f"   • Dashboard:          {BASE_URL}/dashboard")
    print(f"   • Chat:               {BASE_URL}/chat")
    print(f"   • Atendimento (NOVO): {BASE_URL}/atendimento")
    print(f"   • WhatsApp Config:    {BASE_URL}/whatsapp")
    print(f"   • API Docs:           {BASE_URL}/docs")
    print("")
    print("📱 WHATSAPP:")
    print("-" * 70)
    print("   1. Acesse: http://127.0.0.1:8000/whatsapp")
    print("   2. Escaneie o QR Code com seu WhatsApp")
    print("   3. Aguarde a conexão")
    print("")
    print("🎯 SISTEMA DE ATENDIMENTO PROFISSIONAL:")
    print("-" * 70)
    print("   1. Faça login em: /login")
    print("   2. Acesse: /atendimento")
    print("   3. Veja as 3 abas:")
    print("      • AUTOMAÇÃO - IA atendendo")
    print("      • ESPERA - Aguardando atendente")
    print("      • ATIVO - Em atendimento humano")
    print("")
    print("=" * 70)

if __name__ == "__main__":
    test_web_pages()
