Write-Host "Iniciando ISP Customer Support..." -ForegroundColor Green

# Verificar Docker
try {
    docker --version | Out-Null
    Write-Host "Docker encontrado." -ForegroundColor Green
} catch {
    Write-Host "Docker nao esta instalado!" -ForegroundColor Red
    exit 1
}

# Criar diretorios
New-Item -ItemType Directory -Force -Path "uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

Write-Host "Parando containers existentes..." -ForegroundColor Yellow
docker-compose down

Write-Host "Iniciando containers..." -ForegroundColor Blue
docker-compose up -d --build

Write-Host "Aguardando servicos..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "Sistema iniciado!" -ForegroundColor Green
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Usuario: admin / Senha: admin123" -ForegroundColor Yellow