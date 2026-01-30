# Script de inicializacao da aplicacao ISP Customer Support para Windows

Write-Host "Iniciando ISP Customer Support..." -ForegroundColor Green

# Verificar se o arquivo .env existe
if (-not (Test-Path ".env")) {
    Write-Host "Arquivo .env nao encontrado. Copiando .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Arquivo .env criado. Configure as variaveis antes de continuar." -ForegroundColor Green
    exit 1
}

Write-Host "Verificando dependencias..." -ForegroundColor Blue

# Verificar se Docker está instalado
try {
    docker --version | Out-Null
    Write-Host "✅ Docker encontrado." -ForegroundColor Green
} catch {
    Write-Host "❌ Docker não está instalado. Instale o Docker Desktop primeiro." -ForegroundColor Red
    exit 1
}

# Verificar se Docker Compose está instalado
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose encontrado." -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose não está instalado." -ForegroundColor Red
    exit 1
}

# Criar diretórios necessários
Write-Host "📁 Criando diretórios..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
New-Item -ItemType Directory -Force -Path "backups" | Out-Null
New-Item -ItemType Directory -Force -Path "config\ssl" | Out-Null

Write-Host "🐳 Iniciando containers Docker..." -ForegroundColor Blue

# Parar containers existentes
docker-compose down

# Construir e iniciar containers
docker-compose up -d --build

Write-Host "⏳ Aguardando serviços ficarem prontos..." -ForegroundColor Yellow

# Aguardar PostgreSQL
Write-Host "🐘 Aguardando PostgreSQL..." -ForegroundColor Blue
do {
    Start-Sleep -Seconds 2
    $pgReady = docker-compose exec -T postgres pg_isready -U postgres 2>$null
} while ($LASTEXITCODE -ne 0)

# Aguardar Redis
Write-Host "🔴 Aguardando Redis..." -ForegroundColor Blue
do {
    Start-Sleep -Seconds 2
    $redisReady = docker-compose exec -T redis redis-cli ping 2>$null
} while ($LASTEXITCODE -ne 0)

Write-Host "🔄 Executando migrações do banco de dados..." -ForegroundColor Blue

# Executar migrações Alembic
docker-compose exec -T api alembic upgrade head

Write-Host "👤 Criando usuário admin padrão..." -ForegroundColor Blue

# Criar usuário admin via script Python
$createAdminScript = @"
import asyncio
from app.core.database import get_db_session
from app.core.security import security_manager
from app.models.database import Usuario, UserRole
from sqlalchemy import select

async def create_admin():
    async with get_db_session() as db:
        # Verificar se admin já existe
        stmt = select(Usuario).where(Usuario.username == 'admin')
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()
        
        if not admin:
            # Criar usuário admin
            admin = Usuario(
                username='admin',
                email='admin@sistema.com',
                password_hash=security_manager.hash_password('admin123'),
                role=UserRole.ADMIN,
                ativo=True
            )
            db.add(admin)
            await db.commit()
            print('✅ Usuário admin criado com sucesso!')
            print('   Username: admin')
            print('   Password: admin123')
            print('   ⚠️  ALTERE A SENHA PADRÃO IMEDIATAMENTE!')
        else:
            print('ℹ️  Usuário admin já existe.')

asyncio.run(create_admin())
"@

$createAdminScript | docker-compose exec -T api python

Write-Host "🔍 Verificando saúde dos serviços..." -ForegroundColor Blue

# Verificar saúde da API
$maxAttempts = 30
$attempt = 0

do {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ API está funcionando!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "⏳ Tentativa $attempt/$maxAttempts - Aguardando API..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
} while ($attempt -lt $maxAttempts)

if ($attempt -eq $maxAttempts) {
    Write-Host "❌ API não respondeu após $maxAttempts tentativas." -ForegroundColor Red
    Write-Host "📋 Logs da API:" -ForegroundColor Yellow
    docker-compose logs api
    exit 1
}

Write-Host "📊 Status dos serviços:" -ForegroundColor Blue
docker-compose ps

Write-Host ""
Write-Host "🎉 ISP Customer Support iniciado com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Endpoints disponíveis:" -ForegroundColor Cyan
Write-Host "   🌐 API: http://localhost:8000" -ForegroundColor White
Write-Host "   📚 Documentação: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   🔌 WebSocket: ws://localhost:8001/ws/chat" -ForegroundColor White
Write-Host "   ❤️  Health Check: http://localhost:8000/health" -ForegroundColor White
Write-Host "   📈 Métricas: http://localhost:8000/metrics" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Ferramentas de monitoramento:" -ForegroundColor Cyan
Write-Host "   📊 Grafana: http://localhost:3000 (admin/admin123)" -ForegroundColor White
Write-Host "   🎯 Prometheus: http://localhost:9090" -ForegroundColor White
Write-Host "   🔍 Kibana: http://localhost:5601" -ForegroundColor White
Write-Host ""
Write-Host "💾 Banco de dados:" -ForegroundColor Cyan
Write-Host "   🐘 PostgreSQL: localhost:5432" -ForegroundColor White
Write-Host "   🔴 Redis: localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "👤 Usuário padrão:" -ForegroundColor Cyan
Write-Host "   Username: admin" -ForegroundColor White
Write-Host "   Password: admin123" -ForegroundColor White
Write-Host "   ⚠️  ALTERE A SENHA IMEDIATAMENTE!" -ForegroundColor Red
Write-Host ""
Write-Host "📖 Para parar os serviços: docker-compose down" -ForegroundColor Yellow
Write-Host "📖 Para ver logs: docker-compose logs -f [service]" -ForegroundColor Yellow
Write-Host ""
Write-Host "🚀 Sistema pronto para uso!" -ForegroundColor Green