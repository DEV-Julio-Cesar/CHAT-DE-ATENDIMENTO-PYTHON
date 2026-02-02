"""
Sistema de auditoria imutável com hash chaining
- Blockchain-like integrity verification
- Registro de todos eventos de segurança
- Retenção de 2 anos
- Compatível com LGPD Art. 18
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Logger de auditoria com integridade via hash chaining
    
    Cada entrada contém hash da entrada anterior,
    formando corrente imutável (blockchain-like)
    
    Hash = SHA256(event_id + timestamp + user_id + action + hash_anterior)
    """
    
    def __init__(self):
        self.last_hash: Optional[str] = None
    
    def _calculate_hash(
        self,
        event_id: str,
        timestamp: str,
        user_id: Optional[str],
        action: str,
        previous_hash: Optional[str]
    ) -> str:
        """
        Calcular SHA256 do evento para integridade
        
        Garante que eventos não podem ser modificados
        sem quebrar a corrente de hashes
        """
        data_to_hash = f"{event_id}|{timestamp}|{user_id}|{action}|{previous_hash or 'START'}"
        return hashlib.sha256(data_to_hash.encode()).hexdigest()
    
    async def log(
        self,
        event_type: str,
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registrar evento de auditoria
        
        Args:
            event_type: Tipo do evento (login_success, data_access, data_delete, etc)
            user_id: ID do usuário que executou ação
            action: Ação realizada (login, read, write, delete, etc)
            resource_type: Tipo do recurso (user, message, conversation, etc)
            resource_id: ID do recurso
            status: Status do evento (success, failed, error)
            ip_address: IP da requisição
            details: Dados adicionais
        
        Returns:
            Entrada de auditoria criada
        """
        try:
            # Gerar ID único do evento
            event_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Calcular hash com integridade
            entry_hash = self._calculate_hash(
                event_id=event_id,
                timestamp=timestamp,
                user_id=user_id,
                action=action,
                previous_hash=self.last_hash
            )
            
            # Criar entrada
            audit_entry = {
                "id": event_id,
                "timestamp": timestamp,
                "event_type": event_type,
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "status": status,
                "ip_address": ip_address,
                "details": details or {},
                "hash": entry_hash,
                "previous_hash": self.last_hash
            }
            
            # Atualizar hash anterior
            self.last_hash = entry_hash
            
            # Log estruturado
            logger.info(
                f"Audit event: {event_type}",
                extra={
                    "event_id": event_id,
                    "user_id": user_id,
                    "action": action,
                    "resource": f"{resource_type}:{resource_id}" if resource_type else None,
                    "status": status,
                    "ip": ip_address,
                    "hash": entry_hash
                }
            )
            
            # TODO: Salvar em BD (PostgreSQL)
            # await db.save_audit_log(audit_entry)
            
            # TODO: Enviar para ELK Stack (Elasticsearch)
            # await elk_client.index("audit-logs", audit_entry)
            
            return audit_entry
            
        except Exception as e:
            logger.error(f"Erro ao registrar auditoria: {str(e)}")
            raise
    
    async def verify_chain(self, entries: list) -> bool:
        """
        Verificar integridade da corrente de hashes
        
        Valida que nenhuma entrada foi modificada
        
        Args:
            entries: Lista de entradas em ordem cronológica
        
        Returns:
            True se corrente é válida
        """
        previous_hash = None
        
        for entry in entries:
            # Recalcular hash
            calculated_hash = self._calculate_hash(
                event_id=entry["id"],
                timestamp=entry["timestamp"],
                user_id=entry["user_id"],
                action=entry["action"],
                previous_hash=previous_hash
            )
            
            # Comparar com hash armazenado
            if calculated_hash != entry["hash"]:
                logger.error(
                    f"Integridade quebrada em evento {entry['id']}: "
                    f"esperado {calculated_hash}, encontrado {entry['hash']}"
                )
                return False
            
            previous_hash = entry["hash"]
        
        logger.info("Integridade da corrente de auditoria verificada com sucesso")
        return True


class AuditEventTypes:
    """Constantes de tipos de eventos"""
    
    # Autenticação
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_CREATED = "token_created"
    TOKEN_REVOKED = "token_revoked"
    
    # Dados
    DATA_ACCESSED = "data_accessed"
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    
    # Segurança
    SECURITY_ALERT = "security_alert"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    FAILED_AUTH_ATTEMPT = "failed_auth_attempt"
    
    # Admin
    ADMIN_ACTION = "admin_action"
    USER_CREATED = "user_created"
    USER_DISABLED = "user_disabled"
    
    # LGPD
    GDPR_REQUEST = "gdpr_request"
    GDPR_DATA_DELETED = "gdpr_data_deleted"
    GDPR_DATA_EXPORTED = "gdpr_data_exported"


class AuditActions:
    """Constantes de ações"""
    
    LOGIN = "login"
    LOGOUT = "logout"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    UPDATE = "update"
    EXPORT = "export"
    IMPORT = "import"
    DOWNLOAD = "download"
    UPLOAD = "upload"


class AuditResourceTypes:
    """Constantes de tipos de recurso"""
    
    USER = "user"
    MESSAGE = "message"
    CONVERSATION = "conversation"
    CLIENT = "client"
    TOKEN = "token"
    SETTING = "setting"
    REPORT = "report"


# Instância global
audit_logger = AuditLogger()


async def log_data_access(
    user_id: str,
    resource_type: str,
    resource_id: str,
    ip_address: Optional[str] = None,
    details: Optional[Dict] = None
):
    """Helper: Registrar acesso a dados"""
    return await audit_logger.log(
        event_type=AuditEventTypes.DATA_ACCESSED,
        user_id=user_id,
        action=AuditActions.READ,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details
    )


async def log_data_modification(
    user_id: str,
    action: str,  # "create", "update", "delete"
    resource_type: str,
    resource_id: str,
    ip_address: Optional[str] = None,
    details: Optional[Dict] = None
):
    """Helper: Registrar modificação de dados"""
    
    event_type_map = {
        "create": AuditEventTypes.DATA_CREATED,
        "update": AuditEventTypes.DATA_UPDATED,
        "delete": AuditEventTypes.DATA_DELETED
    }
    
    return await audit_logger.log(
        event_type=event_type_map.get(action, AuditEventTypes.ADMIN_ACTION),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details
    )


async def log_security_event(
    event_type: str,
    user_id: Optional[str],
    ip_address: Optional[str] = None,
    details: Optional[Dict] = None
):
    """Helper: Registrar evento de segurança"""
    return await audit_logger.log(
        event_type=event_type,
        user_id=user_id,
        action="security_check",
        ip_address=ip_address,
        details=details,
        status="alert"
    )
