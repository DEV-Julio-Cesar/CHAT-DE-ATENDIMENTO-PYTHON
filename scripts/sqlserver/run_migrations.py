"""
SQL Server Migration Runner
Executa scripts de migração SQL Server em ordem

Execute: python scripts/sqlserver/run_migrations.py
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import pyodbc
except ImportError:
    print("[ERRO] pyodbc não instalado. Execute: pip install pyodbc")
    sys.exit(1)

from app.core.config import settings


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

MIGRATIONS_DIR = Path(__file__).parent
LOG_FILE = MIGRATIONS_DIR / "migration_log.txt"


def get_connection_string(database: str = None) -> str:
    """Construir string de conexão"""
    trust_cert = "Yes" if settings.SQLSERVER_TRUST_CERT else "No"
    db = database or "master"
    
    return (
        f"DRIVER={{{settings.SQLSERVER_DRIVER}}};"
        f"SERVER={settings.SQLSERVER_HOST},{settings.SQLSERVER_PORT};"
        f"DATABASE={db};"
        f"UID={settings.SQLSERVER_USER};"
        f"PWD={settings.SQLSERVER_PASSWORD};"
        f"TrustServerCertificate={trust_cert};"
    )


def log_message(message: str, level: str = "INFO"):
    """Log para console e arquivo"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def test_connection() -> bool:
    """Testar conexão com SQL Server"""
    log_message(f"Testando conexão com SQL Server: {settings.SQLSERVER_HOST}:{settings.SQLSERVER_PORT}")
    
    try:
        conn = pyodbc.connect(get_connection_string(), timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        log_message(f"Conectado: {version.split(chr(10))[0]}")
        conn.close()
        return True
    except pyodbc.Error as e:
        log_message(f"Falha na conexão: {e}", "ERROR")
        return False


def get_migration_files() -> list:
    """Listar arquivos de migração em ordem"""
    migrations = []
    
    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        migrations.append(file)
    
    return migrations


def execute_migration(conn, migration_file: Path, dry_run: bool = False) -> bool:
    """Executar um arquivo de migração"""
    log_message(f"{'[DRY RUN] ' if dry_run else ''}Executando: {migration_file.name}")
    
    try:
        # Ler conteúdo do arquivo
        with open(migration_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
        
        if dry_run:
            log_message(f"  Arquivo tem {len(sql_content)} caracteres")
            log_message(f"  Contém {sql_content.count('CREATE TABLE')} CREATE TABLE")
            log_message(f"  Contém {sql_content.count('CREATE OR ALTER PROCEDURE')} procedures")
            return True
        
        # Dividir por GO (delimitador de batch do SQL Server)
        batches = sql_content.split("\nGO\n")
        batches = [b.strip() for b in batches if b.strip() and not b.strip().startswith("--")]
        
        cursor = conn.cursor()
        
        for i, batch in enumerate(batches, 1):
            if batch and not batch.isspace():
                try:
                    cursor.execute(batch)
                    conn.commit()
                except pyodbc.Error as e:
                    # Alguns erros são esperados (ex: "já existe")
                    error_msg = str(e)
                    if "already exists" in error_msg.lower() or "já existe" in error_msg.lower():
                        log_message(f"  Batch {i}: Objeto já existe (ignorando)", "WARN")
                    else:
                        log_message(f"  Batch {i} falhou: {error_msg}", "ERROR")
                        # Continuar com próximo batch em vez de abortar
        
        log_message(f"  ✓ {migration_file.name} executado com sucesso")
        return True
        
    except Exception as e:
        log_message(f"  ✗ Erro ao executar {migration_file.name}: {e}", "ERROR")
        return False


def create_migrations_table(conn):
    """Criar tabela para controle de migrações"""
    cursor = conn.cursor()
    
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='__migrations' AND xtype='U')
        CREATE TABLE __migrations (
            id INT IDENTITY(1,1) PRIMARY KEY,
            migration_name NVARCHAR(255) NOT NULL UNIQUE,
            executed_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            checksum NVARCHAR(64) NULL,
            success BIT NOT NULL DEFAULT 1
        )
    """)
    conn.commit()


def is_migration_executed(conn, migration_name: str) -> bool:
    """Verificar se migração já foi executada"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM __migrations WHERE migration_name = ? AND success = 1",
        (migration_name,)
    )
    return cursor.fetchone() is not None


def record_migration(conn, migration_name: str, success: bool, checksum: str = None):
    """Registrar execução de migração"""
    cursor = conn.cursor()
    
    cursor.execute("""
        MERGE __migrations AS target
        USING (SELECT ? AS migration_name) AS source
        ON target.migration_name = source.migration_name
        WHEN MATCHED THEN
            UPDATE SET executed_at = GETDATE(), success = ?, checksum = ?
        WHEN NOT MATCHED THEN
            INSERT (migration_name, success, checksum) VALUES (?, ?, ?)
    """, (migration_name, success, checksum, migration_name, success, checksum))
    conn.commit()


def calculate_checksum(file_path: Path) -> str:
    """Calcular checksum do arquivo"""
    import hashlib
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def run_migrations(
    target: str = None,
    dry_run: bool = False,
    force: bool = False,
    skip_check: bool = False
):
    """Executar migrações"""
    log_message("=" * 60)
    log_message("SQL SERVER MIGRATION RUNNER")
    log_message("=" * 60)
    
    # Testar conexão
    if not test_connection():
        return False
    
    # Obter arquivos de migração
    migrations = get_migration_files()
    
    if not migrations:
        log_message("Nenhum arquivo de migração encontrado", "WARN")
        return True
    
    log_message(f"\nEncontrados {len(migrations)} arquivos de migração:")
    for m in migrations:
        log_message(f"  - {m.name}")
    
    # Filtrar por target se especificado
    if target:
        migrations = [m for m in migrations if target in m.name]
        log_message(f"\nFiltrado para: {len(migrations)} migrações")
    
    # Conectar ao banco
    try:
        # Primeiro, garantir que o banco existe (executar 001 no master)
        first_migration = migrations[0] if migrations else None
        if first_migration and "001" in first_migration.name:
            log_message("\nExecutando criação do banco de dados...")
            conn = pyodbc.connect(get_connection_string("master"), autocommit=True)
            execute_migration(conn, first_migration, dry_run)
            conn.close()
            migrations = migrations[1:]  # Remover da lista
        
        # Conectar ao banco específico
        conn = pyodbc.connect(get_connection_string(settings.SQLSERVER_DATABASE))
        
        # Criar tabela de controle
        if not dry_run:
            create_migrations_table(conn)
        
        # Executar migrações
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for migration in migrations:
            checksum = calculate_checksum(migration)
            
            # Verificar se já executada
            if not skip_check and not force and is_migration_executed(conn, migration.name):
                log_message(f"\n⏭ Pulando {migration.name} (já executada)")
                skip_count += 1
                continue
            
            log_message(f"\n{'='*40}")
            success = execute_migration(conn, migration, dry_run)
            
            if not dry_run:
                record_migration(conn, migration.name, success, checksum)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                if not force:
                    log_message("Abortando devido a erro (use --force para continuar)", "ERROR")
                    break
        
        conn.close()
        
        # Resumo
        log_message(f"\n{'='*60}")
        log_message("RESUMO DA EXECUÇÃO")
        log_message(f"{'='*60}")
        log_message(f"  Sucesso:  {success_count}")
        log_message(f"  Puladas:  {skip_count}")
        log_message(f"  Falhas:   {fail_count}")
        log_message(f"{'='*60}")
        
        return fail_count == 0
        
    except pyodbc.Error as e:
        log_message(f"Erro de conexão: {e}", "ERROR")
        return False


def rollback_migration(migration_name: str):
    """Reverter uma migração (se houver script de rollback)"""
    rollback_file = MIGRATIONS_DIR / f"{migration_name.replace('.sql', '')}_rollback.sql"
    
    if not rollback_file.exists():
        log_message(f"Arquivo de rollback não encontrado: {rollback_file}", "ERROR")
        return False
    
    log_message(f"Executando rollback: {rollback_file.name}")
    
    try:
        conn = pyodbc.connect(get_connection_string(settings.SQLSERVER_DATABASE))
        success = execute_migration(conn, rollback_file)
        
        if success:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM __migrations WHERE migration_name = ?",
                (migration_name,)
            )
            conn.commit()
        
        conn.close()
        return success
        
    except pyodbc.Error as e:
        log_message(f"Erro no rollback: {e}", "ERROR")
        return False


def show_status():
    """Mostrar status das migrações"""
    log_message("=" * 60)
    log_message("STATUS DAS MIGRAÇÕES")
    log_message("=" * 60)
    
    if not test_connection():
        return
    
    migrations = get_migration_files()
    
    try:
        conn = pyodbc.connect(get_connection_string(settings.SQLSERVER_DATABASE))
        create_migrations_table(conn)
        
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name, executed_at, success FROM __migrations ORDER BY executed_at")
        executed = {row.migration_name: (row.executed_at, row.success) for row in cursor.fetchall()}
        
        log_message(f"\n{'Migração':<40} {'Status':<15} {'Executada em'}")
        log_message("-" * 80)
        
        for migration in migrations:
            if migration.name in executed:
                exec_time, success = executed[migration.name]
                status = "✓ Executada" if success else "✗ Falhou"
                log_message(f"{migration.name:<40} {status:<15} {exec_time}")
            else:
                log_message(f"{migration.name:<40} {'⏳ Pendente':<15}")
        
        conn.close()
        
    except pyodbc.Error as e:
        log_message(f"Erro ao verificar status: {e}", "ERROR")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SQL Server Migration Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run_migrations.py                    # Executar todas as migrações pendentes
  python run_migrations.py --dry-run          # Simular execução
  python run_migrations.py --target 002       # Executar apenas migração 002
  python run_migrations.py --status           # Mostrar status das migrações
  python run_migrations.py --force            # Forçar re-execução
  python run_migrations.py --rollback 002     # Reverter migração 002
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular execução sem aplicar mudanças"
    )
    
    parser.add_argument(
        "--target",
        type=str,
        help="Executar apenas migração específica (ex: 002)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forçar re-execução de migrações já executadas"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Mostrar status das migrações"
    )
    
    parser.add_argument(
        "--rollback",
        type=str,
        help="Reverter migração específica"
    )
    
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Pular verificação de migrações já executadas"
    )
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.rollback:
        success = rollback_migration(args.rollback)
        sys.exit(0 if success else 1)
    else:
        success = run_migrations(
            target=args.target,
            dry_run=args.dry_run,
            force=args.force,
            skip_check=args.skip_check
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
