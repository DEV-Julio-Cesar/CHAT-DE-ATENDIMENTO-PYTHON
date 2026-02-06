# 🚀 CIANET PROVEDOR - Sistema Enterprise

Sistema completo de atendimento ao cliente via WhatsApp para provedores de internet (ISP) com capacidade para **10.000+ clientes simultâneos**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg)]()

---

## 📋 Índice

- [Características](#-características)
- [Tecnologias](#-tecnologias)
- [Instalação Rápida](#-instalação-rápida)
- [Configuração](#-configuração)
- [Deploy](#-deploy)
- [Documentação](#-documentação)
- [Testes](#-testes)
- [Contribuindo](#-contribuindo)

---

## ✨ Características

### 🎯 Funcionalidades Principais

- ✅ **Chat WhatsApp Integrado** - WhatsApp Business API oficial
- ✅ **Chatbot IA** - Google Gemini para respostas automáticas
- ✅ **Dashboard Executivo** - Métricas em tempo real
- ✅ **Campanhas de Marketing** - Envio em massa segmentado
- ✅ **Gerenciamento de Clientes** - CRM integrado
- ✅ **Sistema de Filas** - Distribuição inteligente de atendimentos
- ✅ **Relatórios Avançados** - Analytics e insights
- ✅ **Multi-usuário** - Controle de acesso por roles

### 🔒 Segurança

- ✅ Autenticação JWT
- ✅ Rate Limiting
- ✅ Criptografia de dados
- ✅ Auditoria completa (LGPD/GDPR)
- ✅ Proteção contra brute force
- ✅ CORS configurável

### 📊 Performance

- ✅ Cache multi-level
- ✅ Connection pooling
- ✅ Compressão automática
- ✅ Circuit breakers
- ✅ Tempo de resposta < 10ms
- ✅ Suporte a 10.000+ clientes

---

## 🛠️ Tecnologias

### Backend
- **FastAPI** - Framework web moderno e rápido
- **Python 3.11+** - Linguagem de programação
- **SQLAlchemy** - ORM para banco de dados
- **Pydantic** - Validação de dados

### Banco de Dados
- **MariaDB/MySQL** - Banco principal
- **Redis** - Cache e filas
- **SQL Server** - Opcional (autenticação legada)

### Integrações
- **WhatsApp Business API** - Meta Cloud API
- **Google Gemini** - IA para chatbot
- **Prometheus** - Métricas
- **Grafana** - Visualização

### Frontend
- **HTML5/CSS3** - Interface moderna
- **JavaScript** - Interatividade
- **Bootstrap Icons** - Ícones

---

## 🚀 Instalação Rápida

### Pré-requisitos

- Python 3.11 ou superior
- MariaDB/MySQL 8.0+
- Redis (opcional)
- Git

### Passo 1: Clonar Repositório

```bash
git clone https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON.git
cd CHAT-DE-ATENDIMENTO-PYTHON
```

### Passo 2: Criar Ambiente Virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Passo 3: Instalar Dependências

```bash
pip install -r requirements.txt
```

### Passo 4: Configurar Banco de Dados

```sql
CREATE DATABASE cianet_provedor;
CREATE USER 'chat_app'@'localhost' IDENTIFIED BY 'sua_senha';
GRANT ALL PRIVILEGES ON cianet_provedor.* TO 'chat_app'@'localhost';
FLUSH PRIVILEGES;
```

### Passo 5: Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env com suas credenciais
nano .env
```

### Passo 6: Executar Aplicação

```bash
python app/main_web_ready.py
```

Acesse: **http://localhost:8000**

---

## ⚙️ Configuração

### Configurações Essenciais

Edite o arquivo `.env`:

```env
# Banco de Dados
DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/cianet_provedor"

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN="seu_token_aqui"
WHATSAPP_PHONE_NUMBER_ID="seu_phone_id"

# Google Gemini AI
GEMINI_API_KEY="sua_chave_aqui"

# Segurança
SECRET_KEY="sua-chave-secreta-32-caracteres-minimo"
```

### Credenciais de Teste

```
Email: admin@empresa.com
Senha: admin123
```

---

## 🌐 Deploy

### Deploy na AWS EC2

```bash
# Executar script automático
curl -sSL https://raw.githubusercontent.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON/main/scripts/deploy-ec2.sh | bash
```

### Deploy com Docker

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Guias Completos

- [Deploy AWS EC2](docs/deployment/deploy-aws-guide.md)
- [Deploy Rápido (15min)](docs/deployment/DEPLOY-RAPIDO.md)
- [Docker Compose](docker-compose.prod.yml)

---

## 📚 Documentação

### URLs da Aplicação

- **Dashboard:** http://localhost:8000
- **Login:** http://localhost:8000/login
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

### Documentação Adicional

- [Guia de Instalação](docs/SETUP-GUIDE.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Arquitetura](docs/ANALISE_ARQUITETURA_COMPLETA.md)
- [Segurança](docs/ANALISE_GAPS_SEGURANCA.md)

---

## 🧪 Testes

### Executar Testes

```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Executar todos os testes
pytest

# Com cobertura
pytest --cov=app tests/

# Testes específicos
pytest tests/test_auth.py
```

### Relatório de Testes

Veja o [Relatório Completo de Testes](docs/deployment/RELATORIO-TESTES.md)

**Resultado:** ✅ 93.3% de aprovação (14/15 testes)

---

## 📊 Estrutura do Projeto

```
CHAT-DE-ATENDIMENTO-PYTHON/
├── app/                      # Código da aplicação
│   ├── api/                  # Endpoints da API
│   ├── core/                 # Configurações core
│   ├── models/               # Modelos de dados
│   ├── schemas/              # Schemas Pydantic
│   ├── services/             # Lógica de negócio
│   ├── web/                  # Templates e static
│   └── main_web_ready.py     # Aplicação principal
├── docs/                     # Documentação
├── scripts/                  # Scripts utilitários
├── tests/                    # Testes
├── .env.example              # Exemplo de configuração
├── requirements.txt          # Dependências
└── README.md                 # Este arquivo
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👥 Autor

**Julio Cesar**
- GitHub: [@DEV-Julio-Cesar](https://github.com/DEV-Julio-Cesar)

---

## 🎯 Status do Projeto

✅ **Produção Ready** - Sistema testado e aprovado para deploy

**Última atualização:** 05/02/2026  
**Versão:** 2.0.0  
**Status:** Ativo e em desenvolvimento

---

## 📞 Suporte

- **Issues:** [GitHub Issues](https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON/issues)
- **Documentação:** [Wiki](https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON/wiki)

---

**🚀 Sistema pronto para transformar seu atendimento ao cliente!**
