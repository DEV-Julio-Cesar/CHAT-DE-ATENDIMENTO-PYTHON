"""
Endpoints de campanhas
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/")
async def list_campaigns(current_user: dict = Depends(get_current_user)):
    """Listar campanhas (protegido por autenticação)"""
    return {"campaigns": []}