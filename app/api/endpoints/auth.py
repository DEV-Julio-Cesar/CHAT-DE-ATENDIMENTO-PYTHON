"""
Endpoints de autenticação
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    """Login do usuário"""
    return {"access_token": "fake_token", "token_type": "bearer"}


@router.post("/logout")
async def logout():
    """Logout do usuário"""
    return {"message": "Logged out successfully"}