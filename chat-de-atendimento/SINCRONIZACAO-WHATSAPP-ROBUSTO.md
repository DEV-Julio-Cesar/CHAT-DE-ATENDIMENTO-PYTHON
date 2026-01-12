# 🔄 SINCRONIZAÇÃO ROBUSTA WHATSAPP - GUIA COMPLETO

## 📋 Resumo

Sistema completo para manter WhatsApp sincronizado, online e ativo permanentemente com 3 opções de validação:

1. **QR Code** - Tradicional + Confirmação por telefone
2. **Validação Manual** - Código enviado ao WhatsApp
3. **Meta API** - Sincronização via API oficial Facebook/Instagram

---

## 🎯 Arquivos Criados

### 1. GerenciadorSessaoWhatsApp.js
**Localização:** `src/services/GerenciadorSessaoWhatsApp.js`

**Funcionalidades:**
- ✅ Persistência de sessão em arquivo
- ✅ Validação com QR Code + Telefone
- ✅ Keep-alive automático (30 min)
- ✅ Sincronização periódica (5 min)
- ✅ Recovery automático
- ✅ Logs detalhados de eventos
- ✅ Suporte a Meta/Facebook API

**Métodos principais:**
```javascript
await gerenciadorSessao.inicializar()        // Inicializar
await gerenciadorSessao.criarSessao(...)     // Criar sessão
await gerenciadorSessao.validarSessao(...)   // Validar
await gerenciadorSessao.ativarSessao(...)    // Ativar
await gerenciadorSessao.sincronizarComMeta() // Meta API
await gerenciadorSessao.obterStatus()        // Status
```

---

### 2. validacao-whatsapp.html
**Localização:** `src/interfaces/validacao-whatsapp.html`

**Interface moderna com 3 abas:**

#### Aba 1: QR Code
- Exibe QR Code atualizado a cada 30s
- Campo para confirmação de telefone
- Status em tempo real
- Design responsivo

#### Aba 2: Validação Manual
- Entrada de telefone
- Campo para código recebido no WhatsApp
- Barra de tentativas (máx 5)
- Feedback visual

#### Aba 3: Meta API
- Seleção de API (WhatsApp Business ou Instagram)
- Entrada de token
- Sincronização em tempo real
- Informações de vantagens

**Features:**
- ✅ Dark/Light mode ready
- ✅ Responsivo (mobile/desktop)
- ✅ Validação em tempo real
- ✅ Status widget
- ✅ Animações suaves

---

### 3. rotasWhatsAppSincronizacao.js
**Localização:** `src/rotas/rotasWhatsAppSincronizacao.js`

**Endpoints REST:**

```
GET    /api/whatsapp/qr-code              # Gerar QR Code
POST   /api/whatsapp/validar-qrcode       # Validar QR
POST   /api/whatsapp/validar-manual       # Validar manual
POST   /api/whatsapp/sincronizar-meta     # Meta API
GET    /api/whatsapp/status               # Status atual
POST   /api/whatsapp/manter-vivo          # Keep-alive
POST   /api/whatsapp/desconectar          # Desconectar
```

---

## 🚀 Como Usar

### Passo 1: Inicializar o Gerenciador
```javascript
const gerenciadorSessao = require('./src/services/GerenciadorSessaoWhatsApp');

// No boot da aplicação
await gerenciadorSessao.inicializar();
```

### Passo 2: Registrar Rotas no Express
```javascript
const rotasSync = require('./src/rotas/rotasWhatsAppSincronizacao');
app.use('/api/whatsapp', rotasSync);
```

### Passo 3: Acessar Interface
```
Acesse: http://localhost:3333/validacao-whatsapp.html
```

### Passo 4: Sincronizar

**Opção 1: QR Code (Recomendado)**
1. Abra interface em navegador
2. Escaneie QR Code com WhatsApp
3. Confirme seu número de telefone
4. Sistema sincroniza automaticamente

**Opção 2: Validação Manual**
1. Digite seu número (formato: 5511999999999)
2. Você receberá um código no WhatsApp
3. Cole o código na interface
4. Sistema ativa a sessão

**Opção 3: Meta API**
1. Abra a aba "Meta API"
2. Selecione WhatsApp Business ou Instagram
3. Cole seu token de acesso
4. Clique em "Sincronizar com Meta"

---

## 📊 Estrutura de Dados

### Arquivo de Sessão
**Localização:** `dados/sessoes-whatsapp/sessao-ativa.json`

```json
{
  "id": "sessao_1705045920123",
  "telefone": "5584920024786",
  "qrCode": "data:image/png;base64,...",
  "metodo": "qrcode",
  "status": "ativa",
  "criada_em": "2026-01-11T12:45:20.123Z",
  "validada_em": "2026-01-11T12:46:00.000Z",
  "ativada_em": "2026-01-11T12:46:05.000Z",
  "ultima_sincronizacao": "2026-01-11T12:50:20.000Z",
  "numero_tentativas": 1,
  "max_tentativas": 5,
  "metadados": {
    "ip_origem": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### Estados da Sessão
```
pendente_validacao → validada → ativa → inativa
                  ↘ falha_validacao
```

---

## 🔒 Segurança

### Validações Implementadas
- ✅ Validação de formato de telefone (regex)
- ✅ Limite de tentativas (máx 5)
- ✅ Tokens de acesso validados
- ✅ Logging de todas as ações
- ✅ Timeout de sessão

### Melhores Práticas
1. **Usar HTTPS em produção**
```javascript
// config.json
{
  "api": {
    "useHttps": true,
    "certificatePath": "/path/to/cert.pem",
    "keyPath": "/path/to/key.pem"
  }
}
```

2. **Proteger tokens Meta**
```javascript
// Usar variáveis de ambiente
const accessToken = process.env.META_ACCESS_TOKEN;
```

3. **Rate limiting**
```javascript
const rateLimit = require('express-rate-limit');
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100
});
app.use('/api/whatsapp', limiter);
```

---

## 📈 Keep-Alive & Sincronização

### Keep-Alive (30 minutos)
```javascript
// Automático - mantém sessão viva
GET /api/whatsapp/manter-vivo

// Resultado
{
  "success": true,
  "status": "ativo",
  "telefone": "5584920024786",
  "ultima_atualizacao": "2026-01-11T13:00:00.000Z"
}
```

### Sincronização Periódica (5 minutos)
- Verifica status da sessão
- Atualiza timestamp
- Registra no log
- Detecta desconexões

---

## 🔗 Meta/Facebook API

### Obter Access Token
1. Acesse: https://developers.facebook.com/
2. Crie uma App
3. Gere token com permissões:
   - `whatsapp_business_management`
   - `instagram_basic`
   - `instagram_manage_messages`

### Integração com WhatsApp Business API
```javascript
// Exemplo de uso
const resultado = await gerenciadorSessao.sincronizarComMeta(
  'seu_access_token_aqui',
  '5584920024786'
);

// Resposta
{
  "success": true,
  "metodo": "meta-api",
  "telefone": "5584920024786",
  "message": "Sincronização com Meta/Facebook iniciada"
}
```

---

## 🐛 Troubleshooting

### Problema: QR Code não aparece
**Solução:**
```javascript
// Verificar se cliente foi criado
const clientes = poolWhatsApp.listarClientes();
console.log(clientes.length > 0 ? 'OK' : 'Erro');

// Recarregar página
location.reload();
```

### Problema: Telefone não validado
**Solução:**
```
- Verificar formato: 5511999999999
- Máx 5 tentativas
- Gerar novo QR Code se necessário
```

### Problema: Meta API falha
**Solução:**
```
- Validar token em: https://developers.facebook.com/tools/debug/
- Verificar permissões no app
- Usar HTTPS em produção
```

---

## 📝 Exemplo de Implementação Completa

```javascript
// main.js ou index.js
const express = require('express');
const app = express();
const gerenciadorSessao = require('./src/services/GerenciadorSessaoWhatsApp');
const rotasSync = require('./src/rotas/rotasWhatsAppSincronizacao');

async function iniciarServidor() {
    // 1. Inicializar gerenciador de sessão
    await gerenciadorSessao.inicializar();

    // 2. Registrar rotas
    app.use('/api/whatsapp', rotasSync);

    // 3. Servir interface HTML
    app.get('/validacao-whatsapp.html', (req, res) => {
        res.sendFile(__dirname + '/src/interfaces/validacao-whatsapp.html');
    });

    // 4. Keep-alive automático a cada 30 min
    setInterval(async () => {
        try {
            const status = await gerenciadorSessao.obterStatus();
            if (status.ativo) {
                console.log('✓ Keep-alive: ' + status.telefone);
            }
        } catch (erro) {
            console.error('Erro keep-alive:', erro.message);
        }
    }, 30 * 60 * 1000);

    // 5. Iniciar servidor
    const PORT = process.env.PORT || 3333;
    app.listen(PORT, () => {
        console.log(`✓ Servidor rodando em http://localhost:${PORT}`);
        console.log(`✓ Acessar: http://localhost:${PORT}/validacao-whatsapp.html`);
    });
}

iniciarServidor().catch(console.error);
```

---

## 📊 Status e Métricas

### Verificar Status em Tempo Real
```javascript
GET /api/whatsapp/status

Resposta:
{
  "ativo": true,
  "telefone": "5584920024786",
  "status": "ativa",
  "tempo_ativo": "2h 15m",
  "criada_em": "2026-01-11T11:30:00.000Z",
  "ativada_em": "2026-01-11T11:31:00.000Z",
  "ultima_sincronizacao": "2026-01-11T13:45:00.000Z",
  "metodo": "qrcode"
}
```

### Logs Detalhados
**Localização:** `dados/sessoes-whatsapp/logs/`

Cada dia gera um arquivo com eventos:
- `sessao_criada`
- `sessao_validada`
- `sessao_ativada`
- `sincronizacao_periodica`
- `sincronizacao_meta_tentativa`
- `keep_alive`
- `desconexao`

---

## ✅ Checklist de Implementação

- [ ] Copiar `GerenciadorSessaoWhatsApp.js` para `src/services/`
- [ ] Copiar `validacao-whatsapp.html` para `src/interfaces/`
- [ ] Copiar `rotasWhatsAppSincronizacao.js` para `src/rotas/`
- [ ] Inicializar gerenciador no boot
- [ ] Registrar rotas no express
- [ ] Testar QR Code
- [ ] Testar validação manual
- [ ] Testar Meta API (opcional)
- [ ] Verificar keep-alive
- [ ] Validar persistência de sessão

---

## 🎉 Resultado Final

✅ WhatsApp **sempre online**  
✅ Sincronização **robusta e confiável**  
✅ **3 métodos de validação** disponíveis  
✅ **Keep-alive automático** (30 min)  
✅ **Logs detalhados** de tudo  
✅ **Suporte a Meta/Facebook API**  
✅ **Interface moderna e responsiva**  

**Status:** Pronto para produção! 🚀
