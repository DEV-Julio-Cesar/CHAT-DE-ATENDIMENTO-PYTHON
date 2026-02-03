# ===========================================
# CIANET - Scripts de Deploy e Operações
# ===========================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "logs", "status", "build", "pull", "backup", "clean")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Header($text) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host " $text" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
}

# Check Docker
function Test-Docker {
    try {
        docker info | Out-Null
        return $true
    } catch {
        Write-Host "❌ Docker não está rodando!" -ForegroundColor Red
        return $false
    }
}

# Start services
function Start-Services {
    Write-Header "🚀 Iniciando CIANET WhatsApp Atendimento"
    
    if (-not (Test-Docker)) { return }
    
    Write-Host "📦 Iniciando containers..." -ForegroundColor Yellow
    docker compose up -d
    
    Write-Host ""
    Write-Host "⏳ Aguardando serviços iniciarem..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Show-Status
    
    Write-Host ""
    Write-Host "✅ Sistema iniciado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📍 URLs:" -ForegroundColor Cyan
    Write-Host "   - API:        http://localhost:8000" -ForegroundColor White
    Write-Host "   - WhatsApp:   http://localhost:3001" -ForegroundColor White
    Write-Host "   - Grafana:    http://localhost:3000 (admin/cianet2026)" -ForegroundColor White
    Write-Host "   - Prometheus: http://localhost:9090" -ForegroundColor White
}

# Stop services
function Stop-Services {
    Write-Header "🛑 Parando CIANET WhatsApp Atendimento"
    
    if (-not (Test-Docker)) { return }
    
    docker compose down
    
    Write-Host "✅ Serviços parados!" -ForegroundColor Green
}

# Restart services
function Restart-Services {
    Write-Header "🔄 Reiniciando CIANET WhatsApp Atendimento"
    
    Stop-Services
    Start-Sleep -Seconds 3
    Start-Services
}

# Show logs
function Show-Logs {
    Write-Header "📋 Logs dos Serviços"
    
    if (-not (Test-Docker)) { return }
    
    docker compose logs -f --tail=100
}

# Show status
function Show-Status {
    Write-Header "📊 Status dos Serviços"
    
    if (-not (Test-Docker)) { return }
    
    docker compose ps
    
    Write-Host ""
    Write-Host "🔍 Health Checks:" -ForegroundColor Cyan
    
    # API Health
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
        Write-Host "   ✅ API: Online" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ API: Offline" -ForegroundColor Red
    }
    
    # WhatsApp Health
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:3001/health" -TimeoutSec 5
        Write-Host "   ✅ WhatsApp: Online" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ WhatsApp: Offline" -ForegroundColor Red
    }
    
    # Redis
    try {
        $result = docker exec cianet-redis redis-cli ping 2>$null
        if ($result -eq "PONG") {
            Write-Host "   ✅ Redis: Online" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Redis: Offline" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ❌ Redis: Offline" -ForegroundColor Red
    }
    
    # SQL Server
    try {
        $result = docker exec cianet-sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Cianet@2026" -C -Q "SELECT 1" 2>$null
        Write-Host "   ✅ SQL Server: Online" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️ SQL Server: Verificando..." -ForegroundColor Yellow
    }
}

# Build images
function Build-Images {
    Write-Header "🔨 Building Docker Images"
    
    if (-not (Test-Docker)) { return }
    
    Write-Host "📦 Building API image..." -ForegroundColor Yellow
    docker compose build api
    
    Write-Host "📦 Building WhatsApp image..." -ForegroundColor Yellow
    docker compose build whatsapp
    
    Write-Host "✅ Build concluído!" -ForegroundColor Green
}

# Pull latest images
function Pull-Images {
    Write-Header "📥 Pulling Latest Images"
    
    if (-not (Test-Docker)) { return }
    
    docker compose pull
    
    Write-Host "✅ Pull concluído!" -ForegroundColor Green
}

# Backup
function Create-Backup {
    Write-Header "💾 Criando Backup"
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupDir = "backups/$timestamp"
    
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    Write-Host "📦 Backup do SQL Server..." -ForegroundColor Yellow
    docker exec cianet-sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Cianet@2026" -C -Q "BACKUP DATABASE isp_support TO DISK='/var/opt/mssql/backup.bak'"
    docker cp cianet-sqlserver:/var/opt/mssql/backup.bak "$backupDir/database.bak"
    
    Write-Host "📦 Backup do Redis..." -ForegroundColor Yellow
    docker exec cianet-redis redis-cli BGSAVE
    Start-Sleep -Seconds 5
    docker cp cianet-redis:/data/dump.rdb "$backupDir/redis.rdb"
    
    Write-Host "📦 Backup das sessões WhatsApp..." -ForegroundColor Yellow
    docker cp cianet-whatsapp:/app/sessions "$backupDir/whatsapp-sessions"
    
    Write-Host "✅ Backup criado em: $backupDir" -ForegroundColor Green
}

# Clean up
function Clean-System {
    Write-Header "🧹 Limpando Sistema"
    
    if (-not (Test-Docker)) { return }
    
    Write-Host "🗑️ Removendo containers parados..." -ForegroundColor Yellow
    docker container prune -f
    
    Write-Host "🗑️ Removendo imagens não utilizadas..." -ForegroundColor Yellow
    docker image prune -f
    
    Write-Host "🗑️ Removendo volumes não utilizados..." -ForegroundColor Yellow
    docker volume prune -f
    
    Write-Host "✅ Limpeza concluída!" -ForegroundColor Green
}

# Main
switch ($Action) {
    "start"   { Start-Services }
    "stop"    { Stop-Services }
    "restart" { Restart-Services }
    "logs"    { Show-Logs }
    "status"  { Show-Status }
    "build"   { Build-Images }
    "pull"    { Pull-Images }
    "backup"  { Create-Backup }
    "clean"   { Clean-System }
}
