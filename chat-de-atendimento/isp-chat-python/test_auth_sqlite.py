#!/usr/bin/env python3
"""
Teste do Auth Service com SQLite
"""
import requests
import json

def test_auth_service_sqlite():
    """Testa o Auth Service com SQLite"""
    base_url = "http://localhost:8002"
    
    print("🧪 Testando Auth Service com SQLite...")
    
    # 1. Teste de health check
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check: OK")
            data = response.json()
            print(f"   Status: {data['status']}")
            print(f"   Database: {data['database']['type']}")
            print(f"   Usuários: {data['database']['users']}")
            print(f"   Conversas: {data['database']['conversations']}")
        else:
            print(f"❌ Health check falhou: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro no health check: {e}")
        return False
    
    # 2. Teste de login
    try:
        login_data = {
            "username": "admin",
            "password": "admin"
        }
        
        response = requests.post(f"{base_url}/login", json=login_data)
        if response.status_code == 200:
            print("✅ Login: OK")
            data = response.json()
            print(f"   Token: {data['access_token'][:20]}...")
            print(f"   Usuário: {data['username']}")
            print(f"   Role: {data['role']}")
            print(f"   User ID: {data['user_id']}")
            
            # Salvar token para próximos testes
            token = data['access_token']
            
            # 3. Teste de verificação de token
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(f"{base_url}/verify", headers=headers)
            if response.status_code == 200:
                print("✅ Verificação de token: OK")
                verify_data = response.json()
                print(f"   Válido: {verify_data['valid']}")
            else:
                print(f"❌ Verificação de token falhou: {response.status_code}")
            
            # 4. Teste de dados do usuário
            response = requests.get(f"{base_url}/users/me", headers=headers)
            if response.status_code == 200:
                print("✅ Dados do usuário: OK")
                user_data = response.json()
                print(f"   ID: {user_data['id']}")
                print(f"   Email: {user_data['email']}")
                print(f"   Último login: {user_data['last_login']}")
            else:
                print(f"❌ Dados do usuário falharam: {response.status_code}")
            
            return True
        else:
            print(f"❌ Login falhou: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return False

def test_performance():
    """Teste de performance básico"""
    import time
    
    print("\n🚀 Testando performance...")
    base_url = "http://localhost:8002"
    
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    # Teste de latência
    start = time.time()
    response = requests.post(f"{base_url}/login", json=login_data)
    latency = (time.time() - start) * 1000
    
    if response.status_code == 200:
        print(f"✅ Latência de login: {latency:.2f}ms")
        
        # Teste de throughput (5 requests)
        start = time.time()
        for _ in range(5):
            requests.post(f"{base_url}/login", json=login_data)
        throughput_time = time.time() - start
        
        print(f"✅ 5 logins sequenciais: {throughput_time:.2f}s")
        print(f"✅ Throughput: {5/throughput_time:.2f} req/s")
    else:
        print(f"❌ Erro no teste de performance: {response.status_code}")

if __name__ == "__main__":
    success = test_auth_service_sqlite()
    if success:
        print("\n🎉 Todos os testes passaram! Auth Service com SQLite funcionando!")
        test_performance()
    else:
        print("\n❌ Alguns testes falharam. Verifique o serviço.")