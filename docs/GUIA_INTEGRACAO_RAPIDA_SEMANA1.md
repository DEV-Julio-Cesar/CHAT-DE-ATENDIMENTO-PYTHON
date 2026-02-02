# 🚀 GUIA DE INTEGRAÇÃO RÁPIDA - SEMANA 1

**Objetivo:** Integrar os 5 módulos criados nos endpoints existentes  
**Tempo:** 2 dias  
**Dificuldade:** Média

---

## 1️⃣ INTEGRAR AUTENTICAÇÃO JWT EM ENDPOINTS

### Passo 1: Atualizar `app/api/endpoints/auth.py`

```python
# ADICIONAR NO TOPO
from fastapi import HTTPException, status, Request
from app.core.dependencies import get_current_user, revoke_token
from app.core.audit_logger import audit_logger, AuditEventTypes
from app.core.security_simple import security_manager  # Já existe
from datetime import datetime, timedelta, timezone
import jwt

# ATUALIZAR ENDPOINT DE LOGIN
@router.post("/login")
async def login(
    request: Request,
    credentials: LoginRequest  # Assume que existe
):
    """Login com autenticação JWT + auditoria"""
    
    try:
        # Buscar usuário
        user = await get_user_by_email(credentials.email)
        
        if not user or not await verify_password(credentials.password, user.password_hash):
            # Registrar tentativa falhada
            await audit_logger.log(
                event_type=AuditEventTypes.LOGIN_FAILED,
                user_id=None,
                action="login",
                ip_address=request.client.host,
                details={"email": credentials.email, "reason": "invalid_credentials"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Criar JWT token
        exp = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "exp": exp,
            "iat": datetime.now(timezone.utc),
            "aud": "isp-support-users",
            "iss": "isp-support-system"
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Registrar login bem-sucedido
        await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_SUCCESS,
            user_id=str(user.id),
            action="login",
            ip_address=request.client.host,
            resource_type="user",
            resource_id=str(user.id)
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        await audit_logger.log(
            event_type=AuditEventTypes.LOGIN_FAILED,
            user_id=None,
            action="login",
            ip_address=request.client.host,
            status="error",
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Login error")


# ATUALIZAR ENDPOINT DE LOGOUT
@router.post("/logout")
async def logout(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Logout com revogação de token"""
    
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # Revogar token
    await revoke_token(token)
    
    # Registrar logout
    await audit_logger.log(
        event_type=AuditEventTypes.LOGOUT,
        user_id=current_user.get("sub"),
        action="logout",
        ip_address=request.client.host,
        resource_type="user",
        resource_id=current_user.get("sub")
    )
    
    return {"status": "logged out"}
```

### Passo 2: Atualizar `app/api/endpoints/users.py`

```python
# ADICIONAR NO TOPO
from app.core.dependencies import get_current_user, require_admin
from app.core.audit_logger import audit_logger, AuditEventTypes
import logging

logger = logging.getLogger(__name__)

# PROTEGER ENDPOINT DE LISTAGEM (ADMIN ONLY)
@router.get("/")
async def list_users(
    current_user = Depends(require_admin)  # ← ADICIONAR
):
    """Listar todos usuários (ADMIN ONLY)"""
    
    # Registrar acesso
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_ACCESSED,
        user_id=current_user.get("sub"),
        action="list",
        resource_type="user",
        details={"count": 0}  # Colocar contagem real
    )
    
    # Lógica existente...
    return {"users": []}


# NOVO ENDPOINT: OBTER DADOS DO USUÁRIO ATUAL
@router.get("/me")
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Obter dados do usuário autenticado"""
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_ACCESSED,
        user_id=current_user.get("sub"),
        action="read",
        resource_type="user",
        resource_id=current_user.get("sub")
    )
    
    return current_user


# PROTEGER ATUALIZAÇÃO DE USUÁRIO
@router.put("/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user = Depends(get_current_user),
    request: Request = None
):
    """Atualizar dados do usuário"""
    
    # Validar autorização
    if current_user.get("sub") != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Atualizar usuário
    # ... lógica aqui ...
    
    # Registrar modificação
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_UPDATED,
        user_id=current_user.get("sub"),
        action="update",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request else None,
        details={"fields": list(update_data.dict(exclude_unset=True).keys())}
    )
    
    return {"status": "updated"}
```

### Passo 3: Atualizar `app/api/endpoints/whatsapp.py`

```python
# ADICIONAR NO TOPO
from app.core.dependencies import get_current_user
from app.core.audit_logger import audit_logger, AuditEventTypes
import hmac
import hashlib
from fastapi import Header
import os

# PROTEGER ENDPOINTS NORMAIS COM JWT
@router.get("/status")
async def whatsapp_status(
    current_user = Depends(get_current_user)  # ← PROTEGER
):
    """Status do WhatsApp (PROTEGIDO)"""
    
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_ACCESSED,
        user_id=current_user.get("sub"),
        action="read",
        resource_type="whatsapp",
        resource_id="status"
    )
    
    return {"status": "connected", "connected_at": "2026-02-01"}


# WEBHOOK: ASSINATURA HMAC (SEM JWT, MAS COM VALIDAÇÃO)
@router.post("/webhooks/messages")
async def receive_whatsapp_message(
    body: Dict,
    x_hub_signature_256: str = Header(None),
    request: Request = None
):
    """
    Webhook do WhatsApp - receber mensagens
    
    Sem JWT, mas validação HMAC da Meta
    """
    
    if not x_hub_signature_256:
        logger.warning("Webhook sem assinatura HMAC")
        await audit_logger.log(
            event_type=AuditEventTypes.SECURITY_ALERT,
            user_id=None,
            action="webhook",
            resource_type="whatsapp",
            status="failed",
            details={"reason": "missing_signature"}
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Validar HMAC
    request_body = await request.body()
    expected_signature = hmac.new(
        settings.WHATSAPP_ACCESS_TOKEN.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    expected_header = f"sha256={expected_signature}"
    
    if not hmac.compare_digest(x_hub_signature_256, expected_header):
        logger.warning("Webhook com HMAC inválido")
        await audit_logger.log(
            event_type=AuditEventTypes.SECURITY_ALERT,
            user_id=None,
            action="webhook",
            resource_type="whatsapp",
            status="failed",
            details={"reason": "invalid_signature"}
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # HMAC válido - processar mensagem
    await audit_logger.log(
        event_type=AuditEventTypes.DATA_RECEIVED,
        user_id=None,
        action="webhook",
        resource_type="whatsapp",
        details={"message_count": 1}
    )
    
    # Processar lógica de mensagem...
    
    return {"ok": True}
```

---

## 2️⃣ INTEGRAR RATE LIMITING EM MIDDLEWARE

### Atualizar `app/main.py`

```python
# ADICIONAR NO TOPO
from fastapi.middleware import Middleware
from app.core.rate_limiter import rate_limiter, RateLimitConfig, check_rate_limit
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# CRIAR MIDDLEWARE DE RATE LIMITING
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware que aplica rate limiting automático"""
    
    async def dispatch(self, request, call_next):
        # Endpoints que NÃO recebem rate limit
        exempt_paths = ["/health", "/docs", "/openapi.json"]
        
        if any(request.url.path.startswith(path) for path in exempt_paths):
            return await call_next(request)
        
        # Definir limite por tipo de endpoint
        if request.url.path.startswith("/api/auth/login"):
            config = RateLimitConfig.LOGIN
            identifier = f"login:{request.client.host}"
        elif request.url.path.startswith("/api/whatsapp/webhooks"):
            config = RateLimitConfig.WHATSAPP_WEBHOOK
            identifier = f"webhook:{request.client.host}"
        else:
            config = RateLimitConfig.API_DEFAULT
            identifier = f"api:{request.client.host}"
        
        # Verificar rate limit
        allowed, headers = await check_rate_limit(identifier, config)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers=headers
            )
        
        # Prosseguir com requisição
        response = await call_next(request)
        
        # Adicionar headers de rate limit
        response.headers.update(headers)
        
        return response


# ADICIONAR MIDDLEWARE NA INICIALIZAÇÃO
app = FastAPI(
    middleware=[
        Middleware(RateLimitMiddleware),
        # ... outros middlewares ...
    ]
)

# OU se app já existe:
app.add_middleware(RateLimitMiddleware)
```

---

## 3️⃣ INTEGRAR CRIPTOGRAFIA DE MENSAGENS

### Atualizar `app/models/database.py`

```python
# Adicionar campos para criptografia no modelo Mensagem
from sqlalchemy import Column, String, LargeBinary

class Mensagem(Base):
    __tablename__ = "mensagens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversa_id = Column(UUID(as_uuid=True), ForeignKey("conversas.id"))
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"))
    
    # NOVOS CAMPOS PARA CRIPTOGRAFIA
    conteudo_criptografado = Column(String, nullable=True)  # Base64 do conteúdo
    iv = Column(String, nullable=True)  # Base64 do IV
    tipo_criptografia = Column(String, default="AES-256-CBC")
    
    # Manter para compatibilidade
    conteudo = Column(String, nullable=True)  # Será deprecado
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Atualizar serviço de mensagens

```python
# Em app/services/whatsapp_enterprise.py ou similar

from app.core.encryption import message_encryption

async def create_encrypted_message(
    message_text: str,
    client_id: str,
    conversation_id: str
):
    """Criar mensagem criptografada"""
    
    # Criptografar conteúdo
    encrypted = await message_encryption.encrypt_message(
        message_content=message_text,
        client_id=str(client_id)
    )
    
    # Salvar no BD
    message = Mensagem(
        conversa_id=conversation_id,
        cliente_id=client_id,
        conteudo_criptografado=encrypted["encrypted_content"],
        iv=encrypted["iv"],
        tipo_criptografia=encrypted["algorithm"]
    )
    
    await db.save(message)
    
    return message


async def get_decrypted_message(message_id: str, client_id: str):
    """Recuperar e descriptografar mensagem"""
    
    message = await db.get(Mensagem, message_id)
    
    if not message:
        return None
    
    # Descriptografar
    decrypted = await message_encryption.decrypt_message(
        encrypted_content=message.conteudo_criptografado,
        iv=message.iv,
        client_id=str(client_id)
    )
    
    return decrypted
```

---

## 4️⃣ EXECUTAR TESTES

```bash
# Instalar dependências de teste (se necessário)
pip install pytest pytest-asyncio

# Executar testes da Semana 1
pytest app/tests/test_security_week1.py -v

# Executar com coverage
pytest app/tests/test_security_week1.py --cov=app.core --cov-report=html

# Executar apenas testes de JWT
pytest app/tests/test_security_week1.py::TestJWTAuthentication -v

# Executar apenas testes de rate limiting
pytest app/tests/test_security_week1.py::TestRateLimiting -v

# Executar apenas testes de criptografia
pytest app/tests/test_security_week1.py::TestMessageEncryption -v
```

---

## 5️⃣ CRIAR TABELAS NO BD (Alembic)

```bash
# Criar migration para AuditLog
alembic revision --autogenerate -m "Add audit_log table"

# Criar migration para GDPRRequest
alembic revision --autogenerate -m "Add gdpr_request table"

# Criar migration para campos criptografados em Mensagem
alembic revision --autogenerate -m "Add encryption fields to message"

# Aplicar todas as migrations
alembic upgrade head
```

---

## ✅ CHECKLIST DE INTEGRAÇÃO

- [ ] `app/api/endpoints/auth.py` atualizado com JWT
- [ ] `app/api/endpoints/users.py` protegido com autenticação
- [ ] `app/api/endpoints/whatsapp.py` validando webhooks
- [ ] Middleware de rate limiting adicionado
- [ ] Modelos de BD atualizados
- [ ] Migrations criadas e aplicadas
- [ ] Testes passando (pytest)
- [ ] Login funcionando com JWT
- [ ] Logout revogando token
- [ ] Rate limiting bloqueando requisições excessivas
- [ ] Mensagens sendo criptografadas
- [ ] Auditoria registrando eventos

---

## 🚀 VALIDAÇÃO FINAL

```bash
# 1. Testar login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# 2. Testar endpoint protegido com JWT
TOKEN="seu-token-aqui"
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"

# 3. Testar rate limiting (múltiplas requisições rápidas)
for i in {1..10}; do
  curl -X GET http://localhost:8000/api/users/me \
    -H "Authorization: Bearer $TOKEN"
done

# 4. Testar deleção de dados (GDPR)
curl -X POST http://localhost:8000/api/v1/gdpr/deletion-request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request_type":"deletion"}'
```

---

**Tempo estimado:** 8 horas  
**Dificuldade:** Média  
**Status:** 🔴 Aguardando execução

Execute os passos nesta ordem para melhor integração!
