# 🧪 Script de Testes Completos do Sistema
# ISP Customer Support - Bateria de Testes

$ErrorActionPreference = "Continue"
$baseUrl = "http://localhost:8000"
$testResults = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [string]$Body = $null
    )
    
    Write-Host "`n🧪 Testando: $Name" -ForegroundColor Cyan
    Write-Host "   URL: $Url" -ForegroundColor Gray
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
        }
        
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-WebRequest @params
        
        if ($response.StatusCode -eq 200) {
            Write-Host "   ✅ PASSOU - Status: $($response.StatusCode)" -ForegroundColor Green
            $script:testResults += [PSCustomObject]@{
                Test = $Name
                Status = "✅ PASSOU"
                StatusCode = $response.StatusCode
                ResponseTime = $response.Headers.'x-process-time'
            }
            return $true
        } else {
            Write-Host "   ⚠️  AVISO - Status: $($response.StatusCode)" -ForegroundColor Yellow
            $script:testResults += [PSCustomObject]@{
                Test = $Name
                Status = "⚠️ AVISO"
                StatusCode = $response.StatusCode
                ResponseTime = $response.Headers.'x-process-time'
            }
            return $false
        }
    }
    catch {
        Write-Host "   ❌ FALHOU - Erro: $($_.Exception.Message)" -ForegroundColor Red
        $script:testResults += [PSCustomObject]@{
            Test = $Name
            Status = "❌ FALHOU"
            StatusCode = "N/A"
            ResponseTime = "N/A"
        }
        return $false
    }
}

function Test-ApiEndpoint {
    param(
        [string]$Name,
        [string]$Endpoint,
        [string]$Method = "GET",
        [hashtable]$Body = $null
    )
    
    $url = "$baseUrl$Endpoint"
    $bodyJson = if ($Body) { $Body | ConvertTo-Json } else { $null }
    Test-Endpoint -Name $Name -Url $url -Method $Method -Body $bodyJson
}

# ============================================================================
# INÍCIO DOS TESTES
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                ║" -ForegroundColor Cyan
Write-Host "║        🧪 BATERIA COMPLETA DE TESTES DO SISTEMA 🧪            ║" -ForegroundColor Cyan
Write-Host "║              ISP Customer Support v2.0.0                       ║" -ForegroundColor Cyan
Write-Host "║                                                                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 2

# ============================================================================
# CATEGORIA 1: TESTES DE SISTEMA
# ============================================================================
Write-Host "`n📋 CATEGORIA 1: TESTES DE SISTEMA" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta

Test-ApiEndpoint -Name "Health Check" -Endpoint "/health"
Test-ApiEndpoint -Name "Info da Aplicação" -Endpoint "/info"
Test-ApiEndpoint -Name "Métricas Prometheus" -Endpoint "/metrics"
Test-ApiEndpoint -Name "Estatísticas da API" -Endpoint "/api/stats"
Test-ApiEndpoint -Name "Cache Stats" -Endpoint "/cache/stats"

# ============================================================================
# CATEGORIA 2: TESTES DE PÁGINAS WEB
# ============================================================================
Write-Host "`n📋 CATEGORIA 2: TESTES DE PÁGINAS WEB" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta

Test-ApiEndpoint -Name "Página Principal" -Endpoint "/"
Test-ApiEndpoint -Name "Página de Login" -Endpoint "/login"
Test-ApiEndpoint -Name "Dashboard" -Endpoint "/dashboard"
Test-ApiEndpoint -Name "Chat" -Endpoint "/chat"
Test-ApiEndpoint -Name "Campanhas" -Endpoint "/campaigns"
Test-ApiEndpoint -Name "Clientes" -Endpoint "/customers"
Test-ApiEndpoint -Name "WhatsApp Config" -Endpoint "/whatsapp"
Test-ApiEndpoint -Name "Chatbot Admin" -Endpoint "/chatbot-admin"
Test-ApiEndpoint -Name "Usuários" -Endpoint "/users"
Test-ApiEndpoint -Name "Configurações" -Endpoint "/settings"

# ============================================================================
# CATEGORIA 3: TESTES DE API DE AUTENTICAÇÃO
# ============================================================================
Write-Host "`n📋 CATEGORIA 3: TESTES DE API DE AUTENTICAÇÃO" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta

# Teste de login com credenciais corretas
$loginBody = @{
    email = "admin@empresa.com"
    password = "admin123"
}
Test-ApiEndpoint -Name "Login (Credenciais Corretas)" -Endpoint "/api/v1/auth/login" -Method "POST" -Body $loginBody

# Teste de login com credenciais incorretas
$loginBodyWrong = @{
    email = "admin@empresa.com"
    password = "senhaerrada"
}
Write-Host "`n🧪 Testando: Login (Credenciais Incorretas)" -ForegroundColor Cyan
Write-Host "   URL: $baseUrl/api/v1/auth/login" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/auth/login" -Method POST -Body ($loginBodyWrong | ConvertTo-Json) -ContentType "application/json" -UseBasicParsing
    Write-Host "   ⚠️  AVISO - Deveria falhar mas retornou: $($response.StatusCode)" -ForegroundColor Yellow
}
catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "   ✅ PASSOU - Retornou 401 como esperado" -ForegroundColor Green
        $script:testResults += [PSCustomObject]@{
            Test = "Login (Credenciais Incorretas)"
            Status = "✅ PASSOU"
            StatusCode = "401"
            ResponseTime = "N/A"
        }
    } else {
        Write-Host "   ❌ FALHOU - Status inesperado: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

# ============================================================================
# CATEGORIA 4: TESTES DE API DE DADOS
# ============================================================================
Write-Host "`n📋 CATEGORIA 4: TESTES DE API DE DADOS" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta

Test-ApiEndpoint -Name "Dashboard Data" -Endpoint "/dashboard"
Test-ApiEndpoint -Name "Conversas" -Endpoint "/api/conversations"
Test-ApiEndpoint -Name "Usuários" -Endpoint "/api/users"

# ============================================================================
# CATEGORIA 5: TESTES DE DOCUMENTAÇÃO
# ============================================================================
Write-Host "`n📋 CATEGORIA 5: TESTES DE DOCUMENTAÇÃO" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta

Test-ApiEndpoint -Name "Swagger UI" -Endpoint "/docs"
Test-ApiEndpoint -Name "ReDoc" -Endpoint "/redoc"
Test-ApiEndpoint -Name "OpenAPI JSON" -Endpoint "/openapi.json"

# ============================================================================
# CATEGORIA 6: TESTES DE PERFORMANCE
# ============================================================================
Write-Host "`n📋 CATEGORIA 6: TESTES DE PERFORMANCE" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta

Write-Host "`n🧪 Testando: Tempo de Resposta (10 requisições)" -ForegroundColor Cyan
$times = @()
for ($i = 1; $i -le 10; $i++) {
    $start = Get-Date
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing
        $end = Get-Date
        $elapsed = ($end - $start).TotalMilliseconds
        $times += $elapsed
        Write-Host "   Requisição $i : $([math]::Round($elapsed, 2))ms" -ForegroundColor Gray
    }
    catch {
        Write-Host "   Requisição $i : FALHOU" -ForegroundColor Red
    }
}

if ($times.Count -gt 0) {
    $avgTime = ($times | Measure-Object -Average).Average
    $minTime = ($times | Measure-Object -Minimum).Minimum
    $maxTime = ($times | Measure-Object -Maximum).Maximum
    
    Write-Host "`n   📊 Estatísticas:" -ForegroundColor Cyan
    Write-Host "      Média: $([math]::Round($avgTime, 2))ms" -ForegroundColor White
    Write-Host "      Mínimo: $([math]::Round($minTime, 2))ms" -ForegroundColor Green
    Write-Host "      Máximo: $([math]::Round($maxTime, 2))ms" -ForegroundColor Yellow
    
    if ($avgTime -lt 100) {
        Write-Host "   ✅ EXCELENTE - Tempo de resposta < 100ms" -ForegroundColor Green
        $perfStatus = "✅ EXCELENTE"
    }
    elseif ($avgTime -lt 500) {
        Write-Host "   ✅ BOM - Tempo de resposta < 500ms" -ForegroundColor Green
        $perfStatus = "✅ BOM"
    }
    else {
        Write-Host "   ⚠️  LENTO - Tempo de resposta > 500ms" -ForegroundColor Yellow
        $perfStatus = "⚠️ LENTO"
    }
    
    $script:testResults += [PSCustomObject]@{
        Test = "Performance (Tempo Médio)"
        Status = $perfStatus
        StatusCode = "$([math]::Round($avgTime, 2))ms"
        ResponseTime = "$([math]::Round($avgTime, 2))ms"
    }
}

# ============================================================================
# CATEGORIA 7: TESTE DE CARGA
# ============================================================================
Write-Host "`n📋 CATEGORIA 7: TESTE DE CARGA BÁSICO" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta

Write-Host "`n🧪 Testando: 50 requisições simultâneas" -ForegroundColor Cyan
$jobs = @()
$startLoad = Get-Date

for ($i = 1; $i -le 50; $i++) {
    $jobs += Start-Job -ScriptBlock {
        param($url)
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
            return $response.StatusCode
        }
        catch {
            return 0
        }
    } -ArgumentList "$baseUrl/health"
}

$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

$endLoad = Get-Date
$loadTime = ($endLoad - $startLoad).TotalSeconds
$successCount = ($results | Where-Object { $_ -eq 200 }).Count
$failCount = 50 - $successCount

Write-Host "   Total: 50 requisições" -ForegroundColor White
Write-Host "   Sucesso: $successCount" -ForegroundColor Green
Write-Host "   Falhas: $failCount" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Red" })
Write-Host "   Tempo total: $([math]::Round($loadTime, 2))s" -ForegroundColor White
Write-Host "   Requisições/segundo: $([math]::Round(50/$loadTime, 2))" -ForegroundColor Cyan

if ($successCount -eq 50) {
    Write-Host "   ✅ PASSOU - Todas as requisições bem-sucedidas" -ForegroundColor Green
    $loadStatus = "✅ PASSOU"
}
elseif ($successCount -ge 45) {
    Write-Host "   ⚠️  AVISO - Algumas falhas ($failCount)" -ForegroundColor Yellow
    $loadStatus = "⚠️ AVISO"
}
else {
    Write-Host "   ❌ FALHOU - Muitas falhas ($failCount)" -ForegroundColor Red
    $loadStatus = "❌ FALHOU"
}

$script:testResults += [PSCustomObject]@{
    Test = "Teste de Carga (50 req)"
    Status = $loadStatus
    StatusCode = "$successCount/50"
    ResponseTime = "$([math]::Round($loadTime, 2))s"
}

# ============================================================================
# RESUMO FINAL
# ============================================================================
Write-Host "`n`n" -NoNewline
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                                ║" -ForegroundColor Green
Write-Host "║                    📊 RESUMO DOS TESTES                        ║" -ForegroundColor Green
Write-Host "║                                                                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

$testResults | Format-Table -AutoSize

$totalTests = $testResults.Count
$passedTests = ($testResults | Where-Object { $_.Status -like "*PASSOU*" -or $_.Status -like "*EXCELENTE*" -or $_.Status -like "*BOM*" }).Count
$failedTests = ($testResults | Where-Object { $_.Status -like "*FALHOU*" }).Count
$warningTests = ($testResults | Where-Object { $_.Status -like "*AVISO*" }).Count

Write-Host "`n📊 ESTATÍSTICAS FINAIS:" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Total de Testes: $totalTests" -ForegroundColor White
Write-Host "   ✅ Passou: $passedTests" -ForegroundColor Green
Write-Host "   ⚠️  Avisos: $warningTests" -ForegroundColor Yellow
Write-Host "   ❌ Falhou: $failedTests" -ForegroundColor Red

$successRate = [math]::Round(($passedTests / $totalTests) * 100, 2)
Write-Host "`n   Taxa de Sucesso: $successRate%" -ForegroundColor $(if ($successRate -ge 90) { "Green" } elseif ($successRate -ge 70) { "Yellow" } else { "Red" })

Write-Host "`n"
if ($failedTests -eq 0 -and $warningTests -eq 0) {
    Write-Host "🎉 TODOS OS TESTES PASSARAM! Sistema pronto para deploy!" -ForegroundColor Green
}
elseif ($failedTests -eq 0) {
    Write-Host "✅ Sistema funcional com alguns avisos. Revisar antes do deploy." -ForegroundColor Yellow
}
else {
    Write-Host "⚠️  Alguns testes falharam. Corrigir antes do deploy!" -ForegroundColor Red
}

Write-Host "`n═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Testes concluídos em: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════════════`n" -ForegroundColor Cyan