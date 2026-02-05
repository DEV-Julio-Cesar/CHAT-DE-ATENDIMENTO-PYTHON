# 🚀 Guia Completo de Deploy na AWS

## 📋 Opções de Deploy

### 1. **AWS EC2 (Recomendado para iniciantes)**
### 2. **AWS Elastic Beanstalk (Mais fácil)**
### 3. **AWS ECS com Docker (Profissional)**
### 4. **AWS Lambda + API Gateway (Serverless)**

---

## 🎯 **OPÇÃO 1: AWS EC2 (Recomendado)**

### **Passo 1: Criar instância EC2**

1. **Acesse AWS Console** → EC2
2. **Launch Instance**
3. **Configurações:**
   - **AMI:** Ubuntu Server 22.04 LTS
   - **Instance Type:** t3.micro (Free Tier) ou t3.small
   - **Key Pair:** Criar nova ou usar existente
   - **Security Group:** 
     - SSH (22) - Seu IP
     - HTTP (80) - 0.0.0.0/0
     - HTTPS (443) - 0.0.0.0/0
     - Custom (8000) - 0.0.0.0/0

### **Passo 2: Conectar via SSH**

```bash
# Windows (PowerShell)
ssh -i "sua-chave.pem" ubuntu@SEU-IP-PUBLICO

# Ou use PuTTY no Windows
```

### **Passo 3: Configurar servidor**

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3.11
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Instalar dependências
sudo apt install git nginx mysql-server redis-server -y

# Instalar pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Configurar MySQL
sudo mysql_secure_installation
```

### **Passo 4: Clonar e configurar projeto**

```bash
# Clonar repositório
git clone https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON.git
cd CHAT-DE-ATENDIMENTO-PYTHON

# Criar ambiente virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar banco MySQL
sudo mysql -u root -p
```

**SQL para configurar banco:**
```sql
CREATE DATABASE cianet_provedor;
CREATE USER 'chat_app'@'localhost' IDENTIFIED BY 'SuaSenhaSegura123!';
GRANT ALL PRIVILEGES ON cianet_provedor.* TO 'chat_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### **Passo 5: Configurar .env para produção**

```bash
# Editar arquivo .env
nano .env
```

**Configuração .env para AWS:**
```env
# Aplicação
APP_NAME="ISP Customer Support"
VERSION="2.0.0"
DEBUG=false
SECRET_KEY="sua-chave-super-secreta-de-producao-com-32-caracteres-minimo"

# Banco de dados
DATABASE_URL="mysql+aiomysql://chat_app:SuaSenhaSegura123!@localhost:3306/cianet_provedor"

# Redis
REDIS_URL="redis://localhost:6379/0"

# WhatsApp (configure suas credenciais reais)
WHATSAPP_ACCESS_TOKEN="seu_token_whatsapp_real"
WHATSAPP_PHONE_NUMBER_ID="seu_phone_id_real"
WHATSAPP_WEBHOOK_VERIFY_TOKEN="seu_webhook_token"

# Gemini AI (configure sua chave real)
GEMINI_API_KEY="sua_chave_gemini_real"

# Produção
TRUSTED_HOSTS="seu-dominio.com,*.seu-dominio.com,SEU-IP-AWS"
CORS_ORIGINS="https://seu-dominio.com"
```

### **Passo 6: Configurar Nginx**

```bash
# Criar configuração Nginx
sudo nano /etc/nginx/sites-available/isp-support
```

**Configuração Nginx:**
```nginx
server {
    listen 80;
    server_name SEU-IP-PUBLICO seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON/app/web/static/;
    }
}
```

```bash
# Ativar site
sudo ln -s /etc/nginx/sites-available/isp-support /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### **Passo 7: Criar serviço systemd**

```bash
# Criar arquivo de serviço
sudo nano /etc/systemd/system/isp-support.service
```

**Configuração do serviço:**
```ini
[Unit]
Description=ISP Customer Support
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON
Environment=PATH=/home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON/venv/bin
ExecStart=/home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON/venv/bin/python app/main_web_ready.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Ativar e iniciar serviço
sudo systemctl daemon-reload
sudo systemctl enable isp-support
sudo systemctl start isp-support
sudo systemctl status isp-support
```

---

## 🎯 **OPÇÃO 2: AWS Elastic Beanstalk (Mais Fácil)**

### **Passo 1: Preparar aplicação**

```bash
# Criar requirements.txt específico
pip freeze > requirements.txt

# Criar arquivo de configuração
mkdir .ebextensions
```

**Criar `.ebextensions/python.config`:**
```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: app.main_web_ready:app
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: "/var/app/current:$PYTHONPATH"
```

**Criar `application.py`:**
```python
from app.main_web_ready import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
```

### **Passo 2: Deploy via EB CLI**

```bash
# Instalar EB CLI
pip install awsebcli

# Inicializar
eb init

# Criar ambiente
eb create production

# Deploy
eb deploy
```

---

## 🎯 **OPÇÃO 3: Docker + ECS (Profissional)**

### **Passo 1: Criar Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicação
COPY . .

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["python", "app/main_web_ready.py"]
```

### **Passo 2: Build e Push para ECR**

```bash
# Criar repositório ECR
aws ecr create-repository --repository-name isp-support

# Build da imagem
docker build -t isp-support .

# Tag e push
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin SEU-ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker tag isp-support:latest SEU-ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/isp-support:latest
docker push SEU-ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/isp-support:latest
```

---

## 🔧 **Scripts de Deploy Automatizado**

### **Script para EC2 (deploy-ec2.sh):**

```bash
#!/bin/bash
echo "🚀 Iniciando deploy na AWS EC2..."

# Atualizar código
git pull origin main

# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Reiniciar serviços
sudo systemctl restart isp-support
sudo systemctl restart nginx

echo "✅ Deploy concluído!"
echo "🌐 Acesse: http://SEU-IP-PUBLICO"
```

---

## 🔒 **Configurações de Segurança**

### **1. SSL/HTTPS com Let's Encrypt**

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado
sudo certbot --nginx -d seu-dominio.com

# Renovação automática
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet
```

### **2. Firewall**

```bash
# Configurar UFW
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### **3. Backup automático**

```bash
# Script de backup
#!/bin/bash
mysqldump -u chat_app -p cianet_provedor > backup_$(date +%Y%m%d).sql
aws s3 cp backup_$(date +%Y%m%d).sql s3://seu-bucket-backup/
```

---

## 📊 **Monitoramento**

### **CloudWatch Logs**

```bash
# Instalar CloudWatch Agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

---

## 🎯 **Custos Estimados (Mensais)**

| Serviço | Configuração | Custo USD |
|---------|-------------|-----------|
| EC2 t3.micro | 1 instância | $8.50 |
| EC2 t3.small | 1 instância | $17.00 |
| RDS MySQL | db.t3.micro | $15.00 |
| Load Balancer | ALB | $22.00 |
| CloudWatch | Básico | $3.00 |
| **Total Básico** | | **~$25-45** |

---

## ✅ **Checklist de Deploy**

- [ ] Instância EC2 criada
- [ ] Security Groups configurados
- [ ] SSH funcionando
- [ ] Python 3.11 instalado
- [ ] MySQL configurado
- [ ] Projeto clonado
- [ ] .env configurado
- [ ] Nginx configurado
- [ ] Serviço systemd criado
- [ ] SSL configurado (opcional)
- [ ] Domínio apontado (opcional)
- [ ] Backup configurado
- [ ] Monitoramento ativo

---

## 🆘 **Troubleshooting**

### **Problemas comuns:**

1. **Erro de conexão MySQL:**
   ```bash
   sudo systemctl status mysql
   sudo mysql -u root -p
   ```

2. **Aplicação não inicia:**
   ```bash
   sudo systemctl status isp-support
   sudo journalctl -u isp-support -f
   ```

3. **Nginx erro 502:**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

---

**🎉 Seu sistema estará rodando em produção na AWS!**