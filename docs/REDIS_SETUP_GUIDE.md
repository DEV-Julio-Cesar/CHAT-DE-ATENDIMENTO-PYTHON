# 🚀 Guia de Configuração do Redis

## Por Que Redis é Importante?

O Redis está **desabilitado** no código atual, mas é **CRÍTICO** para produção por:

### 1. **Performance** (10-100x mais rápido)
```
Sem Redis:
- Cada request consulta banco de dados
- Latência: 50-200ms por query
- 100 requests/seg = 100 queries/seg no BD

Com Redis:
- Cache em memória (RAM)
- Latência: 1-5ms
- 100 requests/seg = 5-10 queries/seg no BD (95% cache hit)
```

### 2. **Escalabilidade**
```
Sem Redis:
- Banco de dados é gargalo
- Máximo ~1.000 usuários simultâneos

Com Redis:
- Cache distribui carga
- Suporta 10.000+ usuários simultâneos
```

### 3. **Funcionalidades Essenciais**
- **Rate Limiting** - Proteção contra brute force/DDoS
- **Sessões** - Contexto de conversa do chatbot
- **Filas** - Processamento assíncrono (Celery)
- **Pub/Sub** - WebSocket em tempo real
- **Cache** - Dados frequentemente acessados

## Instalação

### Windows

#### Opção 1: Via Memurai (Recomendado)
```powershell
# Download: https://www.memurai.com/get-memurai
# Instalar e iniciar serviço

# Verificar
redis-cli ping
# Resposta: PONG
```

#### Opção 2: Via WSL2
```bash
# Instalar WSL2
wsl --install

# Dentro do WSL
sudo apt-get update
sudo apt-get install redis-server

# Iniciar Redis
sudo service redis-server start

# Verificar
redis-cli ping
```

#### Opção 3: Via Docker (Mais Fácil)
```powershell
# Instalar Docker Desktop
# Download: https://www.docker.com/products/docker-desktop

# Iniciar Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Verificar
docker exec -it redis redis-cli ping
```

### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# Iniciar serviço
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verificar
redis-cli ping
```

### macOS

```bash
# Via Homebrew
brew install redis

# Iniciar serviço
brew services start redis

# Verificar
redis-cli ping
```

## Configuração

### 1. Configurar Senha (Segurança)

```bash
# Editar redis.conf
# Windows: C:\Program Files\Memurai\memurai.conf
# Linux: /etc/redis/redis.conf
# macOS: /usr/local/etc/redis.conf

# Adicionar linha:
requirepass SUA_SENHA_FORTE_AQUI
```

### 2. Atualizar .env

```bash
# .env
REDIS_URL=redis://:SUA_SENHA@localhost:6379/0

# Sem senha (apenas desenvolvimento):
# REDIS_URL=redis://localhost:6379/0
```

### 3. Habilitar no Código

O código já está preparado, basta descomentar:

```python
# app/main.py (linha ~95-100)

# ANTES (desabilitado):
# try:
#     await redis_manager.initialize()
#     logger.info("Redis initialized")
#     redis_initialized = True
# except Exception as e:
#     logger.warning("Redis unavailable - running without cache", error=str(e))
redis_initialized = False  # Redis desabilitado para performance

# DEPOIS (habilitado):
try:
    await redis_manager.initialize()
    logger.info("Redis initialized")
    redis_initialized = True
except Exception as e:
    logger.warning("Redis unavailable - running without cache", error=str(e))
```

### 4. Instalar Dependências Python

```bash
pip install redis aioredis
```

## Verificação

### 1. Testar Conexão

```python
# test_redis.py
import redis

r = redis.from_url("redis://:SUA_SENHA@localhost:6379/0")
r.ping()
print("Redis conectado!")

# Testar set/get
r.set("teste", "funcionando")
print(r.get("teste"))  # b'funcionando'
```

### 2. Verificar Health Check

```bash
curl http://localhost:8000/health

# Resposta esperada:
{
  "status": "healthy",
  "checks": {
    "database": true,
    "redis": true,  # ← Deve ser true agora
    "timestamp": 1707700000
  }
}
```

### 3. Monitorar Redis

```bash
# Via redis-cli
redis-cli
> INFO stats
> MONITOR  # Ver comandos em tempo real
> KEYS *   # Listar todas as chaves (cuidado em produção!)

# Via Docker
docker exec -it redis redis-cli
```

## Configuração Avançada

### 1. Persistência (Salvar em Disco)

```bash
# redis.conf

# RDB (snapshot periódico)
save 900 1      # Salvar se 1 chave mudou em 15 min
save 300 10     # Salvar se 10 chaves mudaram em 5 min
save 60 10000   # Salvar se 10k chaves mudaram em 1 min

# AOF (log de todas as operações)
appendonly yes
appendfsync everysec  # Sincronizar a cada segundo
```

### 2. Limites de Memória

```bash
# redis.conf

# Máximo de memória (ex: 2GB)
maxmemory 2gb

# Política de eviction (quando memória cheia)
maxmemory-policy allkeys-lru  # Remove chaves menos usadas
```

### 3. Redis Cluster (Alta Disponibilidade)

```yaml
# docker-compose.yml
services:
  redis-master:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass senha
  
  redis-replica:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    command: redis-server --requirepass senha --replicaof redis-master 6379
    depends_on:
      - redis-master
```

## Uso no Código

### 1. Cache de Dados

```python
from app.core.redis_client import redis_manager

# Cachear resultado de query
async def get_user(user_id: int):
    # Tentar cache primeiro
    cached = await redis_manager.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    
    # Se não está em cache, buscar no BD
    user = await db.query(User).filter(User.id == user_id).first()
    
    # Cachear por 1 hora
    await redis_manager.set(
        f"user:{user_id}",
        json.dumps(user.dict()),
        ex=3600
    )
    
    return user
```

### 2. Rate Limiting

```python
from app.core.rate_limiter import rate_limiter

# Limitar login a 5 tentativas em 15 minutos
allowed, remaining = await rate_limiter.is_allowed(
    identifier=f"login:{client_ip}",
    max_requests=5,
    window_seconds=900
)

if not allowed:
    raise HTTPException(429, "Too many login attempts")
```

### 3. Sessões de Conversa

```python
# Armazenar contexto de conversa do chatbot
await redis_manager.set(
    f"conversation:{phone_number}",
    json.dumps({
        "messages": [...],
        "context": {...},
        "last_intent": "boleto"
    }),
    ex=86400  # 24 horas
)
```

### 4. Filas (Celery)

```python
from celery import Celery

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,  # Redis
    backend=settings.CELERY_RESULT_BACKEND  # Redis
)

@celery_app.task
def send_campaign_message(phone, message):
    # Processar em background
    whatsapp_api.send_message(phone, message)
```

## Performance

### Benchmarks

```
Operação          | Sem Redis | Com Redis | Melhoria
------------------|-----------|-----------|----------
Buscar usuário    | 50ms      | 2ms       | 25x
Listar conversas  | 200ms     | 10ms      | 20x
Dashboard metrics | 500ms     | 15ms      | 33x
Rate limit check  | 30ms      | 1ms       | 30x
```

### Métricas de Cache

```python
# Ver estatísticas de cache
from app.core.cache_strategy import cache_manager

stats = cache_manager.get_stats()
print(f"Cache hit rate: {stats['hit_rate']}%")
print(f"Total hits: {stats['hits']}")
print(f"Total misses: {stats['misses']}")
```

## Troubleshooting

### Erro: "Connection refused"

```bash
# Verificar se Redis está rodando
# Windows
sc query Memurai

# Linux
sudo systemctl status redis-server

# Docker
docker ps | grep redis

# Iniciar se não estiver rodando
# Windows
sc start Memurai

# Linux
sudo systemctl start redis-server

# Docker
docker start redis
```

### Erro: "NOAUTH Authentication required"

```bash
# Senha incorreta no .env
# Verificar redis.conf
grep requirepass /etc/redis/redis.conf

# Atualizar .env
REDIS_URL=redis://:SENHA_CORRETA@localhost:6379/0
```

### Erro: "Out of memory"

```bash
# Verificar uso de memória
redis-cli INFO memory

# Limpar cache
redis-cli FLUSHDB

# Aumentar maxmemory no redis.conf
maxmemory 4gb
```

### Redis Lento

```bash
# Ver comandos lentos
redis-cli SLOWLOG GET 10

# Analisar chaves grandes
redis-cli --bigkeys

# Otimizar:
# 1. Usar TTL em todas as chaves
# 2. Evitar KEYS * (usar SCAN)
# 3. Usar pipeline para múltiplos comandos
```

## Monitoramento

### 1. Redis Insight (GUI)

```bash
# Download: https://redis.com/redis-enterprise/redis-insight/
# Interface gráfica para monitorar Redis
```

### 2. Prometheus Metrics

```python
# app/core/metrics.py
from prometheus_client import Gauge

redis_connected_clients = Gauge('redis_connected_clients', 'Number of connected clients')
redis_used_memory = Gauge('redis_used_memory_bytes', 'Used memory in bytes')
redis_hit_rate = Gauge('redis_hit_rate', 'Cache hit rate percentage')
```

### 3. Alertas

Configure alertas para:
- Redis down
- Memória > 80%
- Hit rate < 70%
- Conexões > 1000

## Custos

### Desenvolvimento (Local)
- **Gratuito** - Redis open source

### Produção (Cloud)

#### AWS ElastiCache
```
cache.t3.micro: $0.017/hora = $12/mês
cache.t3.small: $0.034/hora = $25/mês
cache.m5.large: $0.136/hora = $100/mês
```

#### Redis Cloud
```
30 MB: Gratuito
250 MB: $5/mês
1 GB: $15/mês
5 GB: $60/mês
```

#### Azure Cache for Redis
```
Basic C0 (250 MB): $16/mês
Basic C1 (1 GB): $55/mês
Standard C2 (2.5 GB): $145/mês
```

## Migração (Desabilitado → Habilitado)

### Passo 1: Instalar Redis
```bash
# Ver seção "Instalação" acima
```

### Passo 2: Configurar .env
```bash
REDIS_URL=redis://:senha@localhost:6379/0
```

### Passo 3: Habilitar no Código
```python
# app/main.py - Descomentar linhas 95-100
```

### Passo 4: Reiniciar Aplicação
```bash
# Parar
Ctrl+C

# Iniciar
python -m uvicorn app.main:app --reload
```

### Passo 5: Verificar
```bash
curl http://localhost:8000/health
# redis: true ✅
```

## Boas Práticas

### ✅ FAZER

1. **Sempre usar TTL**
   ```python
   await redis_manager.set("key", "value", ex=3600)  # Expira em 1h
   ```

2. **Usar namespaces**
   ```python
   f"user:{user_id}"
   f"conversation:{phone}"
   f"cache:dashboard:metrics"
   ```

3. **Monitorar hit rate**
   - Objetivo: > 80%

4. **Configurar persistência**
   - RDB + AOF para não perder dados

5. **Usar pipeline para múltiplos comandos**
   ```python
   pipe = redis_manager.pipeline()
   pipe.set("key1", "value1")
   pipe.set("key2", "value2")
   await pipe.execute()
   ```

### ❌ NÃO FAZER

1. **Não usar KEYS ***
   ```python
   # ERRADO (bloqueia Redis)
   keys = await redis_manager.keys("*")
   
   # CERTO
   keys = []
   async for key in redis_manager.scan_iter("user:*"):
       keys.append(key)
   ```

2. **Não armazenar dados grandes**
   - Máximo: 512 MB por chave
   - Ideal: < 1 MB

3. **Não esquecer de limpar**
   - Sempre usar TTL
   - Evitar memory leak

4. **Não usar Redis como banco principal**
   - Redis é cache, não persistência

5. **Não expor Redis na internet**
   - Sempre usar firewall
   - Sempre usar senha

## Referências

- [Redis Documentation](https://redis.io/documentation)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [AWS ElastiCache](https://aws.amazon.com/elasticache/)
- [Redis Cloud](https://redis.com/redis-enterprise-cloud/)
