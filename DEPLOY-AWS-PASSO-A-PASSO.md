# 🚀 Deploy na AWS - Guia Passo a Passo

## ✅ PRÉ-REQUISITOS

Antes de começar, você precisa ter:
- [ ] Conta AWS criada e ativa
- [ ] Cartão de crédito cadastrado na AWS
- [ ] Chave WhatsApp Business API (opcional para teste inicial)
- [ ] Chave Google Gemini AI: `AIzaSyD3meBJ3Qhtrqyzyb3u9L53OyZsC1sPDyE` ✅

---

## 📋 OPÇÃO 1: DEPLOY AUTOMÁTICO (RECOMENDADO - 15 MINUTOS)

### **PASSO 1: Criar Instância EC2**

1. **Acesse AWS Console:** https://console.aws.amazon.com/
2. **Vá para EC2:** Serviços → EC2 → Launch Instance
3. **Configure a instância:**

   **Nome:** `CIANET-PROVEDOR`
   
   **AMI:** Ubuntu Server 22.04 LTS (Free tier eligible)
   
   **Instance Type:** 
   - Para teste: `t2.micro` (Free tier)
   - Para produção: `t3.small` ou `t3.medium`
   
   **Key Pair:**
   - Clique em "Create new key pair"
   - Nome: `isp-support-key`
   - Tipo: RSA
   - Formato: `.pem` (para SSH) ou `.ppk` (para PuTTY)
   - **IMPORTANTE:** Salve o arquivo `.pem` em local seguro!
   
   **Network Settings:**
   - Clique em "Edit"
   - Marque: "Allow SSH traffic from" → "My IP"
   - Marque: "Allow HTTP traffic from the internet"
   - Adicione regra customizada:
     - Type: Custom TCP
     - Port: 8000
     - Source: 0.0.0.0/0
   
   **Storage:** 20 GB (mínimo)
   
4. **Clique em "Launch Instance"**
5. **Aguarde 2-3 minutos** até a instância estar "Running"
6. **Anote o IP Público** da instância (ex: 54.123.45.67)

---

### **PASSO 2: Conectar na Instância**

#### **Windows (PowerShell):**
```powershell
# Navegar até a pasta onde salvou a chave .pem
cd C:\Users\SEU_USUARIO\Downloads

# Conectar via SSH
ssh -i "cianet-provedor-key.pem" ubuntu@SEU-IP-PUBLICO
```

#### **Windows (PuTTY):**
1. Abra PuTTY
2. Host Name: `ubuntu@SEU-IP-PUBLICO`
3. Connection → SSH → Auth → Browse → Selecione o arquivo `.ppk`
4. Clique em "Open"

---

### **PASSO 3: Executar Script de Deploy Automático**

Após conectar via SSH, execute:

```bash
# Baixar e executar script de deploy
curl -sSL https://raw.githubusercontent.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON/main/scripts/deploy-ec2.sh | bash
```

**O script vai:**
- ✅ Instalar Python 3.11
- ✅ Instalar MySQL, Redis, Nginx
- ✅ Clonar o projeto
- ✅ Configurar banco de dados
- ✅ Instalar dependências
- ✅ Configurar serviços
- ✅ Iniciar aplicação

**Tempo estimado:** 10-15 minutos

---

### **PASSO 4: Configurar Credenciais**

Após o script terminar, configure suas credenciais:

```bash
# Entrar no diretório do projeto
cd CHAT-DE-ATENDIMENTO-PYTHON

# Editar arquivo .env
nano .env
```

**Configurações obrigatórias:**

```env
# Gemini AI (já temos a chave)
GEMINI_API_KEY="AIzaSyD3meBJ3Qhtrqyzyb3u9L53OyZsC1sPDyE"

# Segurança (gerar nova chave)
SECRET_KEY="sua-chave-super-secreta-de-producao-32-caracteres-minimo"

# WhatsApp (opcional - pode configurar depois)
WHATSAPP_ACCESS_TOKEN="seu_token_aqui"
WHATSAPP_PHONE_NUMBER_ID="seu_phone_id"
```

**Para salvar no nano:**
- Pressione `Ctrl + X`
- Digite `Y` para confirmar
- Pressione `Enter`

---

### **PASSO 5: Reiniciar Aplicação**

```bash
# Reiniciar serviço
sudo systemctl restart isp-support

# Verificar status
sudo systemctl status isp-support

# Ver logs em tempo real
sudo journalctl -u isp-support -f
```

---

### **PASSO 6: Testar Aplicação**

Abra no navegador:

- **Principal:** `http://SEU-IP-PUBLICO`
- **Login:** `http://SEU-IP-PUBLICO/login`
- **Dashboard:** `http://SEU-IP-PUBLICO/dashboard`
- **API Docs:** `http://SEU-IP-PUBLICO/docs`

**Credenciais de teste:**
- Email: `admin@empresa.com`
- Senha: `admin123`

---

## 📋 OPÇÃO 2: DEPLOY MANUAL (SE O SCRIPT FALHAR)

### **Comandos passo a passo:**

```bash
# 1. Atualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 3. Instalar pip
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.11

# 4. Instalar dependências
sudo apt install -y git nginx mysql-server redis-server

# 5. Clonar projeto
git clone https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON.git
cd CHAT-DE-ATENDIMENTO-PYTHON

# 6. Criar ambiente virtual
python3.11 -m venv venv
source venv/bin/activate

# 7. Instalar dependências Python
pip install -r requirements.txt

# 8. Configurar MySQL
sudo mysql -e "CREATE DATABASE cianet_provedor; CREATE USER 'chat_app'@'localhost' IDENTIFIED BY 'ChatApp2024!'; GRANT ALL PRIVILEGES ON cianet_provedor.* TO 'chat_app'@'localhost'; FLUSH PRIVILEGES;"

# 9. Configurar .env
cp .env.example .env
nano .env  # Editar com suas credenciais

# 10. Executar aplicação
python app/main_web_ready.py
```

---

## 🔧 COMANDOS ÚTEIS

### **Gerenciar Aplicação:**
```bash
# Ver logs em tempo real
sudo journalctl -u isp-support -f

# Reiniciar aplicação
sudo systemctl restart isp-support

# Parar aplicação
sudo systemctl stop isp-support

# Iniciar aplicação
sudo systemctl start isp-support

# Ver status
sudo systemctl status isp-support
```

### **Gerenciar Nginx:**
```bash
# Reiniciar Nginx
sudo systemctl restart nginx

# Testar configuração
sudo nginx -t

# Ver logs
sudo tail -f /var/log/nginx/error.log
```

### **Gerenciar MySQL:**
```bash
# Acessar MySQL
sudo mysql -u root -p

# Ver bancos de dados
sudo mysql -e "SHOW DATABASES;"

# Backup do banco
mysqldump -u chat_app -p cianet_provedor > backup.sql
```

---

## 🔒 CONFIGURAR SSL/HTTPS (OPCIONAL)

Se você tiver um domínio próprio:

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado SSL
sudo certbot --nginx -d seu-dominio.com

# Renovação automática
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 📊 MONITORAMENTO

### **Verificar recursos do servidor:**
```bash
# CPU e memória
htop

# Espaço em disco
df -h

# Processos Python
ps aux | grep python

# Conexões de rede
netstat -tulpn | grep :8000
```

---

## 🆘 TROUBLESHOOTING

### **Problema: Aplicação não inicia**
```bash
# Ver logs detalhados
sudo journalctl -u isp-support -n 100 --no-pager

# Verificar se a porta 8000 está em uso
sudo lsof -i :8000

# Matar processo na porta 8000
sudo kill -9 $(sudo lsof -t -i:8000)
```

### **Problema: Erro de conexão MySQL**
```bash
# Verificar status MySQL
sudo systemctl status mysql

# Reiniciar MySQL
sudo systemctl restart mysql

# Testar conexão
mysql -u chat_app -p -e "USE cianet_provedor; SHOW TABLES;"
```

### **Problema: Nginx erro 502**
```bash
# Verificar se aplicação está rodando
sudo systemctl status isp-support

# Verificar configuração Nginx
sudo nginx -t

# Ver logs Nginx
sudo tail -f /var/log/nginx/error.log
```

---

## 💰 CUSTOS AWS (ESTIMATIVA MENSAL)

| Configuração | Custo USD/mês |
|-------------|---------------|
| EC2 t2.micro (Free Tier) | $0 (primeiro ano) |
| EC2 t3.small | ~$17 |
| EC2 t3.medium | ~$34 |
| Tráfego 100GB | ~$9 |
| **Total Mínimo** | **$0-26** |

---

## ✅ CHECKLIST FINAL

- [ ] Instância EC2 criada
- [ ] SSH funcionando
- [ ] Script de deploy executado
- [ ] Aplicação rodando
- [ ] MySQL configurado
- [ ] .env configurado com Gemini API
- [ ] Login funcionando
- [ ] Dashboard acessível
- [ ] Todas as páginas carregando

---

## 🎯 PRÓXIMOS PASSOS

1. **Configurar WhatsApp Business API** (quando tiver as credenciais)
2. **Configurar domínio personalizado** (opcional)
3. **Configurar SSL/HTTPS** (recomendado para produção)
4. **Configurar backup automático**
5. **Configurar monitoramento com CloudWatch**

---

## 📞 SUPORTE

Se tiver problemas:
1. Verifique os logs: `sudo journalctl -u isp-support -f`
2. Verifique o status: `sudo systemctl status isp-support`
3. Reinicie a aplicação: `sudo systemctl restart isp-support`

---

**🚀 Seu sistema estará rodando em produção na AWS!**
