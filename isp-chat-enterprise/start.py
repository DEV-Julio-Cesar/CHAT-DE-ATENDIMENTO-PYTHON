#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Chat Enterprise - Inicializador Principal
Sistema profissional de inicialização de todos os serviços
"""

import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path
from typing import List, Dict
import signal
import psutil
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.live import Live

console = Console()

class ServiceManager:
    """Gerenciador profissional de serviços"""
    
    def __init__(self):
        self.services = {
            "auth-service": {
                "command": [sys.executable, "services/auth-service/app/main.py"],
                "port": 8001,
                "health_url": "http://localhost:8001/health",
                "process": None,
                "status": "stopped"
            },
            "chat-service": {
                "command": [sys.executable, "services/chat-service/app/main.py"],
                "port": 8002,
                "health_url": "http://localhost:8002/health",
                "process": None,
                "status": "stopped"
            },
            "api-gateway": {
                "command": [sys.executable, "services/api-gateway/app/main.py"],
                "port": 8000,
                "health_url": "http://localhost:8000/health",
                "process": None,
                "status": "stopped"
            },
            "web-interface": {
                "command": [sys.executable, "web-server.py"],
                "port": 3000,
                "health_url": "http://localhost:3000",
                "process": None,
                "status": "stopped"
            }
        }
        
        # Registrar handler para shutdown graceful
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
    
    def check_prerequisites(self) -> bool:
        """Verificar pré-requisitos do sistema"""
        console.print("\n🔍 [bold blue]Verificando Pré-requisitos...[/bold blue]")
        
        # Verificar Python
        if sys.version_info < (3, 11):
            console.print("❌ [red]Python 3.11+ é necessário[/red]")
            return False
        console.print("✅ [green]Python versão OK[/green]")
        
        # Verificar arquivo .env
        if not Path(".env").exists():
            console.print("❌ [red]Arquivo .env não encontrado. Copie .env.example para .env[/red]")
            return False
        console.print("✅ [green]Arquivo .env encontrado[/green]")
        
        # Verificar dependências
        try:
            import fastapi, sqlalchemy, redis
            console.print("✅ [green]Dependências principais instaladas[/green]")
        except ImportError as e:
            console.print(f"❌ [red]Dependência faltando: {e}[/red]")
            console.print("💡 [yellow]Execute: pip install -r requirements.txt[/yellow]")
            return False
        
        return True
    
    def start_service(self, service_name: str) -> bool:
        """Iniciar um serviço específico"""
        service = self.services[service_name]
        
        try:
            # Verificar se porta está livre
            if self.is_port_in_use(service["port"]):
                console.print(f"⚠️ [yellow]Porta {service['port']} já está em uso para {service_name}[/yellow]")
                return False
            
            # Iniciar processo
            service["process"] = subprocess.Popen(
                service["command"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            service["status"] = "starting"
            
            # Aguardar inicialização
            time.sleep(2)
            
            if service["process"].poll() is None:
                service["status"] = "running"
                console.print(f"✅ [green]{service_name} iniciado (PID: {service['process'].pid})[/green]")
                return True
            else:
                service["status"] = "failed"
                console.print(f"❌ [red]{service_name} falhou ao iniciar[/red]")
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Erro ao iniciar {service_name}: {e}[/red]")
            service["status"] = "failed"
            return False
    
    def stop_service(self, service_name: str):
        """Parar um serviço específico"""
        service = self.services[service_name]
        
        if service["process"] and service["process"].poll() is None:
            try:
                # Tentar shutdown graceful
                service["process"].terminate()
                service["process"].wait(timeout=10)
                console.print(f"🛑 [yellow]{service_name} parado[/yellow]")
            except subprocess.TimeoutExpired:
                # Force kill se necessário
                service["process"].kill()
                console.print(f"💀 [red]{service_name} forçado a parar[/red]")
            
            service["status"] = "stopped"
            service["process"] = None
    
    def is_port_in_use(self, port: int) -> bool:
        """Verificar se porta está em uso"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
    
    def get_status_table(self) -> Table:
        """Criar tabela de status dos serviços"""
        table = Table(title="Status dos Serviços")
        table.add_column("Serviço", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Porta", style="green")
        table.add_column("PID", style="yellow")
        
        for name, service in self.services.items():
            status_color = {
                "running": "[green]🟢 Rodando[/green]",
                "starting": "[yellow]🟡 Iniciando[/yellow]",
                "stopped": "[red]🔴 Parado[/red]",
                "failed": "[red]❌ Falhou[/red]"
            }.get(service["status"], service["status"])
            
            pid = str(service["process"].pid) if service["process"] else "-"
            
            table.add_row(
                name,
                status_color,
                str(service["port"]),
                pid
            )
        
        return table
    
    def start_all_services(self):
        """Iniciar todos os serviços em ordem"""
        console.print(Panel.fit(
            "[bold green]🚀 ISP Chat Enterprise System[/bold green]\n"
            "[blue]Iniciando todos os serviços...[/blue]",
            border_style="green"
        ))
        
        # Ordem de inicialização (dependências)
        start_order = ["auth-service", "chat-service", "api-gateway", "web-interface"]
        
        for service_name in start_order:
            console.print(f"\n🔄 [blue]Iniciando {service_name}...[/blue]")
            
            if self.start_service(service_name):
                time.sleep(3)  # Aguardar estabilização
            else:
                console.print(f"❌ [red]Falha ao iniciar {service_name}. Abortando...[/red]")
                return False
        
        return True
    
    def stop_all_services(self):
        """Parar todos os serviços"""
        console.print("\n🛑 [yellow]Parando todos os serviços...[/yellow]")
        
        for service_name in reversed(list(self.services.keys())):
            self.stop_service(service_name)
    
    def shutdown_handler(self, signum, frame):
        """Handler para shutdown graceful"""
        console.print("\n\n🛑 [yellow]Recebido sinal de parada. Finalizando serviços...[/yellow]")
        self.stop_all_services()
        console.print("👋 [green]Sistema finalizado com sucesso![/green]")
        sys.exit(0)
    
    def monitor_services(self):
        """Monitorar serviços em tempo real"""
        try:
            with Live(self.get_status_table(), refresh_per_second=1) as live:
                while True:
                    # Atualizar status dos serviços
                    for name, service in self.services.items():
                        if service["process"]:
                            if service["process"].poll() is None:
                                service["status"] = "running"
                            else:
                                service["status"] = "failed"
                    
                    live.update(self.get_status_table())
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            pass

def main():
    """Função principal"""
    manager = ServiceManager()
    
    # Verificar pré-requisitos
    if not manager.check_prerequisites():
        console.print("\n❌ [red]Pré-requisitos não atendidos. Abortando...[/red]")
        sys.exit(1)
    
    # Iniciar serviços
    if manager.start_all_services():
        console.print(Panel.fit(
            "[bold green]🎉 Sistema Iniciado com Sucesso![/bold green]\n\n"
            "[blue]URLs de Acesso:[/blue]\n"
            "• Interface Web: http://localhost:3000\n"
            "• API Gateway: http://localhost:8000\n"
            "• Documentação: http://localhost:8000/docs\n\n"
            "[yellow]Pressione Ctrl+C para parar[/yellow]",
            border_style="green"
        ))
        
        # Monitorar serviços
        manager.monitor_services()
    else:
        console.print("\n❌ [red]Falha ao iniciar sistema[/red]")
        manager.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    main()