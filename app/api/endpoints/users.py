"""
Endpoints de usuários
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_users():
    """Listar usuários"""
    return {"users": []}