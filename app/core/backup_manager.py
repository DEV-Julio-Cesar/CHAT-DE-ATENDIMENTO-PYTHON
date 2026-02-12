"""
Gerenciador de Backup Automático
Suporta backup de banco de dados MariaDB/MySQL com retenção configurável
"""
import os
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)


class BackupManager:
    """
    Gerenciador de backups automáticos
    
    Funcionalidades:
    - Backup completo do banco de dados
    - Compressão gzip
    - Retenção configurável (padrão: 30 dias)
    - Upload para S3 (opcional)
    - Limpeza automática de backups antigos
    """
    
    def __init__(
        self,
        backup_dir: str = "backups",
        retention_days: int = 30,
        compress: bool = True
    ):
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.compress = compress
        
        # Criar diretório de backup se não existir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "BackupManager initialized",
            backup_dir=str(self.backup_dir),
            retention_days=retention_days
        )
    
    def create_backup(self, backup_name: Optional[str] = None) -> Optional[Path]:
        """
        Criar backup do banco de dados
        
        Args:
            backup_name: Nome customizado do backup (opcional)
            
        Returns:
            Path do arquivo de backup criado ou None se falhar
        """
        try:
            # Gerar nome do backup
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"
            
            # Path do arquivo SQL
            sql_file = self.backup_dir / f"{backup_name}.sql"
            
            # Extrair credenciais do DATABASE_URL
            db_config = self._parse_database_url()
            
            if not db_config:
                logger.error("Failed to parse DATABASE_URL")
                return None
            
            # Comando mysqldump
            cmd = [
                "mysqldump",
                f"--host={db_config['host']}",
                f"--port={db_config['port']}",
                f"--user={db_config['user']}",
                f"--password={db_config['password']}",
                "--single-transaction",  # Consistência sem lock
                "--quick",  # Não carregar tudo na memória
                "--lock-tables=false",  # Não bloquear tabelas
                db_config['database']
            ]
            
            logger.info(f"Creating backup: {sql_file}")
            
            # Executar mysqldump
            with open(sql_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600  # 1 hora timeout
                )
            
            if result.returncode != 0:
                logger.error(f"mysqldump failed: {result.stderr}")
                sql_file.unlink(missing_ok=True)
                return None
            
            # Comprimir se habilitado
            if self.compress:
                compressed_file = self._compress_backup(sql_file)
                if compressed_file:
                    sql_file.unlink()  # Remover arquivo não comprimido
                    logger.info(f"Backup created and compressed: {compressed_file}")
                    return compressed_file
            
            logger.info(f"Backup created: {sql_file}")
            return sql_file
            
        except subprocess.TimeoutExpired:
            logger.error("Backup timeout (> 1 hour)")
            return None
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    def _compress_backup(self, sql_file: Path) -> Optional[Path]:
        """Comprimir backup com gzip"""
        try:
            gz_file = sql_file.with_suffix('.sql.gz')
            
            with open(sql_file, 'rb') as f_in:
                with gzip.open(gz_file, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Verificar tamanho
            original_size = sql_file.stat().st_size
            compressed_size = gz_file.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(
                f"Backup compressed",
                original_size=f"{original_size / 1024 / 1024:.2f} MB",
                compressed_size=f"{compressed_size / 1024 / 1024:.2f} MB",
                ratio=f"{ratio:.1f}%"
            )
            
            return gz_file
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return None
    
    def restore_backup(self, backup_file: Path) -> bool:
        """
        Restaurar backup
        
        Args:
            backup_file: Path do arquivo de backup (.sql ou .sql.gz)
            
        Returns:
            True se restaurado com sucesso
        """
        try:
            # Descomprimir se necessário
            if backup_file.suffix == '.gz':
                sql_file = self._decompress_backup(backup_file)
                if not sql_file:
                    return False
                temp_file = True
            else:
                sql_file = backup_file
                temp_file = False
            
            # Extrair credenciais
            db_config = self._parse_database_url()
            
            if not db_config:
                logger.error("Failed to parse DATABASE_URL")
                return False
            
            # Comando mysql
            cmd = [
                "mysql",
                f"--host={db_config['host']}",
                f"--port={db_config['port']}",
                f"--user={db_config['user']}",
                f"--password={db_config['password']}",
                db_config['database']
            ]
            
            logger.info(f"Restoring backup: {backup_file}")
            
            # Executar mysql
            with open(sql_file, 'r') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600
                )
            
            # Limpar arquivo temporário
            if temp_file:
                sql_file.unlink(missing_ok=True)
            
            if result.returncode != 0:
                logger.error(f"Restore failed: {result.stderr}")
                return False
            
            logger.info(f"Backup restored successfully: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def _decompress_backup(self, gz_file: Path) -> Optional[Path]:
        """Descomprimir backup gzip"""
        try:
            sql_file = gz_file.with_suffix('')
            
            with gzip.open(gz_file, 'rb') as f_in:
                with open(sql_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            return sql_file
            
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return None
    
    def cleanup_old_backups(self) -> int:
        """
        Remover backups antigos baseado em retenção
        
        Returns:
            Número de backups removidos
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            removed_count = 0
            
            for backup_file in self.backup_dir.glob("backup_*.sql*"):
                # Extrair timestamp do nome do arquivo
                try:
                    timestamp_str = backup_file.stem.split('_', 1)[1]
                    if timestamp_str.endswith('.sql'):
                        timestamp_str = timestamp_str[:-4]
                    
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        backup_file.unlink()
                        removed_count += 1
                        logger.info(f"Removed old backup: {backup_file}")
                        
                except (ValueError, IndexError):
                    # Nome de arquivo não segue padrão, pular
                    continue
            
            logger.info(f"Cleanup completed: {removed_count} backups removed")
            return removed_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    def list_backups(self) -> List[dict]:
        """
        Listar todos os backups disponíveis
        
        Returns:
            Lista de dicts com informações dos backups
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("backup_*.sql*")):
            try:
                stat = backup_file.stat()
                
                backups.append({
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "compressed": backup_file.suffix == '.gz'
                })
                
            except Exception as e:
                logger.warning(f"Failed to stat backup {backup_file}: {e}")
                continue
        
        return backups
    
    def upload_to_s3(self, backup_file: Path, bucket: str, prefix: str = "backups") -> bool:
        """
        Upload backup para AWS S3
        
        Requer: boto3
        pip install boto3
        
        Args:
            backup_file: Path do arquivo de backup
            bucket: Nome do bucket S3
            prefix: Prefixo no S3 (pasta)
            
        Returns:
            True se upload bem sucedido
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client('s3')
            
            # Key no S3
            s3_key = f"{prefix}/{backup_file.name}"
            
            logger.info(f"Uploading backup to S3: s3://{bucket}/{s3_key}")
            
            # Upload com progress
            s3_client.upload_file(
                str(backup_file),
                bucket,
                s3_key,
                ExtraArgs={
                    'StorageClass': 'STANDARD_IA',  # Infrequent Access (mais barato)
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            logger.info(f"Backup uploaded to S3 successfully")
            return True
            
        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            return False
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def _parse_database_url(self) -> Optional[dict]:
        """
        Parsear DATABASE_URL para extrair credenciais
        
        Formato: mysql+aiomysql://user:pass@host:port/database
        """
        try:
            from urllib.parse import urlparse, unquote
            
            url = settings.DATABASE_URL
            
            # Remover driver async
            url = url.replace('mysql+aiomysql://', 'mysql://')
            
            parsed = urlparse(url)
            
            return {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 3306,
                'user': unquote(parsed.username) if parsed.username else 'root',
                'password': unquote(parsed.password) if parsed.password else '',
                'database': parsed.path.lstrip('/')
            }
            
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")
            return None


# Instância global
backup_manager = BackupManager(
    backup_dir=os.getenv('BACKUP_DIR', 'backups'),
    retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', '30')),
    compress=True
)


# Função de conveniência
def create_backup(backup_name: Optional[str] = None) -> Optional[Path]:
    """Atalho para criar backup"""
    return backup_manager.create_backup(backup_name)


def restore_backup(backup_file: Path) -> bool:
    """Atalho para restaurar backup"""
    return backup_manager.restore_backup(backup_file)


def cleanup_old_backups() -> int:
    """Atalho para limpar backups antigos"""
    return backup_manager.cleanup_old_backups()
