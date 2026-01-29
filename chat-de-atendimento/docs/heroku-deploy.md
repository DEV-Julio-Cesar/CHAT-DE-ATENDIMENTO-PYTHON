# 🚀 Deploy no Heroku - Guia Completo

## 📋 **Pré-requisitos**

1. **Conta no Heroku** (gratuita)
2. **Git** instalado
3. **Heroku CLI** instalado

## 🛠️ **Passo 1: Instalar Heroku CLI**

### **Windows:**
1. Baixe em: https://devcenter.heroku.com/articles/heroku-cli
2. Execute o instalador
3. Reinicie o terminal

### **macOS:**
```bash
brew tap heroku/brew && brew install heroku
```

### **Linux:**
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

## 🔐 **Passo 2: Fazer Login no Heroku**

```bash
# Fazer login (abrirá o navegador)
heroku login

# Verificar se logou
heroku whoami
```

## 📦 **Passo 3: Preparar o Projeto**

```bash
# Inicializar git (se ainda não fez)
git init

# Adicionar todos os arquivos
git add .

# Fazer primeiro commit
git commit -m "Preparando para deploy no Heroku"
```

## 🚀 **Passo 4: Criar Aplicação no Heroku**

```bash
# Criar aplicação (escolha um nome único)
heroku create meu-chat-atendimento-2024

# Ou deixar o Heroku escolher o nome
heroku create

# Verificar se foi criado
heroku apps
```

## ⚙️ **Passo 5: Configurar Variáveis de Ambiente**

```bash
# Configurar ambiente de produção
heroku config:set NODE_ENV=production

# Configurar chave da IA (opcional)
heroku config:set GEMINI_API_KEY=sua_chave_aqui

# Verificar configurações
heroku config
```

## 📤 **Passo 6: Fazer Deploy**

```bash
# Enviar código para o Heroku
git push heroku main

# Aguardar o build e deploy...
# Isso pode levar alguns minutos
```

## 🌐 **Passo 7: Abrir Aplicação**

```bash
# Abrir no navegador
heroku open

# Ou ver a URL
heroku info
```

## 📊 **Passo 8: Monitorar**

```bash
# Ver logs em tempo real
heroku logs --tail

# Ver status da aplicação
heroku ps

# Reiniciar se necessário
heroku restart
```

## 🎉 **Pronto! Sua aplicação está online!**

Sua aplicação estará disponível em:
`https://seu-app-nome.herokuapp.com`

### **Login padrão:**
- **Usuário:** admin
- **Senha:** admin

## 🔧 **Comandos Úteis**

```bash
# Ver logs
heroku logs --tail

# Executar comandos no servidor
heroku run npm run diagnostico

# Abrir terminal no servidor
heroku run bash

# Ver informações da aplicação
heroku info

# Escalar aplicação (aumentar recursos)
heroku ps:scale web=1

# Adicionar domínio personalizado (pago)
heroku domains:add www.meusite.com
```

## ⚠️ **Limitações da Versão Gratuita**

- **Sleep Mode**: Aplicação "dorme" após 30 min sem uso
- **Horas Limitadas**: 550 horas/mês (pode ser aumentado verificando cartão)
- **Sem Domínio Personalizado**: URL será `*.herokuapp.com`
- **Sem SSL Personalizado**: Apenas SSL básico

## 🔄 **Atualizações Futuras**

Para atualizar sua aplicação:

```bash
# 1. Fazer alterações no código
# 2. Commit das mudanças
git add .
git commit -m "Atualização da aplicação"

# 3. Enviar para o Heroku
git push heroku main

# 4. A aplicação será automaticamente atualizada
```

## 🆘 **Problemas Comuns**

### **1. Erro de Build**
```bash
# Ver logs detalhados
heroku logs --tail

# Verificar se todas as dependências estão no package.json
npm install --save dependencia-faltando
```

### **2. Aplicação não inicia**
```bash
# Verificar se o Procfile está correto
cat Procfile

# Deve conter: web: node server-web.js
```

### **3. Erro de porta**
- O Heroku define a porta automaticamente
- Use `process.env.PORT` no código

### **4. Sessões WhatsApp perdidas**
- Normal no Heroku (reinicia aplicação)
- Considere usar banco de dados para persistir

## 💰 **Upgrade para Versão Paga**

Se precisar de mais recursos:

```bash
# Ver planos disponíveis
heroku addons:plans

# Upgrade para plano básico ($7/mês)
heroku ps:scale web=1 --type=basic

# Adicionar banco de dados
heroku addons:create heroku-postgresql:hobby-dev
```

## 🎯 **Próximos Passos**

1. ✅ **Testar aplicação online**
2. ✅ **Configurar domínio personalizado** (opcional)
3. ✅ **Configurar SSL** (automático no Heroku)
4. ✅ **Monitorar performance**
5. ✅ **Fazer backup dos dados**

---

**🎉 Parabéns! Sua aplicação está online e acessível para o mundo todo!**