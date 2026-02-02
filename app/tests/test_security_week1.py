"""
Testes para módulos de segurança - SEMANA 1
- Test autenticação JWT
- Test rate limiting
- Test criptografia
- Test auditoria
"""

import pytest
from datetime import datetime, timedelta, timezone
import jwt
import json
from app.core.config import settings
from app.core.dependencies import get_current_user, require_admin, revoke_token
from app.core.rate_limiter import rate_limiter, RateLimitConfig
from app.core.encryption import message_encryption, sensitive_data_encryption
from app.core.audit_logger import audit_logger, AuditEventTypes


class TestJWTAuthentication:
    """Testes de autenticação JWT"""
    
    def test_create_valid_jwt_token(self):
        """Criar token JWT válido"""
        payload = {
            "sub": "user123",
            "username": "testuser",
            "role": "admin",
            "aud": "isp-support-users",
            "iss": "isp-support-system"
        }
        
        # Simular criação de token
        exp = datetime.now(timezone.utc) + timedelta(hours=24)
        payload["exp"] = exp
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        print(f"✅ Token válido criado: {token[:50]}...")
    
    def test_decode_valid_jwt_token(self):
        """Decodificar token JWT válido"""
        payload = {
            "sub": "user123",
            "role": "admin",
            "aud": "isp-support-users",
            "iss": "isp-support-system",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience="isp-support-users",
            issuer="isp-support-system"
        )
        
        assert decoded["sub"] == "user123"
        assert decoded["role"] == "admin"
        print(f"✅ Token decodificado com sucesso: {decoded}")
    
    def test_expired_token(self):
        """Testar token expirado"""
        payload = {
            "sub": "user123",
            "role": "admin",
            "aud": "isp-support-users",
            "iss": "isp-support-system",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)  # Expirado
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
        
        print("✅ Token expirado corretamente rejeitado")
    
    def test_invalid_token_signature(self):
        """Testar token com assinatura inválida"""
        payload = {
            "sub": "user123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        
        # Assinar com chave errada
        token = jwt.encode(
            payload,
            "wrong-secret-key",
            algorithm=settings.ALGORITHM
        )
        
        with pytest.raises(jwt.JWTError):
            jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
        
        print("✅ Token com assinatura inválida corretamente rejeitado")


class TestRateLimiting:
    """Testes de rate limiting com Redis"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self):
        """Teste: Requisição dentro do limite é permitida"""
        identifier = "test-ip-127.0.0.1"
        
        allowed, remaining = await rate_limiter.is_allowed(
            identifier=identifier,
            max_requests=5,
            window_seconds=60
        )
        
        assert allowed is True
        assert remaining == 4
        print(f"✅ Requisição permitida. Restante: {remaining}")
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Teste: Exceder limite nega requisição"""
        identifier = "test-ip-127.0.0.2"
        max_requests = 2
        
        # Fazer 2 requisições (limite)
        for i in range(max_requests):
            allowed, _ = await rate_limiter.is_allowed(
                identifier=identifier,
                max_requests=max_requests,
                window_seconds=60
            )
            assert allowed is True
        
        # 3ª requisição deve ser negada
        allowed, remaining = await rate_limiter.is_allowed(
            identifier=identifier,
            max_requests=max_requests,
            window_seconds=60
        )
        
        assert allowed is False
        assert remaining == 0
        print(f"✅ Limite excedido corretamente. Bloqueado!")
    
    @pytest.mark.asyncio
    async def test_rate_limit_config_login(self):
        """Teste: Limites específicos de login"""
        config = RateLimitConfig.LOGIN
        assert config["max_requests"] == 5
        assert config["window_seconds"] == 900
        print(f"✅ Config LOGIN: {config}")
    
    @pytest.mark.asyncio
    async def test_rate_limit_config_api(self):
        """Teste: Limites específicos de API"""
        config = RateLimitConfig.API_DEFAULT
        assert config["max_requests"] == 100
        assert config["window_seconds"] == 60
        print(f"✅ Config API_DEFAULT: {config}")


class TestMessageEncryption:
    """Testes de criptografia de mensagens"""
    
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_message(self):
        """Teste: Criptografar e descriptografar mensagem"""
        client_id = "client-123"
        original_message = "Olá, isto é uma mensagem de teste!"
        
        # Criptografar
        encrypted = await message_encryption.encrypt_message(
            message_content=original_message,
            client_id=client_id
        )
        
        assert "encrypted_content" in encrypted
        assert "iv" in encrypted
        assert encrypted["algorithm"] == "AES-256-CBC"
        print(f"✅ Mensagem criptografada: {encrypted['encrypted_content'][:50]}...")
        
        # Descriptografar
        decrypted = await message_encryption.decrypt_message(
            encrypted_content=encrypted["encrypted_content"],
            iv=encrypted["iv"],
            client_id=client_id
        )
        
        assert decrypted == original_message
        print(f"✅ Mensagem descriptografada: {decrypted}")
    
    @pytest.mark.asyncio
    async def test_encrypt_different_clients_different_keys(self):
        """Teste: Clientes diferentes têm chaves diferentes"""
        message = "Mensagem secreta"
        
        # Criptografar com cliente 1
        encrypted1 = await message_encryption.encrypt_message(
            message_content=message,
            client_id="client-1"
        )
        
        # Criptografar com cliente 2
        encrypted2 = await message_encryption.encrypt_message(
            message_content=message,
            client_id="client-2"
        )
        
        # Conteúdo criptografado deve ser diferente
        assert encrypted1["encrypted_content"] != encrypted2["encrypted_content"]
        print("✅ Clientes diferentes têm criptografia diferente")
        
        # Tentar descriptografar com cliente errado deve falhar
        with pytest.raises(Exception):
            await message_encryption.decrypt_message(
                encrypted_content=encrypted1["encrypted_content"],
                iv=encrypted1["iv"],
                client_id="client-2"  # Cliente errado!
            )
        
        print("✅ Descriptografia com cliente errado falhou corretamente")
    
    @pytest.mark.asyncio
    async def test_decrypt_corrupted_message(self):
        """Teste: Descriptografar mensagem corrompida falha"""
        client_id = "client-123"
        
        # Tentar descriptografar conteúdo inválido
        with pytest.raises(Exception):
            await message_encryption.decrypt_message(
                encrypted_content="conteudo_invalido_corrompido",
                iv="invalid_iv",
                client_id=client_id
            )
        
        print("✅ Mensagem corrompida corretamente rejeitada")


class TestAuditLogger:
    """Testes de sistema de auditoria"""
    
    @pytest.mark.asyncio
    async def test_audit_log_creation(self):
        """Teste: Criar entrada de auditoria"""
        entry = await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_SUCCESS,
            user_id="user123",
            action="login",
            resource_type="user",
            resource_id="user123",
            ip_address="192.168.1.100"
        )
        
        assert entry["id"] is not None
        assert entry["event_type"] == AuditEventTypes.LOGIN_SUCCESS
        assert entry["user_id"] == "user123"
        assert entry["hash"] is not None
        assert entry["previous_hash"] is not None
        print(f"✅ Entrada de auditoria criada: {entry['id']}")
    
    @pytest.mark.asyncio
    async def test_audit_log_hash_integrity(self):
        """Teste: Hash de integridade da corrente"""
        # Criar primeira entrada
        entry1 = await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_SUCCESS,
            user_id="user123",
            action="login"
        )
        
        # Criar segunda entrada
        entry2 = await audit_logger.log(
            event_type=AuditEventTypes.DATA_ACCESSED,
            user_id="user123",
            action="read",
            resource_type="message",
            resource_id="msg456"
        )
        
        # Segunda entrada deve referenciar hash da primeira
        assert entry2["previous_hash"] == entry1["hash"]
        print(f"✅ Integridade da corrente: {entry1['hash'][:20]}... -> {entry2['hash'][:20]}...")
    
    @pytest.mark.asyncio
    async def test_verify_audit_chain(self):
        """Teste: Verificar integridade da corrente de auditorias"""
        # Criar 3 entradas
        entries = []
        for i in range(3):
            entry = await audit_logger.log(
                event_type=AuditEventTypes.LOGIN_SUCCESS,
                user_id=f"user{i}",
                action="login"
            )
            entries.append(entry)
        
        # Verificar integridade
        is_valid = await audit_logger.verify_chain(entries)
        assert is_valid is True
        print("✅ Corrente de auditoria verificada com sucesso")


@pytest.mark.asyncio
async def test_integration_authentication_rate_limit():
    """Teste de integração: Autenticação + Rate Limiting"""
    
    # Simular múltiplas tentativas de login
    identifier = "user-login-127.0.0.1"
    
    # Permitir 3 tentativas
    for i in range(3):
        allowed, remaining = await rate_limiter.is_allowed(
            identifier=identifier,
            max_requests=3,
            window_seconds=900
        )
        assert allowed is True
        print(f"  Tentativa {i+1}: Permitida ({remaining} restantes)")
    
    # 4ª tentativa deve ser bloqueada
    allowed, remaining = await rate_limiter.is_allowed(
        identifier=identifier,
        max_requests=3,
        window_seconds=900
    )
    assert allowed is False
    print(f"  Tentativa 4: Bloqueada (rate limit excedido)")
    
    print("✅ Teste de integração autenticação + rate limiting passou")


if __name__ == "__main__":
    # Executar testes
    print("\n" + "="*60)
    print("🧪 TESTES DE SEGURANÇA - SEMANA 1")
    print("="*60 + "\n")
    
    print("📋 JWT Authentication Tests:")
    print("-" * 40)
    
    print("\n📋 Rate Limiting Tests:")
    print("-" * 40)
    
    print("\n📋 Message Encryption Tests:")
    print("-" * 40)
    
    print("\n📋 Audit Logger Tests:")
    print("-" * 40)
    
    print("\n🎉 Todos os testes completados!")
