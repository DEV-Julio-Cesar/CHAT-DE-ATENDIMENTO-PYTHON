"""
Gerenciador de conexão SQL Server para autenticação
SEMANA 1 - Integração com banco de dados real
"""
import pyodbc
import bcrypt
import logging
import hashlib
import secrets
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class SQLServerManager:
    """
    Gerenciador de conexões SQL Server
    Usado para autenticação e gerenciamento de usuários
    """
    
    def __init__(self):
        self._connection_string = self._build_connection_string()
        self._pool_size = 10
    
    def _build_connection_string(self) -> str:
        """Construir string de conexão SQL Server"""
        trust_cert = "Yes" if settings.SQLSERVER_TRUST_CERT else "No"
        
        # Verificar se deve usar Trusted Connection (Windows Auth)
        use_trusted = getattr(settings, 'SQLSERVER_TRUSTED_CONNECTION', False)
        
        if use_trusted:
            # Autenticação Windows
            conn_str = (
                f"DRIVER={{{settings.SQLSERVER_DRIVER}}};"
                f"SERVER={settings.SQLSERVER_HOST};"
                f"DATABASE={settings.SQLSERVER_DATABASE};"
                f"Trusted_Connection=Yes;"
                f"TrustServerCertificate={trust_cert};"
            )
        else:
            # Autenticação SQL Server
            conn_str = (
                f"DRIVER={{{settings.SQLSERVER_DRIVER}}};"
                f"SERVER={settings.SQLSERVER_HOST},{settings.SQLSERVER_PORT};"
                f"DATABASE={settings.SQLSERVER_DATABASE};"
                f"UID={settings.SQLSERVER_USER};"
                f"PWD={settings.SQLSERVER_PASSWORD};"
                f"TrustServerCertificate={trust_cert};"
            )
        return conn_str
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões"""
        conn = None
        try:
            conn = pyodbc.connect(self._connection_string)
            yield conn
        except pyodbc.Error as e:
            logger.error(f"SQL Server connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """Testar conexão com SQL Server"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check assíncrono para monitoramento"""
        try:
            start = datetime.now()
            is_connected = self.test_connection()
            latency = (datetime.now() - start).total_seconds() * 1000
            
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "latency_ms": round(latency, 2),
                "server": settings.SQLSERVER_HOST,
                "database": settings.SQLSERVER_DATABASE
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # =========================================================================
    # OPERAÇÕES DE USUÁRIO
    # =========================================================================
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Buscar usuário por email"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        id, 
                        email, 
                        password_hash, 
                        nome,
                        role,
                        is_active,
                        two_factor_enabled,
                        failed_login_attempts,
                        locked_until,
                        created_at,
                        last_login
                    FROM usuarios 
                    WHERE email = ? AND is_active = 1 AND deleted_at IS NULL
                """, (email,))
                
                row = cursor.fetchone()
                
                if row:
                    return {
                        "id": str(row.id),
                        "email": row.email,
                        "password_hash": row.password_hash,
                        "nome": row.nome,
                        "role": row.role,
                        "is_active": row.is_active,
                        "two_factor_enabled": row.two_factor_enabled,
                        "failed_login_attempts": row.failed_login_attempts,
                        "locked_until": row.locked_until,
                        "created_at": row.created_at,
                        "last_login": row.last_login
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Buscar usuário por ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        id, 
                        email, 
                        nome,
                        role,
                        is_active,
                        created_at,
                        last_login
                    FROM usuarios 
                    WHERE id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return {
                        "id": str(row.id),
                        "email": row.email,
                        "nome": row.nome,
                        "role": row.role,
                        "is_active": row.is_active,
                        "created_at": row.created_at,
                        "last_login": row.last_login
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user by id: {e}")
            return None
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar senha usando bcrypt"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Autenticar usuário por email e senha
        Retorna dados do usuário se autenticação bem-sucedida, None caso contrário
        """
        try:
            user = self.get_user_by_email(email)
            if not user:
                logger.warning(f"Authentication failed: user not found - {email}")
                return None
            
            # Verificar se conta está bloqueada
            if user.get("locked_until"):
                if user["locked_until"] > datetime.now():
                    logger.warning(f"Authentication failed: account locked - {email}")
                    return None
            
            # Verificar senha
            if not self.verify_password(password, user["password_hash"]):
                # Incrementar tentativas falhas
                self._increment_failed_attempts(user["id"])
                logger.warning(f"Authentication failed: invalid password - {email}")
                return None
            
            # Login bem-sucedido - resetar tentativas e atualizar last_login
            self._reset_failed_attempts(user["id"])
            self.update_last_login(user["id"])
            
            # Remover hash da senha do retorno por segurança
            user.pop("password_hash", None)
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def _increment_failed_attempts(self, user_id: str) -> None:
        """Incrementar contador de tentativas falhas"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usuarios 
                    SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1,
                        locked_until = CASE 
                            WHEN COALESCE(failed_login_attempts, 0) >= 4 
                            THEN DATEADD(minute, 15, GETDATE())
                            ELSE locked_until 
                        END
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing failed attempts: {e}")
    
    def _reset_failed_attempts(self, user_id: str) -> None:
        """Resetar contador de tentativas falhas"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usuarios 
                    SET failed_login_attempts = 0, locked_until = NULL
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error resetting failed attempts: {e}")
    
    def hash_password(self, password: str) -> str:
        """Gerar hash bcrypt da senha"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def update_last_login(self, user_id: int) -> bool:
        """Atualizar último login do usuário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usuarios 
                    SET last_login = GETDATE()
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    def create_user(
        self, 
        email: str, 
        password: str, 
        nome: str, 
        role: str = "user"
    ) -> Optional[Dict[str, Any]]:
        """Criar novo usuário"""
        try:
            password_hash = self.hash_password(password)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar se email já existe
                cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
                if cursor.fetchone():
                    logger.warning(f"Email already exists: {email}")
                    return None
                
                # Inserir usuário
                cursor.execute("""
                    INSERT INTO usuarios (email, password_hash, nome, role, is_active, created_at)
                    OUTPUT INSERTED.id
                    VALUES (?, ?, ?, ?, 1, GETDATE())
                """, (email, password_hash, nome, role))
                
                row = cursor.fetchone()
                conn.commit()
                
                if row:
                    return {
                        "id": str(row.id),
                        "email": email,
                        "nome": nome,
                        "role": role
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def list_users(self, limit: int = 100, offset: int = 0) -> list:
        """Listar usuários"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        id, 
                        email, 
                        nome,
                        role,
                        is_active,
                        created_at,
                        last_login
                    FROM usuarios 
                    ORDER BY created_at DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """, (offset, limit))
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        "id": str(row.id),
                        "email": row.email,
                        "nome": row.nome,
                        "role": row.role,
                        "is_active": row.is_active,
                        "created_at": row.created_at,
                        "last_login": row.last_login
                    })
                return users
                
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def delete_user(self, user_id: int) -> bool:
        """Desativar usuário (soft delete)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usuarios 
                    SET is_active = 0
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def get_user_permissions(self, user_id: int) -> List[Dict[str, Any]]:
        """Obter permissões do usuário baseado em sua role"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT p.code, p.name, p.category
                    FROM usuarios u
                    INNER JOIN role_permissions rp ON u.role = rp.role
                    INNER JOIN permissions p ON rp.permission_id = p.id
                    WHERE u.id = ? AND u.is_active = 1
                """, (user_id,))
                
                permissions = []
                for row in cursor.fetchall():
                    permissions.append({
                        "code": row.code,
                        "name": row.name,
                        "category": row.category
                    })
                
                # Se não encontrou permissões (tabelas não existem), retornar baseado na role
                if not permissions:
                    user = self.get_user_by_id(user_id)
                    if user:
                        role = user.get("role", "atendente")
                        # Permissões padrão por role
                        default_perms = {
                            "admin": [
                                {"code": "dashboard.view", "name": "Ver Dashboard", "category": "dashboard"},
                                {"code": "dashboard.export", "name": "Exportar Relatórios", "category": "dashboard"},
                                {"code": "conversations.view", "name": "Ver Conversas", "category": "conversations"},
                                {"code": "conversations.respond", "name": "Responder", "category": "conversations"},
                                {"code": "conversations.transfer", "name": "Transferir", "category": "conversations"},
                                {"code": "conversations.close", "name": "Encerrar", "category": "conversations"},
                                {"code": "users.view", "name": "Ver Usuários", "category": "users"},
                                {"code": "users.create", "name": "Criar Usuários", "category": "users"},
                                {"code": "users.edit", "name": "Editar Usuários", "category": "users"},
                                {"code": "users.delete", "name": "Excluir Usuários", "category": "users"},
                                {"code": "settings.view", "name": "Ver Configurações", "category": "settings"},
                                {"code": "settings.edit", "name": "Editar Configurações", "category": "settings"},
                            ],
                            "supervisor": [
                                {"code": "dashboard.view", "name": "Ver Dashboard", "category": "dashboard"},
                                {"code": "dashboard.export", "name": "Exportar Relatórios", "category": "dashboard"},
                                {"code": "conversations.view", "name": "Ver Conversas", "category": "conversations"},
                                {"code": "conversations.respond", "name": "Responder", "category": "conversations"},
                                {"code": "conversations.transfer", "name": "Transferir", "category": "conversations"},
                                {"code": "conversations.close", "name": "Encerrar", "category": "conversations"},
                                {"code": "users.view", "name": "Ver Usuários", "category": "users"},
                            ],
                            "atendente": [
                                {"code": "dashboard.view", "name": "Ver Dashboard", "category": "dashboard"},
                                {"code": "conversations.view", "name": "Ver Conversas", "category": "conversations"},
                                {"code": "conversations.respond", "name": "Responder", "category": "conversations"},
                                {"code": "conversations.transfer", "name": "Transferir", "category": "conversations"},
                                {"code": "conversations.close", "name": "Encerrar", "category": "conversations"},
                            ]
                        }
                        return default_perms.get(role, default_perms["atendente"])
                
                return permissions
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return []
    
    def update_user_password(self, user_id: int, password_hash: str) -> bool:
        """Atualizar senha do usuário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usuarios 
                    SET password_hash = ?, password_changed_at = GETDATE(), updated_at = GETDATE()
                    WHERE id = ?
                """, (password_hash, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False

    def update_user(
        self, 
        user_id: int, 
        nome: Optional[str] = None,
        role: Optional[str] = None,
        password: Optional[str] = None
    ) -> bool:
        """Atualizar dados do usuário"""
        try:
            updates = []
            params = []
            
            if nome:
                updates.append("nome = ?")
                params.append(nome)
            if role:
                updates.append("role = ?")
                params.append(role)
            if password:
                updates.append("password_hash = ?")
                params.append(self.hash_password(password))
            
            if not updates:
                return False
            
            params.append(user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE usuarios 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, params)
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    # =========================================================================
    # SESSÕES E TOKENS
    # =========================================================================
    
    def create_session(
        self,
        user_id: int,
        access_token: str,
        ip_address: str,
        user_agent: str = None,
        expires_minutes: int = None
    ) -> Optional[str]:
        """Criar nova sessão de usuário"""
        try:
            session_id = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(access_token.encode()).hexdigest()
            expires_at = datetime.now() + timedelta(
                minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Usar stored procedure se disponível
                try:
                    cursor.execute("""
                        EXEC sp_login_success 
                            @user_id = ?,
                            @session_id = ?,
                            @access_token_hash = ?,
                            @ip_address = ?,
                            @user_agent = ?,
                            @expires_at = ?
                    """, (user_id, session_id, token_hash, ip_address, user_agent, expires_at))
                except:
                    # Fallback para INSERT direto
                    cursor.execute("""
                        INSERT INTO user_sessions 
                            (session_id, user_id, access_token_hash, ip_address, user_agent, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (session_id, user_id, token_hash, ip_address, user_agent, expires_at))
                    
                    # Atualizar último login
                    cursor.execute("""
                        UPDATE usuarios SET last_login = GETDATE(), is_online = 1
                        WHERE id = ?
                    """, (user_id,))
                
                conn.commit()
                return session_id
                
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validar sessão ativa"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        s.user_id,
                        s.expires_at,
                        u.email,
                        u.nome,
                        u.role
                    FROM user_sessions s
                    INNER JOIN usuarios u ON s.user_id = u.id
                    WHERE s.session_id = ? 
                      AND s.is_active = 1 
                      AND s.expires_at > GETDATE()
                      AND u.is_active = 1
                """, (session_id,))
                
                row = cursor.fetchone()
                if row:
                    # Atualizar last_used
                    cursor.execute("""
                        UPDATE user_sessions SET last_used_at = GETDATE()
                        WHERE session_id = ?
                    """, (session_id,))
                    conn.commit()
                    
                    return {
                        "user_id": row.user_id,
                        "email": row.email,
                        "nome": row.nome,
                        "role": row.role,
                        "expires_at": row.expires_at
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    def revoke_session(self, session_id: str, reason: str = "logout") -> bool:
        """Revogar sessão"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_sessions 
                    SET is_active = 0, revoked_at = GETDATE(), revoke_reason = ?
                    WHERE session_id = ?
                """, (reason, session_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error revoking session: {e}")
            return False
    
    def revoke_all_sessions(self, user_id: int, except_session: str = None) -> int:
        """Revogar todas as sessões de um usuário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if except_session:
                    cursor.execute("""
                        UPDATE user_sessions 
                        SET is_active = 0, revoked_at = GETDATE(), revoke_reason = 'revoke_all'
                        WHERE user_id = ? AND session_id != ? AND is_active = 1
                    """, (user_id, except_session))
                else:
                    cursor.execute("""
                        UPDATE user_sessions 
                        SET is_active = 0, revoked_at = GETDATE(), revoke_reason = 'revoke_all'
                        WHERE user_id = ? AND is_active = 1
                    """, (user_id,))
                
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error revoking sessions: {e}")
            return 0
    
    def add_token_to_blacklist(
        self, 
        token: str, 
        user_id: int = None,
        expires_at: datetime = None,
        reason: str = None
    ) -> bool:
        """Adicionar token à blacklist"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires = expires_at or (datetime.now() + timedelta(days=7))
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO token_blacklist (token_hash, user_id, expires_at, reason)
                    VALUES (?, ?, ?, ?)
                """, (token_hash, user_id, expires, reason))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding token to blacklist: {e}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Verificar se token está na blacklist"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM token_blacklist 
                    WHERE token_hash = ? AND expires_at > GETDATE()
                """, (token_hash,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            return False
    
    # =========================================================================
    # AUDITORIA
    # =========================================================================
    
    def log_audit(
        self,
        event_type: str,
        action: str,
        user_id: int = None,
        resource_type: str = None,
        resource_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success",
        details: dict = None,
        old_values: dict = None,
        new_values: dict = None
    ) -> bool:
        """Registrar log de auditoria"""
        try:
            # Calcular hash de integridade
            entry_data = f"{datetime.now()}{event_type}{action}{user_id}"
            entry_hash = hashlib.sha256(entry_data.encode()).hexdigest()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obter hash anterior para cadeia de integridade
                cursor.execute("""
                    SELECT TOP 1 entry_hash FROM audit_logs ORDER BY id DESC
                """)
                row = cursor.fetchone()
                previous_hash = row.entry_hash if row else None
                
                cursor.execute("""
                    INSERT INTO audit_logs (
                        event_type, action, user_id, resource_type, resource_id,
                        ip_address, user_agent, status, details, old_values, new_values,
                        entry_hash, previous_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_type, action, user_id, resource_type, resource_id,
                    ip_address, user_agent, status,
                    json.dumps(details) if details else None,
                    json.dumps(old_values) if old_values else None,
                    json.dumps(new_values) if new_values else None,
                    entry_hash, previous_hash
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging audit: {e}")
            return False
    
    def get_audit_logs(
        self,
        user_id: int = None,
        event_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Buscar logs de auditoria"""
        try:
            conditions = ["1=1"]
            params = []
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)
            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)
            
            params.append(limit)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT TOP (?)
                        id, event_type, action, user_id, resource_type, resource_id,
                        ip_address, status, details, created_at
                    FROM audit_logs
                    WHERE {' AND '.join(conditions)}
                    ORDER BY created_at DESC
                """, params[::-1])  # limit primeiro
                
                logs = []
                for row in cursor.fetchall():
                    logs.append({
                        "id": row.id,
                        "event_type": row.event_type,
                        "action": row.action,
                        "user_id": row.user_id,
                        "resource_type": row.resource_type,
                        "resource_id": row.resource_id,
                        "ip_address": row.ip_address,
                        "status": row.status,
                        "details": json.loads(row.details) if row.details else None,
                        "created_at": row.created_at
                    })
                return logs
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []
    
    # =========================================================================
    # CONSENTIMENTOS LGPD
    # =========================================================================
    
    def save_consent(
        self,
        user_id: int,
        consent_type: str,
        granted: bool,
        ip_address: str = None,
        consent_text: str = None
    ) -> bool:
        """Salvar consentimento do usuário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Revogar consentimento anterior se existir
                cursor.execute("""
                    UPDATE user_consents 
                    SET revoked_at = GETDATE()
                    WHERE user_id = ? AND consent_type = ? AND revoked_at IS NULL
                """, (user_id, consent_type))
                
                # Criar novo registro
                cursor.execute("""
                    INSERT INTO user_consents 
                        (user_id, consent_type, granted, granted_at, ip_address, consent_text)
                    VALUES (?, ?, ?, GETDATE(), ?, ?)
                """, (user_id, consent_type, granted, ip_address, consent_text))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving consent: {e}")
            return False
    
    def get_user_consents(self, user_id: int) -> List[Dict[str, Any]]:
        """Obter consentimentos do usuário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT consent_type, granted, granted_at, revoked_at
                    FROM user_consents
                    WHERE user_id = ? AND revoked_at IS NULL
                """, (user_id,))
                
                consents = []
                for row in cursor.fetchall():
                    consents.append({
                        "type": row.consent_type,
                        "granted": row.granted,
                        "granted_at": row.granted_at
                    })
                return consents
        except Exception as e:
            logger.error(f"Error getting consents: {e}")
            return []
    
    # =========================================================================
    # MÉTRICAS E ESTATÍSTICAS
    # =========================================================================
    
    def get_online_agents(self) -> List[Dict[str, Any]]:
        """Obter lista de atendentes online"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM vw_agents_online
                    WHERE is_online = 1
                    ORDER BY available_slots DESC, nome
                """)
                
                agents = []
                for row in cursor.fetchall():
                    agents.append({
                        "id": row.id,
                        "nome": row.nome,
                        "role": row.role,
                        "current_conversations": row.current_conversations,
                        "max_conversations": row.max_concurrent_conversations,
                        "available_slots": row.available_slots,
                        "status": row.availability_status
                    })
                return agents
        except Exception as e:
            logger.error(f"Error getting online agents: {e}")
            return []
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Obter métricas para dashboard"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM vw_today_metrics")
                row = cursor.fetchone()
                
                if row:
                    return {
                        "conversations_today": row.conversations_today or 0,
                        "resolved_today": row.resolved_today or 0,
                        "in_queue": row.in_queue or 0,
                        "in_progress": row.in_progress or 0,
                        "with_bot": row.with_bot or 0,
                        "avg_resolution_time": row.avg_resolution_time_seconds,
                        "avg_first_response": row.avg_first_response_seconds,
                        "avg_satisfaction": float(row.avg_satisfaction) if row.avg_satisfaction else None,
                        "agents_online": row.agents_online or 0
                    }
                return {}
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return {}


# Instância singleton
sqlserver_manager = SQLServerManager()
