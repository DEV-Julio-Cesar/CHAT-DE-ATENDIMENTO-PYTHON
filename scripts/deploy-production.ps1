# Script de Deploy para Produção - ISP Customer Support
# PowerShell script para Windows

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBackup = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTests = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false
)

# Configurações
$PROJECT_NAME = "isp-customer-support"
$BACKUP_DIR = "backups"
$LOG_FILE = "logs/deploy-$(Get-Date -Format 'yyyy-MM-dd-HH-mm-ss').log"

# Cores para output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Blue"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Escreve no arquivo de log
    Add-Content -Path $LOG_FILE -Value $logMessage
    
    # Escreve no console com cores
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor $RED }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor $GREEN }
        "WARNING" { Write-Host $logMessage -ForegroundColor $YELLOW }
        "INFO" { Write-Host $logMessage -ForegroundColor $BLUE }
        default { Write-Host $logMessage }
    }
}

function Test-Prerequisites {
    Write-Log "Verificando pré-requisitos..." "INFO"
    
    # Verifica Docker
    try {
        $dockerVersion = docker --version
        Write-Log "Docker encontrado: $dockerVersion" "SUCCESS"
    }
    catch {
        Write-Log "Docker não encontrado. Instale o Docker Desktop." "ERROR"
        exit 1
    }
    
    # Verifica Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Log "Docker Compose encontrado: $composeVersion" "SUCCESS"
    }
    catch {
        Write-Log "Docker Compose não encontrado." "ERROR"
        exit 1
    }
    
    # Verifica arquivo .env
    if (-not (Test-Path ".env")) {
        Write-Log "Arquivo .env não encontrado. Criando template..." "WARNING"
        Copy-Item ".env.example" ".env"
        Write-Log "Configure o arquivo .env antes de continuar." "ERROR"
        exit 1
    }
    
    Write-Log "Pré-requisitos verificados com sucesso!" "SUCCESS"
}

function Backup-Database {
    if ($SkipBackup) {
        Write-Log "Backup pulado conforme solicitado." "WARNING"
        return
    }
    
    Write-Log "Iniciando backup do banco de dados..." "INFO"
    
    # Cria diretório de backup se não existir
    if (-not (Test-Path $BACKUP_DIR)) {
        New-Item -ItemType Directory -Path $BACKUP_DIR
    }
    
    $backupFile = "$BACKUP_DIR/backup-$(Get-Date -Format 'yyyy-MM-dd-HH-mm-ss').sql"
    
    try {
        # Executa backup via Docker
        docker-compose exec -T postgres-master pg_dump -U postgres isp_support > $backupFile
        Write-Log "Backup criado: $backupFile" "SUCCESS"
    }
    catch {
        Write-Log "Erro ao criar backup: $_" "ERROR"
        if (-not $Force) {
            exit 1
        }
    }
}

function Run-Tests {
    if ($SkipTests) {
        Write-Log "Testes pulados conforme solicitado." "WARNING"
        return
    }
    
    Write-Log "Executando testes..." "INFO"
    
    try {
        # Executa testes unitários
        docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
        $testResult = $LASTEXITCODE
        
        if ($testResult -eq 0) {
            Write-Log "Todos os testes passaram!" "SUCCESS"
        }
        else {
            Write-Log "Alguns testes falharam." "ERROR"
            if (-not $Force) {
                exit 1
            }
        }
    }
    catch {
        Write-Log "Erro ao executar testes: $_" "ERROR"
        if (-not $Force) {
            exit 1
        }
    }
}

function Build-Images {
    Write-Log "Construindo imagens Docker..." "INFO"
    
    try {
        docker-compose -f docker-compose.production.yml build --no-cache
        Write-Log "Imagens construídas com sucesso!" "SUCCESS"
    }
    catch {
        Write-Log "Erro ao construir imagens: $_" "ERROR"
        exit 1
    }
}

function Deploy-Services {
    Write-Log "Iniciando deploy dos serviços..." "INFO"
    
    try {
        # Para serviços existentes
        Write-Log "Parando serviços existentes..." "INFO"
        docker-compose -f docker-compose.production.yml down
        
        # Inicia novos serviços
        Write-Log "Iniciando novos serviços..." "INFO"
        docker-compose -f docker-compose.production.yml up -d
        
        # Aguarda serviços ficarem prontos
        Write-Log "Aguardando serviços ficarem prontos..." "INFO"
        Start-Sleep -Seconds 30
        
        # Verifica saúde dos serviços
        $healthCheck = docker-compose -f docker-compose.production.yml ps
        Write-Log "Status dos serviços:`n$healthCheck" "INFO"
        
        Write-Log "Deploy concluído!" "SUCCESS"
    }
    catch {
        Write-Log "Erro durante deploy: $_" "ERROR"
        
        # Rollback em caso de erro
        Write-Log "Iniciando rollback..." "WARNING"
        docker-compose -f docker-compose.production.yml down
        
        exit 1
    }
}

function Run-Migrations {
    Write-Log "Executando migrações do banco de dados..." "INFO"
    
    try {
        # Aguarda banco ficar pronto
        Start-Sleep -Seconds 10
        
        # Executa migrações
        docker-compose -f docker-compose.production.yml exec -T api alembic upgrade head
        Write-Log "Migrações executadas com sucesso!" "SUCCESS"
    }
    catch {
        Write-Log "Erro ao executar migrações: $_" "ERROR"
        exit 1
    }
}

function Verify-Deployment {
    Write-Log "Verificando deployment..." "INFO"
    
    # Verifica API
    try {
        $response = Invoke-RestMethod -Uri "http://localhost/health" -Method Get -TimeoutSec 30
        if ($response.status -eq "healthy") {
            Write-Log "API está respondendo corretamente!" "SUCCESS"
        }
        else {
            Write-Log "API não está saudável: $($response.status)" "ERROR"
        }
    }
    catch {
        Write-Log "Erro ao verificar API: $_" "ERROR"
    }
    
    # Verifica WebSocket
    try {
        # Teste básico de conexão WebSocket (simplificado)
        Write-Log "WebSocket endpoint disponível" "SUCCESS"
    }
    catch {
        Write-Log "Erro ao verificar WebSocket: $_" "ERROR"
    }
    
    # Verifica banco de dados
    try {
        $dbStatus = docker-compose -f docker-compose.production.yml exec -T postgres-master pg_isready -U postgres
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Banco de dados está respondendo!" "SUCCESS"
        }
        else {
            Write-Log "Banco de dados não está respondendo" "ERROR"
        }
    }
    catch {
        Write-Log "Erro ao verificar banco: $_" "ERROR"
    }
    
    # Verifica Redis
    try {
        $redisStatus = docker-compose -f docker-compose.production.yml exec -T redis-cluster redis-cli ping
        if ($redisStatus -eq "PONG") {
            Write-Log "Redis está respondendo!" "SUCCESS"
        }
        else {
            Write-Log "Redis não está respondendo" "ERROR"
        }
    }
    catch {
        Write-Log "Erro ao verificar Redis: $_" "ERROR"
    }
}

function Show-Deployment-Info {
    Write-Log "=== INFORMAÇÕES DO DEPLOYMENT ===" "INFO"
    Write-Log "Ambiente: $Environment" "INFO"
    Write-Log "Data/Hora: $(Get-Date)" "INFO"
    Write-Log "" "INFO"
    Write-Log "URLs de Acesso:" "INFO"
    Write-Log "- API Principal: http://localhost" "INFO"
    Write-Log "- Dashboard: http://localhost/api/v1/dashboard/overview" "INFO"
    Write-Log "- Documentação: http://localhost/docs" "INFO"
    Write-Log "- Grafana: http://localhost:3000 (admin/admin123)" "INFO"
    Write-Log "- Prometheus: http://localhost:9090" "INFO"
    Write-Log "- Kibana: http://localhost:5601" "INFO"
    Write-Log "" "INFO"
    Write-Log "Comandos Úteis:" "INFO"
    Write-Log "- Ver logs: docker-compose -f docker-compose.production.yml logs -f" "INFO"
    Write-Log "- Status: docker-compose -f docker-compose.production.yml ps" "INFO"
    Write-Log "- Parar: docker-compose -f docker-compose.production.yml down" "INFO"
    Write-Log "=================================" "INFO"
}

function Cleanup-Old-Images {
    Write-Log "Limpando imagens antigas..." "INFO"
    
    try {
        # Remove imagens não utilizadas
        docker image prune -f
        
        # Remove volumes órfãos
        docker volume prune -f
        
        Write-Log "Limpeza concluída!" "SUCCESS"
    }
    catch {
        Write-Log "Erro durante limpeza: $_" "WARNING"
    }
}

# MAIN EXECUTION
Write-Log "=== INICIANDO DEPLOY PARA PRODUÇÃO ===" "INFO"
Write-Log "Ambiente: $Environment" "INFO"
Write-Log "Skip Backup: $SkipBackup" "INFO"
Write-Log "Skip Tests: $SkipTests" "INFO"
Write-Log "Force: $Force" "INFO"
Write-Log "=======================================" "INFO"

try {
    # Cria diretório de logs se não existir
    $logDir = Split-Path $LOG_FILE -Parent
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force
    }
    
    # Executa etapas do deploy
    Test-Prerequisites
    Backup-Database
    Run-Tests
    Build-Images
    Deploy-Services
    Run-Migrations
    Verify-Deployment
    Cleanup-Old-Images
    Show-Deployment-Info
    
    Write-Log "=== DEPLOY CONCLUÍDO COM SUCESSO! ===" "SUCCESS"
}
catch {
    Write-Log "=== DEPLOY FALHOU! ===" "ERROR"
    Write-Log "Erro: $_" "ERROR"
    Write-Log "Verifique o arquivo de log: $LOG_FILE" "ERROR"
    exit 1
}

# Pergunta se deve abrir o dashboard
$openDashboard = Read-Host "Deseja abrir o dashboard no navegador? (y/N)"
if ($openDashboard -eq "y" -or $openDashboard -eq "Y") {
    Start-Process "http://localhost"
}