# Script para iniciar todos os serviços CIANET
# Execute este script para iniciar o sistema completo

Write-Host "═══════════════════════════════════════════" -ForegroundColor Green
Write-Host "      🟢 CIANET PROVEDOR - Iniciando" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

# Diretório base
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Iniciar serviço WhatsApp Web (Node.js) em background
Write-Host "📱 Iniciando serviço WhatsApp Web..." -ForegroundColor Cyan
$whatsappJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location "$dir\whatsapp-service"
    npm start
} -ArgumentList (Split-Path -Parent $MyInvocation.MyCommand.Path)

Start-Sleep -Seconds 3

# Iniciar API Python
Write-Host "🐍 Iniciando API Python..." -ForegroundColor Yellow
Set-Location $baseDir
& "$baseDir\.venv\Scripts\Activate.ps1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Quando o Python parar, parar o WhatsApp também
Stop-Job $whatsappJob
Remove-Job $whatsappJob
