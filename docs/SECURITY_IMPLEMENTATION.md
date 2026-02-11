# 🔒 Implementação de Segurança

## Visão Geral

Este documento descreve as implementações de segurança aplicadas ao sistema de chat de atendimento.

## ✅ Correções Implementadas

### 1. JWT com Validação Completa

**Arquivo:** `app/core/security.py`

**Melhorias:**
- ✅ Validação de `audience` (aud)
- ✅ Validação de `issuer` (iss)
- ✅ Validação de `jti` (JWT ID único)
- ✅ Verificação de token blacklist
- ✅ Claims obrigatórios: exp, iat, jti, sub

**Uso:**
```python
from app.core.security import security_manager

# Criar token
token = security_manager.create_access_token({
    "sub": user_id,
    "email": user_email,
    "role": user_role
})

# Verificar token
payload = security_manager.verify_token(token)
```

---

### 2. Rate Limiter com Fallback Seguro

**Arquivo:** `app/core/rate_limiter.py`

**Melhorias:**
- ✅ Fallback em memória quando Redis indisponível
- ✅ Thread-safe com locks
- ✅ Não faz bypass de segurança
- ✅ Logging de tentativas excedidas

**Uso:**
```python
from app.core.rate_limiter import RateLimiter

rate_limiter = RateLimiter()

# Verificar rate limit
allowed, remaining = await rate_limiter.is_allowed(
    identifier=f"login:{client_ip}",
    max_requests=5,
    window_seconds=900  # 15 minutos
)

if not allowed:
    raise HTTPException(status_code=429, detail="Too many requests")
```

---

### 3. CORS Seguro

**Arquivo:** `app/main.py`

**Melhorias:**
- ✅ Nunca usa wildcard (*) com credentials
- ✅ Lista específica de origens permitidas
- ✅ Diferentes configurações para dev/prod
- ✅ Headers específicos permitidos

**Configuração:**
```python
# Desenvolvimento
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000"
]

# Produção
allowed_origins = [
    "https://yourdomain.com",
    "https://app.yourdomain.com"
]
```

---

### 4. Security Headers Habilitados

**Arquivo:** `app/main.py`

**Headers Implementados:**
- ✅ Content-Security-Policy (CSP)
- ✅ Strict-Transport-Security (HSTS)
- ✅ X-Frame-Options
- ✅ X-Content-Type-Options
- ✅ X-XSS-Protection
- ✅ Referrer-Policy

---

### 5. Política de Senha Forte

**Arquivo:** `app/core/password_validator.py`

**Requisitos:**
- ✅ Mínimo 12 caracteres (aumentado de 8)
- ✅ Pelo menos 1 letra maiúscula
- ✅ Pelo menos 1 letra minúscula
- ✅ Pelo menos 1 número
- ✅ Pelo menos 1 caractere especial
- ✅ Não pode ser senha comum
- ✅ Não pode conter informações pessoais
- ✅ Não pode ser sequencial
- ✅ Não pode ter muitos caracteres repetidos

**Uso:**
```python
from app.core.password_validator import password_validator

# Validar senha
is_valid, errors = password_validator.validate(
    password="MyP@ssw0rd123",
    user_info={"nome": "João", "email": "joao@example.com"}
)

if not is_valid:
    return {"errors": errors}

# Calcular força
score, level = password_validator.calculate_strength("MyP@ssw0rd123")
# score: 0-100, level: "Very Weak" a "Very Strong"

# Gerar senha forte
strong_password = password_validator.generate_strong_password(length=16)
```

---

### 6. Validação e Sanitização de Input

**Arquivo:** `app/core/input_validator.py`

**Proteções:**
- ✅ Detecção de SQL Injection
- ✅ Detecção de XSS
- ✅ Detecção de Path Traversal
- ✅ Validação de email
- ✅ Validação de telefone
- ✅ Validação de URL
- ✅ Sanitização de HTML
- ✅ Validação de UUID

**Uso:**
```python
from app.core.input_validator import input_validator

# Validar email
is_valid, normalized = input_validator.validate_email("user@example.com")

# Validar telefone
is_valid, normalized = input_validator.validate_phone("+5511999999999", "BR")

# Sanitizar string
safe_text = input_validator.sanitize_string(
    text=user_input,
    max_length=1000,
    allow_html=False
)

# Detectar SQL Injection
if input_validator.detect_sql_injection(user_input):
    raise HTTPException(status_code=400, detail="Invalid input")

# Detectar XSS
if input_validator.detect_xss(user_input):
    raise HTTPException(status_code=400, detail="Invalid input")
```

---

### 7. Segurança de Webhook

**Arquivo:** `app/core/webhook_security.py`

**Proteções:**
- ✅ Verificação de assinatura HMAC-SHA256
- ✅ Proteção contra replay attacks (timestamp)
- ✅ Verificação de nonce
- ✅ Rate limiting específico

**Uso:**
```python
from app.core.webhook_security import verify_webhook
from fastapi import Depends

@app.post("/webhook/whatsapp", dependencies=[Depends(verify_webhook)])
async def whatsapp_webhook(request: Request):
    # Payload já verificado e disponível em request.state
    payload = request.state.webhook_payload
    return {"status": "ok"}
```

**Verificação Manual:**
```python
from app.core.webhook_security import webhook_security

is_valid, error, payload = await webhook_security.verify_webhook_request(
    request,
    require_signature=True,
    require_timestamp=True
)

if not is_valid:
    raise HTTPException(status_code=401, detail=error)
```

---

## 📋 Configurações Necessárias

### Variáveis de Ambiente (.env)

```bash
# Segurança - JWT
SECRET_KEY="gere-uma-chave-forte-de-32-caracteres-ou-mais"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60  # Reduzido de 1440 para 60

# Segurança - Senha
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true
PASSWORD_HISTORY_COUNT=5
PASSWORD_EXPIRY_DAYS=90

# Segurança - Sessão
SESSION_ABSOLUTE_TIMEOUT_HOURS=1  # Reduzido de 24 para 1
SESSION_IDLE_TIMEOUT_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_MINUTES=15

# Segurança - Criptografia
MASTER_ENCRYPTION_KEY="gere-outra-chave-forte-diferente-do-jwt"
ENCRYPTION_SALT="gere-um-salt-unico"

# WhatsApp - Webhook
WHATSAPP_APP_SECRET="seu-app-secret-do-facebook"
WHATSAPP_WEBHOOK_VERIFY_TOKEN="token-aleatorio-forte"
```

### Gerar Chaves Seguras

```python
import secrets

# Gerar SECRET_KEY
print(secrets.token_urlsafe(32))

# Gerar MASTER_ENCRYPTION_KEY
print(secrets.token_urlsafe(32))

# Gerar ENCRYPTION_SALT
print(secrets.token_urlsafe(16))

# Gerar WEBHOOK_VERIFY_TOKEN
print(secrets.token_urlsafe(32))
```

---

## 🔐 Boas Práticas Implementadas

### 1. Princípio do Menor Privilégio
- Usuários têm apenas permissões necessárias
- Roles hierárquicos: admin > supervisor > atendente

### 2. Defesa em Profundidade
- Múltiplas camadas de segurança
- Validação em frontend E backend
- Rate limiting em múltiplos níveis

### 3. Fail Secure
- Rate limiter não faz bypass quando Redis cai
- Validações sempre ativas
- Erros não expõem informações sensíveis

### 4. Logging e Auditoria
- Todas ações sensíveis são logadas
- Tentativas de ataque são registradas
- Logs estruturados para análise

### 5. Criptografia
- Senhas com bcrypt (12 rounds)
- JWT com assinatura HMAC-SHA256
- Dados sensíveis criptografados em repouso

---

## 🧪 Testes de Segurança

### Testar Rate Limiting

```python
import asyncio
from app.core.rate_limiter import RateLimiter

async def test_rate_limit():
    limiter = RateLimiter()
    
    # Fazer 10 requisições
    for i in range(10):
        allowed, remaining = await limiter.is_allowed(
            identifier="test:user",
            max_requests=5,
            window_seconds=60
        )
        print(f"Request {i+1}: allowed={allowed}, remaining={remaining}")

asyncio.run(test_rate_limit())
```

### Testar Validação de Senha

```python
from app.core.password_validator import password_validator

# Senha fraca
is_valid, errors = password_validator.validate("123456")
print(f"Weak password: {errors}")

# Senha forte
is_valid, errors = password_validator.validate("MyStr0ng!P@ssw0rd")
print(f"Strong password: valid={is_valid}")

# Calcular força
score, level = password_validator.calculate_strength("MyStr0ng!P@ssw0rd")
print(f"Strength: {score}/100 ({level})")
```

### Testar Webhook Signature

```python
from app.core.webhook_security import webhook_security
import json

payload = json.dumps({"test": "data"}).encode()
secret = "your-app-secret"

# Gerar assinatura
signature = webhook_security.generate_webhook_signature(payload, secret)
print(f"Signature: {signature}")

# Verificar assinatura
is_valid = webhook_security.verify_whatsapp_signature(payload, signature, secret)
print(f"Valid: {is_valid}")
```

---

## 📊 Métricas de Segurança

### Monitorar

1. **Taxa de tentativas de login falhadas**
   - Alerta se > 10 por minuto

2. **Rate limit excedido**
   - Alerta se > 100 por minuto

3. **Tokens revogados**
   - Monitorar uso de tokens na blacklist

4. **Webhooks com assinatura inválida**
   - Alerta imediato

5. **Detecção de ataques**
   - SQL Injection attempts
   - XSS attempts
   - Path traversal attempts

---

## 🚀 Próximos Passos

### Curto Prazo (1-2 semanas)
- [ ] Implementar criptografia de mensagens em repouso
- [ ] Adicionar 2FA (autenticação de dois fatores)
- [ ] Implementar CSRF tokens
- [ ] Adicionar testes automatizados de segurança

### Médio Prazo (1-2 meses)
- [ ] Implementar WAF (Web Application Firewall)
- [ ] Adicionar IDS/IPS
- [ ] Implementar SIEM
- [ ] Penetration testing profissional

### Longo Prazo (3-6 meses)
- [ ] Certificação ISO 27001
- [ ] Bug bounty program
- [ ] Security Operations Center (SOC)
- [ ] Compliance LGPD/GDPR completo

---

## 📚 Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [WhatsApp Business API Security](https://developers.facebook.com/docs/whatsapp/business-management-api/webhooks)

---

**Última Atualização:** 2024
**Responsável:** Equipe de Segurança
