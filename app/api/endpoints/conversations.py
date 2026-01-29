"""
Endpoints de conversas
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_conversations():
    """Listar conversas"""
    return {"conversations": []}