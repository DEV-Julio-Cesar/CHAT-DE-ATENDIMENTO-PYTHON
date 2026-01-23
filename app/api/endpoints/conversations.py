"""
Endpoints de conversas
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.api.endpoints.auth import get_current_user

router = APIRouter()

@router.get("/")
async def list_conversations(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Lista todas as conversas"""
    # Implementação básica para demonstração
    return [
        {
            "id": "conv_001",
            "customer_name": "Cliente Exemplo",
            "phone": "+55 11 99999-9999",
            "status": "ativo",
            "created_at": "2024-01-22T10:00:00Z"
        }
    ]

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Obtém detalhes de uma conversa"""
    return {
        "id": conversation_id,
        "customer_name": "Cliente Exemplo",
        "phone": "+55 11 99999-9999",
        "status": "ativo",
        "messages": []
    }