# Guia de Instalação - ISP Chat Enterprise

## 📋 Pré-requisitos

### Software Necessário

- **Python 3.11+** - Linguagem principal
- **SQL Server 2019+** - Banco de dados principal  
- **Redis 6.0+** - Cache e sessões
- **Node.js 18+** - Para integração WhatsApp
- **Git** - Controle de versão

### Hardware Recomendado

**Desenvolvimento:**
- CPU: 4 cores
- RAM: 8GB
- Disco: 20GB SSD

**Produção:**
- CPU: 8+ cores
- RAM: 16GB+
- Disco: 100GB+ SSD
- Rede: 1Gbps+

## 🚀 Instalação Passo a Passo

### 1. Clonar Repositório

```bash
git clone <repository-url>
cd isp-chat-enterprise
```

### 2. Configurar Ambiente Python

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente (Windows)
venv\Scripts\activate

# Ativar ambiente (Linux/Mac)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar Banco de Dados

```bash
# Configurar SQL Server
python database/setup.py

# Verificar conexão
python -c "from shared.utils.database import test_connection; test_connection()"
```

### 4. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
copy .env.example .env

# Editar configurações
notepad .env  # Windows
nano .env     # Linux
```

### 5. Inicializar Sistema

```bash
# Iniciar todos os serviços
python start.py

# Ou iniciar serviços individuais
python services/auth-service/app/main.py
python services/chat-service/app/main.py
python services/api-gateway/app/main.py
python web-server.py
```

## 🔧 Configuração Avançada

### SSL/HTTPS

```bash
# Gerar certificados
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Configurar no .env
SSL_ENABLED=true
SSL_CERT_PATH=./cert.pem
SSL_KEY_PATH=./key.pem
```

### Load Balancer

```bash
# Instalar nginx
sudo apt install nginx  # Ubuntu
choco install nginx     # Windows

# Configurar upstream
# Ver docs/nginx.conf
```

### Monitoramento

```bash
# Instalar Prometheus
docker run -p 9090:9090 prom/prometheus

# Configurar métricas
ENABLE_METRICS=true
METRICS_PORT=9090
```

## 🧪 Verificação da Instalação

### Testes Básicos

```bash
# Testar APIs
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Testar interface
curl http://localhost:3000
```

### Testes Completos

```bash
# Executar suite de testes
python -m pytest tests/

# Teste de carga
python tests/load_test.py
```

## 🐛 Solução de Problemas

### Problemas Comuns

**Erro de Conexão com Banco:**
```bash
# Verificar SQL Server
sqlcmd -S localhost -E -Q "SELECT @@VERSION"

# Verificar driver ODBC
odbcinst -q -d
```

**Porta em Uso:**
```bash
# Windows
netstat -ano | findstr :8000

# Linux
lsof -i :8000
```

**Dependências Faltando:**
```bash
# Reinstalar dependências
pip install --force-reinstall -r requirements.txt
```

### Logs de Debug

```bash
# Habilitar logs detalhados
export LOG_LEVEL=DEBUG

# Ver logs em tempo real
tail -f logs/app.log
```

## 📞 Suporte

- **Documentação**: [docs/](./README.md)
- **Issues**: GitHub Issues
- **Email**: suporte@empresa.com

---

**Próximo**: [Configuração](configuration.md)