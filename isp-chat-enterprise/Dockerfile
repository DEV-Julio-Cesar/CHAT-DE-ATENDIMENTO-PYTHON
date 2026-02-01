# ISP Chat Enterprise - Multi-stage Dockerfile
# Otimizado para produção com múltiplos serviços

# === BASE IMAGE ===
FROM python:3.11-slim as base

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar Microsoft ODBC Driver para SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY . .

# === AUTH SERVICE ===
FROM base as auth-service

WORKDIR /app

# Expor porta
EXPOSE 8001

# Comando de inicialização
CMD ["python", "-m", "uvicorn", "services.auth-service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# === CHAT SERVICE ===
FROM base as chat-service

WORKDIR /app

# Expor porta
EXPOSE 8002

# Comando de inicialização
CMD ["python", "-m", "uvicorn", "services.chat-service.app.main:app", "--host", "0.0.0.0", "--port", "8002"]

# === API GATEWAY ===
FROM base as api-gateway

WORKDIR /app

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["python", "-m", "uvicorn", "services.api-gateway.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# === WEB INTERFACE ===
FROM nginx:alpine as web-interface

# Copiar arquivos da interface web
COPY web-interface/ /usr/share/nginx/html/

# Copiar configuração do nginx
COPY config/nginx-web.conf /etc/nginx/conf.d/default.conf

# Expor porta
EXPOSE 3000

# === PRODUCTION (ALL SERVICES) ===
FROM base as production

# Instalar supervisor para gerenciar múltiplos processos
RUN pip install supervisor

# Copiar configuração do supervisor
COPY config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expor todas as portas
EXPOSE 8000 8001 8002 3000

# Comando de inicialização com supervisor
CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# === DEVELOPMENT ===
FROM base as development

# Instalar dependências de desenvolvimento
RUN pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy

# Configurar ambiente de desenvolvimento
ENV PYTHONPATH=/app
ENV DEBUG=true

# Comando padrão para desenvolvimento
CMD ["python", "start.py"]