"""
Testes para SQL Server Manager
Sistema de Chat de Atendimento - Telecomunicações
"""

import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestSQLServerManagerUnit:
    """Testes unitários (sem conexão real)"""
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_connection_string_format(self, mock_pyodbc):
        """Testa formato da string de conexão"""
        from app.core.sqlserver_db import SQLServerManager
        
        manager = SQLServerManager()
        # SQLServerManager tem _connection_string privado
        assert hasattr(manager, '_connection_string')
        conn_str = manager._connection_string
        assert "DRIVER=" in conn_str
        assert "SERVER=" in conn_str
        assert "DATABASE=" in conn_str
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_hash_password(self, mock_pyodbc):
        """Testa hash de senha"""
        from app.core.sqlserver_db import SQLServerManager
        
        manager = SQLServerManager()
        password = "TestPassword123!"
        
        hashed = manager.hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_verify_password_correct(self, mock_pyodbc):
        """Testa verificação de senha correta"""
        from app.core.sqlserver_db import SQLServerManager
        
        manager = SQLServerManager()
        password = "TestPassword123!"
        hashed = manager.hash_password(password)
        
        assert manager.verify_password(password, hashed) is True
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_verify_password_wrong(self, mock_pyodbc):
        """Testa verificação de senha incorreta"""
        from app.core.sqlserver_db import SQLServerManager
        
        manager = SQLServerManager()
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = manager.hash_password(password)
        
        assert manager.verify_password(wrong_password, hashed) is False
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_verify_password_empty(self, mock_pyodbc):
        """Testa verificação com senha vazia"""
        from app.core.sqlserver_db import SQLServerManager
        
        manager = SQLServerManager()
        password = "TestPassword123!"
        hashed = manager.hash_password(password)
        
        assert manager.verify_password("", hashed) is False
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_is_token_blacklisted_no_connection(self, mock_pyodbc):
        """Testa blacklist sem conexão"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_pyodbc.connect.side_effect = Exception("Connection failed")
        
        manager = SQLServerManager()
        result = manager.is_token_blacklisted("some_token")
        
        assert result is False  # Deve retornar False em caso de erro


class TestSQLServerManagerWithMock:
    """Testes com mock de conexão"""
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_get_user_by_email_found(self, mock_pyodbc):
        """Testa busca de usuário existente"""
        from app.core.sqlserver_db import SQLServerManager
        
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock row result
        mock_row = Mock()
        mock_row.id = 1
        mock_row.email = "test@email.com"
        mock_row.nome = "Test User"
        mock_row.password_hash = "$2b$12$hashedpassword"
        mock_row.role = "atendente"
        mock_row.is_active = True
        mock_row.two_factor_enabled = False
        mock_row.failed_login_attempts = 0
        mock_row.locked_until = None
        mock_cursor.fetchone.return_value = mock_row
        
        manager = SQLServerManager()
        result = manager.get_user_by_email("test@email.com")
        
        assert result is not None
        assert result["id"] == 1
        assert result["email"] == "test@email.com"
        assert result["nome"] == "Test User"
        assert result["role"] == "atendente"
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_get_user_by_email_not_found(self, mock_pyodbc):
        """Testa busca de usuário inexistente"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        manager = SQLServerManager()
        result = manager.get_user_by_email("nonexistent@email.com")
        
        assert result is None
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_create_user_success(self, mock_pyodbc):
        """Testa criação de usuário"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock para verificar se email já existe
        mock_cursor.fetchone.side_effect = [None, Mock(id=1)]  # Não existe, depois retorna ID
        
        manager = SQLServerManager()
        result = manager.create_user(
            email="new@email.com",
            password="SecurePass123!",
            nome="New User",
            role="user"
        )
        
        assert result is not None
        assert result == 1
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_create_user_duplicate_email(self, mock_pyodbc):
        """Testa criação de usuário com email duplicado"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Email já existe
        mock_cursor.fetchone.return_value = Mock(id=1)
        
        manager = SQLServerManager()
        result = manager.create_user(
            email="existing@email.com",
            password="SecurePass123!",
            nome="Duplicate User"
        )
        
        assert result is None
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_create_session_success(self, mock_pyodbc):
        """Testa criação de sessão"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        manager = SQLServerManager()
        result = manager.create_session(
            user_id=1,
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        assert result is not None
        assert len(result) == 43  # Base64 URL safe token length
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_validate_session_valid(self, mock_pyodbc):
        """Testa validação de sessão válida"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_row = Mock()
        mock_row.user_id = 1
        mock_row.email = "test@email.com"
        mock_row.nome = "Test User"
        mock_row.role = "atendente"
        mock_row.expires_at = datetime.now() + timedelta(hours=1)
        mock_cursor.fetchone.return_value = mock_row
        
        manager = SQLServerManager()
        result = manager.validate_session("valid_session_id")
        
        assert result is not None
        assert result["user_id"] == 1
        assert result["email"] == "test@email.com"
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_validate_session_expired(self, mock_pyodbc):
        """Testa validação de sessão expirada"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Query não retorna sessão expirada
        
        manager = SQLServerManager()
        result = manager.validate_session("expired_session_id")
        
        assert result is None
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_revoke_session(self, mock_pyodbc):
        """Testa revogação de sessão"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        manager = SQLServerManager()
        result = manager.revoke_session("session_to_revoke", "user_logout")
        
        assert result is True
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_log_audit(self, mock_pyodbc):
        """Testa registro de log de auditoria"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Sem hash anterior
        
        manager = SQLServerManager()
        result = manager.log_audit(
            event_type="auth",
            action="login_success",
            user_id=1,
            ip_address="192.168.1.100",
            status="success",
            details={"method": "password"}
        )
        
        assert result is True
    
    @patch('app.core.sqlserver_db.pyodbc')
    def test_save_consent(self, mock_pyodbc):
        """Testa salvamento de consentimento LGPD"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        manager = SQLServerManager()
        result = manager.save_consent(
            user_id=1,
            consent_type="data_processing",
            granted=True,
            ip_address="192.168.1.100",
            consent_text="Aceito o processamento dos meus dados..."
        )
        
        assert result is True


class TestSQLServerManagerAsync:
    """Testes para métodos assíncronos"""
    
    @pytest.mark.asyncio
    @patch('app.core.sqlserver_db.pyodbc')
    async def test_health_check_success(self, mock_pyodbc):
        """Testa health check com sucesso"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)
        
        manager = SQLServerManager()
        result = await manager.health_check()
        
        assert result["status"] == "healthy"
        assert result["database"] == manager.database
    
    @pytest.mark.asyncio
    @patch('app.core.sqlserver_db.pyodbc')
    async def test_health_check_failure(self, mock_pyodbc):
        """Testa health check com falha"""
        from app.core.sqlserver_db import SQLServerManager
        
        mock_pyodbc.connect.side_effect = Exception("Connection refused")
        
        manager = SQLServerManager()
        result = await manager.health_check()
        
        assert result["status"] == "unhealthy"
        assert "error" in result


# ===========================================================================
# Testes de Integração (requerem SQL Server real)
# ===========================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true"
)
class TestSQLServerManagerIntegration:
    """Testes de integração com SQL Server real"""
    
    @pytest.fixture
    def manager(self):
        from app.core.sqlserver_db import SQLServerManager
        return SQLServerManager()
    
    def test_real_connection(self, manager):
        """Testa conexão real"""
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_create_and_get_user(self, manager):
        """Testa criação e busca de usuário"""
        import uuid
        
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "TestPassword123!"
        
        # Criar usuário
        user_id = manager.create_user(
            email=test_email,
            password=test_password,
            nome="Integration Test User",
            role="user"
        )
        assert user_id is not None
        
        # Buscar usuário
        user = manager.get_user_by_email(test_email)
        assert user is not None
        assert user["email"] == test_email
        
        # Verificar senha
        assert manager.verify_password(test_password, user["password_hash"]) is True
        
        # Cleanup
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
            conn.commit()
    
    def test_session_lifecycle(self, manager):
        """Testa ciclo de vida completo de sessão"""
        import uuid
        
        test_email = f"session_test_{uuid.uuid4().hex[:8]}@test.com"
        
        # Criar usuário de teste
        user_id = manager.create_user(
            email=test_email,
            password="TestPass123!",
            nome="Session Test User"
        )
        
        try:
            # Criar sessão
            session_id = manager.create_session(
                user_id=user_id,
                access_token="test_token_123",
                ip_address="127.0.0.1",
                user_agent="pytest"
            )
            assert session_id is not None
            
            # Validar sessão
            session = manager.validate_session(session_id)
            assert session is not None
            assert session["user_id"] == user_id
            
            # Revogar sessão
            revoked = manager.revoke_session(session_id, "test_logout")
            assert revoked is True
            
            # Sessão não deve mais ser válida
            invalid_session = manager.validate_session(session_id)
            assert invalid_session is None
            
        finally:
            # Cleanup
            with manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
                conn.commit()
    
    def test_audit_logging(self, manager):
        """Testa sistema de auditoria"""
        # Registrar log
        logged = manager.log_audit(
            event_type="test",
            action="integration_test",
            ip_address="127.0.0.1",
            status="success",
            details={"test": True}
        )
        assert logged is True
        
        # Buscar logs
        logs = manager.get_audit_logs(event_type="test", limit=1)
        assert len(logs) >= 1
        assert logs[0]["event_type"] == "test"
        
        # Cleanup
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_logs WHERE event_type = 'test'")
            conn.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
