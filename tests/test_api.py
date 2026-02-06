#!/usr/bin/env python3
"""
Script de teste da API ISP Customer Support
"""
import asyncio
import httpx
import json
import websockets
from datetime import datetime

# Configurações
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8001/ws/chat"

# Credenciais padrão
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


class APITester:
    """Testador da API"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token = None
        self.headers = {}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self, username: str = DEFAULT_USERNAME, password: str = DEFAULT_PASSWORD):
        """Fazer login e obter token"""
        print(f"🔐 Fazendo login com usuário: {username}")
        
        response = await self.client.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            data={
                "username": username,
                "password": password
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.token = data["data"]["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print("✅ Login realizado com sucesso!")
                return True
            else:
                print(f"❌ Erro no login: {data.get('message')}")
                return False
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            return False
    
    async def test_health_check(self):
        """Testar health check"""
        print("\n🏥 Testando health check...")
        
        response = await self.client.get(f"{API_BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data['status']}")
            print(f"   Versão: {data.get('version', 'N/A')}")
            
            checks = data.get('checks', {})
            for service, status in checks.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {service}: {'OK' if status else 'FAIL'}")
            
            return data['status'] == 'healthy'
        else:
            print(f"❌ Health check falhou: {response.status_code}")
            return False
    
    async def test_user_info(self):
        """Testar informações do usuário"""
        print("\n👤 Testando informações do usuário...")
        
        response = await self.client.get(
            f"{API_BASE_URL}/api/v1/auth/me",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                user = data["data"]
                print(f"✅ Usuário: {user['username']} ({user['role']})")
                print(f"   Email: {user['email']}")
                print(f"   Ativo: {user['ativo']}")
                return True
            else:
                print(f"❌ Erro: {data.get('message')}")
                return False
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            return False
    
    async def test_metrics(self):
        """Testar endpoint de métricas"""
        print("\n📊 Testando métricas...")
        
        response = await self.client.get(f"{API_BASE_URL}/metrics")
        
        if response.status_code == 200:
            metrics_text = response.text
            lines = metrics_text.split('\n')
            metric_count = len([line for line in lines if line and not line.startswith('#')])
            print(f"✅ Métricas disponíveis: {metric_count} métricas")
            
            # Mostrar algumas métricas importantes
            important_metrics = [
                'http_requests_total',
                'http_request_duration_seconds',
                'python_info'
            ]
            
            for metric in important_metrics:
                metric_lines = [line for line in lines if line.startswith(metric)]
                if metric_lines:
                    print(f"   📈 {metric}: encontrada")
            
            return True
        else:
            print(f"❌ Erro ao obter métricas: {response.status_code}")
            return False
    
    async def test_websocket(self):
        """Testar conexão WebSocket"""
        print("\n🔌 Testando WebSocket...")
        
        if not self.token:
            print("❌ Token não disponível para WebSocket")
            return False
        
        try:
            uri = f"{WS_URL}?token={self.token}"
            
            async with websockets.connect(uri) as websocket:
                print("✅ Conexão WebSocket estabelecida")
                
                # Aguardar mensagem de boas-vindas
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data.get("type") == "welcome":
                    print(f"✅ Mensagem de boas-vindas recebida")
                    print(f"   Connection ID: {welcome_data.get('connection_id')}")
                
                # Enviar ping
                ping_msg = {"type": "ping"}
                await websocket.send(json.dumps(ping_msg))
                print("📤 Ping enviado")
                
                # Aguardar pong
                pong_msg = await websocket.recv()
                pong_data = json.loads(pong_msg)
                
                if pong_data.get("type") == "pong":
                    print("✅ Pong recebido")
                    return True
                else:
                    print(f"❌ Resposta inesperada: {pong_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Erro no WebSocket: {str(e)}")
            return False
    
    async def test_create_user(self):
        """Testar criação de usuário"""
        print("\n👥 Testando criação de usuário...")
        
        test_user = {
            "username": f"test_user_{int(datetime.now().timestamp())}",
            "email": f"test_{int(datetime.now().timestamp())}@test.com",
            "password": "test123456",
            "role": "atendente",
            "ativo": True
        }
        
        response = await self.client.post(
            f"{API_BASE_URL}/api/v1/users",
            json=test_user,
            headers=self.headers
        )
        
        if response.status_code == 201:
            data = response.json()
            if data.get("success"):
                user = data["data"]
                print(f"✅ Usuário criado: {user['username']}")
                return True
            else:
                print(f"❌ Erro: {data.get('message')}")
                return False
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            return False
    
    async def run_all_tests(self):
        """Executar todos os testes"""
        print("🚀 Iniciando testes da API ISP Customer Support")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Login", self.login),
            ("User Info", self.test_user_info),
            ("Metrics", self.test_metrics),
            ("WebSocket", self.test_websocket),
            ("Create User", self.test_create_user),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                if test_name == "Login":
                    result = await test_func()
                else:
                    result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ Erro no teste {test_name}: {str(e)}")
                results[test_name] = False
        
        # Resumo dos resultados
        print("\n" + "=" * 50)
        print("📋 RESUMO DOS TESTES")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSOU" if result else "❌ FALHOU"
            print(f"{status} - {test_name}")
            if result:
                passed += 1
        
        print(f"\n🎯 Resultado: {passed}/{total} testes passaram")
        
        if passed == total:
            print("🎉 Todos os testes passaram! Sistema funcionando corretamente.")
        else:
            print("⚠️  Alguns testes falharam. Verifique os logs acima.")
        
        return passed == total


async def main():
    """Função principal"""
    print("ISP Customer Support - Teste da API")
    print(f"Testando: {API_BASE_URL}")
    print(f"WebSocket: {WS_URL}")
    print()
    
    async with APITester() as tester:
        success = await tester.run_all_tests()
        
        if success:
            print("\n🚀 Sistema pronto para uso!")
        else:
            print("\n🔧 Verifique a configuração do sistema.")
        
        return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Testes interrompidos pelo usuário.")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {str(e)}")
        exit(1)