"""
Endpoints funcionais do dashboard
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard/metrics")
async def get_metrics():
    """Obter métricas do dashboard"""
    return {"metrics": {}}