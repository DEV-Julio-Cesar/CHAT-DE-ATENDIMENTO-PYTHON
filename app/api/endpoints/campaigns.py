"""
Endpoints de campanhas
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.api.endpoints.auth import get_current_user

router = APIRouter()

@router.get("/")
async def list_campaigns(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Lista todas as campanhas"""
    # Implementação básica para demonstração
    return [
        {
            "id": "camp_001",
            "name": "Campanha Exemplo",
            "status": "ativa",
            "created_at": "2024-01-22T10:00:00Z"
        }
    ]

@router.post("/")
async def create_campaign(campaign_data: Dict[str, Any], current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Cria uma nova campanha"""
    return {
        "id": "camp_new",
        "name": campaign_data.get("name", "Nova Campanha"),
        "status": "criada",
        "message": "Campanha criada com sucesso"
    }