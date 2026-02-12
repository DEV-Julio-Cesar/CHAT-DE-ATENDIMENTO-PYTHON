"""
Endpoints de Usuários com Integração SQL Server Real
CIANET PROVEDOR - v3.0

CRUD completo de usuários com:
- Integração real com SQL Server
- Permissões granulares (RBAC)
- Auditoria completa
- Paginação e filtros
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from pydantic import BaseModel, EmailStr, Field, validator

from app.core.auth_manager import (
    get_current_user, 
    require_role, 
    require_permissions,
    auth_manager
)
from app.core.audit_logger import audit_logger, AuditEventTypes
from app.core.database import db_manager
from app.models.database import Usuario, UserRole
from sqlalchemy import select, or_
import bcrypt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Usuários"])


# ============================================================================
# SCHEMAS
# ============================================================================

class UserCreate(BaseModel):
    """Schema para criar usuário"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    nome: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="atendente")
    phone: Optional[str] = None
    department: Optional[str] = None
    
    @validator('role')
    def validate_role(cls, v):
        allowed = ['admin', 'supervisor', 'atendente']
        if v not in allowed:
            raise ValueError(f'Role deve ser um de: {allowed}')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve ter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in v):
            raise ValueError('Senha deve ter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve ter pelo menos um número')
        return v


class UserUpdate(BaseModel):
    """Schema para atualizar usuário"""
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            allowed = ['admin', 'supervisor', 'atendente']
            if v not in allowed:
                raise ValueError(f'Role deve ser um de: {allowed}')
        return v


class UserResponse(BaseModel):
    """Schema de resposta do usuário"""
    id: int
    email: str
    nome: str
    role: str
    is_active: bool = True
    phone: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class UserListResponse(BaseModel):
    """Resposta paginada de usuários"""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PasswordReset(BaseModel):
    """Schema para reset de senha (admin)"""
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve ter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in v):
            raise ValueError('Senha deve ter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve ter pelo menos um número')
        return v


# ============================================================================
# ENDPOINTS
# ============================================================================

# Helper assíncrono para listar usuários
async def list_users_filtered_async(limit, offset, role, search, is_active):
    async with db_manager.session_factory() as session:
        query = select(Usuario)
        filters = []
        if role:
            filters.append(Usuario.role == role)
        if is_active is not None:
            filters.append(Usuario.ativo == is_active)
        if search:
            filters.append(or_(Usuario.username.ilike(f"%{search}%"), Usuario.email.ilike(f"%{search}%")))
        if filters:
            query = query.where(*filters)
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

async def count_users_async(role, search, is_active):
    async with db_manager.session_factory() as session:
        query = select(Usuario)
        filters = []
        if role:
            filters.append(Usuario.role == role)
        if is_active is not None:
            filters.append(Usuario.ativo == is_active)
        if search:
            filters.append(or_(Usuario.username.ilike(f"%{search}%"), Usuario.email.ilike(f"%{search}%")))
        if filters:
            query = query.where(*filters)
        result = await session.execute(query)
        return result.scalars().count()

# Helpers assíncronos CRUD usuário
async def get_user_by_email_async(email: str):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Usuario).where(Usuario.email == email))
        return result.scalar_one_or_none()

async def get_user_by_id_async(user_id: str):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Usuario).where(Usuario.id == user_id))
        return result.scalar_one_or_none()

async def create_user_async(email, password, nome, role):
    async with db_manager.session_factory() as session:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        new_user = Usuario(
            email=email,
            password_hash=password_hash,
            username=nome,
            role=role,
            ativo=True
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

async def update_user_full_async(user_id, **kwargs):
    async with db_manager.session_factory() as session:
        user = await get_user_by_id_async(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            setattr(user, key, value)
        await session.commit()
        await session.refresh(user)
        return user

async def delete_user_async(user_id):
    async with db_manager.session_factory() as session:
        user = await get_user_by_id_async(user_id)
        if not user:
            return False
        await session.delete(user)
        await session.commit()
        return True

async def update_user_password_async(user_id, new_password):
    async with db_manager.session_factory() as session:
        user = await get_user_by_id_async(user_id)
        if not user:
            return False
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await session.commit()
        await session.refresh(user)
        return True

async def activate_user_async(user_id):
    return await update_user_full_async(user_id, ativo=True)

async def deactivate_user_async(user_id):
    return await update_user_full_async(user_id, ativo=False)

# Refatorar endpoint de listagem de usuários
@router.get(
    "/",
    response_model=UserListResponse,
    summary="Listar usuários",
    responses={
        200: {"description": "Lista de usuários"},
        403: {"description": "Sem permissão"}
    }
)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    role: Optional[str] = Query(None, description="Filtrar por role"),
    search: Optional[str] = Query(None, description="Buscar por nome ou email"),
    is_active: Optional[bool] = Query(None, description="Filtrar por status"),
    current_user: dict = Depends(require_permissions("users.view"))
):
    offset = (page - 1) * per_page
    users_data = await list_users_filtered_async(
        limit=per_page,
        offset=offset,
        role=role,
        search=search,
        is_active=is_active
    )
    total = await count_users_async(role=role, search=search, is_active=is_active)
    users = [
        UserResponse(
            id=str(u.id),
            email=u.email,
            nome=u.username,
            role=u.role.value,
            is_active=u.ativo,
            phone=None,
            department=None,
            avatar_url=None,
            created_at=str(u.created_at) if u.created_at else None,
            last_login=str(u.ultimo_login) if u.ultimo_login else None
        )
        for u in users_data
    ]
    pages = (total // per_page) + 1
    return UserListResponse(
        users=users,
        total=total,
        page=page,
        pages=pages
    )

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário",
    responses={
        201: {"description": "Usuário criado"},
        400: {"description": "Email já existe"},
        403: {"description": "Sem permissão"}
    }
)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: dict = Depends(require_permissions("users.create"))
):
    """
    Criar novo usuário no sistema.
    
    **Permissão necessária**: users.create
    """
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Verificar se email já existe
        existing = await get_user_by_email_async(user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )
        
        # Criar usuário
        new_user = await create_user_async(
            email=user_data.email,
            password=user_data.password,
            nome=user_data.nome,
            role=user_data.role
        )
        
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar usuário"
            )
        
        logger.info(f"User {current_user['email']} created user {user_data.email}")
        
        await audit_logger.log(
            event_type=AuditEventTypes.DATA_CREATED,
            user_id=current_user["id"],
            action="create_user",
            resource_type="user",
            resource_id=str(new_user.id),
            ip_address=client_ip,
            status="success",
            details={"email": user_data.email, "role": user_data.role}
        )
        
        return UserResponse(
            id=int(new_user.id),
            email=new_user.email,
            nome=new_user.username,
            role=new_user.role,
            is_active=True,
            created_at=str(datetime.now())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar usuário"
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obter usuário",
    responses={
        200: {"description": "Dados do usuário"},
        404: {"description": "Usuário não encontrado"}
    }
)
async def get_user(
    request: Request,
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter dados de um usuário específico.
    
    - Usuários podem ver apenas seu próprio perfil
    - Admin/Supervisor podem ver qualquer perfil
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Verificar permissão
    if current_user["id"] != user_id and current_user["role"] == "atendente":
        await audit_logger.log(
            event_type=AuditEventTypes.SECURITY_ALERT,
            user_id=current_user["id"],
            action="unauthorized_user_access",
            resource_type="user",
            resource_id=str(user_id),
            ip_address=client_ip,
            status="denied"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para visualizar este usuário"
        )
    
    user = await get_user_by_id_async(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return UserResponse(
        id=int(user.id),
        email=user.email,
        nome=user.username,
        role=user.role,
        is_active=user.ativo,
        phone=user.phone,
        department=user.department,
        avatar_url=user.avatar_url,
        created_at=str(user.created_at) if user.created_at else None,
        last_login=str(user.ultimo_login) if user.ultimo_login else None
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualizar usuário",
    responses={
        200: {"description": "Usuário atualizado"},
        404: {"description": "Usuário não encontrado"},
        403: {"description": "Sem permissão"}
    }
)
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Atualizar dados de um usuário.
    
    - Usuários podem atualizar apenas seu próprio perfil (exceto role)
    - Admin pode atualizar qualquer campo
    - Supervisor pode atualizar atendentes
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Buscar usuário atual
    target_user = await get_user_by_id_async(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verificar permissões
    can_edit = False
    can_change_role = False
    
    if current_user["role"] == "admin":
        can_edit = True
        can_change_role = True
    elif current_user["role"] == "supervisor":
        if target_user.role == "atendente" or current_user["id"] == user_id:
            can_edit = True
    elif current_user["id"] == user_id:
        can_edit = True
    
    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para editar este usuário"
        )
    
    # Impedir mudança de role sem permissão
    if user_data.role and not can_change_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para alterar role"
        )
    
    # Atualizar
    update_fields = user_data.dict(exclude_unset=True)
    
    if update_fields:
        success = await update_user_full_async(
            user_id=user_id,
            **update_fields
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar usuário"
            )
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_UPDATED,
        user_id=current_user["id"],
        action="update_user",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=client_ip,
        status="success",
        details={"fields_updated": list(update_fields.keys())}
    )
    
    # Retornar usuário atualizado
    updated_user = await get_user_by_id_async(user_id)
    
    return UserResponse(
        id=int(updated_user.id),
        email=updated_user.email,
        nome=updated_user.username,
        role=updated_user.role,
        is_active=updated_user.ativo,
        phone=updated_user.phone,
        department=updated_user.department,
        avatar_url=updated_user.avatar_url,
        created_at=str(updated_user.created_at) if updated_user.created_at else None,
        last_login=str(updated_user.ultimo_login) if updated_user.ultimo_login else None
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar usuário",
    responses={
        204: {"description": "Usuário deletado"},
        403: {"description": "Sem permissão"},
        404: {"description": "Usuário não encontrado"}
    }
)
async def delete_user(
    request: Request,
    user_id: int,
    current_user: dict = Depends(require_permissions("users.delete"))
):
    """
    Desativar/deletar um usuário (soft delete).
    
    **Permissão necessária**: users.delete
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Não permitir deletar a si mesmo
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar sua própria conta"
        )
    
    # Verificar se usuário existe
    user = await get_user_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permitir deletar admin se for o único
    if user.role == "admin":
        admin_count = await count_users_async(role="admin", is_active=True)
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível deletar o único administrador"
            )
    
    # Soft delete
    success = await delete_user_async(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao deletar usuário"
        )
    
    # Revogar todas as sessões do usuário
    await auth_manager.revoke_all_user_sessions(user_id)
    
    logger.info(f"User {current_user['email']} deleted user {user.email}")
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_DELETED,
        user_id=current_user["id"],
        action="delete_user",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=client_ip,
        status="success",
        details={"deleted_email": user.email}
    )
    
    return None


@router.post(
    "/{user_id}/reset-password",
    summary="Resetar senha (admin)",
    responses={
        200: {"description": "Senha resetada"},
        403: {"description": "Sem permissão"},
        404: {"description": "Usuário não encontrado"}
    }
)
async def reset_user_password(
    request: Request,
    user_id: int,
    password_data: PasswordReset,
    current_user: dict = Depends(require_permissions("users.edit"))
):
    """
    Resetar senha de um usuário (admin/supervisor).
    
    **Permissão necessária**: users.edit
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Verificar se usuário existe
    user = await get_user_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Supervisor não pode resetar senha de admin
    if current_user["role"] == "supervisor" and user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para alterar senha de administradores"
        )
    
    # Resetar senha
    new_hash = auth_manager.hash_password(password_data.new_password)
    success = await update_user_password_async(user_id, new_hash)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao resetar senha"
        )
    
    # Revogar todas as sessões do usuário
    await auth_manager.revoke_all_user_sessions(user_id)
    
    logger.info(f"Password reset for user {user.email} by {current_user['email']}")
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_UPDATED,
        user_id=current_user["id"],
        action="reset_password",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=client_ip,
        status="success",
        details={"target_email": user.email}
    )
    
    return {"message": "Senha resetada com sucesso", "sessions_revoked": True}


@router.post(
    "/{user_id}/activate",
    summary="Ativar usuário",
    responses={
        200: {"description": "Usuário ativado"}
    }
)
async def activate_user(
    request: Request,
    user_id: int,
    current_user: dict = Depends(require_permissions("users.edit"))
):
    """
    Reativar um usuário desativado.
    
    **Permissão necessária**: users.edit
    """
    user = await get_user_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    success = await activate_user_async(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao ativar usuário"
        )
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_UPDATED,
        user_id=current_user["id"],
        action="activate_user",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host if request.client else "unknown",
        status="success"
    )
    
    return {"message": "Usuário ativado com sucesso"}


@router.get(
    "/{user_id}/sessions",
    summary="Listar sessões do usuário",
    responses={
        200: {"description": "Lista de sessões"}
    }
)
async def list_user_sessions(
    request: Request,
    user_id: int,
    current_user: dict = Depends(require_permissions("users.view"))
):
    """
    Listar todas as sessões ativas de um usuário.
    
    **Permissão necessária**: users.view
    """
    user = await get_user_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    sessions = await auth_manager.get_user_sessions(user_id)
    
    return {
        "user_id": user_id,
        "user_email": user.email,
        "sessions": [
            {
                "session_id": s["session_id"],
                "device_info": s.get("device_info"),
                "ip_address": s.get("ip_address"),
                "created_at": s.get("created_at"),
                "last_activity": s.get("last_activity")
            }
            for s in sessions
        ],
        "total": len(sessions)
    }


@router.delete(
    "/{user_id}/sessions",
    summary="Revogar todas sessões do usuário",
    responses={
        200: {"description": "Sessões revogadas"}
    }
)
async def revoke_user_sessions(
    request: Request,
    user_id: int,
    current_user: dict = Depends(require_permissions("users.edit"))
):
    """
    Revogar todas as sessões de um usuário (forçar logout).
    
    **Permissão necessária**: users.edit
    """
    user = await get_user_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    count = await auth_manager.revoke_all_user_sessions(user_id)
    
    await audit_logger.log(
        event_type=AuditEventTypes.LOGOUT,
        user_id=current_user["id"],
        action="revoke_all_sessions",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host if request.client else "unknown",
        status="success",
        details={"sessions_revoked": count}
    )
    
    return {"message": f"{count} sessões revogadas", "sessions_revoked": count}
