# 🔒 Security Headers - Proteção HTTP Avançada

## Visão Geral

Implementação profissional de headers de segurança HTTP para proteção contra ataques web comuns como XSS, Clickjacking, MIME sniffing e outros.

## Headers Implementados

| Header | Proteção | Status |
|--------|----------|--------|
| Content-Security-Policy (CSP) | XSS, Injeção de código | ✅ |
| Strict-Transport-Security (HSTS) | Man-in-the-Middle | ✅ |
| X-Frame-Options | Clickjacking | ✅ |
| X-Content-Type-Options | MIME sniffing | ✅ |
| X-XSS-Protection | XSS (legacy) | ✅ |
| Referrer-Policy | Vazamento de referrer | ✅ |
| Permissions-Policy | APIs do browser | ✅ |
| Cross-Origin-Embedder-Policy | Spectre attacks | ✅ |
| Cross-Origin-Opener-Policy | Cross-origin attacks | ✅ |
| Cross-Origin-Resource-Policy | Cross-origin reads | ✅ |

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Security Headers Middleware                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │  Request   │───►│  Middleware     │───►│  Adicionar Headers          │   │
│  │  HTTP      │    │  Intercepta     │    │                              │   │
│  └────────────┘    └─────────────────┘    │  ┌───────────────────────┐  │   │
│                                           │  │ HSTS                   │  │   │
│                                           │  │ CSP                    │  │   │
│                                           │  │ X-Frame-Options        │  │   │
│                                           │  │ X-Content-Type-Options │  │   │
│                                           │  │ Referrer-Policy        │  │   │
│                                           │  │ Permissions-Policy     │  │   │
│                                           │  │ COEP/COOP/CORP         │  │   │
│                                           │  │ Cache-Control          │  │   │
│                                           │  │ X-Request-ID           │  │   │
│                                           │  └───────────────────────┘  │   │
│                                           └──────────────┬──────────────┘   │
│                                                          │                   │
│  ┌────────────┐    ┌─────────────────┐                   │                   │
│  │  Response  │◄───│  Headers        │◄──────────────────┘                   │
│  │  HTTP      │    │  Aplicados      │                                       │
│  └────────────┘    └─────────────────┘                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Configurações Pré-definidas (Presets)

### 1. Strict (Máxima Segurança)
```python
from app.core.security_headers import SecurityPresets

config = SecurityPresets.strict()
# - HSTS: 2 anos + preload
# - CSP: Sem unsafe-inline/unsafe-eval
# - Frame: DENY
# - COEP/COOP: Habilitados
```

### 2. Moderate (Balanceado)
```python
config = SecurityPresets.moderate()
# - HSTS: 1 ano
# - CSP: Permite unsafe-inline (para compatibilidade)
# - Frame: SAMEORIGIN
# - COEP: Desabilitado
```

### 3. Relaxed (Desenvolvimento)
```python
config = SecurityPresets.relaxed()
# - HSTS: Desabilitado
# - CSP: Report-only
# - Permissivo para testes
```

### 4. API Only (APIs REST)
```python
config = SecurityPresets.api_only()
# - Sem CSP (não necessário para APIs)
# - Cache desabilitado
# - Headers mínimos
```

### 5. Telecom ISP (Personalizado)
```python
config = SecurityPresets.telecom_isp()
# - Permite WhatsApp e integrações
# - HSTS habilitado
# - CSP customizado para telecomunicações
```

## Headers Detalhados

### Content-Security-Policy (CSP)

Controla quais recursos podem ser carregados:

```
Content-Security-Policy: 
    default-src 'self';
    script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;
    style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
    img-src 'self' data: https: blob: https://*.whatsapp.net;
    font-src 'self' https://fonts.gstatic.com;
    connect-src 'self' wss: https: https://graph.facebook.com;
    frame-ancestors 'self';
    form-action 'self';
    base-uri 'self'
```

#### Diretivas CSP

| Diretiva | Descrição |
|----------|-----------|
| `default-src` | Fonte padrão para recursos |
| `script-src` | Scripts JavaScript |
| `style-src` | Folhas de estilo CSS |
| `img-src` | Imagens |
| `font-src` | Fontes |
| `connect-src` | Conexões (fetch, WebSocket) |
| `frame-ancestors` | Quem pode embutir a página |
| `form-action` | Destinos de formulários |

### Strict-Transport-Security (HSTS)

Força uso de HTTPS:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `max-age` | 31536000 | 1 ano em segundos |
| `includeSubDomains` | - | Aplica a subdomínios |
| `preload` | - | Elegível para lista preload |

### X-Frame-Options

Previne clickjacking:

```
X-Frame-Options: DENY
```

| Valor | Descrição |
|-------|-----------|
| `DENY` | Não pode ser embutido em frames |
| `SAMEORIGIN` | Apenas mesmo origem |
| `ALLOW-FROM uri` | Permite URI específica (obsoleto) |

### Permissions-Policy

Controla APIs do navegador:

```
Permissions-Policy: 
    camera=(),
    microphone=(),
    geolocation=(),
    payment=(),
    fullscreen=(self),
    autoplay=(self)
```

## Uso

### Configuração Básica

```python
from fastapi import FastAPI
from app.core.security_headers import SecurityHeadersMiddleware, SecurityPresets

app = FastAPI()

# Usar preset para ISP
app.add_middleware(
    SecurityHeadersMiddleware,
    config=SecurityPresets.telecom_isp()
)
```

### Configuração Customizada

```python
from app.core.security_headers import SecurityHeadersConfig

config = SecurityHeadersConfig(
    hsts_enabled=True,
    hsts_max_age=31536000,
    csp_enabled=True,
    csp_directives={
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://meucdn.com"],
        "img-src": ["'self'", "https://imagens.com"],
    },
    frame_options_value="SAMEORIGIN",
    custom_headers={
        "X-Custom-Header": "valor"
    }
)

app.add_middleware(SecurityHeadersMiddleware, config=config)
```

### Usando Nonce para Scripts Inline

```python
# No template HTML
@app.get("/page")
async def page(request: Request):
    nonce = request.state.csp_nonce
    return templates.TemplateResponse(
        "page.html",
        {"request": request, "nonce": nonce}
    )
```

```html
<!-- No HTML -->
<script nonce="{{ nonce }}">
    // Script inline seguro
    console.log("Permitido pelo CSP");
</script>
```

### Request ID para Rastreamento

```python
@app.get("/api/data")
async def get_data(request: Request):
    request_id = request.state.request_id
    # Usar para logs, rastreamento, etc.
    logger.info("Processing request", request_id=request_id)
    return {"data": "..."}
```

## Relatórios CSP

### Configurar Report URI

```python
config = SecurityHeadersConfig(
    csp_enabled=True,
    csp_report_uri="/api/v1/csp-report"
)
```

### Endpoint de Relatório

O endpoint `/api/v1/csp-report` recebe automaticamente violações CSP:

```json
{
    "csp-report": {
        "blocked-uri": "https://malicious.com/script.js",
        "violated-directive": "script-src",
        "original-policy": "script-src 'self'",
        "document-uri": "https://seusite.com/page"
    }
}
```

## Verificação

### Ferramentas Online

- [Security Headers](https://securityheaders.com/)
- [Mozilla Observatory](https://observatory.mozilla.org/)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)

### Via cURL

```bash
# Verificar headers
curl -I https://seudominio.com/api/health

# Resposta esperada
HTTP/2 200
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
content-security-policy: default-src 'self'; ...
permissions-policy: camera=(), microphone=(), ...
cross-origin-opener-policy: same-origin
cross-origin-resource-policy: same-site
```

## Testes

```bash
# Executar testes
pytest app/tests/test_security_headers.py -v

# Com cobertura
pytest app/tests/test_security_headers.py -v --cov=app/core/security_headers
```

## Boas Práticas

### ✅ Fazer

1. **Usar HSTS em produção** - Sempre force HTTPS
2. **CSP restritivo** - Começar restritivo, relaxar se necessário
3. **Testar em report-only** - Antes de bloquear, monitore
4. **Atualizar regularmente** - Revisar políticas periodicamente
5. **Documentar exceções** - Justificar qualquer relaxamento

### ❌ Evitar

1. **`unsafe-inline` sem nonce** - Use nonces quando possível
2. **`unsafe-eval`** - Evitar em produção
3. **HSTS curto** - Usar pelo menos 1 ano
4. **Wildcards em CSP** - Ser específico com domínios
5. **Desabilitar em produção** - Nunca desabilitar headers de segurança

## Troubleshooting

### CSP bloqueando recursos legítimos

1. Verificar console do navegador (F12)
2. Adicionar domínio à diretiva apropriada
3. Usar CSP Report-Only para testar

### HSTS causando problemas

1. Verificar certificado SSL válido
2. Reduzir max-age para testes
3. Limpar HSTS do navegador se necessário

### Recursos externos não carregando

1. Adicionar domínio ao `connect-src` (para fetch/XHR)
2. Adicionar ao `img-src`, `font-src`, etc. conforme tipo
3. Verificar CORS se necessário

## Referências

- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security)
- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)
- [Content Security Policy](https://content-security-policy.com/)
- [HSTS Preload List](https://hstspreload.org/)
