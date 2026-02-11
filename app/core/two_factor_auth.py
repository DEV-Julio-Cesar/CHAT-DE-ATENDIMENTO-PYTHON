"""
Two-Factor Authentication (2FA)
Implementação de TOTP (Time-based One-Time Password)
"""
import pyotp
import qrcode
import io
import base64
from typing import Tuple, Optional
from datetime import datetime, timedelta
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class TwoFactorAuth:
    """
    Gerenciador de autenticação de dois fatores
    
    Usa TOTP (Time-based One-Time Password) compatível com:
    - Google Authenticator
    - Microsoft Authenticator
    - Authy
    - 1Password
    - LastPass Authenticator
    """
    
    def __init__(self):
        self.issuer_name = settings.APP_NAME
        self.interval = 30  # Código válido por 30 segundos
        self.digits = 6  # Código de 6 dígitos
    
    def generate_secret(self) -> str:
        """
        Gerar secret aleatório para novo usuário
        
        Returns:
            Secret em base32
        """
        return pyotp.random_base32()
    
    def get_totp_uri(self, secret: str, user_email: str) -> str:
        """
        Gerar URI para QR Code
        
        Args:
            secret: Secret do usuário
            user_email: Email do usuário
        
        Returns:
            URI otpauth://
        """
        totp = pyotp.TOTP(secret, interval=self.interval, digits=self.digits)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
    
    def generate_qr_code(self, secret: str, user_email: str) -> str:
        """
        Gerar QR Code em base64
        
        Args:
            secret: Secret do usuário
            user_email: Email do usuário
        
        Returns:
            QR Code em base64 (data URI)
        """
        try:
            # Gerar URI
            uri = self.get_totp_uri(secret, user_email)
            
            # Criar QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            
            # Gerar imagem
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Converter para base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error("Failed to generate QR code", error=str(e))
            return ""
    
    def verify_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Verificar código TOTP
        
        Args:
            secret: Secret do usuário
            code: Código fornecido pelo usuário
            window: Janela de tolerância (1 = ±30s)
        
        Returns:
            True se código válido
        """
        try:
            totp = pyotp.TOTP(secret, interval=self.interval, digits=self.digits)
            return totp.verify(code, valid_window=window)
        except Exception as e:
            logger.error("Failed to verify TOTP code", error=str(e))
            return False
    
    def get_current_code(self, secret: str) -> str:
        """
        Obter código atual (para testes)
        
        Args:
            secret: Secret do usuário
        
        Returns:
            Código atual
        """
        totp = pyotp.TOTP(secret, interval=self.interval, digits=self.digits)
        return totp.now()
    
    def generate_backup_codes(self, count: int = 10) -> list:
        """
        Gerar códigos de backup
        
        Args:
            count: Quantidade de códigos
        
        Returns:
            Lista de códigos de backup
        """
        import secrets
        codes = []
        
        for _ in range(count):
            # Gerar código de 8 caracteres
            code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
            # Formatar: XXXX-XXXX
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        
        return codes
    
    def hash_backup_code(self, code: str) -> str:
        """
        Fazer hash de código de backup para armazenamento
        
        Args:
            code: Código de backup
        
        Returns:
            Hash SHA-256
        """
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()
    
    def verify_backup_code(self, code: str, hashed_codes: list) -> Tuple[bool, Optional[str]]:
        """
        Verificar código de backup
        
        Args:
            code: Código fornecido
            hashed_codes: Lista de hashes de códigos válidos
        
        Returns:
            (válido, hash_usado)
        """
        code_hash = self.hash_backup_code(code.upper().replace('-', ''))
        
        if code_hash in hashed_codes:
            return True, code_hash
        
        return False, None


# Instância global
two_factor_auth = TwoFactorAuth()


# Funções de conveniência
def setup_2fa_for_user(user_email: str) -> dict:
    """
    Configurar 2FA para usuário
    
    Args:
        user_email: Email do usuário
    
    Returns:
        {
            'secret': str,
            'qr_code': str (base64),
            'backup_codes': list,
            'backup_codes_hashed': list
        }
    """
    # Gerar secret
    secret = two_factor_auth.generate_secret()
    
    # Gerar QR Code
    qr_code = two_factor_auth.generate_qr_code(secret, user_email)
    
    # Gerar códigos de backup
    backup_codes = two_factor_auth.generate_backup_codes(10)
    backup_codes_hashed = [
        two_factor_auth.hash_backup_code(code.replace('-', ''))
        for code in backup_codes
    ]
    
    return {
        'secret': secret,
        'qr_code': qr_code,
        'backup_codes': backup_codes,
        'backup_codes_hashed': backup_codes_hashed
    }


def verify_2fa_code(secret: str, code: str) -> bool:
    """
    Verificar código 2FA
    
    Args:
        secret: Secret do usuário
        code: Código fornecido
    
    Returns:
        True se válido
    """
    return two_factor_auth.verify_code(secret, code)


def verify_2fa_backup_code(code: str, hashed_codes: list) -> Tuple[bool, Optional[str]]:
    """
    Verificar código de backup
    
    Args:
        code: Código fornecido
        hashed_codes: Lista de hashes válidos
    
    Returns:
        (válido, hash_usado)
    """
    return two_factor_auth.verify_backup_code(code, hashed_codes)
