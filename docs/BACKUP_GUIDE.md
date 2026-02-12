## 💾 Guia de Backup Automático

## Visão Geral

Sistema de backup automático do banco de dados MariaDB/MySQL com:
- Backup completo do banco
- Compressão gzip (economia de ~70% de espaço)
- Retenção configurável (padrão: 30 dias)
- Upload para S3 (opcional)
- Agendamento via cron/Task Scheduler

## Configuração

### 1. Variáveis de Ambiente

```bash
# .env
BACKUP_ENABLED=true
BACKUP_DIR=backups
BACKUP_RETENTION_DAYS=30

# Opcional: Upload para S3
AWS_S3_BUCKET=meu-bucket-backups
AWS_REGION=us-east-1
```

### 2. Criar Diretório de Backup

```bash
mkdir backups
chmod 700 backups  # Apenas owner pode acessar
```

### 3. Instalar mysqldump

#### Windows
```bash
# Já vem com MySQL/MariaDB
# Adicionar ao PATH se necessário
```

#### Linux
```bash
sudo apt-get install mysql-client
```

#### macOS
```bash
brew install mysql-client
```

## Uso Manual

### Via API (Requer Admin)

```bash
# Criar backup
curl -X POST http://localhost:8000/api/v1/backup/create \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN"

# Listar backups
curl http://localhost:8000/api/v1/backup/list \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN"

# Restaurar backup
curl -X POST http://localhost:8000/api/v1/backup/restore \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"backup_name": "backup_20260212_010000.sql.gz"}'

# Limpar backups antigos
curl -X POST http://localhost:8000/api/v1/backup/cleanup \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN"

# Upload para S3
curl -X POST "http://localhost:8000/api/v1/backup/upload-s3?backup_name=backup_20260212_010000.sql.gz&bucket=meu-bucket" \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN"
```

### Via Python

```python
from app.core.backup_manager import backup_manager

# Criar backup
backup_file = backup_manager.create_backup()
print(f"Backup criado: {backup_file}")

# Listar backups
backups = backup_manager.list_backups()
for backup in backups:
    print(f"{backup['name']} - {backup['size_mb']} MB")

# Restaurar backup
from pathlib import Path
backup_manager.restore_backup(Path("backups/backup_20260212_010000.sql.gz"))

# Limpar backups antigos
removed = backup_manager.cleanup_old_backups()
print(f"Removidos {removed} backups antigos")
```

### Via Script

```bash
# Executar backup manual
python scripts/schedule_backup.py
```

## Agendamento Automático

### Linux/macOS (cron)

```bash
# Editar crontab
crontab -e

# Adicionar linha para backup diário às 2h da manhã
0 2 * * * cd /caminho/para/projeto && python scripts/schedule_backup.py >> logs/backup.log 2>&1
```

### Windows (Task Scheduler)

#### Via PowerShell
```powershell
# Criar tarefa agendada
$action = New-ScheduledTaskAction -Execute "python" -Argument "scripts/schedule_backup.py" -WorkingDirectory "C:\caminho\para\projeto"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "ChatBackup" -Action $action -Trigger $trigger -Principal $principal
```

#### Via Interface Gráfica
1. Abrir Task Scheduler (Agendador de Tarefas)
2. Criar Tarefa Básica
3. Nome: "Chat Backup Diário"
4. Gatilho: Diariamente às 2:00
5. Ação: Iniciar programa
   - Programa: `python`
   - Argumentos: `scripts/schedule_backup.py`
   - Iniciar em: `C:\caminho\para\projeto`
6. Concluir

### Docker (cron container)

```yaml
# docker-compose.yml
services:
  backup:
    image: python:3.11
    volumes:
      - .:/app
      - ./backups:/app/backups
    working_dir: /app
    command: >
      sh -c "
        apt-get update && apt-get install -y mysql-client cron &&
        echo '0 2 * * * cd /app && python scripts/schedule_backup.py >> /app/logs/backup.log 2>&1' | crontab - &&
        cron -f
      "
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - AWS_S3_BUCKET=${AWS_S3_BUCKET}
```

## Estrutura de Arquivos

```
backups/
├── backup_20260212_020000.sql.gz  (hoje)
├── backup_20260211_020000.sql.gz  (ontem)
├── backup_20260210_020000.sql.gz  (2 dias atrás)
└── ...
```

## Formato do Nome

```
backup_YYYYMMDD_HHMMSS.sql.gz
       │       │
       │       └─ Hora (02:00:00)
       └───────── Data (2026-02-12)
```

## Tamanho dos Backups

### Estimativa de Espaço

| Registros | Tamanho SQL | Tamanho Comprimido | Economia |
|-----------|-------------|-------------------|----------|
| 1.000     | 2 MB        | 600 KB            | 70%      |
| 10.000    | 20 MB       | 6 MB              | 70%      |
| 100.000   | 200 MB      | 60 MB             | 70%      |
| 1.000.000 | 2 GB        | 600 MB            | 70%      |

### Cálculo de Retenção

```
Tamanho por backup: 60 MB (100k registros)
Retenção: 30 dias
Espaço total: 60 MB × 30 = 1.8 GB
```

## Upload para S3

### Configuração AWS

```bash
# Instalar boto3
pip install boto3

# Configurar credenciais
aws configure
# ou usar IAM Role (recomendado)

# .env
AWS_S3_BUCKET=meu-bucket-backups
AWS_REGION=us-east-1
```

### Criar Bucket S3

```bash
# Via AWS CLI
aws s3 mb s3://meu-bucket-backups --region us-east-1

# Configurar lifecycle para deletar após 90 dias
aws s3api put-bucket-lifecycle-configuration \
  --bucket meu-bucket-backups \
  --lifecycle-configuration '{
    "Rules": [{
      "Id": "DeleteOldBackups",
      "Status": "Enabled",
      "Prefix": "backups/",
      "Expiration": {"Days": 90}
    }]
  }'
```

### Custos S3

```
Storage: $0.023 por GB/mês (Standard-IA)
Backup diário de 60 MB por 30 dias = 1.8 GB
Custo mensal: 1.8 × $0.023 = $0.04/mês
```

## Restauração de Backup

### ⚠️ ATENÇÃO

Restaurar um backup irá **sobrescrever completamente** o banco de dados atual!

### Processo Recomendado

1. **Criar backup do estado atual**
   ```bash
   curl -X POST http://localhost:8000/api/v1/backup/create \
     -H "Authorization: Bearer TOKEN"
   ```

2. **Parar aplicação**
   ```bash
   docker-compose down
   # ou
   systemctl stop chat-app
   ```

3. **Restaurar backup**
   ```bash
   python -c "
   from app.core.backup_manager import backup_manager
   from pathlib import Path
   backup_manager.restore_backup(Path('backups/backup_20260212_020000.sql.gz'))
   "
   ```

4. **Reiniciar aplicação**
   ```bash
   docker-compose up -d
   # ou
   systemctl start chat-app
   ```

5. **Verificar integridade**
   ```bash
   curl http://localhost:8000/health
   ```

## Monitoramento

### Verificar Logs

```bash
# Ver logs de backup
tail -f logs/backup.log

# Verificar último backup
ls -lh backups/ | tail -1
```

### Alertas

Configure alertas para:
- Backup falhou
- Espaço em disco baixo
- Backup não executado nas últimas 24h

```python
# Exemplo com Prometheus
from prometheus_client import Gauge

backup_last_success = Gauge('backup_last_success_timestamp', 'Last successful backup timestamp')
backup_size_bytes = Gauge('backup_size_bytes', 'Size of last backup in bytes')
```

## Troubleshooting

### Erro: "mysqldump: command not found"

```bash
# Linux
sudo apt-get install mysql-client

# macOS
brew install mysql-client

# Windows
# Adicionar MySQL/bin ao PATH
```

### Erro: "Access denied for user"

```bash
# Verificar credenciais no .env
echo $DATABASE_URL

# Testar conexão manual
mysql -h localhost -u root -p cianet_provedor
```

### Erro: "Disk space full"

```bash
# Verificar espaço
df -h

# Limpar backups antigos
python -c "from app.core.backup_manager import backup_manager; backup_manager.cleanup_old_backups()"
```

### Erro: "Backup timeout"

```bash
# Aumentar timeout no código
# app/core/backup_manager.py
timeout=7200  # 2 horas
```

## Boas Práticas

### ✅ FAZER

1. **Testar restauração regularmente**
   - Restaurar backup em ambiente de teste mensalmente

2. **Múltiplas cópias**
   - Local + S3 + Outro cloud (redundância)

3. **Criptografar backups**
   ```bash
   # Criptografar com GPG
   gpg --encrypt --recipient seu@email.com backup.sql.gz
   ```

4. **Monitorar espaço em disco**
   ```bash
   # Alerta se < 10% livre
   df -h | grep backups
   ```

5. **Documentar processo**
   - Manter runbook de restauração atualizado

### ❌ NÃO FAZER

1. **Não armazenar apenas localmente**
   - Servidor pode falhar/ser comprometido

2. **Não ignorar falhas de backup**
   - Configurar alertas imediatos

3. **Não manter backups eternamente**
   - Definir retenção adequada (30-90 dias)

4. **Não fazer backup durante horário de pico**
   - Agendar para madrugada (2-4h)

5. **Não esquecer de testar restauração**
   - Backup não testado = backup inexistente

## Referências

- [mysqldump Documentation](https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html)
- [AWS S3 Backup Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/backup-best-practices.html)
- [Cron Syntax](https://crontab.guru/)
