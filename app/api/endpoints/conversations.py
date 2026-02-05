"""
Endpoints de conversas
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """Listar conversas (protegido por autenticação)"""
    return {"conversations": []}