#!/bin/bash
# ISP Chat Enterprise - Script de Deploy
# Automatiza o processo de deploy em produção

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções auxiliares
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se Docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker não está instalado!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose não está instalado!"
        exit 1
    fi
    
    log_success "Docker e Docker Compose encontrados"
}

# Verificar arquivo .env
check_env() {
    if [ ! -f ".env" ]; then
        log_warning "Arquivo .env não encontrado, copiando .env.example"
        cp .env.example .env
        log_warning "IMPORTANTE: Configure as variáveis em .env antes de continuar!"
        read -p "Pressione Enter para continuar após configurar o .env..."
    fi
    
    log_success "Arquivo .env encontrado"
}

# Fazer backup do banco de dados
backup_database() {
    log_info "Fazendo backup do banco de dados..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup via Docker (se container estiver rodando)
    if docker ps | grep -q "isp-chat-sqlserver"; then
        docker exec isp-chat-sqlserver /opt/mssql-tools/bin/sqlcmd \
            -S localhost -U sa -P "${SA_PASSWORD:-ISPChat2025!}" \
            -Q "BACKUP DATABASE ISPChat TO DISK = '/var/opt/mssql/backup/ISPChat_$(date +%Y%m%d_%H%M%S).bak'"
        
        log_success "Backup do banco criado"
    else
        log_warning "Container do SQL Server não está rodando, pulando backup"
    fi
}

# Build das imagens
build_images() {
    log_info "Fazendo build das imagens Docker..."
    
    docker-compose build --no-cache
    
    log_success "Build das imagens concluído"
}

# Deploy dos serviços
deploy_services() {
    log_info "Fazendo deploy dos serviços..."
    
    # Parar serviços existentes
    docker-compose down
    
    # Iniciar serviços
    docker-compose up -d
    
    log_success "Serviços iniciados"
}

# Verificar saúde dos serviços
check_health() {
    log_info "Verificando saúde dos serviços..."
    
    # Aguardar serviços ficarem prontos
    sleep 30
    
    # Verificar cada serviço
    services=("api-gateway:8000" "auth-service:8001" "chat-service:8002" "web-interface:3000")
    
    for service in "${services[@]}"; do
        name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        
        if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1 || curl -f -s "http://localhost:$port" > /dev/null 2>&1; then
            log_success "$name está saudável"
        else
            log_error "$name não está respondendo"
        fi
    done
}

# Executar testes
run_tests() {
    log_info "Executando testes..."
    
    # Aguardar serviços estarem prontos
    sleep 10
    
    # Executar testes de funcionalidades
    if [ -f "test-all-features.py" ]; then
        python test-all-features.py
        log_success "Testes executados"
    else
        log_warning "Arquivo de testes não encontrado"
    fi
}

# Mostrar informações de acesso
show_access_info() {
    log_success "Deploy concluído com sucesso!"
    echo ""
    echo "🌐 URLs de Acesso:"
    echo "  • Interface Web: http://localhost:3000"
    echo "  • API Gateway: http://localhost:8000"
    echo "  • Documentação: http://localhost:8000/docs"
    echo "  • Auth Service: http://localhost:8001"
    echo "  • Chat Service: http://localhost:8002"
    echo "  • Prometheus: http://localhost:9090"
    echo "  • Grafana: http://localhost:3001 (admin/admin)"
    echo ""
    echo "📊 Monitoramento:"
    echo "  • Logs: docker-compose logs -f"
    echo "  • Status: docker-compose ps"
    echo "  • Parar: docker-compose down"
    echo ""
    echo "🔐 Credenciais padrão:"
    echo "  • Usuário: admin"
    echo "  • Senha: admin123"
    echo ""
}

# Função principal
main() {
    echo "🚀 ISP Chat Enterprise - Deploy Script"
    echo "======================================"
    
    # Verificações iniciais
    check_docker
    check_env
    
    # Perguntar se deve fazer backup
    read -p "Fazer backup do banco de dados? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        backup_database
    fi
    
    # Build e deploy
    build_images
    deploy_services
    
    # Verificações pós-deploy
    check_health
    
    # Perguntar se deve executar testes
    read -p "Executar testes de funcionalidades? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_tests
    fi
    
    # Mostrar informações
    show_access_info
}

# Executar função principal
main "$@"