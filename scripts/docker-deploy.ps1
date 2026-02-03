# Script de Deploy Docker - CIANET Atendimento
# Versão: 3.0
#
# Uso:
#   .\scripts\docker-deploy.ps1 [up|down|logs|test|build]

param(
    [Parameter(Position=0)]
    [string]$Action = "up"
)

$ErrorActionPreference = "Stop"

# Cores
function Write-Color($Text, $Color) {
    $colors = @{
        "Green" = "Green"
        "Red" = "Red"
        "Yellow" = "Yellow"
        "Cyan" = "Cyan"
    }
    Write-Host $Text -ForegroundColor $colors[$Color]
}

# Banner
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  🟢 CIANET ATENDIMENTO - DOCKER DEPLOY" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Diretório do projeto
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$InfraDir = Join-Path $ProjectRoot "infra"

# Verificar Docker
try {
    docker --version | Out-Null
} catch {
    Write-Color "❌ Docker não encontrado. Instale o Docker Desktop." "Red"
    exit 1
}

# Verificar Docker Compose
try {
    docker compose version | Out-Null
} catch {
    Write-Color "❌ Docker Compose não encontrado." "Red"
    exit 1
}

Write-Color "📁 Diretório: $ProjectRoot" "Cyan"
Write-Host ""

switch ($Action.ToLower()) {
    "up" {
        Write-Color "🚀 Iniciando containers..." "Yellow"
        
        # Criar .env se não existir
        $EnvFile = Join-Path $InfraDir ".env"
        if (-not (Test-Path $EnvFile)) {
            Write-Color "📝 Criando arquivo .env..." "Yellow"
            @"
# CIANET Atendimento - Variáveis de Ambiente
SECRET_KEY=cianet-super-secret-key-production-2024
DEBUG=false

# WhatsApp Business API (opcional)
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=cianet-webhook-verify

# Google Gemini AI (opcional)
GEMINI_API_KEY=
"@ | Out-File -FilePath $EnvFile -Encoding UTF8
        }
        
        # Subir containers
        Set-Location $InfraDir
        docker compose -f docker-compose.sqlserver.yml up -d
        
        Write-Host ""
        Write-Color "✅ Containers iniciados!" "Green"
        Write-Host ""
        Write-Host "📊 Serviços disponíveis:"
        Write-Host "   API:        http://localhost:8000"
        Write-Host "   Docs:       http://localhost:8000/docs"
        Write-Host "   Mobile:     http://localhost:8000/mobile"
        Write-Host "   Grafana:    http://localhost:3000 (admin/cianet2024)"
        Write-Host "   Prometheus: http://localhost:9090"
        Write-Host ""
    }
    
    "down" {
        Write-Color "🛑 Parando containers..." "Yellow"
        Set-Location $InfraDir
        docker compose -f docker-compose.sqlserver.yml down
        Write-Color "✅ Containers parados!" "Green"
    }
    
    "logs" {
        Write-Color "📋 Logs dos containers:" "Cyan"
        Set-Location $InfraDir
        docker compose -f docker-compose.sqlserver.yml logs -f --tail=100
    }
    
    "test" {
        Write-Color "🧪 Executando testes do stack..." "Yellow"
        $TestScript = Join-Path $ProjectRoot "scripts\test_docker_stack.py"
        python $TestScript
    }
    
    "build" {
        Write-Color "🔨 Reconstruindo imagens..." "Yellow"
        Set-Location $InfraDir
        docker compose -f docker-compose.sqlserver.yml build --no-cache
        Write-Color "✅ Imagens reconstruídas!" "Green"
    }
    
    "restart" {
        Write-Color "🔄 Reiniciando containers..." "Yellow"
        Set-Location $InfraDir
        docker compose -f docker-compose.sqlserver.yml restart
        Write-Color "✅ Containers reiniciados!" "Green"
    }
    
    "status" {
        Write-Color "📊 Status dos containers:" "Cyan"
        Set-Location $InfraDir
        docker compose -f docker-compose.sqlserver.yml ps
    }
    
    default {
        Write-Host "Uso: .\docker-deploy.ps1 [comando]"
        Write-Host ""
        Write-Host "Comandos:"
        Write-Host "  up      - Inicia todos os containers"
        Write-Host "  down    - Para todos os containers"
        Write-Host "  logs    - Mostra logs dos containers"
        Write-Host "  test    - Executa testes do stack"
        Write-Host "  build   - Reconstrói as imagens"
        Write-Host "  restart - Reinicia os containers"
        Write-Host "  status  - Mostra status dos containers"
    }
}

Set-Location $ProjectRoot
