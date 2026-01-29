"""
Testes do sistema de segurança
"""
import pytest
import asyncio
from datetime import datetime, timedelta
import jwt

from app.core.security_simple import SecurityManager
from app.core.config import settings


class TestSecurityManager:
    """Testes do gerenciador de segurança"""
    
    @pytest.fixture
    def security_manager(self):
        """Fixture do gerenciador de segurança"""
        return SecurityManager()
    
    @pytest.mark.asyncio
    async def test_password_hashing(self, security_manager):
        """Testar hash de senha"""
        password = "test_password_123"
        hashed = await security_manager.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hash é longo
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    @pytest.mark.asyncio
    async def test_password_verification(self, security_manager):
        """Testar verificação de senha"""
        password = "test_password_123"
        hashed = await security_manager.hash_password(password)
        
        # Senha correta
        assert await security_manager.verify_password(password, hashed) is True
        
        # Senha incorreta
        assert await security_manager.verify_password("wrong_password", hashed) is False
    
    @pytest.mark.asyncio
    async def test_secure_token_generation(self, security_manager):
        """Testar geração de token seguro"""
        token1 = await security_manager.generate_secure_token()
        token2 = await security_manager.generate_secure_token()
        
        assert len(token1) > 30
        assert len(token2) > 30
        assert token1 != token2  # Tokens devem ser únicos
    
    @pytest.mark.asyncio
    async def test_jwt_token_creation(self, security_manager):
        """Testar criação de JWT token"""
        user_data = {
            "sub": "user_123",
            "username": "test_user",
            "role": "admin"
        }
        
        token = await security_manager.create_jwt_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens são longos
        
        # Verificar se pode ser decodificado
        decoded = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False, "verify_iss": False}
        )
        
        assert decoded["sub"] == "user_123"
        assert decoded["username"] == "test_user"
        assert decoded["role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_data_encryption(self, security_manager):
        """Testar criptografia de dados"""
        original_data = "sensitive_information_123"
        
        # Criptografar
        encrypted = await security_manager.encrypt_sensitive_data(original_data)
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)
        
        # Descriptografar
        decrypted = await security_manager.decrypt_sensitive_data(encrypted)
        assert decrypted == original_data
    
    @pytest.mark.asyncio
    async def test_password_strength_weak(self, security_manager):
        """Testar senhas fracas"""
        weak_passwords = [
            "123",
            "password",
            "abc"
        ]
        
        for password in weak_passwords:
            strength = await security_manager.check_password_strength(password)
            assert strength["score"] < 3  # Deve ser fraca ou média
    
    @pytest.mark.asyncio
    async def test_password_strength_strong(self, security_manager):
        """Testar senhas fortes"""
        strong_password = "MyStr0ng!P@ssw0rd"
        strength = await security_manager.check_password_strength(strong_password)
        assert strength["score"] >= 4  # Deve ser forte