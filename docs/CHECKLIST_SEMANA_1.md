# ✅ CHECKLIST DE IMPLEMENTAÇÃO - SEMANA 1

**Data de Início:** 1 de Fevereiro de 2026  
**Objetivo:** Implementar 5 módulos críticos de segurança  
**Status:** 🔄 EM PROGRESSO

---

## 📦 MÓDULOS CRIADOS

### 1️⃣ DEPENDÊNCIAS JWT (`app/core/dependencies.py`)

- [x] Criar arquivo
- [x] Implementar `get_current_user()` - extrair e validar JWT
- [x] Implementar `require_admin()` - validar role admin
- [x] Implementar `require_role()` - factory para múltiplas roles
- [x] Implementar `revoke_token()` - blacklist via Redis
- [x] Implementar `get_optional_user()` - autenticação opcional
- [x] Adicionar logging detalhado
- [x] Documentação com exemplos de uso

**Próximos passos:**
- [ ] Atualizar `/app/api/endpoints/auth.py` para usar
- [ ] Atualizar `/app/api/endpoints/users.py` para usar
- [ ] Atualizar `/app/api/endpoints/whatsapp.py` para webhook validation
- [ ] Atualizar `/app/api/endpoints/conversations.py` para usar
- [ ] Testar em staging

---

### 2️⃣ RATE LIMITING (`app/core/rate_limiter.py`)

- [x] Criar arquivo
- [x] Implementar `RateLimiter` com sliding window
- [x] Implementar `RateLimitConfig` com presets
- [x] Implementar `get_identifier_by_type()` para IP/usuário/endpoint
- [x] Implementar `check_rate_limit()` com headers
- [x] Adicionar tipos: LOGIN, PASSWORD_RESET, API_DEFAULT, WHATSAPP, AI, WEBHOOK
- [x] Adicionar logging com métricas
- [x] Documentação

**Próximos passos:**
- [ ] Criar middleware que aplica rate limit automático
- [ ] Configurar limites por endpoint em `main.py`
- [ ] Testar com ferramentas de carga (locust, wrk)
- [ ] Validar headers X-RateLimit-*
- [ ] Integrar com observabilidade

---

### 3️⃣ CRIPTOGRAFIA (`app/core/encryption.py`)

- [x] Criar arquivo
- [x] Implementar `MessageEncryption` com AES-256-CBC
- [x] Implementar derivação de chave PBKDF2 per-cliente
- [x] Implementar `encrypt_message()` com IV aleatório
- [x] Implementar `decrypt_message()` com validação
- [x] Implementar `SensitiveDataEncryption` para dados genéricos
- [x] Adicionar tratamento de exceções robusto
- [x] Documentação com exemplos

**Próximos passos:**
- [ ] Integrar em `/app/services/whatsapp_enterprise.py`
- [ ] Atualizar modelo `Mensagem` para campos criptografados
- [ ] Criar job de re-encryption para mensagens antigas
- [ ] Implementar key rotation (90 dias)
- [ ] Testar decriptografia com cliente errado (deve falhar)

---

### 4️⃣ AUDITORIA (`app/core/audit_logger.py`)

- [x] Criar arquivo
- [x] Implementar `AuditLogger` com hash chaining
- [x] Implementar cálculo SHA256 com integridade
- [x] Implementar `log()` para criar entradas
- [x] Implementar `verify_chain()` para validar integridade
- [x] Adicionar constantes `AuditEventTypes`
- [x] Adicionar constantes `AuditActions`
- [x] Adicionar constantes `AuditResourceTypes`
- [x] Adicionar helpers: `log_data_access()`, `log_data_modification()`, `log_security_event()`
- [x] Documentação

**Próximos passos:**
- [ ] Criar tabela `AuditLog` em `app/models/database.py`
- [ ] Integrar em todos endpoints (via decorators)
- [ ] Enviar para ELK Stack (Elasticsearch)
- [ ] Criar reports de auditoria
- [ ] Configurar retenção de 2 anos
- [ ] Criar dashboards Kibana para análise

---

### 5️⃣ GDPR/LGPD (`app/api/endpoints/gdpr.py`)

- [x] Criar arquivo
- [x] Implementar endpoint `/api/v1/gdpr/deletion-request` (direito ao esquecimento)
- [x] Implementar endpoint `/api/v1/gdpr/confirm-deletion/{token}` (confirmar deleção)
- [x] Implementar endpoint `/api/v1/gdpr/data-export` (portabilidade)
- [x] Implementar endpoint `/api/v1/gdpr/download/{token}` (download exportado)
- [x] Implementar endpoint `/api/v1/gdpr/requests` (listar requisições)
- [x] Implementar endpoint `/api/v1/gdpr/status/{request_id}` (obter status)
- [x] Implementar endpoint `/api/v1/gdpr/admin/cleanup-expired-backups` (admin)
- [x] Adicionar modelos Pydantic
- [x] Adicionar logging de eventos GDPR
- [x] Documentação com exemplos
- [x] Registrar router em `app/api/routes.py`

**Próximos passos:**
- [ ] Criar tabela `GDPRRequest` em `app/models/database.py`
- [ ] Criar tabela `UserConsent` para rastreamento de consentimento
- [ ] Implementar serviço de envio de email com confirmação
- [ ] Implementar tokens seguros (JWT com expiração)
- [ ] Implementar backup isolado (90 dias)
- [ ] Implementar pseudonymization
- [ ] Testar fluxo completo de deleção
- [ ] Testar fluxo completo de exportação

---

## 📝 ARQUIVOS ALTERADOS

### `app/api/routes.py`
- [x] Adicionar import de `gdpr`
- [x] Adicionar `api_router.include_router(gdpr.router)`

### AGUARDANDO ALTERAÇÕES

- [ ] `app/main.py` - adicionar middleware de rate limiting
- [ ] `app/models/database.py` - adicionar modelos AuditLog, GDPRRequest, UserConsent
- [ ] `app/api/endpoints/auth.py` - usar `get_current_user`, adicionar auditoria
- [ ] `app/api/endpoints/users.py` - usar `require_admin`, adicionar auditoria
- [ ] `app/api/endpoints/whatsapp.py` - adicionar webhook validation, usar `get_current_user`
- [ ] `app/api/endpoints/conversations.py` - usar `get_current_user`, auditar acesso
- [ ] `app/services/whatsapp_enterprise.py` - integrar criptografia de mensagens
- [ ] `app/services/chatbot_ai.py` - usar auditoria

---

## 🧪 TESTES

### Arquivo Criado: `app/tests/test_security_week1.py`

- [x] Testes JWT (criar, decodificar, expirado, assinatura inválida)
- [x] Testes Rate Limiting (permitir, exceder, configs)
- [x] Testes Criptografia (encrypt/decrypt, clientes diferentes, corrupted)
- [x] Testes Auditoria (criar entrada, hash integrity, verify chain)
- [x] Teste de integração (autenticação + rate limit)

**Status:** 🔴 AGUARDANDO EXECUÇÃO

```bash
# Executar testes
pytest app/tests/test_security_week1.py -v

# Executar com coverage
pytest app/tests/test_security_week1.py --cov=app.core --cov-report=html

# Executar testes de auditoria específicos
pytest app/tests/test_security_week1.py::TestAuditLogger -v
```

---

## 🚀 PRÓXIMOS PASSOS ORDENADOS

### HOJE (1º dia)

- [x] Criar os 5 módulos principais
- [ ] Executar testes `test_security_week1.py`
- [ ] Validar que todos os imports funcionam
- [ ] Revisar código com linting (pylint, black)

### AMANHÃ (2º dia)

- [ ] Atualizar modelos em `app/models/database.py`
- [ ] Criar migrations Alembic para novas tabelas
- [ ] Integrar dependências em endpoints de autenticação
- [ ] Testar fluxo de login com JWT

### 3º dia

- [ ] Integrar rate limiting em todos endpoints
- [ ] Integrar auditoria em endpoints críticos
- [ ] Testar proteção contra brute force

### 4º dia

- [ ] Integrar criptografia de mensagens
- [ ] Testar encrypt/decrypt em serviço
- [ ] Planejar job de re-encryption

### 5º dia

- [ ] Implementar endpoints GDPR completamente
- [ ] Testar fluxo de deleção
- [ ] Testar fluxo de exportação
- [ ] Revisar compliance LGPD

---

## 📊 MÉTRICAS DE SUCESSO

```
✅ Todos 5 módulos funcionando
✅ Taxa de cobertura de testes: >80%
✅ Zero erros de segurança conhecidos
✅ Endpoints privados todos protegidos
✅ Rate limiting funcionando em produção
✅ Mensagens criptografadas no BD
✅ Auditoria registrando 100% dos eventos
✅ GDPR endpoints respondendo corretamente
```

---

## 🔐 VALIDAÇÕES DE SEGURANÇA

### Checklist de Segurança

- [ ] JWT tokens contêm `aud` (audience) e `iss` (issuer)
- [ ] JWT tokens tem expiração (exp)
- [ ] Tokens revogados são verificados em Redis
- [ ] Rate limiting protege contra brute force (5 tentativas/15min)
- [ ] Mensagens são criptografadas com AES-256
- [ ] Cada cliente tem chave única derivada via PBKDF2
- [ ] IV é aleatório por mensagem (não reutilizado)
- [ ] Auditoria usa hash chaining (blockchain-like)
- [ ] GDPR endpoints requerem confirmação por email
- [ ] Backups isolados por 90 dias após deleção
- [ ] Sem dados em claro em logs (sanitização)

---

## 📋 STATUS GERAL

| Tarefa | Status | Notas |
|--------|--------|-------|
| Dependências JWT | ✅ Completo | Pronto para integração |
| Rate Limiter | ✅ Completo | Pronto para integração |
| Criptografia | ✅ Completo | Pronto para integração |
| Auditoria | ✅ Completo | Pronto para integração |
| GDPR/LGPD | ✅ Completo | Endpoints criados |
| Testes | ✅ Criado | Aguardando execução |
| Integração | 🔄 Em Progresso | Começar amanhã |

---

**Última atualização:** 1 de Fevereiro de 2026  
**Responsável:** GitHub Copilot  
**Timeline:** 40 horas (1 semana com 1 dev em tempo integral)
