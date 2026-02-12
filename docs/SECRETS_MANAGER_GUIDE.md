# 🔐 Guia de Secrets Manager

## Visão Geral

O sistema suporta múltiplos provedores de secrets para armazenamento seguro de credenciais:

- **LOCAL** - Arquivo `.env` (apenas desenvolvimento)
- **AWS** - AWS Secrets Manager (produção recomendado)
- **VAULT** - HashiCorp Vault (enterprise)
- **AZURE** - Azure Key Vault (Azure cloud)

## Configuração

### 1. Desenvolvimento Local (Padrão)

```bash
# .env
SECRETS_PROVIDER=local

# Todas as credenciais ficam no .env
SECRET_KEY=sua-chave-secreta
SGP_TOKEN=seu-token-sgp
GEMINI_API_KEY=sua-chave-gemini
```

### 2. AWS Secrets Manager (Produção)

#### Instalação
```bash
pip install boto3
```

#### Configuração
```bash
# .env
SECRETS_PROVIDER=aws
AWS_REGION=us-east-1

# Credenciais AWS (ou use IAM Role)
AWS_ACCESS_KEY_ID=sua-access-key
AWS_SECRET_ACCESS_KEY=sua-secret-key
```

#### Criar Secrets no AWS
```bash
# Via AWS CLI
aws secretsmanager create-secret \
    --name SECRET_KEY \
    --secret-string "sua-chave-secreta-super-segura"

aws secretsmanager create-secret \
    --name SGP_TOKEN \
    --secret-string "b0cce023-589a-4ea6-80e6-feaa2781bbf3"

aws secretsmanager create-secret \
    --name GEMINI_API_KEY \
    --secret-string "sua-chave-gemini"

# Ou criar um secret JSON com múltiplas chaves
aws secretsmanager create-secret \
    --name app-secrets \
    --secret-string '{
        "SECRET_KEY": "sua-chave",
        "SGP_TOKEN": "seu-token",
        "GEMINI_API_KEY": "sua-chave-gemini"
    }'
```

#### Uso no Código
```python
from app.core.secrets_manager import get_secret

# Buscar secret individual
secret_key = get_secret("SECRET_KEY")
sgp_token = get_secret("SGP_TOKEN")

# Com valor default
api_key = get_secret("GEMINI_API_KEY", default="fallback-key")
```

### 3. HashiCorp Vault (Enterprise)

#### Instalação
```bash
pip install hvac
```

#### Configuração
```bash
# .env
SECRETS_PROVIDER=vault
VAULT_ADDR=http://vault.sua-empresa.com:8200
VAULT_TOKEN=seu-token-vault
VAULT_SECRET_PATH=kv/data/app
```

#### Criar Secrets no Vault
```bash
# Via Vault CLI
vault kv put kv/app \
    SECRET_KEY="sua-chave" \
    SGP_TOKEN="seu-token" \
    GEMINI_API_KEY="sua-chave-gemini"
```

### 4. Azure Key Vault

#### Instalação
```bash
pip install azure-keyvault-secrets azure-identity
```

#### Configuração
```bash
# .env
SECRETS_PROVIDER=azure
AZURE_KEYVAULT_URL=https://seu-vault.vault.azure.net/
```

#### Criar Secrets no Azure
```bash
# Via Azure CLI
az keyvault secret set \
    --vault-name seu-vault \
    --name SECRET-KEY \
    --value "sua-chave"

az keyvault secret set \
    --vault-name seu-vault \
    --name SGP-TOKEN \
    --value "seu-token"
```

## Uso no Código

### Método 1: Via SecretsManager
```python
from app.core.secrets_manager import get_secrets_manager

secrets = get_secrets_manager()
token = secrets.get_secret("SGP_TOKEN")
```

### Método 2: Função de Conveniência
```python
from app.core.secrets_manager import get_secret

token = get_secret("SGP_TOKEN")
api_key = get_secret("GEMINI_API_KEY", default="fallback")
```

### Método 3: Via Settings (Automático)
```python
from app.core.config import settings

# Automaticamente busca do Secrets Manager se configurado
token = settings.SGP_TOKEN
api_key = settings.GEMINI_API_KEY
```

## Secrets Sensíveis

### Lista de Secrets que DEVEM estar no Secrets Manager em produção:

1. **Autenticação**
   - `SECRET_KEY` - Chave JWT
   - `MASTER_ENCRYPTION_KEY` - Chave de criptografia

2. **Banco de Dados**
   - `DATABASE_URL` - URL completa com senha
   - `MYSQL_ROOT_PASSWORD` - Senha root MySQL

3. **Redis**
   - `REDIS_URL` - URL com senha

4. **WhatsApp**
   - `WHATSAPP_ACCESS_TOKEN` - Token Meta API
   - `WHATSAPP_APP_SECRET` - Secret da aplicação

5. **Google Gemini**
   - `GEMINI_API_KEY` - Chave API Gemini

6. **SGP**
   - `SGP_TOKEN` - Token de autenticação
   - `SGP_USERNAME` - Usuário SGP
   - `SGP_PASSWORD` - Senha SGP

7. **Email**
   - `SMTP_PASSWORD` - Senha SMTP

8. **AWS**
   - `AWS_SECRET_ACCESS_KEY` - Secret key AWS

## Boas Práticas

### ✅ FAZER

1. **Usar Secrets Manager em produção**
   ```bash
   SECRETS_PROVIDER=aws  # ou vault, azure
   ```

2. **Rotacionar secrets regularmente**
   - AWS: Configurar rotação automática
   - Vault: Usar dynamic secrets
   - Azure: Configurar expiração

3. **Usar IAM Roles (AWS) ou Managed Identity (Azure)**
   - Evita credenciais hardcoded

4. **Auditar acesso a secrets**
   - CloudTrail (AWS)
   - Audit logs (Vault)
   - Monitor (Azure)

5. **Usar diferentes secrets por ambiente**
   ```
   dev/SECRET_KEY
   staging/SECRET_KEY
   prod/SECRET_KEY
   ```

### ❌ NÃO FAZER

1. **Commitar .env no Git**
   ```bash
   # Sempre no .gitignore
   .env
   .env.local
   .env.production
   ```

2. **Logar secrets**
   ```python
   # ERRADO
   logger.info(f"Token: {token}")
   
   # CERTO
   logger.info("Token loaded successfully")
   ```

3. **Hardcodar credenciais**
   ```python
   # ERRADO
   token = "b0cce023-589a-4ea6-80e6-feaa2781bbf3"
   
   # CERTO
   token = get_secret("SGP_TOKEN")
   ```

4. **Usar secrets em URLs**
   ```python
   # ERRADO
   url = f"https://api.com?token={token}"
   
   # CERTO
   headers = {"Authorization": f"Bearer {token}"}
   ```

## Migração de .env para Secrets Manager

### Passo 1: Identificar Secrets
```bash
# Listar todas as variáveis sensíveis no .env
grep -E "(KEY|TOKEN|PASSWORD|SECRET)" .env
```

### Passo 2: Criar Secrets no Provedor
```bash
# AWS
aws secretsmanager create-secret --name SECRET_KEY --secret-string "valor"

# Vault
vault kv put kv/app SECRET_KEY="valor"

# Azure
az keyvault secret set --vault-name vault --name SECRET-KEY --value "valor"
```

### Passo 3: Atualizar .env
```bash
# Remover valores sensíveis, manter apenas configuração
SECRETS_PROVIDER=aws
AWS_REGION=us-east-1

# Não precisa mais de:
# SECRET_KEY=...
# SGP_TOKEN=...
```

### Passo 4: Testar
```bash
# Verificar se secrets são carregados
python -c "from app.core.secrets_manager import get_secret; print(get_secret('SECRET_KEY'))"
```

## Troubleshooting

### Erro: "boto3 not installed"
```bash
pip install boto3
```

### Erro: "Vault authentication failed"
```bash
# Verificar token
echo $VAULT_TOKEN

# Renovar token
vault login
```

### Erro: "Azure authentication failed"
```bash
# Login no Azure
az login

# Verificar permissões
az keyvault secret show --vault-name vault --name SECRET-KEY
```

### Erro: "Secret not found"
```bash
# AWS
aws secretsmanager list-secrets

# Vault
vault kv list kv/app

# Azure
az keyvault secret list --vault-name vault
```

## Custos

### AWS Secrets Manager
- $0.40 por secret/mês
- $0.05 por 10.000 chamadas de API
- Rotação automática incluída

### HashiCorp Vault
- Open source: Gratuito
- Enterprise: Licença comercial

### Azure Key Vault
- Standard: $0.03 por 10.000 operações
- Premium: $0.15 por 10.000 operações (HSM)

## Referências

- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [Azure Key Vault](https://azure.microsoft.com/services/key-vault/)
