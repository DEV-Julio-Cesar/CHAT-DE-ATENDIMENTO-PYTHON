#!/usr/bin/env python3
"""
Demo WebSocket - Cliente de Teste
Script para testar conexão WebSocket e funcionalidades do chat

Uso:
    python demo_websocket.py --user-id cliente1 --role cliente
    python demo_websocket.py --user-id atendente1 --role atendente
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional
import argparse

try:
    import websockets
    from colorama import init, Fore, Style
    init()  # Inicializar colorama
except ImportError:
    print("Instalando dependências...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "colorama"])
    import websockets
    from colorama import init, Fore, Style
    init()


class WebSocketClient:
    """Cliente WebSocket para testes"""
    
    def __init__(
        self,
        server_url: str = "ws://localhost:8000/ws/chat",
        user_id: str = "test_user",
        role: str = "cliente"
    ):
        self.server_url = server_url
        self.user_id = user_id
        self.role = role
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.current_room: Optional[str] = None
        self.connected = False
    
    def log(self, message: str, color: str = Fore.WHITE):
        """Log com cor"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.CYAN}[{timestamp}]{Style.RESET_ALL} {color}{message}{Style.RESET_ALL}")
    
    def log_event(self, event: str, data: dict):
        """Log de evento recebido"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.CYAN}[{timestamp}]{Style.RESET_ALL} {Fore.YELLOW}◀ {event}{Style.RESET_ALL}")
        if data:
            for key, value in data.items():
                print(f"    {Fore.WHITE}{key}: {value}{Style.RESET_ALL}")
    
    async def connect(self):
        """Conectar ao servidor WebSocket"""
        url = f"{self.server_url}/{self.user_id}?role={self.role}"
        self.log(f"Conectando a {url}...", Fore.YELLOW)
        
        try:
            self.ws = await websockets.connect(url)
            self.connected = True
            self.log("✅ Conectado com sucesso!", Fore.GREEN)
            return True
        except Exception as e:
            self.log(f"❌ Erro na conexão: {e}", Fore.RED)
            return False
    
    async def disconnect(self):
        """Desconectar"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            self.log("🔌 Desconectado", Fore.YELLOW)
    
    async def send_message(self, content: str, room_id: Optional[str] = None):
        """Enviar mensagem"""
        if not self.ws:
            self.log("Não conectado!", Fore.RED)
            return
        
        message = {
            "event": "message",
            "data": {
                "room_id": room_id or self.current_room,
                "content": content,
                "type": "text"
            }
        }
        
        await self.ws.send(json.dumps(message))
        self.log(f"▶ Mensagem enviada: {content}", Fore.GREEN)
    
    async def join_room(self, room_id: str):
        """Entrar em uma sala"""
        if not self.ws:
            return
        
        message = {
            "event": "join_room",
            "data": {"room_id": room_id}
        }
        
        await self.ws.send(json.dumps(message))
        self.current_room = room_id
        self.log(f"🚪 Entrando na sala: {room_id}", Fore.CYAN)
    
    async def leave_room(self, room_id: str):
        """Sair de uma sala"""
        if not self.ws:
            return
        
        message = {
            "event": "leave_room",
            "data": {"room_id": room_id}
        }
        
        await self.ws.send(json.dumps(message))
        if self.current_room == room_id:
            self.current_room = None
        self.log(f"🚪 Saindo da sala: {room_id}", Fore.YELLOW)
    
    async def send_typing(self, is_typing: bool = True):
        """Enviar indicador de digitação"""
        if not self.ws or not self.current_room:
            return
        
        message = {
            "event": "typing_start" if is_typing else "typing_stop",
            "data": {"room_id": self.current_room}
        }
        
        await self.ws.send(json.dumps(message))
    
    async def send_heartbeat(self):
        """Enviar heartbeat"""
        if not self.ws:
            return
        
        message = {
            "event": "heartbeat",
            "data": {}
        }
        
        await self.ws.send(json.dumps(message))
        self.log("💓 Heartbeat enviado", Fore.MAGENTA)
    
    async def listen(self):
        """Escutar mensagens do servidor"""
        if not self.ws:
            return
        
        try:
            async for message in self.ws:
                data = json.loads(message)
                event = data.get("event", "unknown")
                event_data = data.get("data", {})
                
                # Colorir por tipo de evento
                if event == "message":
                    sender = event_data.get("sender_id", "?")
                    content = event_data.get("content", "")
                    print(f"\n{Fore.BLUE}💬 [{sender}]: {content}{Style.RESET_ALL}")
                
                elif event == "bot_response":
                    content = event_data.get("content", "")
                    print(f"\n{Fore.GREEN}🤖 Bot: {content}{Style.RESET_ALL}")
                    
                    # Mostrar quick replies se houver
                    quick_replies = event_data.get("metadata", {}).get("quick_replies", [])
                    if quick_replies:
                        print(f"{Fore.CYAN}   Respostas rápidas: {', '.join(quick_replies)}{Style.RESET_ALL}")
                
                elif event == "typing_start":
                    user = event_data.get("user_id", "Alguém")
                    print(f"{Fore.YELLOW}✏️ {user} está digitando...{Style.RESET_ALL}")
                
                elif event == "typing_stop":
                    pass  # Silencioso
                
                elif event == "connected":
                    self.log_event("Conexão confirmada", event_data)
                
                elif event == "system_message":
                    msg = event_data.get("message", "")
                    print(f"\n{Fore.MAGENTA}📢 Sistema: {msg}{Style.RESET_ALL}")
                
                elif event == "conversation_assigned":
                    print(f"\n{Fore.GREEN}👤 Atendente atribuído!{Style.RESET_ALL}")
                
                elif event == "queue_position":
                    pos = event_data.get("position", "?")
                    wait = event_data.get("estimated_wait", "?")
                    print(f"\n{Fore.YELLOW}📊 Posição na fila: {pos} (tempo estimado: {wait}){Style.RESET_ALL}")
                
                elif event == "heartbeat":
                    self.log("💓 Heartbeat recebido", Fore.MAGENTA)
                
                elif event == "error":
                    error = event_data.get("error", "Erro desconhecido")
                    self.log(f"❌ Erro: {error}", Fore.RED)
                
                else:
                    self.log_event(event, event_data)
                
        except websockets.exceptions.ConnectionClosed:
            self.log("Conexão fechada pelo servidor", Fore.YELLOW)
        except Exception as e:
            self.log(f"Erro ao receber mensagem: {e}", Fore.RED)


async def interactive_mode(client: WebSocketClient):
    """Modo interativo de comandos"""
    
    print(f"""
{Fore.CYAN}{'='*60}
  WebSocket Chat Client - Modo Interativo
{'='*60}{Style.RESET_ALL}

{Fore.YELLOW}Comandos disponíveis:{Style.RESET_ALL}
  {Fore.GREEN}/join <sala>{Style.RESET_ALL}     - Entrar em uma sala
  {Fore.GREEN}/leave <sala>{Style.RESET_ALL}    - Sair de uma sala
  {Fore.GREEN}/typing{Style.RESET_ALL}          - Simular digitação
  {Fore.GREEN}/heartbeat{Style.RESET_ALL}       - Enviar heartbeat
  {Fore.GREEN}/status{Style.RESET_ALL}          - Ver status da conexão
  {Fore.GREEN}/quit{Style.RESET_ALL}            - Sair
  {Fore.GREEN}<mensagem>{Style.RESET_ALL}       - Enviar mensagem

{Fore.CYAN}Sala atual: {client.current_room or 'Nenhuma'}{Style.RESET_ALL}
""")
    
    while client.connected:
        try:
            # Ler input do usuário
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input(f"{Fore.CYAN}> {Style.RESET_ALL}")
            )
            
            if not user_input:
                continue
            
            # Processar comandos
            if user_input.startswith("/join "):
                room_id = user_input[6:].strip()
                await client.join_room(room_id)
            
            elif user_input.startswith("/leave "):
                room_id = user_input[7:].strip()
                await client.leave_room(room_id)
            
            elif user_input == "/typing":
                await client.send_typing(True)
                await asyncio.sleep(2)
                await client.send_typing(False)
            
            elif user_input == "/heartbeat":
                await client.send_heartbeat()
            
            elif user_input == "/status":
                print(f"""
{Fore.CYAN}Status:{Style.RESET_ALL}
  Conectado: {Fore.GREEN if client.connected else Fore.RED}{client.connected}{Style.RESET_ALL}
  User ID: {client.user_id}
  Role: {client.role}
  Sala atual: {client.current_room or 'Nenhuma'}
""")
            
            elif user_input == "/quit":
                await client.disconnect()
                break
            
            elif user_input.startswith("/"):
                print(f"{Fore.RED}Comando desconhecido: {user_input}{Style.RESET_ALL}")
            
            else:
                # Enviar mensagem
                if not client.current_room:
                    print(f"{Fore.YELLOW}⚠️ Use /join <sala> primeiro para entrar em uma sala{Style.RESET_ALL}")
                    # Criar sala automática
                    auto_room = f"conv_{client.user_id}"
                    await client.join_room(auto_room)
                
                await client.send_message(user_input)
        
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.YELLOW}Saindo...{Style.RESET_ALL}")
            await client.disconnect()
            break
        except Exception as e:
            print(f"{Fore.RED}Erro: {e}{Style.RESET_ALL}")


async def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="WebSocket Chat Client")
    parser.add_argument("--server", default="ws://localhost:8000/ws/chat", help="URL do servidor WebSocket")
    parser.add_argument("--user-id", default=None, help="ID do usuário")
    parser.add_argument("--role", choices=["cliente", "atendente", "supervisor"], default="cliente", help="Role do usuário")
    parser.add_argument("--room", default=None, help="Sala para entrar automaticamente")
    
    args = parser.parse_args()
    
    # Gerar user_id se não fornecido
    user_id = args.user_id or f"{args.role}_{datetime.now().strftime('%H%M%S')}"
    
    print(f"""
{Fore.CYAN}{'='*60}
   🌐 WebSocket Chat Client
{'='*60}
   Servidor: {args.server}
   User ID:  {user_id}
   Role:     {args.role}
{'='*60}{Style.RESET_ALL}
""")
    
    client = WebSocketClient(
        server_url=args.server,
        user_id=user_id,
        role=args.role
    )
    
    # Conectar
    if not await client.connect():
        print(f"{Fore.RED}Falha na conexão. Verifique se o servidor está rodando.{Style.RESET_ALL}")
        return
    
    # Entrar em sala se especificado
    if args.room:
        await client.join_room(args.room)
    
    # Iniciar listener em background
    listener_task = asyncio.create_task(client.listen())
    
    # Modo interativo
    try:
        await interactive_mode(client)
    finally:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Programa encerrado.{Style.RESET_ALL}")
