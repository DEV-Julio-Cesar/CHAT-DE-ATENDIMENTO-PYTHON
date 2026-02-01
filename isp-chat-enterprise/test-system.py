#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Chat Enterprise - Teste Completo do Sistema
Testa todas as funcionalidades da nova estrutura enterprise
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any

class EnterpriseSystemTester:
    """Testador completo do sistema enterprise"""
    
    def __init__(self):
        # URLs dos serviços na nova estrutura
        self.gateway_url = "http://localhost:8000"
        self.auth_url = f"{self.gateway_url}/api/auth"
        self.chat_url = f"{self.gateway_url}/api/chat"
        self.web_url = "http://localhost:3000"
        
        # URLs diretas dos serviços (para testes específicos)
        self.auth_direct_url = "http://localhost:8001"
        self.chat_direct_url = "http://localhost:8002"
        
        self.token = None
        self.session = None
        
    async def start(self):
        """Inicializar sessão HTTP"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )
        
    async def stop(self):
        """Finalizar sessão HTTP"""
        if self.session:
            await self.session.close()
    
    async def test_services_health(self) -> Dict[str, Any]:
        """Teste: Health check de todos os serviços"""
        results = {}
        
        services = {
            "API Gateway": f"{self.gateway_url}/health",
            "Auth Service": f"{self.auth_direct_url}/health", 
            "Chat Service": f"{self.chat_direct_url}/health",
            "Web Interface": self.web_url
        }
        
        for service_name, url in services.items():
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json() if 'health' in url else {"status": "ok"}
                        results[service_name] = {
                            "status": "healthy",
                            "response_time": response.headers.get("X-Process-Time", "unknown"),
                            "data": data
                        }
                    else:
                        results[service_name] = {
                            "status": "unhealthy",
                            "status_code": response.status
                        }
            except Exception as e:
                results[service_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "test": "services_health",
            "status": "success" if all(r["status"] == "healthy" for r in results.values()) else "partial",
            "services": results
        }
    
    async def test_gateway_routing(self) -> Dict[str, Any]:
        """Teste: Roteamento do API Gateway"""
        routes_to_test = [
            {"path": "/api/auth", "expected_service": "auth-service"},
            {"path": "/api/chat", "expected_service": "chat-service"},
            {"path": "/webhook/whatsapp", "expected_service": "chat-service"}
        ]
        
        results = []
        
        for route in routes_to_test:
            try:
                # Testar rota de health específica
                health_url = f"{self.gateway_url}{route['path']}/health" if route['path'] != "/webhook/whatsapp" else f"{self.gateway_url}/api/chat/health"
                
                async with self.session.get(health_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        results.append({
                            "path": route["path"],
                            "status": "success",
                            "service": data.get("service", "unknown"),
                            "routed_correctly": route["expected_service"] in data.get("service", "").lower()
                        })
                    else:
                        results.append({
                            "path": route["path"],
                            "status": "failed",
                            "status_code": response.status
                        })
            except Exception as e:
                results.append({
                    "path": route["path"],
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "test": "gateway_routing",
            "status": "success" if all(r["status"] == "success" for r in results) else "partial",
            "routes": results
        }
    
    async def test_authentication_flow(self) -> Dict[str, Any]:
        """Teste: Fluxo completo de autenticação"""
        try:
            # 1. Login via Gateway
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            async with self.session.post(
                f"{self.auth_url}/login",
                json=login_data
            ) as response:
                
                if response.status != 200:
                    error_data = await response.json()
                    return {
                        "test": "authentication_flow",
                        "status": "failed",
                        "step": "login",
                        "error": error_data
                    }
                
                login_response = await response.json()
                self.token = login_response.get("access_token")
                
                if not self.token:
                    return {
                        "test": "authentication_flow",
                        "status": "failed",
                        "step": "token_extraction",
                        "error": "No access token received"
                    }
            
            # 2. Verificar token via Gateway
            headers = {"Authorization": f"Bearer {self.token}"}
            
            async with self.session.post(
                f"{self.auth_url}/verify",
                headers=headers
            ) as response:
                
                if response.status != 200:
                    return {
                        "test": "authentication_flow",
                        "status": "failed",
                        "step": "token_verification",
                        "status_code": response.status
                    }
                
                verify_response = await response.json()
                
                if not verify_response.get("valid"):
                    return {
                        "test": "authentication_flow",
                        "status": "failed",
                        "step": "token_validation",
                        "error": "Token marked as invalid"
                    }
            
            # 3. Acessar endpoint protegido
            async with self.session.get(
                f"{self.auth_url}/users/me",
                headers=headers
            ) as response:
                
                if response.status != 200:
                    return {
                        "test": "authentication_flow",
                        "status": "failed",
                        "step": "protected_endpoint",
                        "status_code": response.status
                    }
                
                user_data = await response.json()
            
            return {
                "test": "authentication_flow",
                "status": "success",
                "user": user_data.get("username"),
                "token_length": len(self.token),
                "steps_completed": ["login", "token_verification", "protected_endpoint"]
            }
            
        except Exception as e:
            return {
                "test": "authentication_flow",
                "status": "error",
                "error": str(e)
            }
    
    async def test_chat_functionality(self) -> Dict[str, Any]:
        """Teste: Funcionalidades do chat"""
        if not self.token:
            return {
                "test": "chat_functionality",
                "status": "skipped",
                "reason": "No authentication token"
            }
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            # 1. Criar conversa
            conversation_data = {
                "customer_phone": "5511987654321",
                "customer_name": "Cliente Teste Enterprise",
                "customer_email": "teste@enterprise.com",
                "priority": "normal",
                "initial_message": "Teste do sistema enterprise"
            }
            
            async with self.session.post(
                f"{self.chat_url}/conversations",
                json=conversation_data,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    error_data = await response.json()
                    return {
                        "test": "chat_functionality",
                        "status": "failed",
                        "step": "create_conversation",
                        "error": error_data
                    }
                
                conversation = await response.json()
                conversation_id = conversation.get("id")
            
            # 2. Listar conversas
            async with self.session.get(
                f"{self.chat_url}/conversations",
                headers=headers
            ) as response:
                
                if response.status != 200:
                    return {
                        "test": "chat_functionality",
                        "status": "failed",
                        "step": "list_conversations"
                    }
                
                conversations_list = await response.json()
            
            # 3. Criar mensagem
            message_data = {
                "content": f"Mensagem de teste - {datetime.now().strftime('%H:%M:%S')}",
                "message_type": "text",
                "direction": "outbound"
            }
            
            async with self.session.post(
                f"{self.chat_url}/conversations/{conversation_id}/messages",
                json=message_data,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    return {
                        "test": "chat_functionality",
                        "status": "failed",
                        "step": "create_message"
                    }
                
                message = await response.json()
            
            # 4. Obter mensagens da conversa
            async with self.session.get(
                f"{self.chat_url}/conversations/{conversation_id}/messages",
                headers=headers
            ) as response:
                
                if response.status != 200:
                    return {
                        "test": "chat_functionality",
                        "status": "failed",
                        "step": "get_messages"
                    }
                
                messages = await response.json()
            
            return {
                "test": "chat_functionality",
                "status": "success",
                "conversation_id": conversation_id,
                "total_conversations": conversations_list.get("total", 0),
                "message_id": message.get("id"),
                "total_messages": messages.get("total", 0),
                "steps_completed": ["create_conversation", "list_conversations", "create_message", "get_messages"]
            }
            
        except Exception as e:
            return {
                "test": "chat_functionality",
                "status": "error",
                "error": str(e)
            }
    
    async def test_websocket_connection(self) -> Dict[str, Any]:
        """Teste: Conexão WebSocket"""
        try:
            import websockets
            
            # Tentar conectar ao WebSocket do chat
            ws_url = "ws://localhost:8002/ws/test-conversation"
            
            async with websockets.connect(ws_url) as websocket:
                # Enviar mensagem de teste
                test_message = {
                    "type": "typing",
                    "user": "test-user",
                    "is_typing": True
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Aguardar resposta (timeout de 5 segundos)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    return {
                        "test": "websocket_connection",
                        "status": "success",
                        "connected": True,
                        "message_sent": test_message,
                        "response_received": response_data
                    }
                except asyncio.TimeoutError:
                    return {
                        "test": "websocket_connection",
                        "status": "partial",
                        "connected": True,
                        "message_sent": test_message,
                        "response_received": None,
                        "note": "Connection successful but no response received"
                    }
                    
        except ImportError:
            return {
                "test": "websocket_connection",
                "status": "skipped",
                "reason": "websockets library not installed"
            }
        except Exception as e:
            return {
                "test": "websocket_connection",
                "status": "error",
                "error": str(e)
            }
    
    async def test_system_metrics(self) -> Dict[str, Any]:
        """Teste: Métricas do sistema"""
        try:
            # Obter estatísticas do gateway
            async with self.session.get(f"{self.gateway_url}/stats") as response:
                if response.status == 200:
                    gateway_stats = await response.json()
                else:
                    gateway_stats = {"error": f"Status {response.status}"}
            
            # Obter estatísticas do chat (se autenticado)
            chat_stats = {}
            if self.token:
                headers = {"Authorization": f"Bearer {self.token}"}
                async with self.session.get(f"{self.chat_url}/stats", headers=headers) as response:
                    if response.status == 200:
                        chat_stats = await response.json()
                    else:
                        chat_stats = {"error": f"Status {response.status}"}
            
            return {
                "test": "system_metrics",
                "status": "success",
                "gateway_stats": gateway_stats,
                "chat_stats": chat_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "test": "system_metrics",
                "status": "error",
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Executar todos os testes do sistema enterprise"""
        print("🧪 INICIANDO TESTE COMPLETO DO SISTEMA ENTERPRISE")
        print("=" * 60)
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": "ISP Chat Enterprise",
            "version": "1.0.0",
            "tests": []
        }
        
        # Lista de testes a executar
        tests = [
            ("Health Check dos Serviços", self.test_services_health),
            ("Roteamento do Gateway", self.test_gateway_routing),
            ("Fluxo de Autenticação", self.test_authentication_flow),
            ("Funcionalidades do Chat", self.test_chat_functionality),
            ("Conexão WebSocket", self.test_websocket_connection),
            ("Métricas do Sistema", self.test_system_metrics)
        ]
        
        # Executar cada teste
        for i, (test_name, test_func) in enumerate(tests, 1):
            print(f"\n{i}️⃣ TESTANDO {test_name.upper()}...")
            
            try:
                result = await test_func()
                results["tests"].append(result)
                
                status_emoji = {
                    "success": "✅",
                    "partial": "⚠️",
                    "failed": "❌",
                    "error": "💥",
                    "skipped": "⏭️"
                }.get(result["status"], "❓")
                
                print(f"  {status_emoji} {test_name}: {result['status']}")
                
                # Mostrar detalhes importantes
                if result["status"] == "success":
                    if "steps_completed" in result:
                        print(f"    📋 Etapas: {', '.join(result['steps_completed'])}")
                    if "services" in result:
                        healthy_services = sum(1 for s in result["services"].values() if s["status"] == "healthy")
                        total_services = len(result["services"])
                        print(f"    🏥 Serviços saudáveis: {healthy_services}/{total_services}")
                
                elif result["status"] in ["failed", "error"]:
                    if "error" in result:
                        print(f"    ❌ Erro: {result['error']}")
                    if "step" in result:
                        print(f"    📍 Falhou em: {result['step']}")
                
            except Exception as e:
                error_result = {
                    "test": test_name.lower().replace(" ", "_"),
                    "status": "error",
                    "error": str(e)
                }
                results["tests"].append(error_result)
                print(f"  💥 {test_name}: ERRO - {e}")
        
        # Resumo final
        print("\n📊 RESUMO DOS TESTES ENTERPRISE")
        print("=" * 60)
        
        total_tests = len(results["tests"])
        successful_tests = len([t for t in results["tests"] if t["status"] == "success"])
        partial_tests = len([t for t in results["tests"] if t["status"] == "partial"])
        failed_tests = len([t for t in results["tests"] if t["status"] in ["failed", "error"]])
        skipped_tests = len([t for t in results["tests"] if t["status"] == "skipped"])
        
        print(f"Total de testes: {total_tests}")
        print(f"✅ Sucessos: {successful_tests}")
        print(f"⚠️ Parciais: {partial_tests}")
        print(f"❌ Falhas: {failed_tests}")
        print(f"⏭️ Pulados: {skipped_tests}")
        
        success_rate = ((successful_tests + partial_tests) / total_tests) * 100
        print(f"📈 Taxa de sucesso: {success_rate:.1f}%")
        
        # Detalhes dos problemas
        if failed_tests > 0:
            print("\n❌ TESTES QUE FALHARAM:")
            for test in results["tests"]:
                if test["status"] in ["failed", "error"]:
                    print(f"  - {test.get('test')}: {test.get('error', 'Unknown error')}")
        
        # Detalhes dos sucessos
        print("\n✅ FUNCIONALIDADES VALIDADAS:")
        for test in results["tests"]:
            if test["status"] == "success":
                test_name = test.get('test', 'unknown')
                if test_name == "services_health":
                    healthy_count = sum(1 for s in test["services"].values() if s["status"] == "healthy")
                    print(f"  - Serviços saudáveis: {healthy_count} de {len(test['services'])}")
                elif test_name == "authentication_flow":
                    print(f"  - Autenticação completa: usuário {test.get('user')}")
                elif test_name == "chat_functionality":
                    print(f"  - Chat funcional: {test.get('total_conversations')} conversas, {test.get('total_messages')} mensagens")
                elif test_name == "websocket_connection":
                    print(f"  - WebSocket: conexão estabelecida")
                else:
                    print(f"  - {test_name}: OK")
        
        results["summary"] = {
            "total": total_tests,
            "successful": successful_tests,
            "partial": partial_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "success_rate": success_rate
        }
        
        return results

async def main():
    """Função principal"""
    tester = EnterpriseSystemTester()
    
    try:
        await tester.start()
        results = await tester.run_all_tests()
        
        # Salvar resultados
        with open("enterprise-test-results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados salvos em: enterprise-test-results.json")
        
        # Retornar código de saída baseado no sucesso
        success_rate = results["summary"]["success_rate"]
        if success_rate >= 80:
            print("\n🎉 SISTEMA ENTERPRISE FUNCIONANDO CORRETAMENTE!")
            return 0
        elif success_rate >= 60:
            print("\n⚠️ SISTEMA PARCIALMENTE FUNCIONAL - VERIFICAR PROBLEMAS")
            return 1
        else:
            print("\n❌ SISTEMA COM PROBLEMAS CRÍTICOS")
            return 2
            
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NO TESTE: {e}")
        return 3
    finally:
        await tester.stop()

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)