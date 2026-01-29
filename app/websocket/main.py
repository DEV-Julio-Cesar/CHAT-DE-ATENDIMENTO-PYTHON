"""
WebSocket simplificado
"""
from fastapi import APIRouter

websocket_router = APIRouter()


@websocket_router.get("/ws/status")
async def websocket_status():
    """Status do WebSocket"""
    return {"status": "ready"}