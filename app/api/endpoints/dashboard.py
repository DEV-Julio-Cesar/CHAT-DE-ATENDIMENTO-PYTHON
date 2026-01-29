"""
Endpoints do dashboard
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats():
    """Obter estatísticas do dashboard"""
    return {
        "total_conversations": 0,
        "active_users": 0,
        "messages_today": 0
    }