#!/usr/bin/env python3
"""
Teste do Auth Service
"""
import requests
import json

def test_auth_service():
    """Testa o Auth Service"""
    base_url = "http://localhost:8001"
    
    print("🧪 Testando Auth Service...")
    
    # 1. Teste de health check
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check: OK")
            print(f"   Resposta: {response.json()}")
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
            
            # Salvar token para próximos testes
            token = data['access_token']
            
            # 3. Teste de verificação de token
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(f"{base_url}/verify", headers=headers)
            if response.status_code == 200:
                print("✅ Verificação de token: OK")
            else:
                print(f"❌ Verificação de token falhou: {response.status_code}")
            
            # 4. Teste de dados do usuário
            response = requests.get(f"{base_url}/users/me", headers=headers)
            if response.status_code == 200:
                print("✅ Dados do usuário: OK")
                user_data = response.json()
                print(f"   ID: {user_data['id']}")
                print(f"   Email: {user_data['email']}")
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

if __name__ == "__main__":
    success = test_auth_service()
    if success:
        print("\n🎉 Todos os testes passaram! Auth Service funcionando perfeitamente!")
    else:
        print("\n❌ Alguns testes falharam. Verifique o serviço.")