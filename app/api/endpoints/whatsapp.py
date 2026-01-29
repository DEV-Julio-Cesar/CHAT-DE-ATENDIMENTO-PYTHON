"""
Endpoints do WhatsApp
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def whatsapp_status():
    """Status do WhatsApp"""
    return {"status": "connected"}