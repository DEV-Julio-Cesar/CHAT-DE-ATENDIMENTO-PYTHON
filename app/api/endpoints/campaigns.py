"""
Endpoints de campanhas
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_campaigns():
    """Listar campanhas"""
    return {"campaigns": []}