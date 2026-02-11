"""
Gerenciador de Criptografia
Criptografia AES-256-GCM para dados sensíveis
"""
import base64
import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EncryptionManager:
    """
    Gerenciador de criptografia para dados sensíveis
    
    Usa AES-256-GCM (Galois/Counter Mode) que fornece:
    - Confidencialidade (criptografia)
    - Autenticidade (verificação de integridade)
    - Proteção contra replay attacks
    """
    
    def __init__(self):
        self._key = None
        self._initialize_key()
    
    def _initialize_key(self):
        """Inicializar chave de criptografia"""
        try:
            if not settings.MASTER_ENCRYPTION_KEY:
                logger.warning("MASTER_ENCRYPTION_KEY not configured, encryption disabled")
                return
            
            if not settings.ENCRYPTION_SALT:
                logger.warning("ENCRYPTION_SALT not configured, encryption disabled")
                return
            
            # Derivar chave de 256 bits usando PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits
                salt=settings.ENCRYPTION_SALT.encode('utf-8'),
                iterations=100000,  # NIST recomenda 100k+
            )
            
            self._key = kdf.derive(settings.MASTER_ENCRYPTION_KEY.encode('utf-8'))
            logger.info("Encryption manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize encryption", error=str(e))
            self._key = None
    
    def is_enabled(self) -> bool:
        """Verificar se criptografia está habilitada"""
        return self._key is not None
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Criptografar texto
        
        Args:
            plaintext: Texto a criptografar
        
        Returns:
            Texto criptografado em base64 ou None se falhar
        """
        if not self.is_enabled():
            logger.warning("Encryption not enabled, returning plaintext")
            return plaintext
        
        if not plaintext:
            return plaintext
        
        try:
            # Gerar nonce aleatório (96 bits para GCM)
            nonce = os.urandom(12)
            
            # Criar cipher AES-GCM
            aesgcm = AESGCM(self._key)
            
            # Criptografar
            ciphertext = aesgcm.encrypt(
                nonce,
                plaintext.encode('utf-8'),
                None  # Sem dados adicionais autenticados
            )
            
            # Combinar nonce + ciphertext e codificar em base64
            encrypted_data = nonce + ciphertext
            encoded = base64.b64encode(encrypted_data).decode('utf-8')
            
            return encoded
            
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            return None
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Descriptografar texto
        
        Args:
            ciphertext: Texto criptografado em base64
        
        Returns:
            Texto descriptografado ou None se falhar
        """
        if not self.is_enabled():
            logger.warning("Encryption not enabled, returning ciphertext")
            return ciphertext
        
        if not ciphertext:
            return ciphertext
        
        try:
            # Decodificar base64
            encrypted_data = base64.b64decode(ciphertext.encode('utf-8'))
            
            # Separar nonce (primeiros 12 bytes) e ciphertext
            nonce = encrypted_data[:12]
            actual_ciphertext = encrypted_data[12:]
            
            # Criar cipher AES-GCM
            aesgcm = AESGCM(self._key)
            
            # Descriptografar
            plaintext_bytes = aesgcm.decrypt(
                nonce,
                actual_ciphertext,
                None  # Sem dados adicionais autenticados
            )
            
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            return None
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Criptografar campos específicos de um dicionário
        
        Args:
            data: Dicionário com dados
            fields: Lista de campos a criptografar
        
        Returns:
            Dicionário com campos criptografados
        """
        if not self.is_enabled():
            return data
        
        encrypted_data = data.copy()
        
        for field in fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_value = self.encrypt(str(encrypted_data[field]))
                if encrypted_value:
                    encrypted_data[field] = encrypted_value
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Descriptografar campos específicos de um dicionário
        
        Args:
            data: Dicionário com dados criptografados
            fields: Lista de campos a descriptografar
        
        Returns:
            Dicionário com campos descriptografados
        """
        if not self.is_enabled():
            return data
        
        decrypted_data = data.copy()
        
        for field in fields:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_value = self.decrypt(str(decrypted_data[field]))
                if decrypted_value:
                    decrypted_data[field] = decrypted_value
        
        return decrypted_data
    
    def hash_data(self, data: str) -> str:
        """
        Criar hash SHA-256 de dados (para busca)
        
        Args:
            data: Dados a fazer hash
        
        Returns:
            Hash em hexadecimal
        """
        import hashlib
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def rotate_key(self, new_master_key: str, new_salt: str):
        """
        Rotacionar chave de criptografia
        
        IMPORTANTE: Antes de rotacionar, você deve:
        1. Descriptografar todos os dados com a chave antiga
        2. Rotacionar a chave
        3. Re-criptografar todos os dados com a chave nova
        
        Args:
            new_master_key: Nova chave mestra
            new_salt: Novo salt
        """
        logger.warning("Key rotation initiated")
        
        # Salvar chave antiga
        old_key = self._key
        
        try:
            # Derivar nova chave
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=new_salt.encode('utf-8'),
                iterations=100000,
            )
            
            self._key = kdf.derive(new_master_key.encode('utf-8'))
            
            logger.info("Key rotation completed successfully")
            return True
            
        except Exception as e:
            logger.error("Key rotation failed", error=str(e))
            # Restaurar chave antiga
            self._key = old_key
            return False


# Instância global
encryption_manager = EncryptionManager()


# Funções de conveniência
def encrypt_message(message: str) -> Optional[str]:
    """Criptografar mensagem"""
    return encryption_manager.encrypt(message)


def decrypt_message(encrypted_message: str) -> Optional[str]:
    """Descriptografar mensagem"""
    return encryption_manager.decrypt(encrypted_message)


def encrypt_sensitive_data(data: dict, fields: list = None) -> dict:
    """
    Criptografar dados sensíveis
    
    Args:
        data: Dicionário com dados
        fields: Campos a criptografar (padrão: campos sensíveis comuns)
    
    Returns:
        Dicionário com campos criptografados
    """
    if fields is None:
        # Campos sensíveis padrão
        fields = [
            'conteudo',  # Conteúdo de mensagem
            'cpf',
            'rg',
            'telefone',
            'email',
            'endereco',
            'cartao_credito',
            'senha',
            'token',
        ]
    
    return encryption_manager.encrypt_dict(data, fields)


def decrypt_sensitive_data(data: dict, fields: list = None) -> dict:
    """
    Descriptografar dados sensíveis
    
    Args:
        data: Dicionário com dados criptografados
        fields: Campos a descriptografar
    
    Returns:
        Dicionário com campos descriptografados
    """
    if fields is None:
        fields = [
            'conteudo',
            'cpf',
            'rg',
            'telefone',
            'email',
            'endereco',
            'cartao_credito',
            'senha',
            'token',
        ]
    
    return encryption_manager.decrypt_dict(data, fields)
