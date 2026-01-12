# 📱 PASSO A PASSO REVISADO - Conexão por Número (v2.0.2)

## ✅ Versão Corrigida e Validada

---

## 🎯 Opção 1: Via Electron (npm start) - Desktop

### ⚠️ Importante
> Quando você usa `npm start`, a aplicação abre como desktop (Electron).
> NÃO é necessário abrir http://localhost:3333 manualmente.

### Passo a Passo Correto

#### Passo 1: Iniciar a Aplicação
```bash
npm start
```
✓ Aguarde 10-15 segundos  
✓ Janela Electron abrirá automaticamente  
✓ Você verá a tela PRINCIPAL com menu

#### Passo 2: Verificar Tela Principal
Você deve ver:
```
╔════════════════════════════════════════╗
║  💼 Sistema de Atendimento WhatsApp    ║
║     Versão 2.0.0                       ║
║                                        ║
║  ✓ Clientes Conectados: 0              ║
║  ✓ Status: Online                      ║
║                                        ║
║  [Recursos Disponíveis]                ║
║  ┌────────────────────────────────┐   ║
║  │ 🔗 Gerenciar Conexões          │   ║
║  │ 📱 Conectar WhatsApp           │   ║
║  │ 💬 Abrir Chat                  │   ║
║  │ 🎯 Chat com Filas             │   ║
║  │ ... mais opções                │   ║
║  └────────────────────────────────┘   ║
╚════════════════════════════════════════╝
```

#### Passo 3: Clique em "🔗 Gerenciar Conexões"
✓ Abrirá a interface **Pool Manager**  
✓ Você verá a lista de conexões (vazia no primeiro uso)

#### Passo 4: Procure pelo Botão "➕ Adicionar Nova Conexão"
✓ Localize na interface Pool Manager  
✓ Este botão abre o modal de seleção

#### Passo 5: Clique em "➕ Adicionar Nova Conexão"
✓ Um **MODAL** apareceá com 2 opções:
```
┌─────────────────────────────────────┐
│  Adicionar Nova Conexão             │
│                                     │
│  📱 Conectar por Número             │
│  Digite o número do WhatsApp para   │
│  conectar                            │
│                                     │
│  📷 Conectar por QR Code            │
│  Escaneie o código QR com seu       │
│  celular                             │
└─────────────────────────────────────┘
```

#### Passo 6: Escolha "📱 Conectar por Número"
✓ **Uma nova janela abrirá** com interface de entrada  
✓ Você verá um formulário pedindo o número

#### Passo 7: Digite seu Número de WhatsApp
Digite no formato: **55DDNNNNNNNNN**

**Exemplos válidos:**
- `5511999999999` (São Paulo, 9 dígitos)
- `5511998765432` (São Paulo, 8 dígitos)  
- `5521987654321` (Rio de Janeiro)
- `5585987654321` (Ceará)

✓ O botão **"CONECTAR"** ficará ativo quando número válido

#### Passo 8: Clique em "CONECTAR"
✓ Sistema enviará pedido ao servidor  
✓ QR Code será gerado (~3-5 segundos)  
✓ Verá mensagem: "Gerando QR Code..."

#### Passo 9: QR Code Aparecerá
```
Você verá na tela:
┌──────────────────┐
│  QR Code aqui    │
│  (imagem        │
│  escaneável)     │
│                  │
│ ⏳ Aguardando...  │
└──────────────────┘
```

#### Passo 10: Escaneie o QR com WhatsApp

**No seu celular:**
1. Abra WhatsApp
2. Vá em **Configurações** → **Dispositivos Conectados** → **Conectar um Dispositivo**
3. Toque em **"Conectar um Dispositivo"**
4. Abra a câmera
5. **Aponte para o QR Code** na tela do computador

#### Passo 11: Confirmação no WhatsApp
Seu celular mostrará:
```
Conectar como [seu número]

✓ [CONECTAR]
```
✓ Toque em **"CONECTAR"** no celular

#### Passo 12: Aguarde Sincronização
- ⏳ Interface mostrará: "Autenticando..."
- ⏳ Aguarde 10-30 segundos
- ✅ Mensagem: "✅ Conectado com sucesso!"

#### Passo 13: Janela Fecha Automaticamente
- ✅ Após 2 segundos, a janela de número fecha
- ✅ Retorna ao **Pool Manager**

#### Passo 14: Verificação
✓ Sua conexão aparece na lista:
```
┌─────────────────────────────────────┐
│ 5511999999999                       │
│ Status: ✅ CONECTADO                │
│ Última atividade: Agora              │
│                                     │
│ [💬 Chat] [🔄 Reconectar] [❌ Desc] │
└─────────────────────────────────────┘
```

---

## 🌐 Opção 2: Via Web (localhost) - Browser

### ⚠️ Importante
> Quando você acessa http://localhost:3333, está acessando a **versão web**.
> A aplicação Electron NÃO precisa estar rodando.
> Você precisará rodar a API separadamente.

### Pré-requisito
```bash
# Terminal 1: API/Backend
npm run ws

# Terminal 2 (opcional): Chat Interno
npm run chat:interno
```

### Passo a Passo Correto

#### Passo 1: Abrir Browser
Abra seu navegador e acesse:
```
http://localhost:3333
```

#### Passo 2: Tela de Login
Você verá:
```
╔════════════════════════════════════════╗
║  Login - Sistema de Atendimento        ║
║                                        ║
║  [Usuário____________]                 ║
║  [Senha______________]                 ║
║                                        ║
║           [ENTRAR]                     ║
╚════════════════════════════════════════╝
```

#### Passo 3: Digite Credenciais
- **Usuário:** `admin`
- **Senha:** `admin`

#### Passo 4: Clique em "ENTRAR"
✓ Será redirecionado para página principal

#### Passo 5: Página Principal Carrega
Você verá um menu com várias opções

#### Passo 6: Procure por Link "Gerenciar Conexões"
✓ No menu ou nav bar
✓ Pode estar como:
   - "🔗 Gerenciar Conexões"
   - "Pool Manager"
   - "Conexões"

#### Passo 7: Clique em "Gerenciar Conexões"
✓ Abrirá a página de Pool Manager
✓ Mostrará lista de conexões

#### Passo 8: Procure por "➕ Adicionar Nova Conexão"
✓ Botão deve estar em destaque
✓ Pode estar no topo ou rodapé da página

#### Passo 9: Clique em "➕ Adicionar Nova Conexão"
✓ Modal ou página abrirá com 2 opções

#### Passo 10: Escolha "📱 Conectar por Número"
✓ Página/modal de entrada abrirá

#### Passos 11-14: (Mesmos que Opção 1)
Siga os passos 7-14 da opção Electron acima

---

## 📊 Comparação: Electron vs Web

| Aspecto | Electron | Web |
|---------|----------|-----|
| **Comando** | `npm start` | `npm run ws` |
| **Acesso** | Desktop app | http://localhost:3333 |
| **Automatico** | Abre sozinho | Manual |
| **Login** | Auto | admin/admin |
| **Recomendado** | ✅ Sim | ⚠️ Desenvolvimento |

---

## ⚠️ Erros Comuns

### ❌ "Não encontro o botão de Adicionar Conexão"
**Solução:**
- Certificar que está em "Gerenciar Conexões" (Pool Manager)
- Atualizar página (F5)
- Procurar no topo/rodapé da página

### ❌ "Número não conecta - Formato Inválido"
**Solução:**
- Usar exatamente: 55DDNNNNNNNNN
- Sem espaços, hífens ou parênteses
- Total de 13 dígitos
- Começar com 55

❌ Errado:
```
11 9999-9999
(11) 99999999
+55 11 99999999
```

✅ Correto:
```
5511999999999
```

### ❌ "QR não aparece"
**Solução:**
- Aguardar 3-5 segundos
- Verificar console (F12) para erros
- Tentar novamente
- Verificar se API está rodando (logs)

### ❌ "QR aparece mas não escaneia"
**Solução:**
- Ter WhatsApp aberto no celular
- Estar em "Dispositivos Conectados"
- QR deve estar legível (não está pixelado)
- Tentar 3-4 vezes

### ❌ "Conexão desconecta após alguns segundos"
**Solução:**
- Verificar se v2.0.2 foi instalada
- Hotfix deve estar ativo
- Reconectar manualmente

---

## ✅ Checklist de Sucesso

- [ ] App inicia sem erros
- [ ] Menu principal carrega
- [ ] Encontra botão "Gerenciar Conexões"
- [ ] Modal de seleção aparece
- [ ] Consegue digitar número
- [ ] QR Code aparece
- [ ] Consegue escanear com celular
- [ ] Mensagem de sucesso aparece
- [ ] Conexão listada no Pool Manager
- [ ] Status mostra "✅ CONECTADO"

---

## 📞 Suporte

### Dúvida sobre passo a passo?
→ Leia [GUIA-CONEXAO-POR-NUMERO.md](GUIA-CONEXAO-POR-NUMERO.md)

### Problema técnico?
→ Veja [CHECKLIST-TESTES-V2-0-2.md](CHECKLIST-TESTES-V2-0-2.md) (Seção 7)

### Quer detalhes?
→ Consulte [docs/TECNICA-CONEXAO-POR-NUMERO.md](docs/TECNICA-CONEXAO-POR-NUMERO.md)

---

**Versão:** 2.0.2  
**Data:** 2026-01-11  
**Status:** ✅ Revisado e Validado

*Passo a passo testado em ambas as plataformas (Electron e Web).*
