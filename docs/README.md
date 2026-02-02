# 📖 Documentação do Sistema de Chat de Atendimento

## Índice da Documentação

### 📋 Documentação Principal

| Documento | Descrição |
|-----------|-----------|
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Documentação completa da API REST |
| [API_EXAMPLES.md](API_EXAMPLES.md) | Exemplos práticos de uso da API em Python |
| [openapi.yaml](openapi.yaml) | Especificação OpenAPI 3.1 (Swagger) |

### 🔧 Guias de Configuração

| Documento | Descrição |
|-----------|-----------|
| [SETUP-GUIDE.md](SETUP-GUIDE.md) | Guia de instalação e configuração inicial |
| [whatsapp-setup-guide.md](whatsapp-setup-guide.md) | Configuração do WhatsApp Business API |
| [whatsapp-token-tutorial.md](whatsapp-token-tutorial.md) | Tutorial para obter tokens do WhatsApp |
| [upgrade-to-postgres.md](upgrade-to-postgres.md) | Migração para PostgreSQL |

### 🏗️ Arquitetura e Design

| Documento | Descrição |
|-----------|-----------|
| [ANALISE_ARQUITETURA_COMPLETA.md](ANALISE_ARQUITETURA_COMPLETA.md) | Análise detalhada da arquitetura |
| [PLANO_ESCALABILIDADE_COMPLETO.md](PLANO_ESCALABILIDADE_COMPLETO.md) | Plano de escalabilidade |
| [web-interface-plan.md](web-interface-plan.md) | Planejamento da interface web |
| [DIAGRAMA_INTEGRACAO_SEMANA1.md](DIAGRAMA_INTEGRACAO_SEMANA1.md) | Diagramas de integração |

### 🛡️ Segurança

| Documento | Descrição |
|-----------|-----------|
| [ANALISE_GAPS_SEGURANCA.md](ANALISE_GAPS_SEGURANCA.md) | Análise de vulnerabilidades |
| [GUIA_IMPLEMENTACAO_PRATICA.md](GUIA_IMPLEMENTACAO_PRATICA.md) | Guia prático de implementação |

### 📊 Monitoramento

| Documento | Descrição |
|-----------|-----------|
| [monitoring-setup.md](monitoring-setup.md) | Configuração de monitoramento |

### 🚀 Roadmap e Evolução

| Documento | Descrição |
|-----------|-----------|
| [ROADMAP-PROFISSIONAL.md](ROADMAP-PROFISSIONAL.md) | Roadmap de desenvolvimento |
| [NEXT-STEPS.md](NEXT-STEPS.md) | Próximos passos |
| [python-migration-plan.md](python-migration-plan.md) | Plano de migração Python |

---

## Acesso Rápido à API

### Swagger UI (Interface Interativa)

Com o servidor rodando, acesse:
```
http://localhost:8000/docs
```

### ReDoc (Documentação Alternativa)

```
http://localhost:8000/redoc
```

### OpenAPI JSON

```
http://localhost:8000/openapi.json
```

---

## Início Rápido

### 1. Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- SQL Server (para autenticação)
- PostgreSQL (para dados)
- Redis (para cache)

### 2. Instalação

```bash
# Clonar repositório
git clone https://github.com/empresa/chat-atendimento.git
cd chat-atendimento

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
copy .env.example .env
# Editar .env com suas configurações
```

### 3. Iniciar com Docker

```bash
# Iniciar todos os serviços
docker-compose -f infra/docker-compose.complete.yml up -d

# Verificar logs
docker-compose logs -f api
```

### 4. Testar API

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@email.com", "password": "admin123"}'
```

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENTES                                      │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┤
│  WhatsApp   │  Web Chat   │  Mobile App │  Dashboard  │   API       │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘
       │             │             │             │             │
       ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         NGINX (Load Balancer)                        │
│                    SSL/TLS • Rate Limiting • Caching                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   API Server    │   │ WebSocket Server│   │   Worker        │
│   (FastAPI)     │   │   (FastAPI)     │   │   (Celery)      │
│   Port 8000     │   │   Port 8001     │   │                 │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   SQL Server    │   │   PostgreSQL    │   │     Redis       │
│ (Autenticação)  │   │   (Dados App)   │   │   (Cache/PubSub)│
│   Port 1433     │   │   Port 5432     │   │   Port 6379     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

## Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave secreta JWT | `sua-chave-super-secreta` |
| `DATABASE_URL` | URL PostgreSQL | `postgresql+asyncpg://user:pass@host/db` |
| `SQLSERVER_HOST` | Host SQL Server | `localhost` |
| `SQLSERVER_DATABASE` | Database SQL Server | `ChatAuth` |
| `SQLSERVER_USER` | Usuário SQL Server | `sa` |
| `SQLSERVER_PASSWORD` | Senha SQL Server | `senha` |
| `REDIS_URL` | URL Redis | `redis://localhost:6379/0` |
| `WHATSAPP_TOKEN` | Token WhatsApp API | `EAAxxxxxxx` |
| `WHATSAPP_PHONE_ID` | Phone Number ID | `123456789` |
| `WHATSAPP_VERIFY_TOKEN` | Token verificação webhook | `meu-token-secreto` |
| `GEMINI_API_KEY` | Chave API Google Gemini | `AIzaxxxxxxx` |

---

## Suporte

- **Email**: suporte@empresa.com
- **Documentação**: https://docs.empresa.com
- **Issues**: https://github.com/empresa/chat-atendimento/issues
