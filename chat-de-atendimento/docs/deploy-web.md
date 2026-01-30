# 🌐 Deploy Web - Sistema de Atendimento WhatsApp

## Guia Completo para Subir a Aplicação Web

### 📋 **Pré-requisitos**

- **Node.js** >= 18.0.0
- **NPM** >= 9.0.0
- **Servidor** com acesso à internet
- **Portas liberadas**: 3000 (HTTP), 8080 (WebSocket), 9090 (Chat WebSocket)

### 🚀 **Instalação e Configuração**

#### 1. **Clonar e Instalar Dependências**
```bash
# Clonar o repositório
git clone <seu-repositorio>
cd chat-de-atendimento

# Instalar dependências
npm install

# Criar usuário admin padrão
npm run seed:admin
```

#### 2. **Configurar Variáveis de Ambiente**
```bash
# Criar arquivo .env (opcional)
PORT=3000
WS_PORT=8080
CHAT_WS_PORT=9090
NODE_ENV=production
GEMINI_API_KEY=sua_chave_gemini_aqui
```

#### 3. **Testar Localmente**
```bash
# Executar diagnóstico
npm run diagnostico

# Iniciar aplicação web
npm run start:web
```

### 🌐 **Acessar a Aplicação**

Após iniciar, acesse:
- **URL Principal**: http://localhost:3000
- **Login Padrão**: admin / admin

### 📱 **Funcionalidades Web**

#### ✅ **Funcionalidades Disponíveis**
- ✅ Login e autenticação
- ✅ Gerenciamento de usuários
- ✅ Conexão com WhatsApp (QR Code)
- ✅ Chat em tempo real
- ✅ Sistema de filas
- ✅ Campanhas de marketing
- ✅ Configuração de IA/Chatbot
- ✅ Dashboard e métricas
- ✅ Chat interno entre atendentes
- ✅ Backup e relatórios

#### 🔄 **Diferenças da Versão Desktop**
- Interface adaptada para navegador
- WebSockets para comunicação em tempo real
- APIs REST para todas as operações
- Sessão salva no localStorage
- Suporte a múltiplas abas

### 🖥️ **Deploy em Servidor**

#### **Opção 1: Servidor VPS/Dedicado**

```bash
# 1. Conectar ao servidor
ssh usuario@seu-servidor.com

# 2. Instalar Node.js (se não tiver)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 3. Clonar aplicação
git clone <seu-repositorio>
cd chat-de-atendimento

# 4. Instalar dependências
npm install --production

# 5. Configurar usuário admin
npm run seed:admin

# 6. Instalar PM2 para gerenciar processo
npm install -g pm2

# 7. Criar arquivo de configuração PM2
```

**ecosystem.config.js:**
```javascript
module.exports = {
  apps: [{
    name: 'chat-atendimento-web',
    script: 'server-web.js',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 3000,
      WS_PORT: 8080,
      CHAT_WS_PORT: 9090
    }
  }]
};
```

```bash
# 8. Iniciar com PM2
pm2 start ecosystem.config.js

# 9. Configurar para iniciar automaticamente
pm2 startup
pm2 save
```

#### **Opção 2: Heroku**

```bash
# 1. Instalar Heroku CLI
# 2. Login no Heroku
heroku login

# 3. Criar aplicação
heroku create seu-app-chat-atendimento

# 4. Configurar variáveis de ambiente
heroku config:set NODE_ENV=production
heroku config:set GEMINI_API_KEY=sua_chave

# 5. Deploy
git add .
git commit -m "Deploy web version"
git push heroku main
```

**Procfile para Heroku:**
```
web: node server-web.js
```

#### **Opção 3: Docker**

**Dockerfile:**
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

RUN npm run seed:admin

EXPOSE 3000 8080 9090

CMD ["npm", "run", "start:web"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  chat-atendimento:
    build: .
    ports:
      - "3000:3000"
      - "8080:8080"
      - "9090:9090"
    environment:
      - NODE_ENV=production
      - PORT=3000
      - WS_PORT=8080
      - CHAT_WS_PORT=9090
    volumes:
      - ./dados:/app/dados
      - ./.wwebjs_auth:/app/.wwebjs_auth
    restart: unless-stopped
```

```bash
# Executar com Docker
docker-compose up -d
```

### 🔧 **Configuração de Proxy Reverso (Nginx)**

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket principal
    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket chat interno
    location /chat-ws {
        proxy_pass http://localhost:9090;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 🔒 **SSL/HTTPS (Certbot)**

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado SSL
sudo certbot --nginx -d seu-dominio.com

# Renovação automática
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 📊 **Monitoramento**

#### **Logs da Aplicação**
```bash
# Ver logs em tempo real
pm2 logs chat-atendimento-web

# Logs salvos em
tail -f dados/logs/app-$(date +%Y-%m-%d).log
```

#### **Métricas do Sistema**
```bash
# Status dos processos
pm2 status

# Monitoramento
pm2 monit

# Reiniciar se necessário
pm2 restart chat-atendimento-web
```

### 🛠️ **Manutenção**

#### **Backup dos Dados**
```bash
# Backup manual
tar -czf backup-$(date +%Y%m%d).tar.gz dados/ .wwebjs_auth/

# Backup automático (crontab)
0 2 * * * cd /caminho/para/app && tar -czf backups/backup-$(date +\%Y\%m\%d).tar.gz dados/ .wwebjs_auth/
```

#### **Atualização da Aplicação**
```bash
# 1. Fazer backup
npm run backup

# 2. Parar aplicação
pm2 stop chat-atendimento-web

# 3. Atualizar código
git pull origin main

# 4. Instalar dependências
npm install --production

# 5. Reiniciar aplicação
pm2 start chat-atendimento-web
```

### 🚨 **Troubleshooting**

#### **Problemas Comuns**

1. **Porta em uso**
```bash
# Verificar portas em uso
netstat -tulpn | grep :3000

# Matar processo se necessário
sudo kill -9 $(lsof -t -i:3000)
```

2. **WhatsApp não conecta**
```bash
# Limpar cache de sessões
rm -rf .wwebjs_auth/*

# Verificar logs
tail -f dados/logs/app-$(date +%Y-%m-%d).log
```

3. **WebSocket não conecta**
- Verificar firewall
- Confirmar portas liberadas
- Verificar proxy reverso

4. **Erro de permissões**
```bash
# Ajustar permissões
sudo chown -R $USER:$USER dados/
sudo chown -R $USER:$USER .wwebjs_auth/
```

### 📈 **Performance**

#### **Otimizações Recomendadas**
- Usar PM2 com cluster mode para múltiplas instâncias
- Configurar cache no Nginx
- Usar CDN para arquivos estáticos
- Monitorar uso de memória
- Configurar log rotation

#### **Limites Recomendados**
- **RAM**: Mínimo 2GB, recomendado 4GB
- **CPU**: Mínimo 2 cores
- **Disco**: Mínimo 10GB para logs e sessões
- **Banda**: Mínimo 10Mbps para múltiplos usuários

### 🎯 **Próximos Passos**

1. **Testar localmente**: `npm run start:web`
2. **Configurar domínio** e SSL
3. **Fazer deploy** em servidor
4. **Configurar monitoramento**
5. **Treinar usuários** na versão web

### 📞 **Suporte**

Em caso de problemas:
1. Verificar logs da aplicação
2. Consultar documentação
3. Verificar issues no GitHub
4. Contatar suporte técnico

---

**🎉 Sua aplicação web está pronta para produção!**