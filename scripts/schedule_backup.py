"""
Script de Agendamento de Backup Automático
Executa backup diário e limpeza de backups antigos
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.backup_manager import backup_manager
import structlog

logger = structlog.get_logger(__name__)


def main():
    """Executar backup e limpeza"""
    logger.info("Starting scheduled backup")
    
    # Criar backup
    backup_file = backup_manager.create_backup()
    
    if backup_file:
        logger.info(f"Backup created successfully: {backup_file}")
        
        # Upload para S3 se configurado
        s3_bucket = os.getenv('AWS_S3_BUCKET')
        if s3_bucket:
            logger.info(f"Uploading backup to S3: {s3_bucket}")
            success = backup_manager.upload_to_s3(backup_file, s3_bucket)
            if success:
                logger.info("Backup uploaded to S3 successfully")
            else:
                logger.warning("Failed to upload backup to S3")
    else:
        logger.error("Backup creation failed")
        sys.exit(1)
    
    # Limpar backups antigos
    logger.info("Cleaning up old backups")
    removed_count = backup_manager.cleanup_old_backups()
    logger.info(f"Cleanup completed: {removed_count} backups removed")
    
    logger.info("Scheduled backup completed successfully")


if __name__ == "__main__":
    main()
