"""
Teste da API de Atendimento Profissional
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def login():
    """Fazer login e obter token"""
    print("🔐 Fazendo login...")
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "Xa&Iaon8oKoPbHb0U&a4"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✅ Login realizado com sucesso!")
        print(f"   Token: {token[:50]}...")
        return token
    else:
        print(f"❌ Erro no login: {response.status_code}")
        return None

def test_atendimento_endpoints(token):
    """Testar endpoints de atendimento"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 70)
    print("🎯 TESTANDO ENDPOINTS DE ATENDIMENTO")
    print("=" * 70)
    
    # 1. Estatísticas
    print("\n📊 1. Estatísticas:")
    print("-" * 70)
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/atendimento/estatisticas",
            headers=headers
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Estatísticas obtidas:")
            print(f"   • Automação: {stats.get('automacao', 0)} conversas")
            print(f"   • Espera: {stats.get('espera', 0)} conversas")
            print(f"   • Ativo: {stats.get('ativo', 0)} conversas")
            print(f"   • Total: {stats.get('total', 0)} conversas")
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # 2. Listar Automação
    print("\n🤖 2. Conversas em AUTOMAÇÃO:")
    print("-" * 70)
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/atendimento/automacao",
            headers=headers
        )
        if response.status_code == 200:
            conversas = response.json()
            print(f"✅ {len(conversas)} conversas encontradas")
            for i, conv in enumerate(conversas[:3], 1):
                print(f"   {i}. {conv.get('cliente_nome')} - {conv.get('cliente_telefone')}")
                print(f"      Tempo: {conv.get('tempo_espera_minutos', 0)} min")
        else:
            print(f"❌ Erro: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # 3. Listar Espera
    print("\n⏳ 3. Conversas em ESPERA:")
    print("-" * 70)
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/atendimento/espera",
            headers=headers
        )
        if response.status_code == 200:
            conversas = response.json()
            print(f"✅ {len(conversas)} conversas encontradas")
            for i, conv in enumerate(conversas[:3], 1):
                print(f"   {i}. {conv.get('cliente_nome')} - {conv.get('cliente_telefone')}")
                print(f"      Tempo: {conv.get('tempo_espera_minutos', 0)} min")
        else:
            print(f"❌ Erro: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # 4. Listar Ativo
    print("\n💬 4. Conversas ATIVAS:")
    print("-" * 70)
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/atendimento/ativo",
            headers=headers
        )
        if response.status_code == 200:
            conversas = response.json()
            print(f"✅ {len(conversas)} conversas encontradas")
            for i, conv in enumerate(conversas[:3], 1):
                print(f"   {i}. {conv.get('cliente_nome')} - {conv.get('cliente_telefone')}")
                print(f"      Atendente: {conv.get('atendente_nome', 'N/A')}")
                print(f"      Tempo: {conv.get('tempo_espera_minutos', 0)} min")
        else:
            print(f"❌ Erro: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print("\n" + "=" * 70)
    print("✅ TESTE CONCLUÍDO!")
    print("=" * 70)
    print("\n📌 Para testar as ações (atribuir, transferir, finalizar):")
    print("   1. Acesse: http://127.0.0.1:8000/atendimento")
    print("   2. Faça login com as credenciais")
    print("   3. Teste as funcionalidades na interface")
    print("\n📖 Documentação completa:")
    print("   http://127.0.0.1:8000/docs")

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TESTE DA API DE ATENDIMENTO PROFISSIONAL")
    print("=" * 70)
    
    # Fazer login
    token = login()
    
    if token:
        # Testar endpoints
        test_atendimento_endpoints(token)
    else:
        print("\n❌ Não foi possível fazer login. Verifique as credenciais.")
