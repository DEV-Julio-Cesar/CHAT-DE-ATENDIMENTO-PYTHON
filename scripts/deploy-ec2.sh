#!/bin/bash

# 🚀 Script de Deploy Automatizado para AWS EC2
# Autor: Sistema ISP Customer Support
# Versão: 2.0.0

set -e  # Parar em caso de erro

echo "🚀 Iniciando deploy na AWS EC2..."
echo "=================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se está rodando como ubuntu
if [ "$USER" != "ubuntu" ]; then
    log_error "Este script deve ser executado como usuário 'ubuntu'"
    exit 1
fi

# Atualizar sistema
log_info "Atualizando sistema..."
sudo apt update && sudo apt upgrade -y
log_success "Sistema atualizado"

# Instalar dependências
log_info "Instalando dependências..."
sudo apt install -y software-properties-common git nginx mysql-server redis-server curl

# Instalar Python 3.11
log_info "Instalando Python 3.11..."
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils

# Instalar pip para Python 3.11
log_info "Instalando pip..."
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.11
log_success "Python 3.11 e pip instalados"

# Clonar repositório se não existir
if [ ! -d "CHAT-DE-ATENDIMENTO-PYTHON" ]; then
    log_info "Clonando repositório..."
    git clone https://github.com/DEV-Julio-Cesar/CHAT-DE-ATENDIMENTO-PYTHON.git
    log_success "Repositório clonado"
else
    log_info "Atualizando repositório..."
    cd CHAT-DE-ATENDIMENTO-PYTHON
    git pull origin main
    cd ..
    log_success "Repositório atualizado"
fi

# Entrar no diretório do projeto
cd CHAT-DE-ATENDIMENTO-PYTHON

# Criar ambiente virtual
log_info "Criando ambiente virtual..."
python3.11 -m venv venv
source venv/bin/activate
log_success "Ambiente virtual criado"

# Instalar dependências Python
log_info "Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt
log_success "Dependências Python instaladas"

# Configurar MySQL
log_info "Configurando MySQL..."
sudo systemctl start mysql
sudo systemctl enable mysql

# Criar banco de dados (se não existir)
mysql -u root -p -e "
CREATE DATABASE IF NOT EXISTS cianet_provedor;
CREATE USER IF NOT EXISTS 'chat_app'@'localhost' IDENTIFIED BY 'ChatApp2024!';
GRANT ALL PRIVILEGES ON cianet_provedor.* TO 'chat_app'@'localhost';
FLUSH PRIVILEGES;
" 2>/dev/null || log_warning "MySQL já configurado ou erro na configuração"

log_success "MySQL configurado"

# Configurar .env se não existir
if [ ! -f ".env" ]; then
    log_info "Criando arquivo .env..."
    cp .env.example .env
    
    # Obter IP público da instância
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    
    # Configurar .env para produção
    sed -i "s/DEBUG=true/DEBUG=false/" .env
    sed -i "s/DATABASE_URL=.*/DATABASE_URL=\"mysql+aiomysql:\/\/chat_app:ChatApp2024!@localhost:3306\/cianet_provedor\"/" .env
    sed -i "s/TRUSTED_HOSTS=.*/TRUSTED_HOSTS=\"localhost,127.0.0.1,$PUBLIC_IP\"/" .env
    sed -i "s/CORS_ORIGINS=.*/CORS_ORIGINS=\"http:\/\/$PUBLIC_IP:8000,http:\/\/$PUBLIC_IP\"/" .env
    
    log_success "Arquivo .env criado e configurado"
else
    log_info "Arquivo .env já existe"
fi

# Configurar Nginx
log_info "Configurando Nginx..."
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

sudo tee /etc/nginx/sites-available/isp-support > /dev/null <<EOF
server {
    listen 80;
    server_name $PUBLIC_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias /home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON/app/web/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Ativar site
sudo ln -sf /etc/nginx/sites-available/isp-support /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Testar configuração Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

log_success "Nginx configurado"

# Criar serviço systemd
log_info "Criando serviço systemd..."
sudo tee /etc/systemd/system/isp-support.service > /dev/null <<EOF
[Unit]
Description=ISP Customer Support
After=network.target mysql.service redis.service
Wants=mysql.service redis.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON
Environment=PATH=/home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON/venv/bin
ExecStart=/home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON/venv/bin/python app/main_web_ready.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recarregar systemd e iniciar serviço
sudo systemctl daemon-reload
sudo systemctl enable isp-support
sudo systemctl start isp-support

log_success "Serviço systemd criado e iniciado"

# Configurar Redis
log_info "Configurando Redis..."
sudo systemctl start redis-server
sudo systemctl enable redis-server
log_success "Redis configurado"

# Configurar firewall
log_info "Configurando firewall..."
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
log_success "Firewall configurado"

# Verificar status dos serviços
log_info "Verificando status dos serviços..."
echo ""
echo "📊 Status dos Serviços:"
echo "======================"

# MySQL
if sudo systemctl is-active --quiet mysql; then
    log_success "MySQL: Ativo"
else
    log_error "MySQL: Inativo"
fi

# Redis
if sudo systemctl is-active --quiet redis-server; then
    log_success "Redis: Ativo"
else
    log_error "Redis: Inativo"
fi

# Nginx
if sudo systemctl is-active --quiet nginx; then
    log_success "Nginx: Ativo"
else
    log_error "Nginx: Inativo"
fi

# Aplicação
if sudo systemctl is-active --quiet isp-support; then
    log_success "ISP Support: Ativo"
else
    log_error "ISP Support: Inativo"
fi

echo ""
echo "🎉 Deploy concluído com sucesso!"
echo "================================"
echo ""
echo "🌐 URLs de Acesso:"
echo "  • Principal: http://$PUBLIC_IP"
echo "  • Login: http://$PUBLIC_IP/login"
echo "  • Dashboard: http://$PUBLIC_IP/dashboard"
echo "  • API Docs: http://$PUBLIC_IP/docs"
echo ""
echo "🔑 Credenciais de Teste:"
echo "  • Email: admin@empresa.com"
echo "  • Senha: admin123"
echo ""
echo "📋 Comandos Úteis:"
echo "  • Ver logs: sudo journalctl -u isp-support -f"
echo "  • Reiniciar: sudo systemctl restart isp-support"
echo "  • Status: sudo systemctl status isp-support"
echo ""
echo "⚠️  Próximos Passos:"
echo "  1. Configure suas credenciais WhatsApp no arquivo .env"
echo "  2. Configure sua chave Gemini AI no arquivo .env"
echo "  3. Configure um domínio personalizado (opcional)"
echo "  4. Configure SSL/HTTPS com Let's Encrypt (recomendado)"
echo ""
log_success "Sistema ISP Customer Support está rodando em produção! 🚀"