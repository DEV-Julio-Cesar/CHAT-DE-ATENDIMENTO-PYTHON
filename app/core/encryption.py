"""
Criptografia de mensagens em repouso
- AES-256-CBC para conteúdo
- PBKDF2 para derivação de chave per-cliente
- IV aleatório por mensagem
"""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from app.core.config import settings
from typing import Dict
import os
import base64
import json
import logging

logger = logging.getLogger(__name__)


class MessageEncryption:
    """
    Criptografia de mensagens em repouso com AES-256-CBC
    
    Fluxo:
    1. Gerar IV aleatório (16 bytes)
    2. Derivar chave específica do cliente via PBKDF2
    3. Criptografar com AES-256-CBC
    4. Armazenar IV junto com conteúdo criptografado
    
    Fluxo de decriptografia:
    1. Derivar mesma chave do cliente
    2. Usar IV armazenado
    3. Descriptografar com AES-256-CBC
    4. Remover padding PKCS7
    """
    
    def __init__(self):
        self.backend = default_backend()
        self.key_iteration_count = 100_000  # PBKDF2 iterations
        self.algorithm = "AES-256-CBC"
    
    def _derive_key(self, client_id: str) -> bytes:
        """
        Derivar chave criptográfica específica por cliente
        
        Usa:
        - Master key (do settings)
        - Client ID como salt único
        - 100k iterações PBKDF2
        - SHA-256 como função hash
        
        Args:
            client_id: ID único do cliente
        
        Returns:
            32 bytes (256 bits) para AES-256
        """
        try:
            # Validar master key
            if not settings.MASTER_ENCRYPTION_KEY:
                raise ValueError("MASTER_ENCRYPTION_KEY não configurada")
            
            # Salt = "salt_" + client_id (específico por cliente)
            salt = f"salt_{client_id}".encode("utf-8")
            
            # PBKDF2 com SHA-256
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits
                salt=salt,
                iterations=self.key_iteration_count,
                backend=self.backend
            )
            
            key = kdf.derive(
                settings.MASTER_ENCRYPTION_KEY.encode("utf-8")
            )
            
            logger.debug(f"Chave derivada para cliente {client_id}")
            return key
            
        except Exception as e:
            logger.error(f"Erro ao derivar chave: {str(e)}")
            raise
    
    async def encrypt_message(
        self,
        message_content: str,
        client_id: str
    ) -> Dict[str, str]:
        """
        Criptografar mensagem antes de salvar no BD
        
        Args:
            message_content: Texto da mensagem
            client_id: ID do cliente (para derivar chave)
        
        Returns:
            {
                "encrypted_content": base64 do conteúdo criptografado,
                "iv": base64 do IV,
                "algorithm": "AES-256-CBC"
            }
        """
        try:
            # 1. Gerar IV aleatório (16 bytes para AES)
            iv = os.urandom(16)
            
            # 2. Derivar chave específica do cliente
            key = self._derive_key(client_id)
            
            # 3. Preparar cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            # 4. Adicionar padding PKCS7
            padder = padding.PKCS7(128).padder()
            message_bytes = message_content.encode("utf-8")
            padded_data = padder.update(message_bytes) + padder.finalize()
            
            # 5. Encriptar
            encrypted_content = encryptor.update(padded_data) + encryptor.finalize()
            
            # 6. Retornar resultado em base64
            result = {
                "encrypted_content": base64.b64encode(encrypted_content).decode("utf-8"),
                "iv": base64.b64encode(iv).decode("utf-8"),
                "algorithm": self.algorithm
            }
            
            logger.debug(f"Mensagem criptografada para cliente {client_id}")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao criptografar mensagem: {str(e)}")
            raise
    
    async def decrypt_message(
        self,
        encrypted_content: str,
        iv: str,
        client_id: str
    ) -> str:
        """
        Descriptografar mensagem ao recuperar do BD
        
        Args:
            encrypted_content: Base64 do conteúdo criptografado
            iv: Base64 do IV
            client_id: ID do cliente (para derivar chave)
        
        Returns:
            Texto original da mensagem
        """
        try:
            # 1. Derivar chave (mesma do cliente)
            key = self._derive_key(client_id)
            
            # 2. Decodificar base64
            encrypted_bytes = base64.b64decode(encrypted_content)
            iv_bytes = base64.b64decode(iv)
            
            # 3. Preparar cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv_bytes),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            
            # 4. Descriptografar
            padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
            
            # 5. Remover padding PKCS7
            unpadder = padding.PKCS7(128).unpadder()
            original_data = unpadder.update(padded_data) + unpadder.finalize()
            
            # 6. Retornar texto
            message = original_data.decode("utf-8")
            
            logger.debug(f"Mensagem descriptografada para cliente {client_id}")
            return message
            
        except ValueError as e:
            logger.error(f"Erro ao descriptografar (padding inválido): {str(e)}")
            raise ValueError("Falha ao descriptografar: conteúdo corrompido")
        except Exception as e:
            logger.error(f"Erro ao descriptografar mensagem: {str(e)}")
            raise


class SensitiveDataEncryption:
    """
    Criptografia genérica de dados sensíveis
    
    Diferente de MessageEncryption:
    - Não usa chave per-cliente
    - Usa master key diretamente
    - Para dados confidenciais do sistema
    """
    
    def __init__(self):
        self.backend = default_backend()
        self.algorithm = "AES-256-CBC"
    
    async def encrypt(self, data: str) -> str:
        """Criptografar dados genéricos"""
        try:
            iv = os.urandom(16)
            key = settings.MASTER_ENCRYPTION_KEY.encode("utf-8")
            
            # Garantir que a chave tem 32 bytes
            from hashlib import sha256
            key = sha256(key).digest()
            
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data.encode()) + padder.finalize()
            
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
            result = f"{base64.b64encode(iv).decode()}:{base64.b64encode(encrypted).decode()}"
            return result
            
        except Exception as e:
            logger.error(f"Erro ao criptografar dados: {str(e)}")
            raise
    
    async def decrypt(self, encrypted_data: str) -> str:
        """Descriptografar dados genéricos"""
        try:
            parts = encrypted_data.split(":")
            if len(parts) != 2:
                raise ValueError("Formato inválido")
            
            iv = base64.b64decode(parts[0])
            encrypted_bytes = base64.b64decode(parts[1])
            
            key = settings.MASTER_ENCRYPTION_KEY.encode("utf-8")
            from hashlib import sha256
            key = sha256(key).digest()
            
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            
            padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
            
            unpadder = padding.PKCS7(128).unpadder()
            original = unpadder.update(padded_data) + unpadder.finalize()
            
            return original.decode()
            
        except Exception as e:
            logger.error(f"Erro ao descriptografar dados: {str(e)}")
            raise


# Instâncias globais
message_encryption = MessageEncryption()
sensitive_data_encryption = SensitiveDataEncryption()
