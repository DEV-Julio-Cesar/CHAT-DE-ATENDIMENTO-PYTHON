"""
Endpoints de autenticação
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.security import security_manager, get_current_user, rate_limit_middleware
from app.core.redis_client import redis_manager, CacheKeys
from app.models.database import Usuario
from app.schemas.auth import Token, UserLogin, UserResponse, RefreshTokenRequest
from app.schemas.base import ResponseModel

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/login", response_model=ResponseModel[Token])
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login do usuário"""
    
    # Rate limiting por IP
    await rate_limit_middleware(request, limit=10, window=300)  # 10 tentativas por 5 min
    
    try:
        # Buscar usuário no banco
        stmt = select(Usuario).where(Usuario.username == form_data.username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        # Verificar credenciais
        if not user or not security_manager.verify_password(form_data.password, user.password_hash):
            logger.warning(
                "Failed login attempt",
                username=form_data.username,
                ip=request.client.host if request.client else None
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar se usuário está ativo
        if not user.ativo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Criar tokens
        access_token_expires = timedelta(minutes=security_manager.access_token_expire_minutes)
        access_token = security_manager.create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role.value},
            expires_delta=access_token_expires
        )
        
        refresh_token = security_manager.create_refresh_token(str(user.id))
        
        # Salvar sessão no cache
        user_data = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "ativo": user.ativo,
            "ultimo_login": user.ultimo_login.isoformat() if user.ultimo_login else None
        }
        
        cache_key = CacheKeys.format_key(CacheKeys.USER_SESSION, user_id=str(user.id))
        await redis_manager.set_json(
            cache_key, 
            user_data, 
            ex=security_manager.access_token_expire_minutes * 60
        )
        
        # Atualizar último login
        from datetime import datetime
        user.ultimo_login = datetime.utcnow()
        await db.commit()
        
        logger.info(
            "User logged in successfully",
            user_id=str(user.id),
            username=user.username,
            ip=request.client.host if request.client else None
        )
        
        return ResponseModel(
            success=True,
            data=Token(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=security_manager.access_token_expire_minutes * 60
            ),
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e), username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/refresh", response_model=ResponseModel[Token])
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Renovar token de acesso"""
    
    try:
        # Verificar refresh token
        payload = security_manager.verify_token(request.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Buscar usuário
        stmt = select(Usuario).where(Usuario.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Criar novo access token
        access_token_expires = timedelta(minutes=security_manager.access_token_expire_minutes)
        access_token = security_manager.create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role.value},
            expires_delta=access_token_expires
        )
        
        # Atualizar cache da sessão
        user_data = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "ativo": user.ativo,
            "ultimo_login": user.ultimo_login.isoformat() if user.ultimo_login else None
        }
        
        cache_key = CacheKeys.format_key(CacheKeys.USER_SESSION, user_id=str(user.id))
        await redis_manager.set_json(
            cache_key, 
            user_data, 
            ex=security_manager.access_token_expire_minutes * 60
        )
        
        logger.info("Token refreshed successfully", user_id=str(user.id))
        
        return ResponseModel(
            success=True,
            data=Token(
                access_token=access_token,
                refresh_token=request.refresh_token,  # Manter o mesmo refresh token
                token_type="bearer",
                expires_in=security_manager.access_token_expire_minutes * 60
            ),
            message="Token refreshed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout", response_model=ResponseModel[dict])
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Logout do usuário"""
    
    try:
        # Obter token do header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            # Revogar token
            await security_manager.revoke_token(token)
        
        # Remover sessão do cache
        cache_key = CacheKeys.format_key(CacheKeys.USER_SESSION, user_id=current_user["id"])
        await redis_manager.delete(cache_key)
        
        logger.info("User logged out successfully", user_id=current_user["id"])
        
        return ResponseModel(
            success=True,
            data={},
            message="Logout successful"
        )
        
    except Exception as e:
        logger.error("Logout error", error=str(e), user_id=current_user.get("id"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=ResponseModel[UserResponse])
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Obter informações do usuário atual"""
    
    try:
        user_response = UserResponse(
            id=current_user["id"],
            username=current_user["username"],
            email=current_user["email"],
            role=current_user["role"],
            ativo=current_user["ativo"],
            ultimo_login=current_user.get("ultimo_login")
        )
        
        return ResponseModel(
            success=True,
            data=user_response,
            message="User information retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Get current user error", error=str(e), user_id=current_user.get("id"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/change-password", response_model=ResponseModel[dict])
async def change_password(
    request: Request,
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Alterar senha do usuário"""
    
    # Rate limiting
    await rate_limit_middleware(request, limit=5, window=300)  # 5 tentativas por 5 min
    
    try:
        # Buscar usuário no banco
        stmt = select(Usuario).where(Usuario.id == current_user["id"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verificar senha atual
        if not security_manager.verify_password(old_password, user.password_hash):
            logger.warning("Failed password change attempt", user_id=current_user["id"])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Validar nova senha
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Atualizar senha
        user.password_hash = security_manager.hash_password(new_password)
        await db.commit()
        
        logger.info("Password changed successfully", user_id=current_user["id"])
        
        return ResponseModel(
            success=True,
            data={},
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Change password error", error=str(e), user_id=current_user.get("id"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )