# 🚀 GUIA PASSO A PASSO - SINCRONIZAÇÃO WHATSAPP

## 📖 Índice

1. [Arquitetura do Sistema](#arquitetura-do-sistema)
2. [Como Sincronizar - QR Code](#como-sincronizar---qr-code)
3. [Como Sincronizar - Validação Manual](#como-sincronizar---validação-manual)
4. [Como Sincronizar - Meta API](#como-sincronizar---meta-api)
5. [Troubleshooting](#troubleshooting)
6. [Testes e Validação](#testes-e-validação)

---

## 🏗️ Arquitetura do Sistema

### Componentes

```
┌─────────────────────────────────────────────────┐
│         SISTEMA DE SINCRONIZAÇÃO WHATSAPP      │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │  validacao-whatsapp.html (UI/Frontend)    │ │
│  │  - 3 abas (QR, Manual, Meta)              │ │
│  │  - Status em tempo real                   │ │
│  │  - Validação de entrada                   │ │
│  └───────────────────────────────────────────┘ │
│                     ↓                           │
│  ┌───────────────────────────────────────────┐ │
│  │ rotasWhatsAppSincronizacao.js (API)       │ │
│  │ - 7 endpoints REST                        │ │
│  │ - Validação de dados                      │ │
│  │ - Resposta em JSON                        │ │
│  └───────────────────────────────────────────┘ │
│                     ↓                           │
│  ┌───────────────────────────────────────────┐ │
│  │ GerenciadorSessaoWhatsApp.js (Backend)    │ │
│  │ - Persistência JSON                       │ │
│  │ - Keep-alive (30 min)                     │ │
│  │ - Sincronização (5 min)                   │ │
│  │ - Meta API integration                    │ │
│  └───────────────────────────────────────────┘ │
│                     ↓                           │
│  ┌───────────────────────────────────────────┐ │
│  │    GerenciadorPoolWhatsApp                │ │
│  │    (Gerencia clientes WhatsApp)           │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Fluxo de Dados

```
Usuário acessa interface
    ↓
Seleciona método de validação
    ↓
Envia dados para API
    ↓
Gerenciador cria/valida sessão
    ↓
Status armazenado em arquivo JSON
    ↓
Keep-alive ativa a cada 30 min
    ↓
WhatsApp permanece online ✓
```

---

## 🔐 Como Sincronizar - QR Code

### ✅ Pré-requisitos

- [ ] Aplicação iniciada (`npm start`)
- [ ] Navegador aberto (Chrome, Firefox, Safari)
- [ ] Smartphone com WhatsApp instalado
- [ ] Conexão de internet ativa

### 📱 Passo a Passo

#### 1️⃣ Acesse a Interface

Abra seu navegador e acesse:
```
http://localhost:3333/validacao-whatsapp.html
```

**Resultado esperado:**
- Página com 3 abas carrega
- Aba "QR Code" aberta por padrão
- Status widget no topo mostra "Desconectado"

#### 2️⃣ Visualize o QR Code

A interface automaticamente:
- ✓ Carrega o QR Code gerado
- ✓ Exibe instruções
- ✓ Recarrega a cada 30 segundos (se expirar)

**Se QR Code não aparecer:**
```
- Verificar console do navegador (F12)
- Recarregar página (Ctrl+R)
- Checar se API está rodando (http://localhost:3333/api/status)
```

#### 3️⃣ Escaneie com Seu Celular

No seu **smartphone**:
1. Abra **WhatsApp**
2. Menu → **Dispositivos Conectados**
3. **Vincular um dispositivo**
4. Aponte câmera para o **QR Code** na tela

**Resultado esperado:**
- Seu WhatsApp escaneará o código
- Você verá uma mensagem "Dispositivo conectado"
- Na interface da web, o status mudará

#### 4️⃣ Confirme Seu Telefone

Após escanear o QR Code, você verá um campo:

```
┌─────────────────────────────┐
│ Seu número de telefone      │
│ [    5584920024786     ]    │ ← Preencha com seu número
│ [  CONFIRMAR  ]             │
└─────────────────────────────┘
```

**Formato do número:**
```
Correto:   5584920024786    (55 + DDD + número)
Errado:    11 98765-4321    (com hífen)
Errado:    (85) 98765-4321  (com parênteses)
```

**Onde encontrar seu número:**
- Android: Configurações → Sobre o telefone → Número do telefone
- iPhone: Configurações → Telefone → Meu número

#### 5️⃣ Aguarde Sincronização

Após confirmar:
- ⏳ Status muda para "Sincronizando..."
- ⌛ Aguarde até 30 segundos
- ✅ Status muda para "Ativo" (verde)

**Indicadores de sucesso:**
- [ ] Widget de status: "ATIVO" com cor verde
- [ ] Mensagem: "WhatsApp sincronizado com sucesso"
- [ ] Keep-alive iniciado
- [ ] Contador "Tentativas restantes": desaparece

#### 6️⃣ Verificar Status

Acesse o endpoint de status:
```
http://localhost:3333/api/whatsapp/status
```

**Resposta esperada:**
```json
{
  "ativo": true,
  "telefone": "5584920024786",
  "status": "ativa",
  "tempo_ativo": "2h 15m",
  "ultima_sincronizacao": "2026-01-11T13:45:00.000Z",
  "metodo": "qrcode"
}
```

---

## 📝 Como Sincronizar - Validação Manual

### 📌 Use Quando

- QR Code não funciona
- Câmera do dispositivo com problema
- Quer usar código de confirmação

### 🎯 Passo a Passo

#### 1️⃣ Abra a Aba "Manual"

Na interface `http://localhost:3333/validacao-whatsapp.html`:
- Clique na aba **"Validação Manual"**
- Você verá um formulário com 2 campos

#### 2️⃣ Insira Seu Número

Campo "Número de Telefone":
```
┌─────────────────────────────┐
│ Número de Telefone          │
│ [    5584920024786     ]    │
└─────────────────────────────┘
```

**Regras:**
- ✅ 11-13 dígitos
- ✅ Começar com 55 (Brasil)
- ❌ Sem símbolos (-,,,), espaços
- ❌ Sem 0 à esquerda

#### 3️⃣ Clique em "Gerar Código"

Botão "Gerar Código":
- Sistema gera uma sessão
- WhatsApp envia um código para seu número
- Você recebe mensagem: `"Seu código de validação: 123456"`

**Tempo de espera:** 1-2 minutos

#### 4️⃣ Insira o Código Recebido

Campo "Código de Validação":
```
┌─────────────────────────────┐
│ Código (6 dígitos)          │
│ [  1 2 3 4 5 6        ]     │
│ [  VALIDAR  ]               │
└─────────────────────────────┘
```

**Barra de tentativas:**
```
Tentativa 1: ●○○○○ (4 restantes)
Tentativa 2: ●●○○○ (3 restantes)
Tentativa 3: ●●●○○ (2 restantes)
Tentativa 4: ●●●●○ (1 restante)
Tentativa 5: ●●●●● (Bloqueado por 1 hora)
```

#### 5️⃣ Aguarde Confirmação

- Sistema valida o código
- Se correto: ✅ "Sincronização concluída"
- Se errado: ❌ "Código inválido" (tente novamente)

**Máximo 5 tentativas:**
- Após 5 erros, aguarde 1 hora
- Ou reinicie a validação com QR Code

---

## 🔌 Como Sincronizar - Meta API

### 🎓 O Que É?

Integração direta com a API oficial do WhatsApp Business do Facebook.

**Vantagens:**
- ✅ Sem necessidade de escanear QR Code
- ✅ Sincronização automática
- ✅ Oficial e seguro
- ✅ Acesso a recursos avançados

**Desvantagens:**
- ❌ Requer conta Facebook Business
- ❌ Requer token de desenvolvedor
- ❌ Mais complexo de configurar

### 🔑 Como Obter o Token

#### Passo 1: Crie uma Conta Facebook Developer

1. Acesse [developers.facebook.com](https://developers.facebook.com/)
2. Clique em **"Começar"**
3. Faça login com sua conta Facebook
4. Preencha as informações solicitadas

#### Passo 2: Crie uma Aplicação

1. No painel, clique em **"Meus Aplicativos"**
2. Clique em **"Criar Aplicativo"**
3. Selecione **"Negócios"**
4. Preencha:
   - Nome do aplicativo: "Chat Atendimento WhatsApp"
   - Email: seu email
   - Clique em **"Criar Aplicativo"**

#### Passo 3: Configure o WhatsApp Business

1. No painel do aplicativo, procure por **"WhatsApp"**
2. Clique em **"Configurar"**
3. Siga as instruções:
   - Escolha sua conta do WhatsApp Business
   - Ou crie uma nova conta

#### Passo 4: Gere o Token de Acesso

1. No painel esquerdo, vá para **"Configurações"** → **"Básico"**
2. Copie seu **App ID**
3. Vá para **"Ferramentas"** → **"Explorador de API"**
4. Selecione seu aplicativo
5. Mude para **"App Token"**
6. Gere um novo token com permissões:
   - `whatsapp_business_management`
   - `instagram_basic`

**Resultado:** Um token como este:
```
EAAj7ZBrk7XYBAT1ZA3sKZAjZ...
```

### 📱 Use a Aba Meta API

#### 1️⃣ Clique na Aba "Meta API"

Na interface `http://localhost:3333/validacao-whatsapp.html`:
- Clique na aba **"Meta API"**
- Você verá opções de API

#### 2️⃣ Selecione a API

Escolha uma opção:

```
☐ WhatsApp Business API
  - Oficial do WhatsApp
  - Melhor para negócios
  - Mais recursos

☐ Instagram Direct
  - API do Instagram
  - Mensagens diretas
  - Integração social
```

#### 3️⃣ Insira o Token

Campo "Token de Acesso":
```
┌─────────────────────────────┐
│ Token (será mascarado)      │
│ [EAAj7ZBrk7XYBAT1ZA...]   │
│ [  SINCRONIZAR  ]           │
└─────────────────────────────┘
```

#### 4️⃣ Clique em Sincronizar

Sistema:
- ✓ Valida o token
- ✓ Conecta à Meta API
- ✓ Sincroniza sua conta
- ✓ Ativa automaticamente

**Tempo:** 5-10 segundos

#### 5️⃣ Confirme Sincronização

Mensagem de sucesso:
```
✅ Sincronizado com Meta/Facebook com sucesso!

Número: 5584920024786
Status: ATIVO
Método: Meta API
```

---

## 🔧 Troubleshooting

### ❌ Problema: Interface HTML não carrega

**Solução:**

1. Verificar se API está rodando:
   ```
   http://localhost:3333/api/status
   ```

2. Se mostrar erro `Cannot GET /validacao-whatsapp.html`:
   - Arquivo não está em `src/interfaces/validacao-whatsapp.html`
   - Verifique se foi copiado corretamente
   - Reinicie a aplicação

3. Se API não responde:
   - Verificar console: `npm start`
   - Procurar por erros de inicialização
   - Verificar porta (padrão 3333)

### ❌ Problema: QR Code não aparece

**Solução:**

1. Abrir Console do Navegador (F12):
   - Verificar se há erro de CORS
   - Verificar se API responde a `/api/whatsapp/qr-code`

2. Testar endpoint manualmente:
   ```bash
   curl http://localhost:3333/api/whatsapp/qr-code
   ```

3. Se retornar erro 404:
   - Rotas não foram registradas
   - Verificar se `rotasWhatsAppSincronizacao.js` está em `src/rotas/`
   - Verificar se foi importado em `api.js`
   - Reiniciar aplicação

### ❌ Problema: Validação falha

**Solução:**

1. **QR Code:**
   - Verifique se escaneia com câmera focada
   - Não use foto/screenshot do QR Code
   - Certifique-se de usar câmera nativa do WhatsApp

2. **Manual:**
   - Código expira em 10 minutos
   - Máximo 5 tentativas por hora
   - Se bloqueado, aguarde 1 hora ou use QR Code

3. **Meta API:**
   - Token pode estar expirado (duram 60 dias)
   - Gerar novo token se necessário
   - Verificar se tem permissões corretas

### ❌ Problema: WhatsApp desconecta após 30 min

**Causa:** Keep-alive não está rodando

**Solução:**

1. Verificar se gerenciador foi inicializado:
   ```javascript
   // No console da aplicação
   GerenciadorSessaoWhatsApp.inicializar()
   ```

2. Verificar arquivo de sessão:
   ```bash
   cat dados/sessoes-whatsapp/sessao-ativa.json
   ```

3. Se não existe, criar manualmente:
   ```bash
   mkdir -p dados/sessoes-whatsapp
   # Sincronize novamente
   ```

### ❌ Problema: Telefone não validado

**Causa:** Formato incorreto

**Solução:**

Formato correto:
```
Certo:   5584920024786     (55 + DDD + número sem 0)
Errado:  084920024786      (sem 55)
Errado:  +55 84 98765-4321 (com símbolos)
Errado:  0(84)9876-54321   (com 0 e símbolos)
```

---

## ✅ Testes e Validação

### 🧪 Executar Suite de Testes

```bash
node teste-sincronizacao.js
```

**Resultado esperado:**
```
✓ OK  Conectividade API
✓ OK  Interface HTML
✓ OK  Endpoint QR Code
✓ OK  Endpoint Status
✓ OK  Validação QR Code
✓ OK  Keep-Alive
✓ OK  Validação Manual
✓ OK  Meta API
✓ OK  Arquivos Gerenciador

Resultado: 9/9 (100%)
🎉 TODOS OS TESTES PASSARAM! 🎉
```

### 🔍 Verificações Manuais

#### 1. Verificar Status em Tempo Real

```bash
curl http://localhost:3333/api/whatsapp/status
```

Resposta esperada (se sincronizado):
```json
{
  "ativo": true,
  "telefone": "5584920024786",
  "status": "ativa",
  "tempo_ativo": "2h 30m",
  "ultima_sincronizacao": "2026-01-11T13:50:00.000Z",
  "metodo": "qrcode"
}
```

#### 2. Verificar Keep-Alive

Acionar manualmente:
```bash
curl -X POST http://localhost:3333/api/whatsapp/manter-vivo
```

Deve retornar:
```json
{
  "success": true,
  "status": "ativo",
  "telefone": "5584920024786",
  "ultima_atualizacao": "2026-01-11T13:55:00.000Z"
}
```

#### 3. Verificar Logs

```bash
# Mostrar últimas 50 linhas
tail -50 dados/sessoes-whatsapp/logs/sincronizacao-2026-01-11.log
```

Eventos esperados:
- `sessao_criada`
- `sessao_validada`
- `sessao_ativada`
- `sincronizacao_periodica`
- `keep_alive`

#### 4. Verificar Arquivo de Sessão

```bash
cat dados/sessoes-whatsapp/sessao-ativa.json | jq .
```

Estrutura esperada:
```json
{
  "id": "sessao_123...",
  "telefone": "5584920024786",
  "status": "ativa",
  "ativada_em": "2026-01-11T11:30:00.000Z",
  "ultima_sincronizacao": "2026-01-11T13:50:00.000Z"
}
```

### 📊 Monitoramento Contínuo

Verificar status a cada 5 minutos:
```bash
watch -n 300 'curl -s http://localhost:3333/api/whatsapp/status | jq .'
```

---

## 📞 Suporte

### Quando Contatar Suporte

- ❌ Interface não carrega
- ❌ QR Code não aparece
- ❌ Validação falha em todos os métodos
- ❌ WhatsApp desconecta constantemente
- ❌ Erros na aplicação (console)

### Informações para Incluir

1. **Versão do Node.js:**
   ```bash
   node --version
   ```

2. **Versão da aplicação:**
   ```bash
   grep version package.json
   ```

3. **Logs da aplicação:**
   ```bash
   tail -100 dados/sessoes-whatsapp/logs/*
   ```

4. **Erro no console:**
   ```
   Copiar texto completo do erro
   ```

5. **Navegador e SO:**
   - Chrome/Firefox/Safari/Edge
   - Windows/Mac/Linux

---

## 🎉 Sucesso!

Parabéns! Seu WhatsApp agora está:

✅ **Sincronizado** - Com validação robusta  
✅ **Online** - 24/7 com keep-alive automático  
✅ **Protegido** - Com múltiplas opções de autenticação  
✅ **Monitorado** - Com logs e status em tempo real  

Para mais informações, consulte `SINCRONIZACAO-WHATSAPP-ROBUSTO.md`
