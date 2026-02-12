"""
Endpoints de Backup
Gerenciamento de backups do banco de dados
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
from pathlib import Path
from pydantic import BaseModel
from app.core.backup_manager import backup_manager
from app.core.dependencies import require_admin
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/backup", tags=["backup"])


class BackupInfo(BaseModel):
    """Informações de um backup"""
    name: str
    path: str
    size: int
    size_mb: float
    created: str
    compressed: bool


class BackupCreateResponse(BaseModel):
    """Resposta de criação de backup"""
    success: bool
    backup_file: str
    message: str


class BackupRestoreRequest(BaseModel):
    """Request de restauração de backup"""
    backup_name: str


class BackupCleanupResponse(BaseModel):
    """Resposta de limpeza de backups"""
    removed_count: int
    message: str


@router.post("/create", response_model=BackupCreateResponse)
async def create_backup_endpoint(
    background_tasks: BackgroundTasks,
    backup_name: str = None,
    user = Depends(require_admin)
):
    """
    Criar backup do banco de dados
    
    Requer permissão de admin.
    Backup é criado em background.
    """
    try:
        # Criar backup em background
        def create_backup_task():
            backup_file = backup_manager.create_backup(backup_name)
            if backup_file:
                logger.info(f"Backup created by user {user.get('sub')}: {backup_file}")
            else:
                logger.error(f"Backup creation failed for user {user.get('sub')}")
        
        background_tasks.add_task(create_backup_task)
        
        return BackupCreateResponse(
            success=True,
            backup_file="Creating in background...",
            message="Backup creation started in background"
        )
        
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[BackupInfo])
async def list_backups_endpoint(user = Depends(require_admin)):
    """
    Listar todos os backups disponíveis
    
    Requer permissão de admin.
    """
    try:
        backups = backup_manager.list_backups()
        return [BackupInfo(**backup) for backup in backups]
        
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore")
async def restore_backup_endpoint(
    request: BackupRestoreRequest,
    user = Depends(require_admin)
):
    """
    Restaurar backup do banco de dados
    
    ⚠️ ATENÇÃO: Esta operação irá sobrescrever o banco de dados atual!
    
    Requer permissão de admin.
    """
    try:
        backup_file = backup_manager.backup_dir / request.backup_name
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="Backup not found")
        
        success = backup_manager.restore_backup(backup_file)
        
        if success:
            logger.info(f"Backup restored by user {user.get('sub')}: {backup_file}")
            return {"success": True, "message": "Backup restored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Restore failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", response_model=BackupCleanupResponse)
async def cleanup_backups_endpoint(user = Depends(require_admin)):
    """
    Remover backups antigos baseado em retenção configurada
    
    Requer permissão de admin.
    """
    try:
        removed_count = backup_manager.cleanup_old_backups()
        
        logger.info(f"Backup cleanup by user {user.get('sub')}: {removed_count} removed")
        
        return BackupCleanupResponse(
            removed_count=removed_count,
            message=f"Removed {removed_count} old backups"
        )
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-s3")
async def upload_backup_to_s3_endpoint(
    backup_name: str,
    bucket: str,
    prefix: str = "backups",
    user = Depends(require_admin)
):
    """
    Upload backup para AWS S3
    
    Requer permissão de admin e boto3 instalado.
    """
    try:
        backup_file = backup_manager.backup_dir / backup_name
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="Backup not found")
        
        success = backup_manager.upload_to_s3(backup_file, bucket, prefix)
        
        if success:
            logger.info(f"Backup uploaded to S3 by user {user.get('sub')}: {backup_file}")
            return {"success": True, "message": f"Backup uploaded to s3://{bucket}/{prefix}/{backup_name}"}
        else:
            raise HTTPException(status_code=500, detail="S3 upload failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
