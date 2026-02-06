# 🚀 Deploy Rápido na AWS - 15 Minutos

## 📋 **Opção 1: Deploy Automático EC2 (Recomendado)**

### **Passo 1: Criar EC2**
1. **AWS Console** → EC2 → Launch Instance
2. **Configurações:**
   - **AMI:** Ubuntu Server 22.04 LTS
   - **Instance:** t3.small (ou t3.micro para teste)
   - **Key Pair:** Criar/usar existente
   - **Security Group:** 
     - SSH (22) - Seu IP
     - HTTP (80) - 0.0.0.0/0
     - Custom (8000) - 0.0.0.0/0

### **Passo 2: Conectar e Executar Script**
```bash
# Conectar via SSH
ssh -i "sua-chave.pem" ubuntu@SEU-IP-PUBLICO

# Executar script de deploy automático
curl -sSL https://raw.githubusercontent.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON/main/scripts/deploy-ec2.sh | bash
```

### **Passo 3: Configurar Credenciais**
```bash
# Editar arquivo .env
nano CHAT-DE-ATENDIMENTO-PYTHON/.env

# Configurar:
# - WHATSAPP_ACCESS_TOKEN
# - GEMINI_API_KEY
# - SECRET_KEY (gerar nova)

# Reiniciar aplicação
sudo systemctl restart isp-support
```

**✅ Pronto! Acesse: http://SEU-IP-PUBLICO**

---

## 📋 **Opção 2: Deploy Manual Rápido**

### **Comandos Essenciais:**
```bash
# 1. Atualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependências
sudo apt install -y python3.11 python3.11-venv git nginx mysql-server

# 3. Clonar projeto
git clone https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON.git
cd CHAT-DE-ATENDIMENTO-PYTHON

# 4. Configurar Python
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Configurar MySQL
sudo mysql -e "CREATE DATABASE cianet_provedor; CREATE USER 'chat_app'@'localhost' IDENTIFIED BY 'ChatApp2024!'; GRANT ALL PRIVILEGES ON cianet_provedor.* TO 'chat_app'@'localhost'; FLUSH PRIVILEGES;"

# 6. Configurar .env
cp .env.example .env
# Editar .env com suas credenciais

# 7. Executar aplicação
python app/main_web_ready.py
```

---

## 📋 **Opção 3: Docker (Mais Rápido)**

```bash
# 1. Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 2. Clonar e executar
git clone https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON.git
cd CHAT-DE-ATENDIMENTO-PYTHON

# 3. Configurar variáveis
cp .env.production .env
# Editar .env

# 4. Executar com Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔧 **Configurações Essenciais**

### **1. WhatsApp Business API**
```env
WHATSAPP_ACCESS_TOKEN="EAAxxxxx"  # Token permanente
WHATSAPP_PHONE_NUMBER_ID="123456789"
WHATSAPP_WEBHOOK_VERIFY_TOKEN="meu_token_123"
```

### **2. Google Gemini AI**
```env
GEMINI_API_KEY="AIzaxxxxx"  # Chave da API
```

### **3. Segurança**
```env
SECRET_KEY="chave-super-secreta-32-caracteres-minimo"
DEBUG=false
TRUSTED_HOSTS="seu-ip-aws,seu-dominio.com"
```

---

## 🌐 **URLs Após Deploy**

- **Principal:** http://SEU-IP-PUBLICO
- **Login:** http://SEU-IP-PUBLICO/login
- **Dashboard:** http://SEU-IP-PUBLICO/dashboard
- **API Docs:** http://SEU-IP-PUBLICO/docs

**Credenciais de teste:** admin@empresa.com / admin123

---

## 🔒 **SSL/HTTPS (Opcional)**

```bash
# Se tiver domínio próprio
./scripts/setup-ssl.sh seu-dominio.com
```

---

## 📊 **Monitoramento**

- **Logs:** `sudo journalctl -u isp-support -f`
- **Status:** `sudo systemctl status isp-support`
- **Reiniciar:** `sudo systemctl restart isp-support`

---

## 💰 **Custos AWS (Estimativa Mensal)**

| Configuração | Custo USD |
|-------------|-----------|
| EC2 t3.micro | $8.50 |
| EC2 t3.small | $17.00 |
| Tráfego (100GB) | $9.00 |
| **Total** | **$17-26** |

---

## ✅ **Checklist Final**

- [ ] EC2 criada e rodando
- [ ] Script executado com sucesso
- [ ] .env configurado
- [ ] WhatsApp API configurada
- [ ] Gemini AI configurada
- [ ] Login funcionando
- [ ] Dashboard acessível
- [ ] SSL configurado (se aplicável)

**🎉 Sistema em produção em 15 minutos!**