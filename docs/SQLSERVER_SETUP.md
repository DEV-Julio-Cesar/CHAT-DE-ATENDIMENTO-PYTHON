# 📊 Guia de Configuração SQL Server

## Visão Geral

Este documento descreve a configuração completa do SQL Server para o sistema de chat de atendimento.

## 🏗️ Arquitetura de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│                    SQL Server Database                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │   usuarios   │──│  user_sessions  │──│ token_blacklist │   │
│  │  (usuários)  │  │    (sessões)    │  │ (tokens rev.)   │   │
│  └──────────────┘  └─────────────────┘  └─────────────────┘   │
│         │                                                       │
│         │         ┌─────────────────┐  ┌─────────────────┐    │
│         ├────────│  audit_logs     │  │  user_consents  │    │
│         │        │  (auditoria)    │  │     (LGPD)      │    │
│         │        └─────────────────┘  └─────────────────┘    │
│         │                                                       │
│         │         ┌─────────────────┐  ┌─────────────────┐    │
│         └────────│  api_keys       │  │ rate_limit_rec  │    │
│                  │  (API keys)     │  │ (rate limits)   │    │
│                  └─────────────────┘  └─────────────────┘    │
│                                                                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ whatsapp_    │──│  conversations  │──│    messages     │   │
│  │   clients    │  │  (conversas)    │  │  (mensagens)    │   │
│  └──────────────┘  └─────────────────┘  └─────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ agent_       │  │  queue_entries  │  │ quick_replies   │   │
│  │   metrics    │  │     (fila)      │  │  (respostas)    │   │
│  └──────────────┘  └─────────────────┘  └─────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Pré-requisitos

### 1. SQL Server Instalado
- SQL Server 2019 ou superior
- SQL Server Express (gratuito) ou versão comercial
- SQL Server Authentication habilitado

### 2. Driver ODBC
```powershell
# Verificar drivers instalados
Get-OdbcDriver | Where-Object { $_.Name -like "*SQL Server*" }

# Baixar ODBC Driver 17 ou 18
# https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

### 3. Dependências Python
```bash
pip install pyodbc bcrypt
```

## ⚙️ Configuração

### 1. Variáveis de Ambiente (.env)

```env
# SQL Server Authentication
SQLSERVER_HOST=localhost
SQLSERVER_PORT=1433
SQLSERVER_DATABASE=chat_atendimento
SQLSERVER_USER=chat_app
SQLSERVER_PASSWORD=sua_senha_segura_aqui
SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server

# Token Configuration
SECRET_KEY=sua_chave_secreta_jwt_256_bits
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 2. Criar Database e Usuário

```sql
-- Conectar como sa ou admin
CREATE DATABASE chat_atendimento;
GO

USE chat_atendimento;
GO

-- Criar login
CREATE LOGIN chat_app WITH PASSWORD = 'sua_senha_segura_aqui';
GO

-- Criar usuário no database
CREATE USER chat_app FOR LOGIN chat_app;
GO

-- Conceder permissões
EXEC sp_addrolemember 'db_datareader', 'chat_app';
EXEC sp_addrolemember 'db_datawriter', 'chat_app';
GRANT EXECUTE TO chat_app;
GO
```

## 🚀 Executando Migrations

### Estrutura de Migrations

```
scripts/sqlserver/
├── 001_create_database.sql      # Schema principal
├── 002_add_metrics_tables.sql   # Tabelas de métricas
├── 003_create_views_functions.sql # Views e procedures
└── run_migrations.py            # Script Python de execução
```

### Comandos

```bash
# Ver status das migrations
python scripts/sqlserver/run_migrations.py --status

# Executar todas as migrations pendentes
python scripts/sqlserver/run_migrations.py

# Dry run (sem executar)
python scripts/sqlserver/run_migrations.py --dry-run

# Executar até uma migration específica
python scripts/sqlserver/run_migrations.py --target 002

# Forçar re-execução
python scripts/sqlserver/run_migrations.py --force
```

### Saída Esperada

```
╔══════════════════════════════════════════════════════════════════╗
║              SQL Server Migration Tool v1.0                       ║
╚══════════════════════════════════════════════════════════════════╝

[INFO] Conectando ao SQL Server: localhost:1433/chat_atendimento
[INFO] Conexão estabelecida com sucesso!

Migrations pendentes:
  ○ 001_create_database.sql
  ○ 002_add_metrics_tables.sql
  ○ 003_create_views_functions.sql

[INFO] Executando: 001_create_database.sql
[SUCCESS] ✓ 001_create_database.sql executado (2.45s)

[INFO] Executando: 002_add_metrics_tables.sql
[SUCCESS] ✓ 002_add_metrics_tables.sql executado (0.89s)

[INFO] Executando: 003_create_views_functions.sql
[SUCCESS] ✓ 003_create_views_functions.sql executado (0.56s)

════════════════════════════════════════════════════════════════════
Resumo: 3 migrations executadas com sucesso
════════════════════════════════════════════════════════════════════
```

## 📊 Tabelas Principais

### usuarios
Armazena informações dos usuários do sistema.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INT | PK, Identity |
| email | NVARCHAR(255) | Único, indexado |
| password_hash | NVARCHAR(255) | Hash bcrypt |
| nome | NVARCHAR(100) | Nome completo |
| role | NVARCHAR(50) | admin/atendente/user |
| is_active | BIT | Status ativo |
| two_factor_enabled | BIT | 2FA habilitado |
| failed_login_attempts | INT | Tentativas falhas |
| locked_until | DATETIME2 | Bloqueio temporário |

### user_sessions
Controle de sessões ativas.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| session_id | NVARCHAR(64) | Identificador único |
| user_id | INT | FK usuarios |
| access_token_hash | NVARCHAR(64) | Hash SHA256 |
| ip_address | NVARCHAR(45) | IPv4/IPv6 |
| user_agent | NVARCHAR(500) | Browser/device |
| expires_at | DATETIME2 | Expiração |
| is_active | BIT | Sessão ativa |

### audit_logs
Logs de auditoria com integridade.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | BIGINT | PK, Identity |
| event_type | NVARCHAR(50) | auth/data/admin |
| action | NVARCHAR(100) | Ação realizada |
| user_id | INT | FK usuarios |
| ip_address | NVARCHAR(45) | IP do cliente |
| status | NVARCHAR(20) | success/failure |
| entry_hash | NVARCHAR(64) | Hash SHA256 |
| previous_hash | NVARCHAR(64) | Cadeia de integridade |

### conversations
Conversas de atendimento.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | NVARCHAR(36) | UUID |
| customer_phone | NVARCHAR(20) | WhatsApp do cliente |
| customer_name | NVARCHAR(100) | Nome do cliente |
| assigned_to | INT | Atendente (FK) |
| status | NVARCHAR(20) | queue/in_progress/resolved |
| channel | NVARCHAR(20) | whatsapp/web/api |
| started_with_bot | BIT | Iniciou com bot |

## 🔒 Stored Procedures

### sp_authenticate_user
Autentica usuário verificando bloqueios.

```sql
EXEC sp_authenticate_user @email = 'user@email.com';
```

### sp_login_success
Registra login bem-sucedido.

```sql
EXEC sp_login_success 
    @user_id = 1,
    @session_id = 'abc123...',
    @access_token_hash = 'sha256hash...',
    @ip_address = '192.168.1.1',
    @user_agent = 'Mozilla/5.0...',
    @expires_at = '2024-01-01 12:00:00';
```

### sp_login_failure
Registra falha de login e aplica bloqueio se necessário.

```sql
EXEC sp_login_failure @email = 'user@email.com';
```

### sp_get_next_from_queue
Obtém próximo cliente da fila para atendente.

```sql
EXEC sp_get_next_from_queue @agent_id = 1;
```

## 📈 Views Úteis

### vw_agents_online
Atendentes online com disponibilidade.

```sql
SELECT * FROM vw_agents_online WHERE available_slots > 0;
```

### vw_today_metrics
Métricas do dia para dashboard.

```sql
SELECT * FROM vw_today_metrics;
```

### vw_agent_ranking
Ranking de atendentes por performance.

```sql
SELECT * FROM vw_agent_ranking ORDER BY pontuacao DESC;
```

### vw_conversation_history
Histórico de conversas com detalhes.

```sql
SELECT * FROM vw_conversation_history WHERE customer_phone = '+5511999999999';
```

## 🔧 Manutenção

### Limpeza de Dados Antigos

```sql
-- Limpar tokens expirados
DELETE FROM token_blacklist WHERE expires_at < DATEADD(day, -7, GETDATE());

-- Limpar sessões inativas
DELETE FROM user_sessions 
WHERE is_active = 0 AND revoked_at < DATEADD(day, -30, GETDATE());

-- Arquivar logs antigos (manter últimos 90 dias)
-- Recomendado: mover para tabela de arquivo antes de deletar
DELETE FROM audit_logs WHERE created_at < DATEADD(day, -90, GETDATE());
```

### Verificar Integridade dos Logs

```sql
-- Verificar cadeia de integridade
SELECT 
    l1.id,
    l1.entry_hash,
    l1.previous_hash,
    l2.entry_hash as expected_previous,
    CASE 
        WHEN l1.previous_hash = l2.entry_hash THEN 'OK'
        ELSE 'INTEGRITY ERROR'
    END as status
FROM audit_logs l1
LEFT JOIN audit_logs l2 ON l2.id = l1.id - 1
WHERE l1.id > 1
ORDER BY l1.id DESC;
```

### Backup Recomendado

```sql
-- Backup completo
BACKUP DATABASE chat_atendimento 
TO DISK = 'C:\Backups\chat_atendimento_full.bak'
WITH FORMAT, COMPRESSION;

-- Backup diferencial (diário)
BACKUP DATABASE chat_atendimento 
TO DISK = 'C:\Backups\chat_atendimento_diff.bak'
WITH DIFFERENTIAL, COMPRESSION;
```

## 🐛 Troubleshooting

### Erro de Conexão

```
[ERRO] Connection failed: [ODBC Driver...] Login failed for user
```

**Solução:**
1. Verificar se SQL Server Authentication está habilitado
2. Confirmar credenciais no .env
3. Testar conexão: `sqlcmd -S localhost -U chat_app -P senha`

### Erro de Driver

```
[ERRO] Can't find ODBC driver
```

**Solução:**
```powershell
# Listar drivers disponíveis
Get-OdbcDriver

# Instalar ODBC Driver 17
# Download: https://go.microsoft.com/fwlink/?linkid=2187214
```

### Timeout em Migrations

```
[ERRO] Query timeout expired
```

**Solução:**
- Aumentar timeout no pyodbc: `connection.timeout = 300`
- Executar statements em lotes menores

## 📞 Suporte

Para problemas de configuração:
1. Verificar logs em `logs/sqlserver.log`
2. Executar diagnóstico: `python scripts/sqlserver/run_migrations.py --status`
3. Contatar equipe de infraestrutura
