"""
Endpoints de usuários
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.api.endpoints.auth import get_current_user

router = APIRouter()

@router.get("/")
async def list_users(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Lista todos os usuários"""
    # Implementação básica para demonstração
    return [
        {
            "id": "1",
            "username": "admin",
            "email": "admin@sistema.com",
            "role": "admin",
            "active": True
        }
    ]

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Obtém informações do usuário atual"""
    return current_user