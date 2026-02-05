#!/bin/bash

# 🔒 Script para configurar SSL/HTTPS com Let's Encrypt
# Autor: Sistema ISP Customer Support

set -e

echo "🔒 Configurando SSL/HTTPS com Let's Encrypt..."
echo "=============================================="

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se o domínio foi fornecido
if [ -z "$1" ]; then
    log_error "Uso: $0 <seu-dominio.com>"
    echo "Exemplo: $0 meusite.com"
    exit 1
fi

DOMAIN=$1

log_info "Configurando SSL para domínio: $DOMAIN"

# Instalar Certbot
log_info "Instalando Certbot..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Verificar se Nginx está rodando
if ! sudo systemctl is-active --quiet nginx; then
    log_error "Nginx não está rodando. Inicie o Nginx primeiro."
    exit 1
fi

# Obter certificado SSL
log_info "Obtendo certificado SSL..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# Configurar renovação automática
log_info "Configurando renovação automática..."
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

# Testar renovação
log_info "Testando renovação..."
sudo certbot renew --dry-run

# Atualizar configuração do .env
log_info "Atualizando configuração..."
cd /home/ubuntu/CHAT-DE-ATENDIMENTO-PYTHON
sed -i "s/TRUSTED_HOSTS=.*/TRUSTED_HOSTS=\"$DOMAIN,*.$DOMAIN\"/" .env
sed -i "s/CORS_ORIGINS=.*/CORS_ORIGINS=\"https:\/\/$DOMAIN\"/" .env

# Reiniciar serviços
sudo systemctl restart isp-support
sudo systemctl restart nginx

log_success "SSL configurado com sucesso!"
echo ""
echo "🌐 Seu site agora está disponível em:"
echo "  • https://$DOMAIN"
echo "  • https://$DOMAIN/login"
echo "  • https://$DOMAIN/dashboard"
echo ""
echo "🔒 Certificado SSL válido por 90 dias"
echo "🔄 Renovação automática configurada"