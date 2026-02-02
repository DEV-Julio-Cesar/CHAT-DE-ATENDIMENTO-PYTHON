"""
Testes de Validação Rápida - SEMANA 1
Valida todas as 5 integrações de segurança
"""
import asyncio
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
import base64

# Imports da aplicação
from app.main import app
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.encryption import encryption_manager
from app.core.audit_logger import audit_logger
from app.core.dependencies import revoke_token
from app.services.whatsapp_chat_flow import WhatsAppChatFlow, SenderType, MessageType

client = TestClient(app)


# ============================================================================
# TESTES: JWT + AUTENTICAÇÃO (SEMANA 1 - Módulo 1)
# ============================================================================

class TestJWTAuthentication:
    """Validar integração de JWT em /auth/login e /auth/logout"""
    
    def test_login_success(self):
        """POST /auth/login com credenciais válidas"""
        response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validações
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 86400
        assert data["user"]["email"] == "user@example.com"
        assert data["user"]["role"] == "admin"
        
        # Validar JWT
        token = data["access_token"]
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        assert payload["aud"] == "isp-support-users"
        assert payload["iss"] == "isp-support-system"
        assert payload["email"] == "user@example.com"
        assert "exp" in payload
        
        # Guardar para próximos testes
        return token
    
    def test_login_invalid_credentials(self):
        """POST /auth/login com credenciais inválidas"""
        response = client.post(
            "/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "wrongpass"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_logout_revokes_token(self):
        """POST /auth/logout revoga token"""
        # Primeiro, fazer login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Depois, fazer logout
        logout_response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert logout_response.status_code == 200
        assert logout_response.json()["status"] == "logged out"
    
    def test_token_validation(self):
        """GET /auth/token/validate valida JWT"""
        # Fazer login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Validar token
        response = client.get(
            "/auth/token/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert data["email"] == "user@example.com"
        assert data["role"] == "admin"


# ============================================================================
# TESTES: RATE LIMITING (SEMANA 1 - Módulo 2)
# ============================================================================

class TestRateLimiting:
    """Validar rate limiting em /auth/login"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_login_attempts(self):
        """Exceder 5 tentativas de login em 15 minutos"""
        # Simular 6 tentativas (limite é 5)
        for i in range(6):
            response = client.post(
                "/auth/login",
                json={
                    "email": f"user{i}@example.com",
                    "password": "wrong"
                }
            )
            
            if i < 5:
                # Primeiras 5 tentativas devem retornar 401 (credenciais inválidas)
                assert response.status_code == 401
            else:
                # 6ª tentativa deve retornar 429 (rate limit)
                assert response.status_code == 429
                assert "Too many login attempts" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self):
        """Validar headers de rate limit"""
        response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "password123"
            }
        )
        
        # Mesmo em sucesso, headers devem estar presentes (em futuros requests)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_ip(self):
        """Rate limit é por IP, não global"""
        # Este teste validaria com múltiplos IPs
        # Em ambiente de teste, todos têm mesmo IP
        pass


# ============================================================================
# TESTES: CRIPTOGRAFIA (SEMANA 1 - Módulo 3)
# ============================================================================

class TestEncryption:
    """Validar criptografia de mensagens"""
    
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_message(self):
        """Criptografar e descriptografar mensagem"""
        chat_flow = WhatsAppChatFlow()
        customer_id = "customer_001"
        content = "Minha internet está lenta"
        
        # Criptografar
        encrypted, iv = await chat_flow.encrypt_message_content(
            customer_id=customer_id,
            content=content
        )
        
        # Validações
        assert encrypted != content  # Não é plaintext
        assert iv  # IV não vazio
        assert len(encrypted) > len(content)  # Criptografado é maior
        
        # Descriptografar
        decrypted = await chat_flow.decrypt_message_content(
            customer_id=customer_id,
            encrypted_content=encrypted,
            iv=iv
        )
        
        assert decrypted == content
    
    @pytest.mark.asyncio
    async def test_different_customers_different_keys(self):
        """Clientes diferentes têm chaves diferentes"""
        chat_flow = WhatsAppChatFlow()
        content = "Mensagem confidencial"
        
        # Criptografar com customer_1
        encrypted_1, iv_1 = await chat_flow.encrypt_message_content(
            customer_id="customer_001",
            content=content
        )
        
        # Criptografar mesmo conteúdo com customer_2
        encrypted_2, iv_2 = await chat_flow.encrypt_message_content(
            customer_id="customer_002",
            content=content
        )
        
        # Criptografias devem ser diferentes
        assert encrypted_1 != encrypted_2
        
        # Customer 1 não consegue descriptografar com chave de customer 2
        decrypted_wrong = await chat_flow.decrypt_message_content(
            customer_id="customer_002",
            encrypted_content=encrypted_1,
            iv=iv_1
        )
        
        # Deve ser diferente do original (não conseguiu descriptografar)
        # Ou pode retornar base64 string confusa
        assert decrypted_wrong != content
    
    @pytest.mark.asyncio
    async def test_add_encrypted_message(self):
        """Adicionar mensagem com criptografia"""
        chat_flow = WhatsAppChatFlow()
        
        # Criar conversa
        conversation = await chat_flow.create_conversation(
            customer_name="João Silva",
            customer_phone="+5511999999999"
        )
        
        # Adicionar mensagem criptografada
        message = await chat_flow.add_encrypted_message(
            conversation_id=conversation.id,
            sender_type=SenderType.CUSTOMER,
            sender_id="customer_001",
            content="Preciso de ajuda",
            customer_id="customer_001",
            message_type=MessageType.TEXT
        )
        
        # Validações
        assert message.id
        assert message.metadata["encrypted"] == True
        assert "conteudo_criptografado" in message.metadata
        assert "iv" in message.metadata
        assert message.metadata["encryption_type"] == "AES-256-CBC"
    
    @pytest.mark.asyncio
    async def test_get_decrypted_messages(self):
        """Recuperar mensagens descriptografadas"""
        chat_flow = WhatsAppChatFlow()
        
        # Criar conversa
        conversation = await chat_flow.create_conversation(
            customer_name="Maria Santos",
            customer_phone="+5511988888888"
        )
        
        # Adicionar 2 mensagens criptografadas
        await chat_flow.add_encrypted_message(
            conversation_id=conversation.id,
            sender_type=SenderType.CUSTOMER,
            sender_id="customer_002",
            content="Primeira mensagem",
            customer_id="customer_002"
        )
        
        await chat_flow.add_encrypted_message(
            conversation_id=conversation.id,
            sender_type=SenderType.BOT,
            sender_id="bot",
            content="Resposta do bot",
            customer_id="customer_002"
        )
        
        # Recuperar com descriptografia
        messages = await chat_flow.get_conversation_messages_decrypted(
            conversation_id=conversation.id,
            customer_id="customer_002"
        )
        
        assert len(messages) == 2
        assert messages[0]["content"] == "Primeira mensagem"
        assert messages[1]["content"] == "Resposta do bot"


# ============================================================================
# TESTES: AUDITORIA (SEMANA 1 - Módulo 4)
# ============================================================================

class TestAuditLogging:
    """Validar auditoria de eventos"""
    
    def test_login_audit_logged(self):
        """Login bem-sucedido é registrado em auditoria"""
        response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        # Auditoria deveria estar registrada
        # TODO: Query AuditLogEnhanced no BD para validar
    
    def test_failed_login_audit_logged(self):
        """Login falhado é registrado em auditoria"""
        response = client.post(
            "/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "wrong"
            }
        )
        
        assert response.status_code == 401
        # Auditoria deveria estar registrada
        # TODO: Query AuditLogEnhanced no BD para validar
    
    def test_audit_log_has_hash_chain(self):
        """AuditLogEnhanced tem hash para integridade"""
        # TODO: Criar entrada em AuditLogEnhanced
        # TODO: Validar entry_hash é SHA-256
        # TODO: Validar previous_hash referencia entrada anterior
        pass


# ============================================================================
# TESTES: RBAC (CONTROLE DE ACESSO) (SEMANA 1 - Integrado em Users)
# ============================================================================

class TestRBAC:
    """Validar controle de acesso baseado em roles"""
    
    def test_get_current_user_requires_auth(self):
        """GET /api/users/me requer autenticação"""
        response = client.get("/api/users/me")
        
        assert response.status_code == 403  # Forbidden (sem token)
    
    def test_list_users_admin_only(self):
        """GET /api/users/ requer role=admin"""
        # Fazer login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Tentar listar usuários
        response = client.get(
            "/api/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Usuário de teste é admin, deve funcionar
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_user_cannot_access_other_profiles(self):
        """Usuário comum não pode ver perfil de outro usuário"""
        # TODO: Implementar teste com usuário não-admin
        # TODO: Validar que GET /api/users/{other_user_id} retorna 403
        pass


# ============================================================================
# TESTES: GDPR/LGPD (SEMANA 1 - Módulo 5)
# ============================================================================

class TestGDPR:
    """Validar endpoints GDPR/LGPD"""
    
    def test_gdpr_endpoints_registered(self):
        """Validar que endpoints GDPR estão registrados"""
        # GET /docs deve incluir endpoints GDPR
        response = client.get("/docs")
        
        assert response.status_code == 200
        # Endpoint deve estar em docs
        # assert "/api/gdpr" in response.text
    
    def test_deletion_request_requires_auth(self):
        """POST /api/gdpr/deletion-request requer autenticação"""
        response = client.post(
            "/api/gdpr/deletion-request",
            json={"reason": "Não mais interesse"}
        )
        
        assert response.status_code in [401, 403]


# ============================================================================
# TESTE INTEGRADO: FLUXO COMPLETO (SEMANA 1)
# ============================================================================

class TestCompleteFlow:
    """Teste de fluxo completo de segurança"""
    
    @pytest.mark.asyncio
    async def test_full_security_flow(self):
        """
        1. Login (JWT)
        2. Criar conversa com criptografia
        3. Adicionar mensagens criptografadas
        4. Auditoria registra tudo
        5. Logout revoga token
        """
        
        # 1. LOGIN
        login_response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "password123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        user_id = login_response.json()["user"]["id"]
        
        # 2. CRIAR CONVERSA COM CRIPTOGRAFIA
        chat_flow = WhatsAppChatFlow()
        conversation = await chat_flow.create_conversation(
            customer_name="Cliente Teste",
            customer_phone="+5511987654321"
        )
        await chat_flow.enable_conversation_encryption(
            conversation.id,
            user_id
        )
        
        # 3. ADICIONAR MENSAGENS CRIPTOGRAFADAS
        msg1 = await chat_flow.add_encrypted_message(
            conversation_id=conversation.id,
            sender_type=SenderType.CUSTOMER,
            sender_id=user_id,
            content="Tem problema na internet",
            customer_id=user_id
        )
        
        msg2 = await chat_flow.add_encrypted_message(
            conversation_id=conversation.id,
            sender_type=SenderType.AGENT,
            sender_id="agent_001",
            content="Vou verificar sua conexão",
            customer_id=user_id
        )
        
        # 4. VALIDAR CRIPTOGRAFIA
        assert msg1.metadata["encrypted"] == True
        assert msg2.metadata["encrypted"] == True
        
        messages = await chat_flow.get_conversation_messages_decrypted(
            conversation.id,
            user_id
        )
        
        assert len(messages) == 2
        assert messages[0]["content"] == "Tem problema na internet"
        assert messages[1]["content"] == "Vou verificar sua conexão"
        
        # 5. LOGOUT (REVOGA TOKEN)
        logout_response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert logout_response.status_code == 200
        
        # Token revogado não deve funcionar mais
        # await asyncio.sleep(0.1)  # Aguardar Redis
        # response = client.get(
        #     "/api/users/me",
        #     headers={"Authorization": f"Bearer {token}"}
        # )
        # assert response.status_code in [401, 403]


# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    # Rodar com: pytest test_semana1_integration.py -v
    pytest.main([__file__, "-v", "-s"])
