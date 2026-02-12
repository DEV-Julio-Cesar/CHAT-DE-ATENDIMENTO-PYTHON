"""
Segurança de Webhook
Verificação de assinatura HMAC e proteção contra replay attacks
"""
import hmac
import hashlib
import time
from typing import Optional, Tuple
from fastapi import HTTPException, Request
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class WebhookSecurity:
    """
    Gerenciador de segurança para webhooks
    
    Features:
    - Verificação de assinatura HMAC
    - Proteção contra replay attacks
    - Rate limiting específico para webhooks
    """
    
    def __init__(self):
        self.replay_window = 300  # 5 minutos
        self._processed_requests = set()  # Cache de requests processados
    
    def verify_whatsapp_signature(
        self,
        payload: bytes,
        signature: str,
        secret: Optional[str] = None
    ) -> bool:
        """
        Verificar assinatura HMAC do webhook WhatsApp
        
        Args:
            payload: Corpo da requisição (bytes)
            signature: Assinatura do header X-Hub-Signature-256
            secret: Secret da aplicação (usa settings se não fornecido)
        
        Returns:
            True se assinatura válida
        """
        if not signature:
            logger.warning("Webhook signature missing")
            return False
        
        if secret is None:
            secret = settings.WHATSAPP_APP_SECRET
        
        if not secret:
            logger.error("WhatsApp app secret not configured")
            return False
        
        try:
            # Calcular assinatura esperada
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Remover prefixo "sha256=" se presente
            if signature.startswith("sha256="):
                signature = signature[7:]
            
            # Comparação segura contra timing attacks
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if not is_valid:
                logger.warning(
                    "Invalid webhook signature",
                    expected=expected_signature[:10] + "...",
                    received=signature[:10] + "..."
                )
            
            return is_valid
            
        except Exception as e:
            logger.error("Error verifying webhook signature", error=str(e))
            return False
    
    def verify_timestamp(self, timestamp: int) -> Tuple[bool, str]:
        """
        Verificar se timestamp está dentro da janela permitida
        Proteção contra replay attacks
        
        Args:
            timestamp: Unix timestamp da requisição
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        current_time = int(time.time())
        time_diff = abs(current_time - timestamp)
        
        if time_diff > self.replay_window:
            return False, f"Request timestamp too old (diff: {time_diff}s)"
        
        return True, ""
    
    def verify_nonce(self, nonce: str) -> Tuple[bool, str]:
        """
        Verificar se nonce já foi usado
        Proteção adicional contra replay attacks
        
        Args:
            nonce: Identificador único da requisição
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        if nonce in self._processed_requests:
            return False, "Request already processed (duplicate nonce)"
        
        # Adicionar ao cache (em produção, usar Redis)
        self._processed_requests.add(nonce)
        
        # Limpar cache antigo (manter apenas últimos 1000)
        if len(self._processed_requests) > 1000:
            # Remover 20% mais antigos
            to_remove = list(self._processed_requests)[:200]
            for item in to_remove:
                self._processed_requests.discard(item)
        
        return True, ""
    
    async def verify_webhook_request(
        self,
        request: Request,
        require_signature: bool = True,
        require_timestamp: bool = True
    ) -> Tuple[bool, str, dict]:
        """
        Verificação completa de webhook
        
        Args:
            request: FastAPI Request object
            require_signature: Se exige verificação de assinatura
            require_timestamp: Se exige verificação de timestamp
        
        Returns:
            (is_valid: bool, error_message: str, payload: dict)
        """
        try:
            # Ler corpo da requisição
            body = await request.body()
            
            # Verificar assinatura
            if require_signature:
                signature = request.headers.get("X-Hub-Signature-256")
                if not signature:
                    return False, "Missing signature header", {}
                
                if not self.verify_whatsapp_signature(body, signature):
                    return False, "Invalid signature", {}
            
            # Parse JSON
            import json
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return False, "Invalid JSON payload", {}
            
            # Verificar timestamp
            if require_timestamp:
                timestamp = payload.get("timestamp")
                if not timestamp:
                    return False, "Missing timestamp in payload", {}
                
                is_valid, error = self.verify_timestamp(int(timestamp))
                if not is_valid:
                    return False, error, {}
            
            # Verificar nonce (se presente)
            nonce = payload.get("nonce") or request.headers.get("X-Request-ID")
            if nonce:
                is_valid, error = self.verify_nonce(nonce)
                if not is_valid:
                    return False, error, {}
            
            return True, "", payload
            
        except Exception as e:
            logger.error("Error verifying webhook request", error=str(e))
            return False, f"Verification error: {str(e)}", {}
    
    def generate_webhook_signature(self, payload: bytes, secret: str) -> str:
        """
        Gerar assinatura para webhook (para testes)
        
        Args:
            payload: Corpo da requisição
            secret: Secret da aplicação
        
        Returns:
            Assinatura HMAC-SHA256
        """
        signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"


# Instância global
webhook_security = WebhookSecurity()


# Dependency para FastAPI
async def verify_webhook(request: Request):
    """
    Dependency para verificar webhook em endpoints
    
    Usage:
        @app.post("/webhook", dependencies=[Depends(verify_webhook)])
        async def webhook_handler(request: Request):
            ...
    """
    is_valid, error, payload = await webhook_security.verify_webhook_request(
        request,
        require_signature=True,
        require_timestamp=True
    )
    
    if not is_valid:
        logger.warning("Webhook verification failed", error=error)
        raise HTTPException(status_code=401, detail=error)
    
    # Adicionar payload ao request state
    request.state.webhook_payload = payload
    
    return payload
