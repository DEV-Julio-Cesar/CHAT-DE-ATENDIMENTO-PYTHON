"""
Criptografia de dados sensíveis em repouso
Usa AES-256-GCM para criptografia simétrica
"""
import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import structlog

logger = structlog.get_logger(__name__)


class EncryptionManager:
    """
    Gerenciador de criptografia para dados sensíveis
    
    Usa AES-256-GCM (Galois/Counter Mode) que fornece:
    - Confidencialidade (dados criptografados)
    - Integridade (detecta modificações)
    - Autenticidade (verifica origem)
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Inicializar gerenciador de criptografia
        
        Args:
            master_key: Chave mestra (deve vir do Secrets Manager)
        """
        if not master_key:
            # Usar chave do ambiente ou gerar temporária
            master_key = os.getenv('MASTER_ENCRYPTION_KEY')
            if not master_key:
                logger.warning("MASTER_ENCRYPTION_KEY não configurada, usando chave temporária")
                master_key = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        self.master_key = master_key.encode() if isinstance(master_key, str) else master_key
    
    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derivar chave de criptografia usando PBKDF2
        
        Args:
            salt: Salt único para derivação
            
        Returns:
            Chave derivada de 32 bytes
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # 100k iterações (seguro)
            backend=default_backend()
        )
        return kdf.derive(self.master_key)
    
    def encrypt(self, plaintext: str, associated_data: Optional[str] = None) -> str:
        """
        Criptografar texto
        
        Args:
            plaintext: Texto a criptografar
            associated_data: Dados associados (não criptografados mas autenticados)
            
        Returns:
            Texto criptografado em base64 (formato: salt:nonce:ciphertext)
        """
        try:
            # Gerar salt e nonce únicos
            salt = os.urandom(16)
            nonce = os.urandom(12)  # 96 bits para GCM
            
            # Derivar chave
            key = self._derive_key(salt)
            
            # Criar cipher AES-GCM
            aesgcm = AESGCM(key)
            
            # Preparar dados associados
            aad = associated_data.encode() if associated_data else b""
            
            # Criptografar
            ciphertext = aesgcm.encrypt(
                nonce,
                plaintext.encode('utf-8'),
                aad
            )
            
            # Combinar salt:nonce:ciphertext e codificar em base64
            encrypted_data = salt + nonce + ciphertext
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_text: str, associated_data: Optional[str] = None) -> str:
        """
        Descriptografar texto
        
        Args:
            encrypted_text: Texto criptografado em base64
            associated_data: Dados associados (devem ser os mesmos da criptografia)
            
        Returns:
            Texto descriptografado
        """
        try:
            # Decodificar base64
            encrypted_data = base64.b64decode(encrypted_text)
            
            # Extrair salt, nonce e ciphertext
            salt = encrypted_data[:16]
            nonce = encrypted_data[16:28]
            ciphertext = encrypted_data[28:]
            
            # Derivar chave
            key = self._derive_key(salt)
            
            # Criar cipher AES-GCM
            aesgcm = AESGCM(key)
            
            # Preparar dados associados
            aad = associated_data.encode() if associated_data else b""
            
            # Descriptografar
            plaintext = aesgcm.decrypt(
                nonce,
                ciphertext,
                aad
            )
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_field(self, value: Optional[str], field_name: str = "") -> Optional[str]:
        """
        Criptografar campo de banco de dados
        
        Args:
            value: Valor a criptografar
            field_name: Nome do campo (usado como associated data)
            
        Returns:
            Valor criptografado ou None
        """
        if value is None or value == "":
            return None
        
        return self.encrypt(value, associated_data=field_name)
    
    def decrypt_field(self, encrypted_value: Optional[str], field_name: str = "") -> Optional[str]:
        """
        Descriptografar campo de banco de dados
        
        Args:
            encrypted_value: Valor criptografado
            field_name: Nome do campo (usado como associated data)
            
        Returns:
            Valor descriptografado ou None
        """
        if encrypted_value is None or encrypted_value == "":
            return None
        
        try:
            return self.decrypt(encrypted_value, associated_data=field_name)
        except Exception as e:
            logger.error(f"Failed to decrypt field '{field_name}': {e}")
            return None


# Instância global
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """
    Obter instância global do EncryptionManager
    
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    
    if _encryption_manager is None:
        from app.core.config import settings
        _encryption_manager = EncryptionManager(settings.MASTER_ENCRYPTION_KEY)
    
    return _encryption_manager


# Funções de conveniência
def encrypt_data(plaintext: str, associated_data: Optional[str] = None) -> str:
    """Atalho para criptografar dados"""
    return get_encryption_manager().encrypt(plaintext, associated_data)


def decrypt_data(encrypted_text: str, associated_data: Optional[str] = None) -> str:
    """Atalho para descriptografar dados"""
    return get_encryption_manager().decrypt(encrypted_text, associated_data)
