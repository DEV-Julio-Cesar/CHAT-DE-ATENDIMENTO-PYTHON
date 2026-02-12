# 🔒 Guia de Segurança

## Implementações de Segurança

### ✅ Implementado

#### 1. Criptografia de Dados em Repouso
- **Algoritmo:** AES-256-GCM
- **Uso:** Mensagens de clientes criptografadas no banco
- **Arquivo:** `app/core/encryption.py`

```python
from app.core.encryption import encrypt_data, decrypt_data

# Criptografar
encrypted = encrypt_data("Dados sensíveis")

# Descriptografar
decrypted = decrypt_data(encrypted)
```

#### 2. Validação de CPF/CNPJ
- **Validação:** Dígitos verificadores
- **Arquivo:** `app/core/validators.py`

```python
from app.core.validators import validar_cpf

if validar_cpf("07013042439"):
    print("CPF válido")
```

#### 3. Headers de Segurança
- **CSP:** Content Security Policy
- **HSTS:** Strict Transport Security
- **X-Frame-Options:** DENY
- **X-Content-Type-Options:** nosniff
- **X-XSS-Protection:** 1; mode=block

#### 4. Rate Limiting
- **Login:** 3 tentativas em 15 minutos
- **API:** 100 requisições por minuto
- **Password Reset:** 2 tentativas em 1 hora

#### 5. CORS Seguro
- **Desenvolvimento:** Apenas localhost
- **Produção:** Lista específica de domínios
- **Nunca:** Wildcard (*) com credentials

#### 6. Autenticação JWT
- **Algoritmo:** HS256 (migrar para RS256)
- **Expiração:** 24 horas
- **Blacklist:** Tokens revogados em Redis

#### 7. Secrets Manager
- **Suporte:** AWS, Vault, Azure, Local
- **Arquivo:** `app/core/secrets_manager.py`

---

## Verificação de Segurança

### Executar Verificação

```bash
python scripts/security_check.py
```

**Resultado esperado:**
```
🔒 VERIFICAÇÃO DE SEGURANÇA
✅ Headers de Segurança
✅ Configuração CORS
✅ Rate Limiting
✅ Criptografia
✅ Validadores
✅ Secrets
✅ JWT

🎯 Score: 7/7 (100%)
🎉 Todas as verificações passaram!
```

---

## Checklist de Segurança

### Desenvolvimento
- [ ] .env no .gitignore
- [ ] DEBUG=True apenas local
- [ ] CORS permite localhost
- [ ] Secrets em .env local

### Produção
- [ ] DEBUG=False
- [ ] CORS lista específica
- [ ] Secrets Manager (AWS/Vault/Azure)
- [ ] HTTPS obrigatório
- [ ] SESSION_COOKIE_SECURE=True
- [ ] Rate limiting habilitado
- [ ] Logs não expõem credenciais
- [ ] Backup criptografado
- [ ] 2FA para admins
- [ ] Monitoramento de segurança

---

## Vulnerabilidades Corrigidas

### 🔴 Críticas
1. ✅ Validação de CPF (dígitos verificadores)
2. ✅ Token em URL removido (agora em header)
3. ✅ CORS sem wildcard
4. ✅ Rate limiting rigoroso (3 tentativas)
5. ✅ Criptografia de mensagens (AES-256-GCM)

### 🟠 Altas
6. ✅ Timeout em requisições externas
7. ✅ Logs não expõem credenciais
8. ✅ Dependências atualizadas
9. ✅ Headers de segurança habilitados
10. ✅ Merge conflict resolvido

---

## Próximas Melhorias

### Curto Prazo
1. **Migrar JWT para RS256**
   - Gerar par de chaves pública/privada
   - Atualizar configuração

2. **Implementar 2FA**
   - TOTP com QR code
   - Obrigatório para admins

3. **Adicionar WAF**
   - ModSecurity ou Cloudflare
   - Proteção contra OWASP Top 10

### Médio Prazo
4. **Detecção de Anomalias**
   - IP diferente do usual
   - Horário suspeito
   - Múltiplos logins

5. **Auditoria Avançada**
   - Rastreamento completo
   - Logs imutáveis
   - Compliance LGPD

---

## Contato de Segurança

**Reportar Vulnerabilidade:**
- Email: security@yourdomain.com
- PGP Key: [link]

**Política de Divulgação:**
- Resposta em 24 horas
- Correção em 7 dias (críticas)
- Crédito ao pesquisador

---

## Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework/)
- [LGPD](https://www.gov.br/cidadania/pt-br/acesso-a-informacao/lgpd)
