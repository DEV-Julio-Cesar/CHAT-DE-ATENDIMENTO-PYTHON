"""
Sistema de Segurança Avançado para ISP
Segurança enterprise para 10k+ clientes
"""
import asyncio
import hashlib
import hmac
import secrets
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import jwt
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import structlog
from fastapi import HTTPException, Request
from app.core.config import settings
from app.core.redis_client import redis_manager
import ipaddress
import re
import pyotp

logger = structlog.get_logger(__name__)


class SecurityManager:
    """Gerenciador de segurança avançado"""
    
    def __init__(self):
        self.encryption_key = self._generate_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.failed_attempts = {}
        self.blocked_ips = set()
        self.suspicious_activities = []
        
    def _generate_encryption_key(self) -> bytes:
        """Gera chave de criptografia baseada na SECRET_KEY"""
        password = settings.SECRET_KEY.encode()
        salt = b'isp_security_salt_2024'  # Em produção, usar salt aleatório
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
        
    async def encrypt_sensitive_data(self, data: str) -> str:
        """Criptografa dados sensíveis"""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Error encrypting data", error=str(e))
            raise
            
    async def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Descriptografa dados sensíveis"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Error decrypting data", error=str(e))
            raise
            
    async def hash_password(self, password: str) -> str:
        """Hash seguro de senha com bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
        
    async def verify_password(self, password: str, hashed: str) -> bool:
        """Verifica senha contra hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error("Error verifying password", error=str(e))
            return False
            
    async def generate_secure_token(self, length: int = 32) -> str:
        """Gera token seguro"""
        return secrets.token_urlsafe(length)
        
    async def create_jwt_token(
        self,
        user_data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Cria JWT token com dados do usuário"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode = user_data.copy()
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "isp-support-system",
            "aud": "isp-users"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return encoded_jwt
        
    async def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verifica e decodifica JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                audience="isp-users",
                issuer="isp-support-system"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
            
    async def check_rate_limit(
        self,
        identifier: str,
        max_attempts: int = 5,
        window_minutes: int = 15
    ) -> Tuple[bool, int]:
        """
        Verifica rate limiting
        Retorna (permitido, tentativas_restantes)
        """
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - (window_minutes * 60)
        
        # Remove tentativas antigas
        await redis_manager.zremrangebyscore(key, 0, window_start)
        
        # Conta tentativas atuais
        current_attempts = await redis_manager.zcard(key)
        
        if current_attempts >= max_attempts:
            return False, 0
            
        # Registra nova tentativa
        await redis_manager.zadd(key, {str(current_time): current_time})
        await redis_manager.expire(key, window_minutes * 60)
        
        remaining = max_attempts - current_attempts - 1
        return True, remaining
        
    async def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ):
        """Registra evento de segurança"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details or {},
            'severity': severity
        }
        
        # Log estruturado
        logger.info(
            "Security event",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
            details=details
        )
        
        # Armazena no Redis para análise
        await redis_manager.lpush(
            'security:events',
            json.dumps(event)
        )
        
        # Mantém apenas últimos 10000 eventos
        await redis_manager.ltrim('security:events', 0, 9999)
        
        # Alerta para eventos críticos
        if severity in ['critical', 'high']:
            await self._trigger_security_alert(event)
            
    async def detect_suspicious_activity(
        self,
        request: Request,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detecta atividade suspeita"""
        suspicion_score = 0
        reasons = []
        
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', '')
        
        # Verifica IP suspeito
        if await self._is_suspicious_ip(client_ip):
            suspicion_score += 30
            reasons.append('suspicious_ip')
            
        # Verifica geolocalização incomum
        if await self._is_unusual_location(client_ip, user_id):
            suspicion_score += 25
            reasons.append('unusual_location')
            
        # Verifica User-Agent suspeito
        if self._is_suspicious_user_agent(user_agent):
            suspicion_score += 20
            reasons.append('suspicious_user_agent')
            
        # Verifica padrão de acesso
        if await self._is_unusual_access_pattern(user_id, client_ip):
            suspicion_score += 15
            reasons.append('unusual_access_pattern')
            
        # Verifica múltiplas tentativas de login
        if await self._has_multiple_failed_attempts(client_ip):
            suspicion_score += 35
            reasons.append('multiple_failed_attempts')
            
        is_suspicious = suspicion_score >= 50
        
        if is_suspicious:
            await self.log_security_event(
                'suspicious_activity_detected',
                user_id=user_id,
                ip_address=client_ip,
                details={
                    'suspicion_score': suspicion_score,
                    'reasons': reasons,
                    'user_agent': user_agent
                },
                severity='high'
            )
            
        return {
            'is_suspicious': is_suspicious,
            'suspicion_score': suspicion_score,
            'reasons': reasons
        }
        
    async def validate_input_security(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida entrada contra ataques comuns"""
        issues = []
        
        for key, value in data.items():
            if isinstance(value, str):
                # SQL Injection
                if self._detect_sql_injection(value):
                    issues.append(f'sql_injection_attempt_in_{key}')
                    
                # XSS
                if self._detect_xss(value):
                    issues.append(f'xss_attempt_in_{key}')
                    
                # Command Injection
                if self._detect_command_injection(value):
                    issues.append(f'command_injection_attempt_in_{key}')
                    
                # Path Traversal
                if self._detect_path_traversal(value):
                    issues.append(f'path_traversal_attempt_in_{key}')
                    
        return {
            'is_safe': len(issues) == 0,
            'issues': issues
        }
        
    async def setup_mfa(self, user_id: str) -> Dict[str, Any]:
        """Configura autenticação multi-fator"""
        # Gera secret para TOTP
        secret = pyotp.random_base32()
        
        # Cria URI para QR Code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name="ISP Support System"
        )
        
        # Armazena secret criptografado
        encrypted_secret = await self.encrypt_sensitive_data(secret)
        await redis_manager.setex(
            f"mfa:setup:{user_id}",
            300,  # 5 minutos para completar setup
            encrypted_secret
        )
        
        return {
            'secret': secret,
            'qr_uri': provisioning_uri,
            'backup_codes': [secrets.token_hex(4) for _ in range(10)]
        }
        
    async def verify_mfa(self, user_id: str, token: str) -> bool:
        """Verifica token MFA"""
        try:
            # Obtém secret do usuário
            encrypted_secret = await redis_manager.get(f"mfa:secret:{user_id}")
            if not encrypted_secret:
                return False
                
            secret = await self.decrypt_sensitive_data(encrypted_secret)
            
            # Verifica token TOTP
            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(token, valid_window=1)
            
            if is_valid:
                await self.log_security_event(
                    'mfa_verification_success',
                    user_id=user_id,
                    severity='info'
                )
            else:
                await self.log_security_event(
                    'mfa_verification_failed',
                    user_id=user_id,
                    severity='warning'
                )
                
            return is_valid
            
        except Exception as e:
            logger.error("Error verifying MFA", error=str(e))
            return False
            
    async def enable_mfa(self, user_id: str, verification_token: str) -> bool:
        """Ativa MFA após verificação"""
        # Verifica token de setup
        setup_secret = await redis_manager.get(f"mfa:setup:{user_id}")
        if not setup_secret:
            return False
            
        secret = await self.decrypt_sensitive_data(setup_secret)
        totp = pyotp.TOTP(secret)
        
        if totp.verify(verification_token):
            # Move secret para storage permanente
            await redis_manager.set(f"mfa:secret:{user_id}", setup_secret)
            await redis_manager.delete(f"mfa:setup:{user_id}")
            
            await self.log_security_event(
                'mfa_enabled',
                user_id=user_id,
                severity='info'
            )
            
            return True
            
        return False
        
    async def check_password_strength(self, password: str) -> Dict[str, Any]:
        """Verifica força da senha"""
        score = 0
        issues = []
        
        # Comprimento
        if len(password) >= 12:
            score += 25
        elif len(password) >= 8:
            score += 15
        else:
            issues.append('password_too_short')
            
        # Caracteres maiúsculos
        if re.search(r'[A-Z]', password):
            score += 15
        else:
            issues.append('missing_uppercase')
            
        # Caracteres minúsculos
        if re.search(r'[a-z]', password):
            score += 15
        else:
            issues.append('missing_lowercase')
            
        # Números
        if re.search(r'\d', password):
            score += 15
        else:
            issues.append('missing_numbers')
            
        # Caracteres especiais
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 20
        else:
            issues.append('missing_special_chars')
            
        # Sequências comuns
        if self._has_common_sequences(password):
            score -= 20
            issues.append('common_sequences')
            
        # Palavras do dicionário
        if self._has_dictionary_words(password):
            score -= 15
            issues.append('dictionary_words')
            
        strength = 'weak'
        if score >= 80:
            strength = 'very_strong'
        elif score >= 60:
            strength = 'strong'
        elif score >= 40:
            strength = 'medium'
            
        return {
            'score': max(0, score),
            'strength': strength,
            'issues': issues,
            'is_acceptable': score >= 60
        }
        
    # Métodos auxiliares
    def _get_client_ip(self, request: Request) -> str:
        """Obtém IP real do cliente"""
        # Verifica headers de proxy
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
            
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
            
        return request.client.host if request.client else '127.0.0.1'
        
    async def _is_suspicious_ip(self, ip: str) -> bool:
        """Verifica se IP é suspeito"""
        # Lista de IPs bloqueados
        blocked = await redis_manager.sismember('security:blocked_ips', ip)
        if blocked:
            return True
            
        # Verifica se é IP privado em contexto público
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private and not settings.DEBUG:
                return True
        except ValueError:
            return True
            
        return False
        
    async def _is_unusual_location(self, ip: str, user_id: Optional[str]) -> bool:
        """Verifica localização incomum"""
        if not user_id:
            return False
            
        # Implementar verificação de geolocalização
        # Por enquanto, placeholder
        return False
        
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Verifica User-Agent suspeito"""
        suspicious_patterns = [
            r'bot',
            r'crawler',
            r'spider',
            r'scraper',
            r'curl',
            r'wget',
            r'python',
            r'java',
            r'go-http-client'
        ]
        
        user_agent_lower = user_agent.lower()
        return any(re.search(pattern, user_agent_lower) for pattern in suspicious_patterns)
        
    async def _is_unusual_access_pattern(self, user_id: Optional[str], ip: str) -> bool:
        """Verifica padrão de acesso incomum"""
        if not user_id:
            return False
            
        # Verifica frequência de acesso
        key = f"access_pattern:{user_id}:{ip}"
        current_hour = int(time.time() // 3600)
        
        access_count = await redis_manager.get(f"{key}:{current_hour}")
        if access_count and int(access_count) > 100:  # Mais de 100 acessos por hora
            return True
            
        return False
        
    async def _has_multiple_failed_attempts(self, ip: str) -> bool:
        """Verifica múltiplas tentativas falhadas"""
        key = f"failed_attempts:{ip}"
        attempts = await redis_manager.get(key)
        return attempts and int(attempts) >= 5
        
    def _detect_sql_injection(self, value: str) -> bool:
        """Detecta tentativas de SQL injection"""
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|#|/\*|\*/)",
            r"(\bxp_cmdshell\b)",
            r"(\bsp_executesql\b)"
        ]
        
        value_upper = value.upper()
        return any(re.search(pattern, value_upper, re.IGNORECASE) for pattern in sql_patterns)
        
    def _detect_xss(self, value: str) -> bool:
        """Detecta tentativas de XSS"""
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>"
        ]
        
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in xss_patterns)
        
    def _detect_command_injection(self, value: str) -> bool:
        """Detecta tentativas de command injection"""
        cmd_patterns = [
            r"[;&|`$(){}[\]\\]",
            r"\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig|ping|nslookup|dig)\b",
            r"\b(rm|mv|cp|chmod|chown|kill|killall|sudo|su)\b",
            r"\b(wget|curl|nc|telnet|ssh|ftp)\b"
        ]
        
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in cmd_patterns)
        
    def _detect_path_traversal(self, value: str) -> bool:
        """Detecta tentativas de path traversal"""
        traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"..%2f",
            r"..%5c"
        ]
        
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in traversal_patterns)
        
    def _has_common_sequences(self, password: str) -> bool:
        """Verifica sequências comuns"""
        common_sequences = [
            '123456', '654321', 'abcdef', 'fedcba',
            'qwerty', 'asdfgh', 'zxcvbn', '111111',
            '000000', 'password', 'admin', 'login'
        ]
        
        password_lower = password.lower()
        return any(seq in password_lower for seq in common_sequences)
        
    def _has_dictionary_words(self, password: str) -> bool:
        """Verifica palavras do dicionário"""
        # Lista básica de palavras comuns
        common_words = [
            'password', 'admin', 'user', 'login', 'system',
            'computer', 'internet', 'security', 'access', 'account'
        ]
        
        password_lower = password.lower()
        return any(word in password_lower for word in common_words)
        
    async def _trigger_security_alert(self, event: Dict[str, Any]):
        """Dispara alerta de segurança"""
        alert = {
            'id': secrets.token_hex(8),
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'security_alert',
            'severity': event['severity'],
            'event': event,
            'acknowledged': False
        }
        
        # Adiciona à lista de alertas ativos
        alerts_data = await redis_manager.get('system:alerts:active')
        alerts = json.loads(alerts_data) if alerts_data else []
        alerts.append(alert)
        
        # Mantém apenas últimos 100 alertas
        if len(alerts) > 100:
            alerts = alerts[-100:]
            
        await redis_manager.set('system:alerts:active', json.dumps(alerts))
        
        logger.critical(
            "Security alert triggered",
            alert_id=alert['id'],
            event_type=event['event_type'],
            severity=event['severity']
        )


# Instância global
security_manager = SecurityManager()


# Middleware de segurança
class SecurityMiddleware:
    """Middleware de segurança para FastAPI"""
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Verifica rate limiting
            client_ip = security_manager._get_client_ip(request)
            allowed, remaining = await security_manager.check_rate_limit(
                f"global:{client_ip}",
                max_attempts=1000,  # 1000 requests por 15 min
                window_minutes=15
            )
            
            if not allowed:
                response = {
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED"
                }
                await send({
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [[b"content-type", b"application/json"]]
                })
                await send({
                    "type": "http.response.body",
                    "body": json.dumps(response).encode()
                })
                return
                
            # Detecta atividade suspeita
            suspicion = await security_manager.detect_suspicious_activity(request)
            if suspicion['is_suspicious'] and suspicion['suspicion_score'] >= 80:
                response = {
                    "error": "Suspicious activity detected",
                    "code": "SUSPICIOUS_ACTIVITY"
                }
                await send({
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [[b"content-type", b"application/json"]]
                })
                await send({
                    "type": "http.response.body",
                    "body": json.dumps(response).encode()
                })
                return
                
        await self.app(scope, receive, send)


import json