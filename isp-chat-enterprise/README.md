# ISP Chat Enterprise

Sistema profissional de chat de atendimento para ISPs e empresas de telecomunicações, desenvolvido com arquitetura de microserviços em Python/FastAPI.

## 🚀 Características Principais

### 💬 **Chat de Atendimento Completo**
- Interface web moderna e responsiva
- Chat em tempo real via WebSocket
- Suporte a múltiplos canais (WhatsApp, Web)
- Sistema de filas inteligentes
- Transferência entre agentes
- Histórico completo de conversas

### 🏗️ **Arquitetura Enterprise**
- **Microserviços**: Auth, Chat, AI, API Gateway
- **Banco de dados**: SQL Server 2025 Enterprise
- **Cache**: Redis para alta performance
- **Monitoramento**: Prometheus + Grafana
- **Load Balancer**: Nginx com SSL
- **Containerização**: Docker + Docker Compose

### 🔐 **Segurança Avançada**
- Autenticação JWT com refresh tokens
- Rate limiting inteligente
- CORS configurável
- Criptografia de dados sensíveis
- Auditoria completa de ações
- Controle de acesso baseado em papéis (RBAC)

### 📊 **Métricas e Relatórios**
- Dashboard em tempo real
- Métricas de SLA e performance
- Relatórios de produtividade
- Análise de satisfação do cliente
- Alertas automáticos

### 🤖 **Inteligência Artificial**
- Chatbot com IA humanizada
- Classificação automática de tickets
- Sugestões de respostas
- Análise de sentimento
- Escalação inteligente

## 🛠️ Tecnologias Utilizadas

### **Backend**
- **Python 3.11+** - Linguagem principal
- **FastAPI** - Framework web moderno e rápido
- **SQLAlchemy 2.0** - ORM assíncrono
- **Pydantic** - Validação de dados
- **Alembic** - Migrações de banco
- **Redis** - Cache e sessões
- **JWT** - Autenticação stateless

### **Banco de Dados**
- **SQL Server 2025** - Banco principal
- **Redis** - Cache e filas
- **Backup automático** - Estratégia de recuperação

### **Frontend**
- **HTML5/CSS3** - Interface moderna
- **JavaScript ES6+** - Lógica do cliente
- **WebSocket** - Comunicação em tempo real
- **Chart.js** - Gráficos e métricas
- **Tailwind CSS** - Framework CSS

### **DevOps**
- **Docker** - Containerização
- **Docker Compose** - Orquestração
- **Nginx** - Proxy reverso e load balancer
- **Prometheus** - Métricas
- **Grafana** - Dashboards
- **GitHub Actions** - CI/CD

## 📋 Pré-requisitos

### **Sistema Operacional**
- Windows 10/11 ou Linux Ubuntu 20.04+
- 8GB RAM mínimo (16GB recomendado)
- 50GB espaço em disco
- Conexão com internet

### **Software Necessário**
- **Docker Desktop** 4.0+
- **Docker Compose** 2.0+
- **Python 3.11+** (para desenvolvimento)
- **Git** (para versionamento)

## 🚀 Instalação Rápida

### **1. Clonar o Repositório**
```bash
git clone https://github.com/seu-usuario/isp-chat-enterprise.git
cd isp-chat-enterprise
```

### **2. Configurar Ambiente**
```bash
# Copiar arquivo de configuração
cp .env.example .env

# Editar configurações (obrigatório)
nano .env  # Linux/Mac
notepad .env  # Windows
```

### **3. Deploy com Docker (Recomendado)**
```bash
# Linux/Mac
./scripts/deploy.sh

# Windows PowerShell
.\scripts\deploy.ps1
```

### **4. Deploy Manual (Desenvolvimento)**
```bash
# Instalar dependências
pip install -r requirements.txt

# Inicializar banco de dados
python database/setup.py

# Iniciar todos os serviços
python start.py
```

## 🌐 URLs de Acesso

Após a instalação, os serviços estarão disponíveis em:

- **🖥️ Interface Web**: http://localhost:3000
- **🔗 API Gateway**: http://localhost:8000
- **📚 Documentação**: http://localhost:8000/docs
- **🔐 Auth Service**: http://localhost:8001
- **💬 Chat Service**: http://localhost:8002
- **📊 Prometheus**: http://localhost:9090
- **📈 Grafana**: http://localhost:3001

## 🔐 Credenciais Padrão

**Usuário Administrador:**
- **Username**: `admin`
- **Password**: `admin123`

**Grafana:**
- **Username**: `admin`
- **Password**: `admin`

> ⚠️ **IMPORTANTE**: Altere as senhas padrão em produção!

## 📖 Documentação Completa

### **Guias de Uso**
- [📘 Guia de Instalação](docs/installation.md)
- [🔧 Configuração Avançada](docs/configuration.md)
- [🚀 Deploy em Produção](docs/production.md)
- [🔒 Configuração de Segurança](docs/security.md)
- [📊 Monitoramento](docs/monitoring.md)

### **Desenvolvimento**
- [🏗️ Arquitetura do Sistema](docs/architecture.md)
- [🔌 API Reference](docs/api.md)
- [🧪 Testes](docs/testing.md)
- [🐛 Troubleshooting](docs/troubleshooting.md)

### **Integrações**
- [📱 WhatsApp Business API](docs/whatsapp.md)
- [🤖 Configuração de IA](docs/ai-setup.md)
- [📧 Notificações por Email](docs/email.md)
- [📞 Integração Telefônica](docs/telephony.md)

## 🏢 Funcionalidades Enterprise

### **Dashboard Executivo**
- Métricas em tempo real
- KPIs de atendimento
- Relatórios gerenciais
- Análise de tendências

### **Gestão de Equipes**
- Controle de jornada
- Distribuição de carga
- Avaliação de performance
- Treinamento integrado

### **Automação Inteligente**
- Chatbot com IA
- Roteamento automático
- Respostas sugeridas
- Escalação por prioridade

### **Compliance e Auditoria**
- Log completo de ações
- Relatórios de conformidade
- Backup automático
- Retenção de dados configurável

## 🔧 Configurações Avançadas

### **Variáveis de Ambiente (.env)**
```env
# Banco de Dados
DATABASE_URL=mssql+pyodbc://sa:password@localhost:1433/ISPChat
SQL_SERVER_HOST=localhost
SQL_SERVER_PORT=1433
SQL_SERVER_USER=sa
SQL_SERVER_PASSWORD=ISPChat2025!
SQL_SERVER_DATABASE=ISPChat

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# WhatsApp
WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_ID=your-phone-id
WHATSAPP_VERIFY_TOKEN=your-verify-token

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Ambiente
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### **Configuração de Produção**
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl
      - ./config/nginx.conf:/etc/nginx/nginx.conf
```

## 📊 Monitoramento e Métricas

### **Métricas Coletadas**
- Tempo de resposta das APIs
- Número de conversas ativas
- Taxa de resolução
- Satisfação do cliente
- Utilização de recursos

### **Alertas Configurados**
- Serviço indisponível
- Alto tempo de resposta
- Fila de atendimento cheia
- Erro de autenticação
- Uso excessivo de recursos

## 🧪 Testes

### **Executar Testes**
```bash
# Testes unitários
pytest tests/unit/

# Testes de integração
pytest tests/integration/

# Testes de funcionalidades
python test-all-features.py

# Testes de carga
python tests/load_test.py
```

### **Cobertura de Testes**
```bash
# Gerar relatório de cobertura
pytest --cov=. --cov-report=html
```

## 🚀 Deploy em Produção

### **Preparação**
1. Configurar domínio e SSL
2. Ajustar variáveis de ambiente
3. Configurar backup automático
4. Definir políticas de segurança

### **Deploy Automatizado**
```bash
# Com CI/CD (GitHub Actions)
git push origin main

# Deploy manual
./scripts/deploy.sh --production
```

### **Monitoramento Pós-Deploy**
- Verificar logs de todos os serviços
- Confirmar métricas no Grafana
- Testar funcionalidades críticas
- Validar backups

## 🤝 Contribuição

### **Como Contribuir**
1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

### **Padrões de Código**
- Seguir PEP 8 para Python
- Documentar todas as funções
- Escrever testes para novas features
- Usar type hints

## 📞 Suporte

### **Canais de Suporte**
- **Email**: suporte@ispchatsystem.com
- **WhatsApp**: +55 11 99999-9999
- **Discord**: [ISP Chat Community](https://discord.gg/ispchatsystem)
- **GitHub Issues**: Para bugs e features

### **Documentação Adicional**
- **Wiki**: https://github.com/seu-usuario/isp-chat-enterprise/wiki
- **FAQ**: https://docs.ispchatsystem.com/faq
- **Vídeos**: https://youtube.com/ispchatsystem

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🏆 Reconhecimentos

- **FastAPI** - Framework web moderno
- **SQLAlchemy** - ORM poderoso
- **Docker** - Containerização
- **Tailwind CSS** - Framework CSS
- **Chart.js** - Biblioteca de gráficos

---

**Desenvolvido com ❤️ para ISPs e empresas de telecomunicações**

*Sistema profissional de chat de atendimento com arquitetura enterprise, alta disponibilidade e escalabilidade.*