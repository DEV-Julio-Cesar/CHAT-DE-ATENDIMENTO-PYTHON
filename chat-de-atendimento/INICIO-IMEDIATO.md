# 🚀 INÍCIO IMEDIATO - MIGRAÇÃO PARA PYTHON

## 📋 CHECKLIST PARA COMEÇAR HOJE

### ✅ Preparação (2 horas)
- [ ] Criar repositório GitHub
- [ ] Setup ambiente Python 3.11+
- [ ] Instalar Docker Desktop
- [ ] Configurar VS Code/PyCharm
- [ ] Criar arquivo .env

### ✅ Setup Básico (4 horas)
- [ ] Estrutura de pastas
- [ ] Docker Compose
- [ ] PostgreSQL + Redis
- [ ] Primeiro microserviço (Auth)
- [ ] Teste básico funcionando

---

## 🛠️ COMANDOS PARA EXECUTAR AGORA

### 1. Criar Estrutura do Projeto
```bash
# Criar diretório principal
mkdir isp-chat-system
cd isp-chat-system

# Estrutura completa
mkdir -p {services/{auth,chat,ai,queue,whatsapp,campaign,analytics}-service,shared/{models,utils,middleware,config},infrastructure/{docker,kubernetes,monitoring},frontend/{web-dashboard,mobile-app},tests/{unit,integration,load},docs}

# Inicializar Git
git init
echo "# ISP Chat System - Python Migration" > README.md
git add README.md
git commit -m "Initial commit"
```

### 2. Configurar Ambiente Python
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Ativar (Linux/Mac)
source venv/bin/activate

# Instalar dependências base
pip install fastapi uvicorn sqlalchemy asyncpg redis celery python-multipart python-jose[cryptography] passlib[bcrypt] pydantic[email] alembic pytest pytest-asyncio httpx
```

### 3. Criar Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: isp_postgres
    environment:
      POSTGRES_DB: isp_chat
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: isp_redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  adminer:
    image: adminer
    container_name: isp_adminer
    ports:
      - "8080:8080"
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

### 4. Inicializar Banco de Dados
```sql
-- scripts/init.sql
-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tipos enumerados
CREATE TYPE user_role AS ENUM ('admin', 'supervisor', 'agent', 'viewer');
CREATE TYPE conversation_status AS ENUM ('automation', 'waiting', 'in_service', 'closed');

-- Tabela de usuários
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'agent',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usuário admin padrão (senha: admin123)
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES ('admin', 'admin@empresa.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJflLxQjm', 'admin', true);

-- Tabela de conversas
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),
    status conversation_status NOT NULL DEFAULT 'automation',
    agent_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message TEXT,
    bot_attempts INTEGER DEFAULT 0
);

-- Índices básicos
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_agent ON conversations(agent_id);
```

### 5. Configuração Base
```python
# shared/config/settings.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "ISP Chat System"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres123@localhost:5432/isp_chat"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    JWT_SECRET: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    
    # WhatsApp (configurar depois)
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    
    # OpenAI (configurar depois)
    OPENAI_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 6. Primeiro Microserviço (Auth)
```python
# services/auth-service/app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
import asyncio

# Configuração
DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/isp_chat"
JWT_SECRET = "your-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"

# FastAPI app
app = FastAPI(title="Auth Service", version="1.0.0")

# Database
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Schemas
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str
    role: str

# Routes
@app.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Buscar usuário (simulado - implementar com SQLAlchemy depois)
    if credentials.username == "admin" and credentials.password == "admin123":
        # Criar token
        token_data = {
            "sub": credentials.username,
            "user_id": "admin-id",
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user_id="admin-id",
            username="admin",
            role="admin"
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@app.post("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"valid": True, "user": payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

### 7. Arquivo de Dependências
```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
redis==5.0.1
celery==5.3.4
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic[email]==2.5.0
alembic==1.13.0
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

### 8. Arquivo de Ambiente
```env
# .env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/isp_chat

# Redis
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET=your-super-secret-jwt-key-change-in-production-please
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# WhatsApp Business API (configurar depois)
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=

# OpenAI (configurar depois)
OPENAI_API_KEY=

# App
DEBUG=true
LOG_LEVEL=INFO
```

---

## 🧪 TESTE IMEDIATO

### 1. Iniciar Infraestrutura
```bash
# Subir PostgreSQL e Redis
docker-compose -f docker-compose.dev.yml up -d

# Verificar se estão rodando
docker-compose ps
```

### 2. Testar Auth Service
```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar o serviço
cd services/auth-service
python -m app.main

# Em outro terminal, testar
curl -X POST "http://localhost:8001/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 3. Verificar Banco de Dados
```bash
# Acessar Adminer
# http://localhost:8080
# Server: postgres
# Username: postgres
# Password: postgres123
# Database: isp_chat
```

---

## 📊 VALIDAÇÃO DO SETUP

### ✅ Checklist de Funcionamento
- [ ] PostgreSQL conectando (porta 5432)
- [ ] Redis respondendo (porta 6379)
- [ ] Auth Service rodando (porta 8001)
- [ ] Login funcionando (admin/admin123)
- [ ] Token JWT sendo gerado
- [ ] Adminer acessível (porta 8080)

### 🧪 Testes Básicos
```bash
# Teste 1: Health check
curl http://localhost:8001/health

# Teste 2: Login
curl -X POST "http://localhost:8001/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Teste 3: Verificar token (usar token do teste 2)
curl -X POST "http://localhost:8001/verify" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

---

## 🎯 PRÓXIMOS PASSOS (Próximas 2 semanas)

### Semana 1: Completar Auth Service
- [ ] Implementar SQLAlchemy models
- [ ] CRUD completo de usuários
- [ ] Testes unitários
- [ ] Rate limiting
- [ ] Logs estruturados

### Semana 2: Chat Service Base
- [ ] Modelos de conversa
- [ ] WebSocket básico
- [ ] CRUD de conversas
- [ ] Sistema de filas simples
- [ ] Integração com Auth

### Semana 3: AI Service
- [ ] Integração OpenAI
- [ ] Processamento de mensagens
- [ ] Base de conhecimento
- [ ] Classificação de intenções

### Semana 4: WhatsApp Integration
- [ ] WhatsApp Business API
- [ ] Webhook processing
- [ ] Envio de mensagens
- [ ] Pool básico

---

## 💡 DICAS IMPORTANTES

### 🔧 Desenvolvimento
1. **Use ambiente virtual sempre**
2. **Commit pequeno e frequente**
3. **Teste cada componente isoladamente**
4. **Documente as APIs com FastAPI**
5. **Use type hints em Python**

### 🚀 Performance
1. **Async/await em tudo**
2. **Connection pooling no PostgreSQL**
3. **Cache Redis para sessões**
4. **Índices no banco desde o início**
5. **Monitoramento básico sempre ativo**

### 🔒 Segurança
1. **Nunca commitar .env**
2. **JWT secrets fortes**
3. **Rate limiting desde o início**
4. **Validação de entrada sempre**
5. **HTTPS em produção**

---

## 📞 SUPORTE

### 🆘 Se algo não funcionar:
1. **Verificar logs**: `docker-compose logs`
2. **Testar conexões**: `telnet localhost 5432`
3. **Verificar portas**: `netstat -an | grep 5432`
4. **Reiniciar serviços**: `docker-compose restart`

### 📚 Documentação Útil:
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Redis**: https://redis.io/documentation

---

**🎯 Meta: Ter o primeiro microserviço funcionando em 6 horas!**

*Com este setup, você terá uma base sólida para construir o sistema completo nos próximos 4 meses.*