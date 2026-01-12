# 📱 Guia de Conexão por Número de Telefone

## Visão Geral

A partir da versão v2.0.2, o chat de atendimento suporta **dois métodos de conexão** com WhatsApp:

1. **Conectar por QR Code** (método tradicional)
2. **Conectar por Número** (novo método - v2.0.2)

## 🎯 Método: Conectar por Número

Este novo método permite que o atendente conecte uma conta WhatsApp digitando manualmente o número de telefone, sem depender de QR Code automático.

### Vantagens

✅ Maior controle sobre qual número conectar
✅ Menos dependência de auto-scanning
✅ Mais previsível e determinístico
✅ Ideal para múltiplas contas
✅ Sessões persistem indefinidamente

### Pré-requisitos

- Número de telefone no formato internacional: `55DDNNNNNNNNN`
  - `55` = código do Brasil
  - `DD` = código da área (DDD)
  - `NNNNNNNNN` = número com 8-9 dígitos

**Exemplos válidos:**
- `5511987654321` (São Paulo com 9 dígitos)
- `5511987654321` (São Paulo com 8 dígitos)
- `5521987654321` (Rio de Janeiro)
- `5585987654321` (Ceará)

## 📝 Como Usar

### Passo 1: Abrir o Gerenciador de Pool

1. Faça login no chat de atendimento
2. Navegue até **"Pool Manager"** (Gerenciador de Conexões)
3. Clique no botão **"➕ Adicionar Nova Conexão"**

### Passo 2: Escolher Método de Conexão

Uma modal aparecerá com duas opções:

```
┌─────────────────────────────────────┐
│  📱 Conectar por Número             │
│  Digite o número do WhatsApp para   │
│  conectar                            │
│                                     │
│  📷 Conectar por QR Code            │
│  Escaneie o código QR com seu       │
│  celular                             │
└─────────────────────────────────────┘
```

**Clique em "📱 Conectar por Número"**

### Passo 3: Digite o Número

Uma nova janela abrirá (conectar-numero.html):

```
┌─────────────────────────────────────┐
│  Conectar WhatsApp por Número      │
│                                     │
│  Formato: 55 + DDD + Número         │
│  Exemplo: 5511999999999             │
│                                     │
│  [____________________] ← Número    │
│                                     │
│  [    CONECTAR    ] ← Botão         │
└─────────────────────────────────────┘
```

**Exemplo:**
- Você está em São Paulo (DDD 11)
- Seu número é 9 9876-5432
- Digite: `5511998765432`

### Passo 4: Sistema Gera QR

Após digitar e clicar em "CONECTAR":

1. O servidor cria uma nova sessão WhatsApp
2. Gera automaticamente um **QR Code**
3. A interface exibe o QR na tela

```
┌─────────────────────────────────────┐
│  QR Code gerado!                    │
│  Escaneie com seu telefone          │
│                                     │
│  ┌─────────────────┐               │
│  │  █████████      │               │
│  │  █ ███████ █    │               │
│  │  █ █   █ █ █    │               │
│  │  █ ███████ █    │               │
│  │  █       █      │               │
│  │  █████████      │               │
│  └─────────────────┘               │
│                                     │
│  ⏳ Aguardando confirmação...       │
└─────────────────────────────────────┘
```

### Passo 5: Escanear QR com o Celular

1. Abra WhatsApp no seu telefone
2. Vá para **Configurações** → **Dispositivos conectados** → **Conectar um dispositivo**
3. **Escaneie o QR Code** exibido na tela

### Passo 6: Confirmação de Sucesso

Após escanear o QR Code:

```
┌─────────────────────────────────────┐
│  ✅ Conectado com sucesso!          │
│                                     │
│  Número: 5511998765432              │
│  Status: PRONTO                     │
│                                     │
│  A janela será fechada...           │
└─────────────────────────────────────┘
```

A janela **fecha automaticamente** em alguns segundos e você retorna ao Gerenciador de Pool.

## 🔍 Verificação de Status

Na interface do Gerenciador de Pool, você verá a nova conexão:

```
┌──────────────────────────────────────┐
│ Cliente ID: abc123                   │
│ Número: 5511998765432                │
│ Status: ✅ CONECTADO                 │
│ Última atividade: agora               │
│                                      │
│ [💬 Chat] [🔄 Reconectar] [❌ Desconectar]
└──────────────────────────────────────┘
```

## ⚙️ Endpoints da API

### 1. Conectar por Número

```http
POST /api/whatsapp/conectar-por-numero
Content-Type: application/json

{
  "telefone": "5511998765432",
  "metodo": "numero-manual"
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "clientId": "cliente_abc123",
  "telefone": "5511998765432",
  "qrCode": "[QR_CODE_BASE64_STRING]"
}
```

**Resposta de Erro (400):**
```json
{
  "success": false,
  "message": "Formato inválido. Use: 5511999999999"
}
```

### 2. Verificar Status da Conexão

```http
GET /api/whatsapp/status/:clientId
```

**Resposta:**
```json
{
  "success": true,
  "clientId": "cliente_abc123",
  "telefone": "5511998765432",
  "status": "ready",
  "ativo": true
}
```

**Status Possíveis:**
- `qr_ready` - QR Code pronto para escanear
- `ready` - Conectado e pronto
- `authenticated` - Autenticado
- `disconnected` - Desconectado
- `error` - Erro na conexão

## 🔧 Comparação: Número vs QR

| Aspecto | Por Número | Por QR Code |
|---------|-----------|-----------|
| **Controle** | Alto | Automático |
| **Velocidade** | Média | Rápida |
| **Confiabilidade** | Alta | Variável |
| **Múltiplas contas** | Excelente | Bom |
| **Uso em produção** | ✅ Recomendado | ⚠️ Alternativa |

## ⚠️ Erros Comuns

### Erro 1: "Formato Inválido"

**Problema:** Número digitado no formato errado

**Solução:**
- Use exatamente 55 + DDD + número
- Sem espaços, hífen ou parênteses
- Total de 13 dígitos

❌ Errado:
```
11 9 9876-5432
(11) 99876-5432
+55 11 99876-5432
```

✅ Correto:
```
5511998765432
```

### Erro 2: "Timeout - Conexão não confirmada"

**Problema:** QR Code não foi escaneado a tempo

**Solução:**
1. Certifique-se que WhatsApp está aberto
2. Tente novamente
3. Verifique conexão de internet
4. Reinicie a aplicação se necessário

### Erro 3: "Sessão Expirada"

**Problema:** Sessão expirou antes da confirmação

**Solução:**
1. Clique novamente em "Adicionar Nova Conexão"
2. Digite o número novamente
3. Escaneie o novo QR Code imediatamente

## 🚀 Recurso: Auto-Reconnect

Desde a v2.0.2, todas as conexões (por número ou QR) têm:

- ✅ **Auto-reconexão automática** em caso de desconexão
- ✅ **Persistência de sessão** indefinida
- ✅ **Health check** a cada 60 segundos
- ✅ **Detecção de desconexão** em tempo real

## 📞 Suporte

Se encontrar problemas:

1. Verifique o log em: `dados/logs/`
2. Procure erros relacionados a "conectar-por-numero"
3. Tente limpar cache e cookies
4. Reinicie a aplicação

## 📚 Documentação Relacionada

- [SOLUCAO-DESCONEXAO-WHATSAPP.md](./SOLUCAO-DESCONEXAO-WHATSAPP.md) - Corrigir desconexões
- [CHANGELOG.md](./CHANGELOG.md) - Histórico de versões
- [ESTRUTURA.md](./docs/ESTRUTURA.md) - Arquitetura geral

---

**Versão:** 2.0.2  
**Data:** 2026-01-11  
**Tipo:** Feature Enhancement
