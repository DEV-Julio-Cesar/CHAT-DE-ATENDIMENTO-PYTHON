"""
Endpoints de migração
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/migration/status")
async def get_migration_status():
    """Status da migração"""
    return {"status": "ready"}