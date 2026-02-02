"""
Endpoints de usuários com RBAC
SEMANA 1 - Integração de segurança
"""
from fastapi import APIRouter, HTTPException, status, Request, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import logging

from app.core.dependencies import (
    get_current_user, 
    require_admin,
    require_role,
    get_current_active_user
)
from app.core.audit_logger import audit_logger, AuditEventTypes

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/me", response_model=User)
async def get_current_user_info(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Retorna informações do usuário autenticado
    
    Requer: JWT válido
    """
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_ACCESSED,
        user_id=current_user.get("user_id"),
        action="get_profile",
        resource_type="user",
        resource_id=current_user.get("user_id"),
        ip_address=request.client.host if request.client else "unknown",
        status="success"
    )
    
    return {
        "id": current_user.get("user_id"),
        "email": current_user.get("email"),
        "full_name": current_user.get("username"),
        "role": current_user.get("role"),
        "is_active": True,
        "created_at": datetime.utcnow()
    }


@router.get("/", response_model=List[User])
async def list_users(
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """
    Listar todos os usuários (ADMIN ONLY)
    
    Requer: JWT com role=admin
    Auditado: SIM
    """
    
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"Admin {current_user.get('user_id')} listing users from {client_ip}")
    
    # TODO: Buscar do banco de dados
    users = [
        {
            "id": "user-1",
            "email": "admin@example.com",
            "full_name": "Admin User",
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
    ]
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_ACCESSED,
        user_id=current_user.get("user_id"),
        action="list_users",
        resource_type="user",
        ip_address=client_ip,
        status="success",
        details={"count": len(users)}
    )
    
    return users


@router.post("/", response_model=User)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: dict = Depends(require_admin)
):
    """
    Criar novo usuário (ADMIN ONLY)
    
    Requer: JWT com role=admin
    Auditado: SIM
    """
    
    client_ip = request.client.host if request.client else "unknown"
    
    # TODO: Validar se email já existe
    # TODO: Hash de senha
    # TODO: Salvar no BD
    
    new_user = {
        "id": "user-new",
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": "user",
        "is_active": user_data.is_active,
        "created_at": datetime.utcnow()
    }
    
    logger.info(f"Admin {current_user.get('user_id')} created user {user_data.email}")
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_CREATED,
        user_id=current_user.get("user_id"),
        action="create_user",
        resource_type="user",
        resource_id="user-new",
        ip_address=client_ip,
        status="success",
        details={"email": user_data.email}
    )
    
    return new_user


@router.get("/{user_id}", response_model=User)
async def get_user(
    request: Request,
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obter informações de um usuário
    
    Requer: JWT válido
    Segurança: Usuários comuns só podem ver própil perfil
    Auditado: SIM
    """
    
    client_ip = request.client.host if request.client else "unknown"
    
    # Verificar permissão
    if (current_user.get("role") != "admin" and 
        current_user.get("user_id") != user_id):
        logger.warning(
            f"User {current_user.get('user_id')} tried to access user {user_id} from {client_ip}"
        )
        
        await audit_logger.log(
            event_type=AuditEventTypes.SECURITY_ALERT,
            user_id=current_user.get("user_id"),
            action="unauthorized_access_attempt",
            resource_type="user",
            resource_id=user_id,
            ip_address=client_ip,
            status="failed",
            details={"attempted_user_id": user_id}
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this user"
        )
    
    # TODO: Buscar do BD
    user = {
        "id": user_id,
        "email": "user@example.com",
        "full_name": "Example User",
        "role": "user",
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_ACCESSED,
        user_id=current_user.get("user_id"),
        action="get_user",
        resource_type="user",
        resource_id=user_id,
        ip_address=client_ip,
        status="success"
    )
    
    return user


@router.patch("/{user_id}", response_model=User)
async def update_user(
    request: Request,
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Atualizar informações do usuário
    
    Requer: JWT válido
    Segurança: Usuários comuns só podem atualizar próprio perfil
    Auditado: SIM
    """
    
    client_ip = request.client.host if request.client else "unknown"
    
    # Verificar permissão
    if (current_user.get("role") != "admin" and 
        current_user.get("user_id") != user_id):
        
        await audit_logger.log(
            event_type=AuditEventTypes.SECURITY_ALERT,
            user_id=current_user.get("user_id"),
            action="unauthorized_update_attempt",
            resource_type="user",
            resource_id=user_id,
            ip_address=client_ip,
            status="failed"
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this user"
        )
    
    # TODO: Atualizar no BD
    
    logger.info(f"User {current_user.get('user_id')} updated user {user_id}")
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_MODIFIED,
        user_id=current_user.get("user_id"),
        action="update_user",
        resource_type="user",
        resource_id=user_id,
        ip_address=client_ip,
        status="success",
        details=user_data.dict(exclude_unset=True)
    )
    
    return {
        "id": user_id,
        "email": "user@example.com",
        "full_name": user_data.full_name or "User",
        "role": "user",
        "is_active": user_data.is_active if user_data.is_active is not None else True,
        "created_at": datetime.utcnow()
    }


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Deletar usuário (ADMIN ONLY)
    
    Requer: JWT com role=admin
    Auditado: SIM (com detalhes)
    """
    
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"Admin {current_user.get('user_id')} deleted user {user_id}")
    
    # TODO: Deletar do BD
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_DELETED,
        user_id=current_user.get("user_id"),
        action="delete_user",
        resource_type="user",
        resource_id=user_id,
        ip_address=client_ip,
        status="success",
        details={"deleted_user_id": user_id}
    )
    
    return None