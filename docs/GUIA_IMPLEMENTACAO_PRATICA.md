# 🚀 PLANO DE AÇÃO PRÁTICO - IMPLEMENTAÇÃO PASSO A PASSO

**Data:** 1 de Fevereiro de 2026  
**Objetivo:** Deixar aplicação funcionando em produção segura  
**Timeline:** 4 semanas  
**Prioridade:** P1 → P2 → P3  

---

## 📋 RESUMO EXECUTIVO

```
SEMANA 1: CRÍTICOS DE SEGURANÇA (Deploy bloqueador)
SEMANA 2: INFRAESTRUTURA (Escalabilidade)
SEMANA 3: MONITORAMENTO (Observabilidade)
SEMANA 4: TESTES + PRODUÇÃO (Deploy final)
```

---

## SEMANA 1: CRÍTICOS DE SEGURANÇA ⏱️ 40 horas

### TAREFA 1.1: Autenticação em Todos Endpoints 🔐
**Tempo:** 8 horas | **Prioridade:** 🔴 CRÍTICO

#### Passo 1: Criar dependency de autenticação

```python
# /app/core/dependencies.py (NOVO)

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredential
import jwt
from app.core.config import settings
from app.core.redis_client import redis_manager

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthCredential = Depends(security)
):
    """Dependency para verificar autenticação"""
    try:
        token = credentials.credentials
        
        # 1. Verificar se está na blacklist (revogado)
        is_revoked = await redis_manager.get(f"revoked_token:{token}")
        if is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked"
            )
        
        # 2. Decodificar JWT
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience="isp-users",
            issuer="isp-support-system"
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def require_admin(user = Depends(get_current_user)):
    """Verificar se é admin"""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
```

#### Passo 2: Atualizar endpoints

```python
# /app/api/endpoints/users.py (ATUALIZAR)

from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user, require_admin

router = APIRouter()

@router.get("/")
async def list_users(user = Depends(require_admin)):
    """Listar usuários - APENAS ADMIN"""
    # Agora protegido! ✅
    return {"users": []}

@router.get("/me")
async def get_current_user_info(user = Depends(get_current_user)):
    """Obter dados do usuário atual"""
    # Qualquer usuário autenticado pode acessar
    return user

# /app/api/endpoints/whatsapp.py (ATUALIZAR)

@router.get("/status")
async def whatsapp_status(user = Depends(get_current_user)):
    """Status do WhatsApp - PROTEGIDO"""
    return {"status": "connected"}

@router.post("/webhooks/messages")
async def receive_whatsapp_message(
    body: Dict,
    # ⚠️ Webhook do WhatsApp não precisa de JWT
    # Mas precisa de secret token!
    x_hub_signature_256: str = Header(None)
):
    """
    Webhooks do WhatsApp são públicos MAS
    verificam assinatura HMAC
    """
    if not x_hub_signature_256:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Verificar assinatura
    expected_signature = hmac.new(
        settings.WHATSAPP_ACCESS_TOKEN.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if x_hub_signature_256 != f"sha256={expected_signature}":
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Processar mensagem
    return {"ok": True}
```

**✅ Resultado:** Todos endpoints privados agora protegidos com JWT

---

### TAREFA 1.2: Rate Limiting Real 🛡️
**Tempo:** 6 horas | **Prioridade:** 🔴 CRÍTICO

#### Passo 1: Implementar RateLimitManager

```python
# /app/core/rate_limiter.py (NOVO)

from app.core.redis_client import redis_manager

class RateLimiter:
    """Rate limiting com Redis sliding window"""
    
    async def is_allowed(
        self,
        identifier: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ) -> bool:
        """Verificar se requisição é permitida"""
        
        key = f"ratelimit:{identifier}"
        
        # Obter contador atual
        current = await redis_manager.get(key)
        current_count = int(current or 0)
        
        # Verificar limite
        if current_count >= max_requests:
            return False
        
        # Incrementar
        await redis_manager.set(
            key,
            str(current_count + 1),
            ex=window_seconds
        )
        
        return True

rate_limiter = RateLimiter()

# Usar em endpoints:

@router.post("/login")
async def login(request: Request, credentials: LoginRequest):
    """Login com rate limiting"""
    
    # Verificar rate limit por IP
    is_allowed = await rate_limiter.is_allowed(
        identifier=request.client.host,
        max_requests=5,
        window_seconds=900  # 15 minutos
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts"
        )
    
    # Prosseguir com login...
    return {"access_token": token}
```

**✅ Resultado:** Proteção contra brute force e DDoS

---

### TAREFA 1.3: Criptografia em Repouso 🔒
**Tempo:** 10 horas | **Prioridade:** 🔴 CRÍTICO

#### Passo 1: Implementar criptografia de mensagens

```python
# /app/services/message_encryption.py (NOVO)

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import os
import base64

class MessageEncryption:
    """Criptografia de mensagens AES-256"""
    
    async def encrypt_message(
        self,
        message_content: str,
        cliente_id: str
    ) -> Dict[str, str]:
        """Criptografar mensagem antes de salvar no BD"""
        
        # 1. Gerar IV aleatório
        iv = os.urandom(16)
        
        # 2. Derivar chave específica do cliente
        key = self._derive_key(cliente_id)
        
        # 3. Criptografar com AES-256-CBC
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # 4. Adicionar padding (PKCS7)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(
            message_content.encode()
        ) + padder.finalize()
        
        # 5. Encriptar
        encrypted_content = (
            encryptor.update(padded_data) + 
            encryptor.finalize()
        )
        
        return {
            "encrypted_content": base64.b64encode(encrypted_content).decode(),
            "iv": base64.b64encode(iv).decode(),
            "algorithm": "AES-256-CBC"
        }
    
    async def decrypt_message(
        self,
        encrypted_content: str,
        iv: str,
        cliente_id: str
    ) -> str:
        """Descriptografar mensagem ao recuperar"""
        
        # 1. Derivar chave
        key = self._derive_key(cliente_id)
        
        # 2. Decodificar base64
        encrypted_bytes = base64.b64decode(encrypted_content)
        iv_bytes = base64.b64decode(iv)
        
        # 3. Descriptografar
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv_bytes),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        padded_data = (
            decryptor.update(encrypted_bytes) + 
            decryptor.finalize()
        )
        
        # 4. Remover padding
        unpadder = padding.PKCS7(128).unpadder()
        original_data = (
            unpadder.update(padded_data) + 
            unpadder.finalize()
        )
        
        return original_data.decode()
    
    def _derive_key(self, cliente_id: str) -> bytes:
        """Derivar chave específica do cliente"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=f"salt_{cliente_id}".encode(),
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(settings.MASTER_ENCRYPTION_KEY.encode())

message_encryption = MessageEncryption()

# Usar ao salvar mensagem:

@router.post("/messages")
async def create_message(
    message_data: MessageRequest,
    user = Depends(get_current_user)
):
    """Criar mensagem criptografada"""
    
    # Criptografar conteúdo
    encrypted = await message_encryption.encrypt_message(
        message_content=message_data.content,
        cliente_id=message_data.client_id
    )
    
    # Salvar no BD
    message = Mensagem(
        conversa_id=message_data.conversa_id,
        conteudo_criptografado=encrypted["encrypted_content"],
        iv=encrypted["iv"],
        tipo_criptografia=encrypted["algorithm"],
        remetente_tipo=SenderType.ATENDENTE
    )
    
    await db.save(message)
    
    return {"message_id": str(message.id), "encrypted": True}
```

**✅ Resultado:** Todas as mensagens criptografadas em repouso

---

### TAREFA 1.4: Auditoria Detalhada 📝
**Tempo:** 8 horas | **Prioridade:** 🔴 CRÍTICO

#### Passo 1: Criar AuditLogger

```python
# /app/core/audit_logger.py (NOVO)

import uuid
from datetime import datetime, timezone

class AuditLogger:
    """Sistema de auditoria imutável"""
    
    async def log(
        self,
        event_type: str,
        user_id: Optional[str],
        resource_type: Optional[str],
        resource_id: Optional[str],
        action: str,
        status: str = "success",
        details: Dict = None,
        ip_address: Optional[str] = None
    ):
        """Registrar evento de auditoria"""
        
        entry = AuditLog(
            id=uuid.uuid4(),
            event_type=event_type,  # "login", "data_access", "data_delete"
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
            details=details or {}
        )
        
        # Salvar em BD (imutável)
        await db.save(entry)
        
        # Também enviar para ELK Stack (opcional)
        logger.info("audit_event", extra={
            "event_type": event_type,
            "user_id": user_id,
            "action": action,
            "resource": f"{resource_type}:{resource_id}"
        })

audit_logger = AuditLogger()

# Usar em endpoints:

@router.post("/login")
async def login(request: Request, credentials: LoginRequest):
    """Login com auditoria"""
    
    try:
        # Validar credentials...
        user = await db.get_user_by_username(credentials.username)
        
        if not user or not await verify_password(credentials.password, user.password_hash):
            # Registrar tentativa falhada
            await audit_logger.log(
                event_type="login_failed",
                user_id=None,
                resource_type="user",
                resource_id=None,
                action="login",
                status="failed",
                ip_address=request.client.host,
                details={"reason": "invalid_credentials"}
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Registrar sucesso
        await audit_logger.log(
            event_type="login_success",
            user_id=str(user.id),
            resource_type="user",
            resource_id=str(user.id),
            action="login",
            status="success",
            ip_address=request.client.host
        )
        
        # Gerar token
        token = await security_manager.create_jwt_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role
        })
        
        return {"access_token": token, "token_type": "bearer"}
        
    except Exception as e:
        await audit_logger.log(
            event_type="login_error",
            user_id=None,
            resource_type="user",
            action="login",
            status="error",
            ip_address=request.client.host,
            details={"error": str(e)}
        )
        raise
```

**✅ Resultado:** Todos os eventos registrados para compliance LGPD

---

### TAREFA 1.5: LGPD Compliance ⚖️
**Tempo:** 8 horas | **Prioridade:** 🔴 CRÍTICO

#### Passo 1: Endpoint de Direito ao Esquecimento

```python
# /app/api/endpoints/gdpr.py (NOVO)

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

@router.delete("/users/{user_id}/data")
async def delete_user_data(
    user_id: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    LGPD Art. 16 - Direito ao Esquecimento
    
    Apagar todos os dados pessoais do usuário
    """
    
    # 1. Verificar autorização (apenas admin ou próprio user)
    if (current_user.get("sub") != user_id and 
        current_user.get("role") != "admin"):
        await audit_logger.log(
            event_type="unauthorized_deletion_attempt",
            user_id=current_user.get("sub"),
            resource_type="user",
            resource_id=user_id,
            action="delete"
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 2. Registrar pedido LGPD
    gdpr_request = GDPRRequest(
        user_id=user_id,
        request_type="deletion",
        requested_at=datetime.now(),
        requested_by=current_user.get("sub") or user_id,
        status="pending"
    )
    await db.save(gdpr_request)
    
    # 3. Enviar email de confirmação
    user = await db.get_user(user_id)
    await send_confirmation_email(
        user.email,
        f"Confirme exclusão de dados em: {request.base_url}gdpr/confirm/{gdpr_request.id}"
    )
    
    return {
        "status": "confirmation_email_sent",
        "message": "Verifique seu email para confirmar"
    }

@router.post("/gdpr/confirm/{request_id}")
async def confirm_deletion(request_id: str):
    """Confirmar e executar deleção"""
    
    gdpr_req = await db.get_gdpr_request(request_id)
    
    if not gdpr_req:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Backup para retenção legal (90 dias isolado)
    await db.backup_user_data(
        user_id=gdpr_req.user_id,
        retention_days=90
    )
    
    # 1. Apagar dados pessoais
    await db.delete_user(gdpr_req.user_id)
    
    # 2. Pseudonymize histórico (não pode deletar por legal)
    await db.pseudonymize_conversations(gdpr_req.user_id)
    
    # 3. Registrar em auditoria
    await audit_logger.log(
        event_type="gdpr_deletion_executed",
        user_id=None,
        resource_type="user",
        resource_id=gdpr_req.user_id,
        action="delete",
        details={"gdpr_request_id": request_id}
    )
    
    # 4. Enviar confirmação
    await send_deletion_confirmation_email(gdpr_req.user_id)
    
    gdpr_req.status = "completed"
    await db.save(gdpr_req)
    
    return {"status": "deletion_completed"}

@router.get("/users/{user_id}/export")
async def export_user_data(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """
    LGPD Art. 18 - Portabilidade de Dados
    
    Exportar dados do usuário em formato aberto
    """
    
    if current_user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Coletar todos os dados
    user_data = {
        "usuario": await db.get_user(user_id),
        "conversas": await db.get_conversations(user_id),
        "mensagens": await db.get_messages(user_id),
        "metadados": {
            "export_date": datetime.now().isoformat(),
            "format": "json-ld"
        }
    }
    
    # Criptografar antes de enviar
    encrypted = await security_manager.encrypt_sensitive_data(
        json.dumps(user_data)
    )
    
    # Enviar por email seguro
    await send_secure_email(
        to=user.email,
        subject="Seus dados - Exportação LGPD",
        attachment=encrypted
    )
    
    await audit_logger.log(
        event_type="gdpr_data_export",
        user_id=user_id,
        resource_type="user",
        resource_id=user_id,
        action="export"
    )
    
    return {"status": "export_queued"}
```

**✅ Resultado:** LGPD compliance completo (direito ao esquecimento, portabilidade)

---

## ✅ SEMANA 1 - CHECKLIST

- [ ] Criar dependencies.py com autenticação JWT
- [ ] Proteger todos endpoints privados
- [ ] Implementar rate_limiter.py com Redis
- [ ] Criar message_encryption.py com AES-256
- [ ] Criptografar todas as mensagens
- [ ] Implementar audit_logger.py
- [ ] Criar endpoints GDPR (delete, export)
- [ ] Testar autenticação em staging
- [ ] Testar rate limiting
- [ ] Testes de criptografia/decriptografia

**Após Semana 1:**
```
✅ Deploy seguro possível
✅ LGPD compliance implementado
✅ Auditoria funcionando
```

---

## SEMANA 2: INFRAESTRUTURA ⏱️ 80 horas

### TAREFA 2.1: Setup Load Balancer + API Escalada

#### Atualizar docker-compose.production.yml

```yaml
version: '3.8'

services:
  haproxy:
    image: haproxy:2.8-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg
    depends_on:
      - api-1
      - api-2
      - api-3
      - api-4
    restart: unless-stopped

  api-1:
    build: .
    command: >
      gunicorn app.main:app
        --workers 4
        --worker-class uvicorn.workers.UvicornWorker
        --bind 0.0.0.0:8000
        --max-requests 10000
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres-master:5432/isp_support
      - REDIS_URL=redis://redis-master-1:6379/0
    depends_on:
      - postgres-master
      - redis-master-1
    restart: unless-stopped

  # api-2, api-3, api-4 (mesmo que api-1)

  postgres-master:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: isp_support
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  postgres-slave:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    depends_on:
      - postgres-master
    volumes:
      - postgres-slave-data:/var/lib/postgresql/data

  redis-master-1:
    image: redis:7-alpine
    command: >
      redis-server
        --maxmemory 1gb
        --maxmemory-policy allkeys-lru
        --appendonly yes
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"

volumes:
  postgres-data:
  postgres-slave-data:
  redis-data:
```

### TAREFA 2.2: PostgreSQL Master/Slave

- Configurar replicação streaming WAL
- Setup Patroni para failover automático
- Testar failover manual

### TAREFA 2.3: RabbitMQ + Celery Workers

```yaml
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    ports:
      - "5672:5672"
      - "15672:15672"

  celery-worker-ai:
    build: .
    command: >
      celery -A app.workers.main worker
        --queue=ai_tasks --concurrency=4

  celery-worker-messages:
    build: .
    command: >
      celery -A app.workers.main worker
        --queue=messages --concurrency=8
```

---

## SEMANA 3: MONITORAMENTO ⏱️ 60 horas

### TAREFA 3.1: Prometheus + Grafana

```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infra/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    ports:
      - "3000:3000"
```

### TAREFA 3.2: ELK Stack (Logs)

```yaml
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
    environment:
      - discovery.type=single-node

  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
```

---

## SEMANA 4: PRODUÇÃO ✅

### TAREFA 4.1: Deploy em Staging
- Rodar docker-compose completo
- Executar testes de carga
- Validar failover automático

### TAREFA 4.2: Deploy em Produção
- Backup do BD antigo
- Migração de dados
- Ativar monitoramento
- Validar SLA (99.95%)

---

## 🚀 COMEÇAR AGORA - QUICKSTART

### Passo 1: Configurar variáveis de ambiente

```bash
# .env.production
DEBUG=false
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@postgres-master:5432/isp_support
REDIS_URL=redis://redis-master-1:6379/0
CELERY_BROKER_URL=amqp://user:pass@rabbitmq:5672/isp_support
GEMINI_API_KEY=sua-key-gemini
WHATSAPP_ACCESS_TOKEN=seu-token-whatsapp
MASTER_ENCRYPTION_KEY=chave-mestre-criptografia
```

### Passo 2: Deploy staging

```bash
cd infra
docker-compose -f docker-compose.production.yml up -d
```

### Passo 3: Rodar migrations

```bash
docker-compose exec api alembic upgrade head
```

### Passo 4: Criar usuário admin

```bash
docker-compose exec api python -c "
from app.core.database import db_manager
from app.models.database import Usuario
import asyncio

async def create_admin():
    await db_manager.initialize()
    admin = Usuario(
        username='admin',
        email='admin@example.com',
        password_hash='...',  # hash da senha
        role='admin'
    )
    await db_manager.session_factory().add(admin)
    await db_manager.session_factory().commit()

asyncio.run(create_admin())
"
```

### Passo 5: Testar acesso

```bash
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"sua-senha"}'
```

---

## 📊 MÉTRICAS DE SUCESSO

Após 4 semanas:

```
✅ Uptime: 99.95%
✅ Response time p95: < 200ms
✅ LGPD compliance: 100%
✅ Security score: 8.5/10
✅ Escalabilidade: 10k+ clientes
✅ Auditoria: 100% de eventos
```

---

## 🆘 PROBLEMAS COMUNS

### Problema: BD slow query
```
Solução: 
1. Adicionar índices missing (veja ANALISE_ARQUITETURA)
2. Aumentar pool de conexões
3. Implementar query caching
```

### Problema: Redis memory full
```
Solução:
1. Ativar eviction policy: allkeys-lru
2. Aumentar maxmemory
3. Monitorar com Prometheus
```

### Problema: Webhook WhatsApp timeout
```
Solução:
1. Adicionar retry com backoff
2. Usar Celery task queue
3. Responder imediatamente (202 Accepted)
```

---

## 📞 PRÓXIMOS PASSOS

1. ✅ Implementar Semana 1 (Segurança)
2. ✅ Testar em staging
3. ✅ Implementar Semana 2 (Infra)
4. ✅ Testar failover
5. ✅ Deploy em produção

**Status:** Pronto para começar! 🚀

---

**Data:** 1 de Fevereiro de 2026
