"""
Endpoints de otimização
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/optimization/status")
async def get_optimization_status():
    """Status da otimização"""
    return {"status": "active"}