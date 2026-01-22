# 🚀 GUIA DE CONFIGURAÇÃO - ISP Customer Support

## OPÇÕES DE INSTALAÇÃO

### 📦 OPÇÃO 1: DOCKER (RECOMENDADO PARA PRODUÇÃO)

#### Pré-requisitos:
- Docker Desktop instalado e rodando
- PowerShell como Administrador

#### Passos:
1. **Inicie o Docker Desktop**
2. **Abra PowerShell como Administrador**
3. **Navegue até o diretório do projeto**
4. **Execute:**
```powershell
# Versão completa (com monitoramento)
docker-compose up -d

# Versão simples (apenas API + DB)
docker-compose -f docker-compose.simple.yml up -d
```

#### Verificar se funcionou:
```powershell
# Ver containers rodando
docker-compose ps

# Ver logs
docker-compose logs api

# Testar API
curl http://localhost:8000/health
```

---

### 🐍 OPÇÃO 2: PYTHON LOCAL (DESENVOLVIMENTO)

#### Pré-requisitos:
- Python 3.11+
- pip

#### Passos:
1. **Instalar dependências:**
```bash
pip install -r requirements-dev.txt
```

2. **Executar aplicação:**
```bash
python run-local.py
```

3. **Acessar:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

### 🔧 OPÇÃO 3: CONFIGURAÇÃO MANUAL

#### 1. Configurar Banco de Dados

**PostgreSQL:**
```sql
CREATE DATABASE isp_support;
CREATE USER isp_app WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE isp_support TO isp_app;
```

**Redis:**
```bash
# Instalar Redis no Windows
# Ou usar Redis Cloud: https://redis.com/
```

#### 2. Configurar Variáveis de Ambiente

Edite o arquivo `.env`:
```env
DATABASE_URL=postgresql+asyncpg://isp_app:password@localhost:5432/isp_support
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=sua-chave-secreta-aqui
```

#### 3. Executar Migrações
```bash
alembic upgrade head
```

#### 4. Iniciar Aplicação
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔑 CONFIGURAÇÕES IMPORTANTES

### WhatsApp Business API

1. **Criar conta Meta for Developers:**
   - Acesse: https://developers.facebook.com/
   - Crie um app Business
   - Configure WhatsApp Business API

2. **Obter credenciais:**
   - Access Token
   - Phone Number ID
   - Webhook Verify Token

3. **Configurar no .env:**
```env
WHATSAPP_ACCESS_TOKEN=seu_token_aqui
WHATSAPP_PHONE_NUMBER_ID=seu_phone_id_aqui
WHATSAPP_WEBHOOK_VERIFY_TOKEN=seu_webhook_token_aqui
```

### Google Gemini AI

1. **Criar conta Google Cloud:**
   - Acesse: https://console.cloud.google.com/
   - Ative a API Gemini
   - Crie uma chave de API

2. **Configurar no .env:**
```env
GEMINI_API_KEY=sua_chave_gemini_aqui
```

---

## 🧪 TESTANDO A INSTALAÇÃO

### Teste Básico
```bash
# Testar health check
curl http://localhost:8000/health

# Testar documentação
# Abrir: http://localhost:8000/docs
```

### Teste Completo
```bash
python test_api.py
```

### Login Padrão
- **Username:** admin
- **Password:** admin123
- ⚠️ **ALTERE IMEDIATAMENTE EM PRODUÇÃO!**

---

## 🔍 TROUBLESHOOTING

### Problema: Docker não inicia
**Solução:**
1. Verificar se Docker Desktop está rodando
2. Executar PowerShell como Administrador
3. Verificar se WSL2 está habilitado

### Problema: Erro de conexão com banco
**Solução:**
1. Verificar se PostgreSQL está rodando
2. Verificar credenciais no .env
3. Testar conexão: `psql -h localhost -U postgres`

### Problema: API não responde
**Solução:**
1. Verificar logs: `docker-compose logs api`
2. Verificar se porta 8000 está livre
3. Testar: `netstat -an | findstr 8000`

### Problema: WhatsApp não conecta
**Solução:**
1. Verificar credenciais no .env
2. Verificar se webhook está configurado
3. Testar token na API do Meta

---

## 📊 MONITORAMENTO

### Acessar Dashboards:
- **Grafana:** http://localhost:3000 (admin/admin123)
- **Prometheus:** http://localhost:9090
- **Kibana:** http://localhost:5601

### Métricas Importantes:
- Requests por segundo
- Tempo de resposta
- Conexões WhatsApp ativas
- Uso de memória/CPU

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ **Configurar credenciais** (WhatsApp + Gemini)
2. ✅ **Testar funcionalidades básicas**
3. ✅ **Configurar monitoramento**
4. ✅ **Criar usuários adicionais**
5. ✅ **Configurar backup automático**
6. ✅ **Configurar SSL/HTTPS**
7. ✅ **Deploy em produção**

---

## 📞 SUPORTE

Se encontrar problemas:
1. Verificar logs dos containers
2. Consultar documentação da API
3. Verificar configurações no .env
4. Testar conectividade de rede

**Logs úteis:**
```bash
# Ver todos os logs
docker-compose logs -f

# Ver logs específicos
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f redis
```