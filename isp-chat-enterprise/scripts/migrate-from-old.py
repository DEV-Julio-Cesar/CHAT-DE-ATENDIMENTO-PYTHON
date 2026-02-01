#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Chat Enterprise - Migração da Estrutura Antiga
Migra dados e configurações do sistema antigo para a nova estrutura enterprise
"""

import os
import json
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class SystemMigrator:
    """Migrador do sistema antigo para enterprise"""
    
    def __init__(self):
        self.old_paths = [
            "isp-chat-python",
            "chat-de-atendimento", 
            "app"
        ]
        self.new_path = "isp-chat-enterprise"
        self.backup_path = f"migration-backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.migration_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log de migração"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
    
    def find_old_system(self) -> str:
        """Encontrar sistema antigo"""
        for path in self.old_paths:
            if os.path.exists(path):
                self.log(f"Sistema antigo encontrado em: {path}")
                return path
        
        self.log("Nenhum sistema antigo encontrado", "WARNING")
        return None
    
    def create_backup(self, old_path: str):
        """Criar backup do sistema antigo"""
        self.log("Criando backup do sistema antigo...")
        
        try:
            shutil.copytree(old_path, self.backup_path)
            self.log(f"Backup criado em: {self.backup_path}")
        except Exception as e:
            self.log(f"Erro ao criar backup: {e}", "ERROR")
            raise
    
    def migrate_database_data(self, old_path: str) -> Dict[str, Any]:
        """Migrar dados do banco SQLite antigo"""
        self.log("Migrando dados do banco de dados...")
        
        # Procurar arquivos de banco SQLite
        sqlite_files = []
        for root, dirs, files in os.walk(old_path):
            for file in files:
                if file.endswith('.db') or file.endswith('.sqlite'):
                    sqlite_files.append(os.path.join(root, file))
        
        if not sqlite_files:
            self.log("Nenhum banco SQLite encontrado", "WARNING")
            return {}
        
        migrated_data = {}
        
        for db_file in sqlite_files:
            self.log(f"Processando banco: {db_file}")
            
            try:
                conn = sqlite3.connect(db_file)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Obter lista de tabelas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                db_data = {}
                
                for table in tables:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    
                    db_data[table] = [dict(row) for row in rows]
                    self.log(f"  - Tabela {table}: {len(rows)} registros")
                
                migrated_data[os.path.basename(db_file)] = db_data
                conn.close()
                
            except Exception as e:
                self.log(f"Erro ao processar {db_file}: {e}", "ERROR")
        
        return migrated_data
    
    def migrate_json_data(self, old_path: str) -> Dict[str, Any]:
        """Migrar dados de arquivos JSON"""
        self.log("Migrando dados de arquivos JSON...")
        
        json_data = {}
        
        # Procurar arquivos JSON
        for root, dirs, files in os.walk(old_path):
            for file in files:
                if file.endswith('.json') and not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        relative_path = os.path.relpath(file_path, old_path)
                        json_data[relative_path] = data
                        
                        self.log(f"  - Arquivo JSON: {relative_path}")
                        
                    except Exception as e:
                        self.log(f"Erro ao processar {file_path}: {e}", "ERROR")
        
        return json_data
    
    def migrate_configuration(self, old_path: str) -> Dict[str, Any]:
        """Migrar configurações"""
        self.log("Migrando configurações...")
        
        config_data = {}
        
        # Procurar arquivos de configuração
        config_files = ['.env', 'config.json', 'settings.py', 'alembic.ini']
        
        for config_file in config_files:
            file_path = os.path.join(old_path, config_file)
            
            if os.path.exists(file_path):
                try:
                    if config_file.endswith('.json'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            config_data[config_file] = json.load(f)
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            config_data[config_file] = f.read()
                    
                    self.log(f"  - Configuração: {config_file}")
                    
                except Exception as e:
                    self.log(f"Erro ao processar {config_file}: {e}", "ERROR")
        
        return config_data
    
    def migrate_static_files(self, old_path: str):
        """Migrar arquivos estáticos (HTML, CSS, JS)"""
        self.log("Migrando arquivos estáticos...")
        
        static_extensions = ['.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']
        
        for root, dirs, files in os.walk(old_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in static_extensions):
                    source_path = os.path.join(root, file)
                    relative_path = os.path.relpath(source_path, old_path)
                    
                    # Determinar destino na nova estrutura
                    if any(web_dir in relative_path for web_dir in ['web', 'static', 'templates', 'public']):
                        dest_path = os.path.join(self.new_path, 'web-interface', file)
                    else:
                        dest_path = os.path.join(self.new_path, 'web-interface', 'assets', file)
                    
                    try:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                        self.log(f"  - Arquivo estático: {relative_path} -> {os.path.relpath(dest_path, self.new_path)}")
                    except Exception as e:
                        self.log(f"Erro ao copiar {relative_path}: {e}", "ERROR")
    
    def generate_migration_sql(self, db_data: Dict[str, Any]) -> str:
        """Gerar SQL para migração dos dados"""
        self.log("Gerando SQL de migração...")
        
        sql_statements = []
        sql_statements.append("-- ISP Chat Enterprise - Migração de Dados")
        sql_statements.append(f"-- Gerado em: {datetime.now().isoformat()}")
        sql_statements.append("")
        
        for db_file, tables in db_data.items():
            sql_statements.append(f"-- Dados de: {db_file}")
            
            for table_name, rows in tables.items():
                if not rows:
                    continue
                
                # Mapear nomes de tabelas antigas para novas
                table_mapping = {
                    'users': 'users',
                    'conversations': 'conversations', 
                    'messages': 'messages',
                    'atendimentos': 'conversations',
                    'mensagens': 'messages',
                    'usuarios': 'users'
                }
                
                new_table = table_mapping.get(table_name, table_name)
                
                sql_statements.append(f"-- Migração da tabela {table_name} -> {new_table}")
                
                for row in rows:
                    columns = list(row.keys())
                    values = []
                    
                    for value in row.values():
                        if value is None:
                            values.append('NULL')
                        elif isinstance(value, str):
                            values.append(f"'{value.replace(\"'\", \"''\")}'")
                        else:
                            values.append(str(value))
                    
                    sql = f"INSERT INTO {new_table} ({', '.join(columns)}) VALUES ({', '.join(values)});"
                    sql_statements.append(sql)
                
                sql_statements.append("")
        
        return '\n'.join(sql_statements)
    
    def create_migration_report(self, db_data: Dict[str, Any], json_data: Dict[str, Any], config_data: Dict[str, Any]):
        """Criar relatório de migração"""
        self.log("Criando relatório de migração...")
        
        report = {
            "migration_timestamp": datetime.now().isoformat(),
            "source_system": "Legacy ISP Chat",
            "target_system": "ISP Chat Enterprise",
            "summary": {
                "databases_migrated": len(db_data),
                "json_files_migrated": len(json_data),
                "config_files_migrated": len(config_data),
                "total_records": sum(
                    sum(len(table_data) for table_data in db.values()) 
                    for db in db_data.values()
                )
            },
            "database_data": {
                db_name: {
                    table_name: len(table_data)
                    for table_name, table_data in db.items()
                }
                for db_name, db in db_data.items()
            },
            "json_files": list(json_data.keys()),
            "config_files": list(config_data.keys()),
            "migration_log": self.migration_log
        }
        
        # Salvar relatório
        report_path = os.path.join(self.new_path, 'migration-report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log(f"Relatório salvo em: {report_path}")
        
        return report
    
    def run_migration(self):
        """Executar migração completa"""
        print("🔄 ISP CHAT ENTERPRISE - MIGRAÇÃO DO SISTEMA ANTIGO")
        print("=" * 60)
        
        # 1. Encontrar sistema antigo
        old_path = self.find_old_system()
        if not old_path:
            print("❌ Nenhum sistema antigo encontrado para migrar")
            return False
        
        # 2. Criar backup
        self.create_backup(old_path)
        
        # 3. Migrar dados do banco
        db_data = self.migrate_database_data(old_path)
        
        # 4. Migrar dados JSON
        json_data = self.migrate_json_data(old_path)
        
        # 5. Migrar configurações
        config_data = self.migrate_configuration(old_path)
        
        # 6. Migrar arquivos estáticos
        self.migrate_static_files(old_path)
        
        # 7. Gerar SQL de migração
        if db_data:
            migration_sql = self.generate_migration_sql(db_data)
            sql_path = os.path.join(self.new_path, 'database', 'migration.sql')
            os.makedirs(os.path.dirname(sql_path), exist_ok=True)
            
            with open(sql_path, 'w', encoding='utf-8') as f:
                f.write(migration_sql)
            
            self.log(f"SQL de migração salvo em: {sql_path}")
        
        # 8. Salvar dados JSON migrados
        if json_data:
            json_path = os.path.join(self.new_path, 'data', 'migrated-data.json')
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Dados JSON salvos em: {json_path}")
        
        # 9. Salvar configurações migradas
        if config_data:
            config_path = os.path.join(self.new_path, 'config', 'migrated-config.json')
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"Configurações salvas em: {config_path}")
        
        # 10. Criar relatório final
        report = self.create_migration_report(db_data, json_data, config_data)
        
        # Resumo final
        print("\n📊 RESUMO DA MIGRAÇÃO")
        print("=" * 40)
        print(f"✅ Bancos de dados: {report['summary']['databases_migrated']}")
        print(f"✅ Arquivos JSON: {report['summary']['json_files_migrated']}")
        print(f"✅ Configurações: {report['summary']['config_files_migrated']}")
        print(f"✅ Total de registros: {report['summary']['total_records']}")
        print(f"💾 Backup criado em: {self.backup_path}")
        print(f"📋 Relatório: {os.path.join(self.new_path, 'migration-report.json')}")
        
        print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📝 PRÓXIMOS PASSOS:")
        print("1. Revisar o arquivo migration.sql")
        print("2. Executar o SQL no banco SQL Server")
        print("3. Verificar configurações migradas")
        print("4. Testar o sistema enterprise")
        print("5. Remover sistema antigo (após validação)")
        
        return True

def main():
    """Função principal"""
    migrator = SystemMigrator()
    
    try:
        success = migrator.run_migration()
        return 0 if success else 1
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NA MIGRAÇÃO: {e}")
        return 2

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)