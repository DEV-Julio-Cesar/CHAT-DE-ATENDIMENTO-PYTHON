# 📱 WhatsApp Enterprise Integration - Meta Business API

## Visão Geral

Sistema completo de integração com a API do WhatsApp Business (Meta Cloud API) para comunicação profissional com clientes.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WhatsApp Enterprise System                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐   │
│  │   Cliente    │◄──►│  Meta Cloud  │◄──►│  Nossa API (FastAPI)         │   │
│  │  WhatsApp    │    │  API         │    │                               │   │
│  └──────────────┘    └──────────────┘    │  ┌─────────────────────────┐ │   │
│                                          │  │ WhatsApp Webhook        │ │   │
│                                          │  │ - Recebe mensagens      │ │   │
│                                          │  │ - Verifica assinaturas  │ │   │
│                                          │  │ - Processa eventos      │ │   │
│                                          │  └─────────────────────────┘ │   │
│                                          │                               │   │
│                                          │  ┌─────────────────────────┐ │   │
│                                          │  │ WhatsApp Enterprise API │ │   │
│                                          │  │ - Envia mensagens       │ │   │
│                                          │  │ - Upload de mídia       │ │   │
│                                          │  │ - Templates             │ │   │
│                                          │  │ - Mensagens interativas │ │   │
│                                          │  └─────────────────────────┘ │   │
│                                          └──────────────────────────────┘   │
│                                                       │                      │
│                                                       ▼                      │
│                                          ┌──────────────────────────────┐   │
│                                          │  Integrações                 │   │
│                                          │  ┌──────┐ ┌─────┐ ┌───────┐  │   │
│                                          │  │Redis │ │AI   │ │WebSock│  │   │
│                                          │  │Cache │ │Bot  │ │et     │  │   │
│                                          │  └──────┘ └─────┘ └───────┘  │   │
│                                          └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Funcionalidades

### ✅ Tipos de Mensagens Suportados

| Tipo | Descrição | Método |
|------|-----------|--------|
| 📝 Texto | Mensagens de texto simples | `send_text_message()` |
| 🖼️ Imagem | Fotos e imagens | `send_image()` |
| 📄 Documento | PDFs, documentos | `send_document()` |
| 🎵 Áudio | Mensagens de voz | `send_audio()` |
| 🎬 Vídeo | Vídeos | `send_video()` |
| 📍 Localização | Enviar localização | `send_location()` |
| 👤 Contato | Compartilhar contatos | `send_contacts()` |
| 😀 Reação | Reagir a mensagens | `send_reaction()` |
| 🔘 Botões | Mensagens com botões | `send_button_message()` |
| 📋 Lista | Menus com opções | `send_list_message()` |
| 📐 Template | Templates aprovados | `send_template()` |

### ✅ Recursos de Webhook

- Verificação de webhook (GET)
- Recebimento de mensagens (POST)
- Verificação de assinatura SHA256
- Processamento de status de mensagens
- Suporte a mensagens interativas

### ✅ Templates Pré-Definidos

```python
from app.services.whatsapp_enterprise import TemplateLibrary

# Boas-vindas
TemplateLibrary.WELCOME

# Fatura disponível
TemplateLibrary.INVOICE_READY

# Lembrete de pagamento
TemplateLibrary.PAYMENT_REMINDER

# Confirmação de serviço
TemplateLibrary.SERVICE_CONFIRMATION

# Status do atendimento
TemplateLibrary.SUPPORT_STATUS
```

## Configuração

### 1. Configuração do Meta Business

1. Acesse [Meta for Developers](https://developers.facebook.com/)
2. Crie um App do tipo "Business"
3. Adicione o produto "WhatsApp"
4. Configure o número de telefone
5. Obtenha as credenciais

### 2. Variáveis de Ambiente

```bash
# .env
WHATSAPP_ACCESS_TOKEN="EAAxxxxxxxx..."
WHATSAPP_PHONE_NUMBER_ID="123456789012345"
WHATSAPP_WEBHOOK_VERIFY_TOKEN="meu_token_secreto"
WHATSAPP_BUSINESS_ACCOUNT_ID="987654321098765"
WHATSAPP_APP_SECRET="abcdef123456..."
WHATSAPP_API_VERSION="v18.0"
```

### 3. Configurar Webhook no Meta

No painel do Meta for Developers:

1. Vá em **WhatsApp > Configuration**
2. Configure a URL do webhook: `https://seudominio.com/api/v1/whatsapp/webhook`
3. Use o mesmo `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
4. Inscreva nos campos: `messages`

## Uso da API

### Inicialização

```python
from app.services.whatsapp_enterprise import get_whatsapp_api

# O serviço é singleton e inicializa automaticamente
api = get_whatsapp_api()
await api.initialize()
```

### Enviar Mensagem de Texto

```python
result = await api.send_text_message(
    to="5511999999999",
    text="Olá! Como posso ajudar?"
)
print(f"Message ID: {result['message_id']}")
```

### Enviar Mensagem com Botões

```python
result = await api.send_button_message(
    to="5511999999999",
    body_text="Escolha uma opção:",
    buttons=[
        {"id": "opt_1", "title": "Ver Fatura"},
        {"id": "opt_2", "title": "Suporte Técnico"},
        {"id": "opt_3", "title": "Falar com Atendente"}
    ],
    header_text="Menu Principal"
)
```

### Enviar Lista de Opções

```python
result = await api.send_list_message(
    to="5511999999999",
    body_text="Selecione o serviço desejado:",
    button_text="Ver Opções",
    sections=[
        {
            "title": "Financeiro",
            "rows": [
                {"id": "fat_1", "title": "2ª Via de Fatura", "description": "Receba sua fatura por WhatsApp"},
                {"id": "fat_2", "title": "Código de Barras", "description": "Copie o código para pagamento"}
            ]
        },
        {
            "title": "Suporte",
            "rows": [
                {"id": "sup_1", "title": "Problema de Conexão", "description": "Internet lenta ou sem conexão"},
                {"id": "sup_2", "title": "Visita Técnica", "description": "Agendar visita de técnico"}
            ]
        }
    ]
)
```

### Enviar Template

```python
from app.services.whatsapp_enterprise import TemplateLibrary

# Template de fatura
template = TemplateLibrary.INVOICE_READY
template.components[0]["parameters"] = [
    {"type": "text", "text": "João Silva"},
    {"type": "text", "text": "R$ 99,90"},
    {"type": "text", "text": "15/01/2025"}
]

result = await api.send_template(
    to="5511999999999",
    template=template
)
```

### Enviar Imagem

```python
result = await api.send_image(
    to="5511999999999",
    image_url="https://exemplo.com/fatura.png",
    caption="Sua fatura de janeiro"
)
```

### Enviar Documento

```python
result = await api.send_document(
    to="5511999999999",
    document_url="https://exemplo.com/contrato.pdf",
    filename="contrato.pdf",
    caption="Seu contrato de serviço"
)
```

## Endpoints da API

### Webhook

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/whatsapp/webhook` | Verificação do webhook |
| POST | `/api/v1/whatsapp/webhook` | Receber eventos |

### Envio de Mensagens

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/whatsapp/send/text` | Enviar texto |
| POST | `/api/v1/whatsapp/send/template` | Enviar template |
| POST | `/api/v1/whatsapp/send/buttons` | Enviar botões |
| POST | `/api/v1/whatsapp/send/image` | Enviar imagem |
| POST | `/api/v1/whatsapp/send/document` | Enviar documento |

### Gerenciamento de Fila

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/whatsapp/queue/pending` | Fila de atendimento |
| POST | `/api/v1/whatsapp/queue/{phone}/assign` | Atribuir a atendente |
| POST | `/api/v1/whatsapp/queue/{phone}/close` | Encerrar conversa |

### Histórico

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/whatsapp/conversations/{phone}/history` | Histórico de mensagens |

## Fluxo de Atendimento

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Fluxo de Mensagem Recebida                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────────────────────────────┐  │
│  │ Cliente │───►│ Webhook │───►│ Verificar Assinatura             │  │
│  │ envia   │    │ recebe  │    │ (SHA256 HMAC)                    │  │
│  │ mensagem│    │ evento  │    └──────────────┬──────────────────┘  │
│  └─────────┘    └─────────┘                   │                      │
│                                               ▼                      │
│                              ┌────────────────────────────────────┐  │
│                              │ Processar Evento                   │  │
│                              │ - Extrair dados da mensagem        │  │
│                              │ - Identificar tipo                 │  │
│                              └──────────────┬─────────────────────┘  │
│                                             │                        │
│                                             ▼                        │
│                              ┌────────────────────────────────────┐  │
│                              │ Verificar Conversa Existente       │  │
│                              │ (Redis/Cache)                      │  │
│                              └──────────────┬─────────────────────┘  │
│                                             │                        │
│                           ┌─────────────────┼─────────────────┐      │
│                           │                 │                 │      │
│                           ▼                 ▼                 ▼      │
│                    ┌──────────┐      ┌──────────┐      ┌──────────┐  │
│                    │ Chatbot  │      │ Fila de  │      │ Atendente│  │
│                    │   IA     │      │ Espera   │      │ Humano   │  │
│                    └────┬─────┘      └────┬─────┘      └────┬─────┘  │
│                         │                 │                 │        │
│                         └─────────────────┴─────────────────┘        │
│                                           │                          │
│                                           ▼                          │
│                              ┌────────────────────────────────────┐  │
│                              │ Enviar Resposta via                │  │
│                              │ WhatsApp Enterprise API            │  │
│                              └────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Segurança

### Verificação de Assinatura

Toda requisição de webhook é verificada usando HMAC SHA256:

```python
# Automático no endpoint
signature = request.headers.get("X-Hub-Signature-256")
is_valid = api.verify_signature(body, signature)
```

### Rate Limiting

- Limite de 80 mensagens/segundo por número
- Limite configurável por cliente
- Cooldown automático após erros 429

### Sessões

- Sessões de 24 horas (configurável)
- Rastreamento de contexto por número
- Cache em Redis para performance

## Métricas

```python
metrics = api.get_metrics()
# {
#     "messages_sent": 1500,
#     "messages_received": 1200,
#     "media_uploaded": 50,
#     "templates_sent": 300,
#     "errors": 5,
#     "api_calls": 3000,
#     "initialized": True,
#     "uptime_seconds": 86400
# }
```

## Testes

```bash
# Executar testes do WhatsApp Enterprise
pytest app/tests/test_whatsapp_enterprise.py -v

# Com cobertura
pytest app/tests/test_whatsapp_enterprise.py -v --cov=app/services/whatsapp_enterprise
```

## Troubleshooting

### Webhook não recebe mensagens

1. Verifique se a URL está acessível publicamente
2. Confirme que o `WHATSAPP_WEBHOOK_VERIFY_TOKEN` está correto
3. Verifique os logs do webhook em `GET /api/v1/whatsapp/webhook`

### Erro de assinatura

1. Verifique se `WHATSAPP_APP_SECRET` está correto
2. Confirme que o body não está sendo modificado antes da verificação

### Rate limit atingido

1. Aguarde o cooldown (1 segundo por padrão)
2. Considere usar templates para mensagens em massa
3. Implemente filas para envio distribuído

### Mensagem não entregue

1. Verifique o número de destino (formato internacional)
2. Confirme que o número tem WhatsApp ativo
3. Verifique se está dentro da janela de 24 horas para mensagens de resposta

## Referências

- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Message Templates](https://developers.facebook.com/docs/whatsapp/message-templates)
- [Webhooks Reference](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Rate Limits](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/rate-limits)
