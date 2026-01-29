#!/bin/bash

# Script de inicialização da aplicação ISP Customer Support

set -e

echo "🚀 Iniciando ISP Customer Support..."

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
    echo "⚠️  Arquivo .env não encontrado. Copiando .env.example..."
    cp .env.example .env
    echo "✅ Arquivo .env criado. Configure as variáveis antes de continuar."
    exit 1
fi

# Carregar variáveis de ambiente
source .env

echo "📦 Verificando dependências..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Instale o Docker primeiro."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Instale o Docker Compose primeiro."
    exit 1
fi

echo "✅ Dependências verificadas."

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p uploads
mkdir -p logs
mkdir -p backups
mkdir -p config/ssl

echo "🐳 Iniciando containers Docker..."

# Parar containers existentes
docker-compose down

# Construir e iniciar containers
docker-compose up -d --build

echo "⏳ Aguardando serviços ficarem prontos..."

# Aguardar PostgreSQL
echo "🐘 Aguardando PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U postgres; do
    sleep 2
done

# Aguardar Redis
echo "🔴 Aguardando Redis..."
until docker-compose exec -T redis redis-cli ping; do
    sleep 2
done

echo "🔄 Executando migrações do banco de dados..."

# Executar migrações Alembic
docker-compose exec -T api alembic upgrade head

echo "👤 Criando usuário admin padrão..."

# Criar usuário admin via API (se não existir)
docker-compose exec -T api python -c "
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
"

echo "🔍 Verificando saúde dos serviços..."

# Verificar saúde da API
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API está funcionando!"
        break
    fi
    
    attempt=$((attempt + 1))
    echo "⏳ Tentativa $attempt/$max_attempts - Aguardando API..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ API não respondeu após $max_attempts tentativas."
    echo "📋 Logs da API:"
    docker-compose logs api
    exit 1
fi

echo "📊 Status dos serviços:"
docker-compose ps

echo ""
echo "🎉 ISP Customer Support iniciado com sucesso!"
echo ""
echo "📍 Endpoints disponíveis:"
echo "   🌐 API: http://localhost:8000"
echo "   📚 Documentação: http://localhost:8000/docs"
echo "   🔌 WebSocket: ws://localhost:8001/ws/chat"
echo "   ❤️  Health Check: http://localhost:8000/health"
echo "   📈 Métricas: http://localhost:8000/metrics"
echo ""
echo "🔧 Ferramentas de monitoramento:"
echo "   📊 Grafana: http://localhost:3000 (admin/admin123)"
echo "   🎯 Prometheus: http://localhost:9090"
echo "   🔍 Kibana: http://localhost:5601"
echo ""
echo "💾 Banco de dados:"
echo "   🐘 PostgreSQL: localhost:5432"
echo "   🔴 Redis: localhost:6379"
echo ""
echo "👤 Usuário padrão:"
echo "   Username: admin"
echo "   Password: admin123"
echo "   ⚠️  ALTERE A SENHA IMEDIATAMENTE!"
echo ""
echo "📖 Para parar os serviços: docker-compose down"
echo "📖 Para ver logs: docker-compose logs -f [service]"
echo ""
echo "🚀 Sistema pronto para uso!"