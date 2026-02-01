#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Chat Enterprise - Limpeza de Arquivos Antigos
Remove arquivos e pastas desnecessárias após migração para estrutura enterprise
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class SystemCleaner:
    """Limpador de arquivos antigos do sistema"""
    
    def __init__(self):
        self.cleanup_log = []
        self.dry_run = False  # Se True, apenas simula a limpeza
        
    def log(self, message: str, level: str = "INFO"):
        """Log de limpeza"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.cleanup_log.append(log_entry)
        print(log_entry)
    
    def get_old_directories(self) -> List[str]:
        """Obter lista de diretórios antigos para remoção"""
        old_dirs = [
            "isp-chat-python",
            "chat-de-atendimento", 
            "app",
            ".wwebjs_auth",
            ".wwebjs_cache",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "venv",
            ".venv"
        ]
        
        existing_dirs = []
        for dir_name in old_dirs:
            if os.path.exists(dir_name):
                existing_dirs.append(dir_name)
        
        return existing_dirs
    
    def get_old_files(self) -> List[str]:
        """Obter lista de arquivos antigos para remoção"""
        old_files = [
            # Node.js files
            "package.json",
            "package-lock.json",
            "main.js",
            "auth.js",
            "renderer.js",
            "preload.js",
            "preload-login.js",
            "preload-history.js",
            "websocket_server.js",
            
            # Python files antigos
            "run-local.py",
            "whatsapp-web-simple.py",
            "configure_whatsapp.py",
            "test_api.py",
            "test_complete_system.py",
            
            # HTML files antigos
            "index.html",
            "login.html",
            "history.html",
            
            # Arquivos de configuração antigos
            "tsconfig.json",
            "Procfile",
            
            # Arquivos de documentação antigos
            "NEXT-STEPS.md",
            "ROADMAP-PROFISSIONAL.md",
            "monitoring-setup.md",
            "python-migration-plan.md",
            "upgrade-to-postgres.md",
            "web-interface-plan.md",
            "whatsapp-setup-guide.md",
            "whatsapp-token-tutorial.md",
            
            # Arquivos de backup e temporários
            "*.log",
            "*.tmp",
            "*.bak",
            "*.old"
        ]
        
        existing_files = []
        for file_pattern in old_files:
            if "*" in file_pattern:
                # Usar glob para padrões
                import glob
                matching_files = glob.glob(file_pattern)
                existing_files.extend(matching_files)
            else:
                if os.path.exists(file_pattern):
                    existing_files.append(file_pattern)
        
        return existing_files
    
    def get_duplicate_files(self) -> List[str]:
        """Obter arquivos duplicados que existem na nova estrutura"""
        duplicates = []
        
        # Verificar se existem arquivos duplicados
        enterprise_path = "isp-chat-enterprise"
        if not os.path.exists(enterprise_path):
            return duplicates
        
        # Arquivos que podem estar duplicados
        potential_duplicates = [
            "requirements.txt",
            "docker-compose.yml",
            "Dockerfile",
            ".env.example",
            ".gitignore",
            "README.md"
        ]
        
        for file_name in potential_duplicates:
            root_file = file_name
            enterprise_file = os.path.join(enterprise_path, file_name)
            
            if os.path.exists(root_file) and os.path.exists(enterprise_file):
                # Verificar se são diferentes
                try:
                    with open(root_file, 'r', encoding='utf-8') as f1:
                        content1 = f1.read()
                    with open(enterprise_file, 'r', encoding='utf-8') as f2:
                        content2 = f2.read()
                    
                    if content1 != content2:
                        self.log(f"Arquivo {file_name} é diferente na raiz e no enterprise", "WARNING")
                    else:
                        duplicates.append(root_file)
                        
                except Exception as e:
                    self.log(f"Erro ao comparar {file_name}: {e}", "ERROR")
        
        return duplicates
    
    def calculate_space_savings(self, paths: List[str]) -> int:
        """Calcular espaço que será liberado"""
        total_size = 0
        
        for path in paths:
            try:
                if os.path.isfile(path):
                    total_size += os.path.getsize(path)
                elif os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                total_size += os.path.getsize(file_path)
                            except (OSError, IOError):
                                pass
            except (OSError, IOError):
                pass
        
        return total_size
    
    def format_size(self, size_bytes: int) -> str:
        """Formatar tamanho em bytes para formato legível"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def remove_path(self, path: str) -> bool:
        """Remover arquivo ou diretório"""
        try:
            if self.dry_run:
                self.log(f"[DRY RUN] Removeria: {path}")
                return True
            
            if os.path.isfile(path):
                os.remove(path)
                self.log(f"Arquivo removido: {path}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                self.log(f"Diretório removido: {path}")
            else:
                self.log(f"Caminho não encontrado: {path}", "WARNING")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"Erro ao remover {path}: {e}", "ERROR")
            return False
    
    def create_cleanup_summary(self, removed_paths: List[str], space_saved: int) -> Dict:
        """Criar resumo da limpeza"""
        summary = {
            "cleanup_timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "total_items_removed": len(removed_paths),
            "space_saved_bytes": space_saved,
            "space_saved_formatted": self.format_size(space_saved),
            "removed_paths": removed_paths,
            "cleanup_log": self.cleanup_log
        }
        
        return summary
    
    def run_cleanup(self, dry_run: bool = False, interactive: bool = True):
        """Executar limpeza completa"""
        self.dry_run = dry_run
        
        print("🧹 ISP CHAT ENTERPRISE - LIMPEZA DE ARQUIVOS ANTIGOS")
        print("=" * 60)
        
        if dry_run:
            print("🔍 MODO SIMULAÇÃO - Nenhum arquivo será removido")
        
        # 1. Obter listas de arquivos/diretórios
        old_dirs = self.get_old_directories()
        old_files = self.get_old_files()
        duplicate_files = self.get_duplicate_files()
        
        all_paths = old_dirs + old_files + duplicate_files
        
        if not all_paths:
            print("✅ Nenhum arquivo antigo encontrado para limpeza")
            return True
        
        # 2. Calcular espaço que será liberado
        space_to_save = self.calculate_space_savings(all_paths)
        
        print(f"\n📊 ANÁLISE DE LIMPEZA:")
        print(f"  • Diretórios antigos: {len(old_dirs)}")
        print(f"  • Arquivos antigos: {len(old_files)}")
        print(f"  • Arquivos duplicados: {len(duplicate_files)}")
        print(f"  • Total de itens: {len(all_paths)}")
        print(f"  • Espaço a ser liberado: {self.format_size(space_to_save)}")
        
        # 3. Mostrar detalhes
        if old_dirs:
            print(f"\n📁 DIRETÓRIOS A REMOVER:")
            for dir_path in old_dirs:
                print(f"  - {dir_path}")
        
        if old_files:
            print(f"\n📄 ARQUIVOS A REMOVER:")
            for file_path in old_files[:10]:  # Mostrar apenas os primeiros 10
                print(f"  - {file_path}")
            if len(old_files) > 10:
                print(f"  ... e mais {len(old_files) - 10} arquivos")
        
        if duplicate_files:
            print(f"\n🔄 ARQUIVOS DUPLICADOS A REMOVER:")
            for dup_path in duplicate_files:
                print(f"  - {dup_path}")
        
        # 4. Confirmação interativa
        if interactive and not dry_run:
            print(f"\n⚠️ ATENÇÃO: Esta operação removerá {len(all_paths)} itens e liberará {self.format_size(space_to_save)}")
            response = input("Deseja continuar? (s/N): ").lower().strip()
            
            if response not in ['s', 'sim', 'y', 'yes']:
                print("❌ Limpeza cancelada pelo usuário")
                return False
        
        # 5. Executar remoção
        print(f"\n🧹 {'SIMULANDO' if dry_run else 'EXECUTANDO'} LIMPEZA...")
        
        removed_paths = []
        
        for path in all_paths:
            if self.remove_path(path):
                removed_paths.append(path)
        
        # 6. Criar resumo
        actual_space_saved = self.calculate_space_savings(removed_paths) if not dry_run else space_to_save
        summary = self.create_cleanup_summary(removed_paths, actual_space_saved)
        
        # 7. Salvar log de limpeza
        log_path = "isp-chat-enterprise/cleanup-log.json"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        import json
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # 8. Resumo final
        print(f"\n📊 RESUMO DA LIMPEZA")
        print("=" * 40)
        print(f"✅ Itens {'simulados' if dry_run else 'removidos'}: {len(removed_paths)}")
        print(f"💾 Espaço {'que seria' if dry_run else ''} liberado: {self.format_size(actual_space_saved)}")
        print(f"📋 Log salvo em: {log_path}")
        
        if dry_run:
            print(f"\n💡 Para executar a limpeza real, execute:")
            print(f"   python scripts/cleanup-old-files.py --execute")
        else:
            print(f"\n🎉 LIMPEZA CONCLUÍDA COM SUCESSO!")
        
        return True

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Limpeza de arquivos antigos do ISP Chat")
    parser.add_argument("--dry-run", action="store_true", help="Simular limpeza sem remover arquivos")
    parser.add_argument("--execute", action="store_true", help="Executar limpeza real")
    parser.add_argument("--no-interactive", action="store_true", help="Não pedir confirmação")
    
    args = parser.parse_args()
    
    cleaner = SystemCleaner()
    
    try:
        if args.execute:
            success = cleaner.run_cleanup(dry_run=False, interactive=not args.no_interactive)
        else:
            success = cleaner.run_cleanup(dry_run=True, interactive=False)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Limpeza interrompida pelo usuário")
        return 1
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NA LIMPEZA: {e}")
        return 2

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)