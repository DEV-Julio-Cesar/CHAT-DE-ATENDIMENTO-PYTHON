# PLANO DE MIGRAÇÃO PYTHON - PROVEDOR INTERNET 10K CLIENTES

## STACK TECNOLÓGICA PROFISSIONAL

### Backend Core
- **FastAPI**: API REST + WebSocket (substitui Express)
- **SQLAlchemy 2.0**: ORM com async support
- **PostgreSQL 15**: Banco principal com replicação
- **Redis Cluster**: Cache distribuído + sessões
- **Celery**: Processamento assíncrono
- **RabbitMQ**: Message broker

### WhatsApp Integration
- **WhatsApp Business API**: Solução oficial (recomendado para escala)
- **Alternativa**: `whatsapp-web.py` + Selenium Grid
- **Load Balancer**: Nginx para distribuir conexões

### Segurança & Monitoramento
- **JWT**: Autenticação stateless
- **bcrypt**: Hash de senhas
- **Rate Limiting**: Redis-based
- **Prometheus**: Métricas
- **Grafana**: Dashboards
- **ELK Stack**: Logs centralizados

### Infraestrutura
- **Docker**: Containerização
- **Kubernetes**: Orquestração
- **Helm**: Package manager K8s
- **ArgoCD**: GitOps deployment

## MELHORIAS CRÍTICAS PARA 10K CLIENTES

### 1. BANCO DE DADOS PROFISSIONAL

#### Migração JSON → PostgreSQL
```sql
-- Estrutura otimizada para 10k clientes
CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ultimo_login TIMESTAMP WITH TIME ZONE
);

CREATE TABLE clientes_whatsapp (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(100) UNIQUE NOT NULL,
    nome VARCHAR(255) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    status client_status DEFAULT 'ativo',
    servidor_id VARCHAR(50), -- Para sharding
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE conversas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID REFERENCES clientes_whatsapp(id),
    chat_id VARCHAR(255) NOT NULL,
    estado conversa_estado DEFAULT 'automacao',
    atendente_id UUID REFERENCES usuarios(id),
    tentativas_bot INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Particionamento por mês para performance
CREATE TABLE conversas_2024_01 PARTITION OF conversas
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE mensagens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID REFERENCES conversas(id),
    remetente_tipo sender_type NOT NULL,
    conteudo TEXT NOT NULL,
    tipo_mensagem message_type DEFAULT 'texto',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Índices para performance
CREATE INDEX idx_conversas_cliente_estado ON conversas(cliente_id, estado);
CREATE INDEX idx_conversas_atendente ON conversas(atendente_id) WHERE atendente_id IS NOT NULL;
CREATE INDEX idx_mensagens_conversa_data ON mensagens(conversa_id, created_at);
```

### 2. CACHE DISTRIBUÍDO COM REDIS

```python
# Redis configuration for 10k clients
REDIS_CONFIG = {
    'cluster_nodes': [
        {'host': 'redis-node-1', 'port': 7000},
        {'host': 'redis-node-2', 'port': 7000},
        {'host': 'redis-node-3', 'port': 7000},
    ],
    'decode_responses': True,
    'skip_full_coverage_check': True,
    'max_connections': 1000
}

# Cache strategy
CACHE_KEYS = {
    'user_session': 'session:{user_id}',  # TTL: 24h
    'whatsapp_client': 'wa_client:{client_id}',  # TTL: 1h
    'conversation_state': 'conv:{conv_id}',  # TTL: 6h
    'rate_limit': 'rate:{user_id}:{endpoint}',  # TTL: 1min
    'metrics': 'metrics:{date}:{type}',  # TTL: 7d
}
```

### 3. ARQUITETURA DE MICROSERVIÇOS

```yaml
# docker-compose.yml para desenvolvimento
version: '3.8'
services:
  api-gateway:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    
  api-server:
    build: ./app
    replicas: 3
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/isp_support
      - REDIS_URL=redis://redis-cluster:7000
      
  websocket-server:
    build: ./app
    command: uvicorn app.websocket.main:app --host 0.0.0.0 --port 8001
    replicas: 2
    
  worker:
    build: ./app
    command: celery -A app.workers.main worker --loglevel=info
    replicas: 4
    
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: isp_support
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis-cluster:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes
    
  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: password
```

### 4. ESCALABILIDADE WHATSAPP

#### Opção 1: WhatsApp Business API (Recomendado)
```python
# WhatsApp Business API integration
class WhatsAppBusinessAPI:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v18.0"
        
    async def send_message(self, to: str, message: str):
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "text": {"body": message}
        }
        # Implementar rate limiting e retry logic
        return await self.http_client.post(url, json=payload, headers=headers)
```

#### Opção 2: Sharding com whatsapp-web.py
```python
# Distribuição de clientes por servidor
class WhatsAppShardManager:
    def __init__(self):
        self.shards = {
            'shard_1': {'server': 'wa-server-1', 'clients': 0, 'max_clients': 10},
            'shard_2': {'server': 'wa-server-2', 'clients': 0, 'max_clients': 10},
            # ... até 1000 shards para 10k clientes
        }
    
    def assign_client_to_shard(self, client_id: str) -> str:
        # Load balancing algorithm
        available_shard = min(
            self.shards.items(),
            key=lambda x: x[1]['clients']
        )
        return available_shard[0]
```

### 5. PROCESSAMENTO ASSÍNCRONO COM CELERY

```python
# Celery tasks for heavy operations
from celery import Celery

celery_app = Celery('isp_support')

@celery_app.task(bind=True, max_retries=3)
def send_campaign_message(self, campaign_id: str, recipient: str, message: str):
    try:
        # Send message via WhatsApp API
        result = whatsapp_service.send_message(recipient, message)
        # Update campaign metrics
        update_campaign_metrics(campaign_id, 'sent', recipient)
        return result
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery_app.task
def process_ai_response(conversation_id: str, user_message: str):
    # Generate AI response using Gemini
    ai_response = gemini_service.generate_response(user_message)
    # Save to database
    save_message(conversation_id, ai_response, sender_type='bot')
    # Send via WhatsApp
    send_whatsapp_message(conversation_id, ai_response)

@celery_app.task
def generate_daily_reports():
    # Generate metrics and reports
    metrics = calculate_daily_metrics()
    send_report_to_managers(metrics)
```

### 6. MONITORAMENTO E OBSERVABILIDADE

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Métricas de negócio
messages_sent = Counter('messages_sent_total', 'Total messages sent', ['client_type'])
response_time = Histogram('response_time_seconds', 'Response time')
active_conversations = Gauge('active_conversations', 'Active conversations')
whatsapp_clients_connected = Gauge('whatsapp_clients_connected', 'Connected WhatsApp clients')

# Health checks
@app.get("/health")
async def health_check():
    checks = {
        'database': await check_database_connection(),
        'redis': await check_redis_connection(),
        'whatsapp': await check_whatsapp_status(),
        'celery': await check_celery_workers()
    }
    
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return {'status': status, 'checks': checks}
```

### 7. SEGURANÇA PROFISSIONAL

```python
# JWT Authentication
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTAuthentication

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/messages/send")
@limiter.limit("100/minute")  # 100 mensagens por minuto por IP
async def send_message(request: Request, message_data: MessageCreate):
    # Validação de entrada
    validated_data = validate_message_input(message_data)
    # Envio da mensagem
    return await message_service.send(validated_data)

# Input validation
from pydantic import BaseModel, validator

class MessageCreate(BaseModel):
    recipient: str
    content: str
    
    @validator('recipient')
    def validate_phone(cls, v):
        # Validar formato de telefone
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        # Sanitizar conteúdo
        if len(v) > 4096:
            raise ValueError('Message too long')
        return sanitize_html(v)
```

### 8. DEPLOYMENT E CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          python -m pytest tests/ --cov=app --cov-report=xml
          
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: docker build -t isp-support:${{ github.sha }} .
        
      - name: Push to registry
        run: docker push registry.company.com/isp-support:${{ github.sha }}
        
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          helm upgrade --install isp-support ./helm-chart \
            --set image.tag=${{ github.sha }} \
            --set replicas.api=5 \
            --set replicas.worker=10
```

## ESTIMATIVAS DE CAPACIDADE

### Hardware Requirements (10k clientes)
- **API Servers**: 5 instâncias (4 CPU, 8GB RAM cada)
- **Worker Servers**: 10 instâncias (2 CPU, 4GB RAM cada)
- **Database**: PostgreSQL cluster (16 CPU, 64GB RAM, 2TB SSD)
- **Redis Cluster**: 3 nós (4 CPU, 16GB RAM cada)
- **WhatsApp Servers**: 1000 instâncias (1 CPU, 2GB RAM cada) se usar web.py

### Performance Targets
- **Latência**: < 200ms (P95) para API calls
- **Throughput**: 10,000 mensagens/minuto
- **Disponibilidade**: 99.9% uptime
- **Conexões simultâneas**: 50,000+

### Custos Estimados (AWS)
- **Infraestrutura**: ~$15,000/mês
- **WhatsApp Business API**: ~$0.005 por mensagem
- **Monitoramento**: ~$500/mês
- **Total**: ~$16,000/mês para 10k clientes ativos

## CRONOGRAMA DE MIGRAÇÃO

### Fase 1 (2-3 meses): Fundação
- [ ] Setup da infraestrutura base (K8s, PostgreSQL, Redis)
- [ ] Migração do sistema de usuários
- [ ] API REST básica com FastAPI
- [ ] Autenticação JWT

### Fase 2 (2-3 meses): Core Features
- [ ] Sistema de conversas e filas
- [ ] Integração WhatsApp Business API
- [ ] WebSocket para chat real-time
- [ ] Chatbot com IA

### Fase 3 (2-3 meses): Escalabilidade
- [ ] Sistema de campanhas
- [ ] Processamento assíncrono (Celery)
- [ ] Monitoramento completo
- [ ] Testes de carga

### Fase 4 (1-2 meses): Produção
- [ ] CI/CD pipeline
- [ ] Backup e disaster recovery
- [ ] Documentação
- [ ] Treinamento da equipe

## PRÓXIMOS PASSOS IMEDIATOS

1. **Definir arquitetura de dados** (PostgreSQL schema)
2. **Setup ambiente de desenvolvimento** (Docker Compose)
3. **Implementar autenticação** (FastAPI + JWT)
4. **Criar API básica** (CRUD usuários)
5. **Integrar WhatsApp Business API** (conta de teste)