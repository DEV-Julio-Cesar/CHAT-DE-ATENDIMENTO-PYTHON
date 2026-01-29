"""
API Endpoints para Migração de Dados
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any
from pydantic import BaseModel
from app.services.data_migration import migration_service
from app.api.endpoints.auth import get_current_user
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/migration", tags=["migration"])


class MigrationRequest(BaseModel):
    dry_run: bool = True
    backup_before: bool = True


@router.post("/start")
async def start_migration(
    migration_request: MigrationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Inicia migração de dados do Node.js para Python
    """
    try:
        # Verificar permissões
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Only administrators can perform data migration"
            )
            
        # Executar migração em background
        if migration_request.dry_run:
            result = await migration_service.migrate_all_data(dry_run=True)
            return {
                "status": "completed",
                "dry_run": True,
                "result": result
            }
        else:
            background_tasks.add_task(
                migration_service.migrate_all_data,
                dry_run=False
            )
            return {
                "status": "started",
                "dry_run": False,
                "message": "Migration started in background. Check status endpoint for progress."
            }
            
    except Exception as e:
        logger.error("Error starting migration", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_migration_status(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtém status da migração
    """
    try:
        return {
            "statistics": migration_service.stats,
            "migration_log": migration_service.migration_log[-10:],  # Últimas 10 entradas
            "source_path_exists": migration_service.source_path.exists(),
            "backup_path": str(migration_service.backup_path)
        }
        
    except Exception as e:
        logger.error("Error getting migration status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_migration(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Valida dados migrados
    """
    try:
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Only administrators can validate migration"
            )
            
        result = await migration_service.validate_migration()
        return result
        
    except Exception as e:
        logger.error("Error validating migration", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))