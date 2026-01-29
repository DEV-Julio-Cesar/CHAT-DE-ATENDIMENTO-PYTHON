# 🚀 ISP Chat System - Python Migration

Sistema de chat de atendimento com IA para telecomunicações, migrado de Node.js para Python/FastAPI.

## 🎯 Objetivo
Escalar de 50 para 10,000+ clientes simultâneos com 99.9% uptime.

## 📊 Status Atual
- ✅ Estrutura criada
- ⏳ Auth Service (em desenvolvimento)
- ⏳ PostgreSQL setup
- ⏳ Migração de dados

## 🚀 Como executar
```bash
# 1. Ativar ambiente Python
venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Subir infraestrutura
docker-compose -f docker-compose.dev.yml up -d

# 4. Iniciar Auth Service
cd services/auth-service
python -m app.main
```

## 📈 Progresso
- [x] Estrutura do projeto
- [ ] Docker Compose
- [ ] Auth Service
- [ ] Migração de dados
- [ ] Testes básicos