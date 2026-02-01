# ISP Chat Enterprise - Script de Deploy PowerShell
# Automatiza o processo de deploy em produção no Windows

param(
    [switch]$SkipBackup,
    [switch]$SkipTests,
    [switch]$Development
)

# Configurar cores
$Host.UI.RawUI.ForegroundColor = "White"

function Write-Info {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Verificar se Docker está instalado
function Test-Docker {
    Write-Info "Verificando Docker..."
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker não está instalado!"
        exit 1
    }
    
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Docker Compose não está instalado!"
        exit 1
    }
    
    Write-Success "Docker e Docker Compose encontrados"
}

# Verificar arquivo .env
function Test-Environment {
    Write-Info "Verificando arquivo .env..."
    
    if (-not (Test-Path ".env")) {
        Write-Warning "Arquivo .env não encontrado, copiando .env.example"
        Copy-Item ".env.example" ".env"
        Write-Warning "IMPORTANTE: Configure as variáveis em .env antes de continuar!"
        Read-Host "Pressione Enter para continuar após configurar o .env"
    }
    
    Write-Success "Arquivo .env encontrado"
}

# Fazer backup do banco de dados
function Backup-Database {
    if ($SkipBackup) {
        Write-Info "Pulando backup (parâmetro -SkipBackup)"
        return
    }
    
    Write-Info "Fazendo backup do banco de dados..."
    
    $BackupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    
    # Verificar se container está rodando
    $SqlContainer = docker ps --filter "name=isp-chat-sqlserver" --format "{{.Names}}"
    
    if ($SqlContainer) {
        $Password = $env:SA_PASSWORD
        if (-not $Password) { $Password = "ISPChat2025!" }
        
        $BackupFile = "ISPChat_$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
        
        docker exec isp-chat-sqlserver /opt/mssql-tools/bin/sqlcmd `
            -S localhost -U sa -P $Password `
            -Q "BACKUP DATABASE ISPChat TO DISK = '/var/opt/mssql/backup/$BackupFile'"
        
        Write-Success "Backup do banco criado: $BackupFile"
    } else {
        Write-Warning "Container do SQL Server não está rodando, pulando backup"
    }
}

# Build das imagens
function Build-Images {
    Write-Info "Fazendo build das imagens Docker..."
    
    docker-compose build --no-cache
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Build das imagens concluído"
    } else {
        Write-Error "Erro no build das imagens"
        exit 1
    }
}

# Deploy dos serviços
function Deploy-Services {
    Write-Info "Fazendo deploy dos serviços..."
    
    # Parar serviços existentes
    docker-compose down
    
    # Escolher arquivo de compose baseado no ambiente
    $ComposeFile = if ($Development) { "docker-compose.dev.yml" } else { "docker-compose.yml" }
    
    if (Test-Path $ComposeFile) {
        docker-compose -f $ComposeFile up -d
    } else {
        docker-compose up -d
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Serviços iniciados"
    } else {
        Write-Error "Erro ao iniciar serviços"
        exit 1
    }
}

# Verificar saúde dos serviços
function Test-ServiceHealth {
    Write-Info "Verificando saúde dos serviços..."
    
    # Aguardar serviços ficarem prontos
    Start-Sleep -Seconds 30
    
    $Services = @(
        @{Name="API Gateway"; Port=8000; Path="/health"},
        @{Name="Auth Service"; Port=8001; Path="/health"},
        @{Name="Chat Service"; Port=8002; Path="/health"},
        @{Name="Web Interface"; Port=3000; Path="/"}
    )
    
    foreach ($Service in $Services) {
        try {
            $Url = "http://localhost:$($Service.Port)$($Service.Path)"
            $Response = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -UseBasicParsing
            
            if ($Response.StatusCode -eq 200) {
                Write-Success "$($Service.Name) está saudável"
            } else {
                Write-Warning "$($Service.Name) retornou status $($Response.StatusCode)"
            }
        } catch {
            Write-Error "$($Service.Name) não está respondendo"
        }
    }
}

# Executar testes
function Invoke-Tests {
    if ($SkipTests) {
        Write-Info "Pulando testes (parâmetro -SkipTests)"
        return
    }
    
    Write-Info "Executando testes..."
    
    # Aguardar serviços estarem prontos
    Start-Sleep -Seconds 10
    
    # Executar testes de funcionalidades
    if (Test-Path "test-all-features.py") {
        python test-all-features.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Testes executados com sucesso"
        } else {
            Write-Warning "Alguns testes falharam"
        }
    } else {
        Write-Warning "Arquivo de testes não encontrado"
    }
}

# Mostrar informações de acesso
function Show-AccessInfo {
    Write-Success "Deploy concluído com sucesso!"
    Write-Host ""
    Write-Host "🌐 URLs de Acesso:" -ForegroundColor Cyan
    Write-Host "  • Interface Web: http://localhost:3000" -ForegroundColor White
    Write-Host "  • API Gateway: http://localhost:8000" -ForegroundColor White
    Write-Host "  • Documentação: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  • Auth Service: http://localhost:8001" -ForegroundColor White
    Write-Host "  • Chat Service: http://localhost:8002" -ForegroundColor White
    Write-Host "  • Prometheus: http://localhost:9090" -ForegroundColor White
    Write-Host "  • Grafana: http://localhost:3001 (admin/admin)" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 Comandos úteis:" -ForegroundColor Cyan
    Write-Host "  • Logs: docker-compose logs -f" -ForegroundColor White
    Write-Host "  • Status: docker-compose ps" -ForegroundColor White
    Write-Host "  • Parar: docker-compose down" -ForegroundColor White
    Write-Host "  • Reiniciar: docker-compose restart" -ForegroundColor White
    Write-Host ""
    Write-Host "🔐 Credenciais padrão:" -ForegroundColor Cyan
    Write-Host "  • Usuário: admin" -ForegroundColor White
    Write-Host "  • Senha: admin123" -ForegroundColor White
    Write-Host ""
}

# Função principal
function Main {
    Write-Host "🚀 ISP Chat Enterprise - Deploy Script" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
    Write-Host ""
    
    # Verificações iniciais
    Test-Docker
    Test-Environment
    
    # Backup
    if (-not $SkipBackup) {
        $BackupChoice = Read-Host "Fazer backup do banco de dados? (y/N)"
        if ($BackupChoice -match "^[Yy]") {
            Backup-Database
        }
    }
    
    # Build e deploy
    Build-Images
    Deploy-Services
    
    # Verificações pós-deploy
    Test-ServiceHealth
    
    # Testes
    if (-not $SkipTests) {
        $TestChoice = Read-Host "Executar testes de funcionalidades? (y/N)"
        if ($TestChoice -match "^[Yy]") {
            Invoke-Tests
        }
    }
    
    # Mostrar informações
    Show-AccessInfo
}

# Executar função principal
try {
    Main
} catch {
    Write-Error "Erro durante o deploy: $($_.Exception.Message)"
    exit 1
}