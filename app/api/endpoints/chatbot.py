"""
Endpoints do chatbot
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/chatbot/status")
async def get_chatbot_status():
    """Status do chatbot"""
    return {"status": "active"}