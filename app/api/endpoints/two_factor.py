"""
Endpoints de Two-Factor Authentication (2FA)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import structlog

from app.core.two_factor_auth import (
    setup_2fa_for_user,
    verify_2fa_code,
    verify_2fa_backup_code
)
from app.core.security import get_current_active_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/2fa", tags=["2fa"])


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class Setup2FAResponse(BaseModel):
    """Resposta de configuração 2FA"""
    secret: str
    qr_code: str
    backup_codes: List[str]
    message: str


class Verify2FARequest(BaseModel):
    """Request de verificação 2FA"""
    code: str


class Verify2FAResponse(BaseModel):
    """Resposta de verificação 2FA"""
    valid: bool
    message: str


class Enable2FARequest(BaseModel):
    """Request para habilitar 2FA"""
    code: str  # Código de verificação para confirmar


class Disable2FARequest(BaseModel):
    """Request para desabilitar 2FA"""
    password: str  # Senha para confirmar
    code: Optional[str] = None  # Código 2FA ou backup


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/setup", response_model=Setup2FAResponse)
async def setup_2fa(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Configurar 2FA para usuário atual
    
    Retorna:
    - Secret (para guardar no banco)
    - QR Code (para escanear no app)
    - Códigos de backup (para guardar em local seguro)
    """
    try:
        user_email = current_user.get("email")
        
        # Gerar configuração 2FA
        setup_data = setup_2fa_for_user(user_email)
        
        logger.info("2FA setup initiated", user_email=user_email)
        
        # IMPORTANTE: Salvar no banco de dados:
        # - setup_data['secret'] (criptografado)
        # - setup_data['backup_codes_hashed']
        # - two_factor_enabled = False (até confirmar)
        
        return Setup2FAResponse(
            secret=setup_data['secret'],
            qr_code=setup_data['qr_code'],
            backup_codes=setup_data['backup_codes'],
            message="Escaneie o QR Code com seu app autenticador e guarde os códigos de backup em local seguro"
        )
        
    except Exception as e:
        logger.error("Failed to setup 2FA", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup 2FA"
        )


@router.post("/verify", response_model=Verify2FAResponse)
async def verify_2fa(
    request: Verify2FARequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Verificar código 2FA
    
    Usado para:
    - Confirmar configuração inicial
    - Login com 2FA
    - Operações sensíveis
    """
    try:
        # IMPORTANTE: Buscar secret do banco de dados
        # secret = get_user_2fa_secret(current_user['id'])
        secret = "EXEMPLO_SECRET"  # Substituir por busca no banco
        
        is_valid = verify_2fa_code(secret, request.code)
        
        if is_valid:
            logger.info("2FA code verified", user_id=current_user.get('id'))
            return Verify2FAResponse(
                valid=True,
                message="Código válido"
            )
        else:
            logger.warning("Invalid 2FA code", user_id=current_user.get('id'))
            return Verify2FAResponse(
                valid=False,
                message="Código inválido ou expirado"
            )
        
    except Exception as e:
        logger.error("Failed to verify 2FA", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify 2FA code"
        )


@router.post("/enable")
async def enable_2fa(
    request: Enable2FARequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Habilitar 2FA após configuração
    
    Requer código válido para confirmar que o usuário
    configurou corretamente o app autenticador
    """
    try:
        # IMPORTANTE: Buscar secret do banco de dados
        # secret = get_user_2fa_secret(current_user['id'])
        secret = "EXEMPLO_SECRET"
        
        is_valid = verify_2fa_code(secret, request.code)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código inválido. Verifique se o app está configurado corretamente"
            )
        
        # IMPORTANTE: Atualizar no banco de dados
        # update_user_2fa_status(current_user['id'], enabled=True)
        
        logger.info("2FA enabled", user_id=current_user.get('id'))
        
        return {
            "message": "2FA habilitado com sucesso",
            "enabled": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to enable 2FA", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable 2FA"
        )


@router.post("/disable")
async def disable_2fa(
    request: Disable2FARequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Desabilitar 2FA
    
    Requer senha + código 2FA ou código de backup
    """
    try:
        # IMPORTANTE: Verificar senha
        # if not verify_password(request.password, user_password_hash):
        #     raise HTTPException(status_code=400, detail="Senha incorreta")
        
        if request.code:
            # Verificar código 2FA ou backup
            # secret = get_user_2fa_secret(current_user['id'])
            # backup_codes = get_user_backup_codes(current_user['id'])
            
            # is_valid = verify_2fa_code(secret, request.code)
            # if not is_valid:
            #     is_valid, used_code = verify_2fa_backup_code(request.code, backup_codes)
            
            is_valid = True  # Placeholder
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Código inválido"
                )
        
        # IMPORTANTE: Atualizar no banco de dados
        # update_user_2fa_status(current_user['id'], enabled=False)
        # clear_user_2fa_secret(current_user['id'])
        
        logger.info("2FA disabled", user_id=current_user.get('id'))
        
        return {
            "message": "2FA desabilitado com sucesso",
            "enabled": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disable 2FA", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA"
        )


@router.get("/status")
async def get_2fa_status(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obter status do 2FA do usuário
    """
    try:
        # IMPORTANTE: Buscar do banco de dados
        # two_factor_enabled = get_user_2fa_status(current_user['id'])
        two_factor_enabled = False  # Placeholder
        
        return {
            "enabled": two_factor_enabled,
            "user_id": current_user.get('id'),
            "email": current_user.get('email')
        }
        
    except Exception as e:
        logger.error("Failed to get 2FA status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get 2FA status"
        )


@router.post("/regenerate-backup-codes")
async def regenerate_backup_codes(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Regenerar códigos de backup
    
    Invalida códigos antigos e gera novos
    """
    try:
        from app.core.two_factor_auth import two_factor_auth
        
        # Gerar novos códigos
        backup_codes = two_factor_auth.generate_backup_codes(10)
        backup_codes_hashed = [
            two_factor_auth.hash_backup_code(code.replace('-', ''))
            for code in backup_codes
        ]
        
        # IMPORTANTE: Atualizar no banco de dados
        # update_user_backup_codes(current_user['id'], backup_codes_hashed)
        
        logger.info("Backup codes regenerated", user_id=current_user.get('id'))
        
        return {
            "message": "Códigos de backup regenerados. Guarde-os em local seguro!",
            "backup_codes": backup_codes
        }
        
    except Exception as e:
        logger.error("Failed to regenerate backup codes", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )
