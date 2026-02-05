"""
Endpoints do WhatsApp
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/status")
async def whatsapp_status(current_user: dict = Depends(get_current_user)):
    """Status do WhatsApp (protegido por autenticação)"""
    return {"status": "connected"}