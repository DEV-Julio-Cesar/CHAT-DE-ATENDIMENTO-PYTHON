# 🧪 Checklist de Testes - v2.0.2

## Status: ✅ PRONTO PARA TESTES

Este documento serve como checklist para validar todas as funcionalidades implementadas na v2.0.2.

---

## 📋 Seção 1: Inicialização e Login

### Teste 1.1: Inicializar Aplicação
- [ ] Executar `npm start`
- [ ] Aguardar: "API ouvindo em http://localhost:3333"
- [ ] Nenhum erro na console
- [ ] Janela Electron abre corretamente

**Esperado:** ✅ Tela de login aparece
**Falha:** ❌ Se houver erro JavaScript ou erro de conexão

### Teste 1.2: Fazer Login
- [ ] Abrir: http://localhost:3333 (se não automático)
- [ ] Digitar usuário: `admin`
- [ ] Digitar senha: `admin`
- [ ] Clicar em "Entrar"

**Esperado:** ✅ Redirecionado para tela principal
**Falha:** ❌ Se auth falhar ou ficar na tela de login

### Teste 1.3: Navegação para Pool Manager
- [ ] Na tela principal, procurar menu de navegação
- [ ] Clicar em "Pool Manager" ou equivalente
- [ ] Aguardar carregamento

**Esperado:** ✅ Interface do gerenciador de pool carrega
**Falha:** ❌ Se página ficar em branco ou erro 404

---

## 🎯 Seção 2: Modal de Seleção de Método

### Teste 2.1: Abrir Modal
- [ ] No Pool Manager, clicar em "➕ Adicionar Nova Conexão"
- [ ] Aguardar modal aparecer

**Esperado:** ✅ Modal com duas opções aparece:
```
📱 Conectar por Número
📷 Conectar por QR Code
```
**Falha:** ❌ Modal não abre, botão não funciona

### Teste 2.2: Verificar Estilos do Modal
- [ ] Modal tem fundo escuro
- [ ] Modal está centralizado na tela
- [ ] Duas opções com ícones e textos
- [ ] Texto legível

**Esperado:** ✅ Interface bonita e profissional
**Falha:** ❌ Elementos fora de lugar, cores erradas

### Teste 2.3: Fechar Modal
- [ ] Clicar em "✕" (botão de fechar)
- [ ] Ou clicar fora do modal

**Esperado:** ✅ Modal desaparece
**Falha:** ❌ Modal fica visível

---

## 📱 Seção 3: Interface de Conexão por Número

### Teste 3.1: Abrir Interface de Número
- [ ] Com modal aberto, clicar em "📱 Conectar por Número"
- [ ] Aguardar nova janela/aba abrir

**Esperado:** ✅ Nova janela com interface `conectar-numero.html`
**Falha:** ❌ Janela não abre, erro JavaScript

### Teste 3.2: Verificar Componentes da Interface
- [ ] Título "Conectar WhatsApp por Número"
- [ ] Campo de entrada de telefone
- [ ] Texto de formato: "55 + DDD + Número"
- [ ] Exemplo: "5511999999999"
- [ ] Botão "CONECTAR"
- [ ] Área para QR Code (vazia inicialmente)

**Esperado:** ✅ Todos os componentes visíveis
**Falha:** ❌ Faltam elementos, layout quebrado

### Teste 3.3: Validação de Número - Formato Inválido
- [ ] Digitar: `1199999999` (sem 55)
- [ ] Observar: Input muda cor ou exibe mensagem

**Esperado:** ✅ Input fica vermelho ou mostra erro
**Falha:** ❌ Nenhuma validação visual

### Teste 3.4: Validação de Número - Formato Inválido (caracteres)
- [ ] Digitar: `55-11-99999999` (com hífens)
- [ ] Observar: Validação

**Esperado:** ✅ Input invalida ou remove caracteres
**Falha:** ❌ Aceita formato errado

### Teste 3.5: Validação de Número - Formato Válido
- [ ] Limpar campo
- [ ] Digitar: `5511999999999` (13 dígitos válidos)
- [ ] Observar: Botão CONECTAR fica ativo

**Esperado:** ✅ Botão CONECTAR ativado (não mais cinza)
**Falha:** ❌ Botão continua desativado

### Teste 3.6: Botão CONECTAR Desativado até Preenchimento
- [ ] Recarregar página
- [ ] Verificar: Botão está cinza/desativado
- [ ] Digitar um número válido
- [ ] Verificar: Botão ativa (cor diferente)

**Esperado:** ✅ Botão responde a preenchimento
**Falha:** ❌ Botão sempre ativado ou sempre desativado

---

## 🔌 Seção 4: Conexão WhatsApp

### Teste 4.1: Clique em CONECTAR
- [ ] Com número válido digitado
- [ ] Clicar em botão "CONECTAR"
- [ ] Aguardar resposta do servidor

**Esperado:** 
✅ Spinner/loading aparece
✅ Texto: "Gerando QR Code..."
✅ Após ~5 segundos: QR Code aparece

**Falha:** ❌ Erro de servidor, timeout

### Teste 4.2: Verificar QR Code Gerado
- [ ] QR Code deve ser uma imagem quadrada
- [ ] Deve ter padrão de pixels preto e branco
- [ ] Deve ser legível por câmera de celular

**Esperado:** ✅ QR válido e escaneável
**Falha:** ❌ Imagem corrupta, não é QR válido

### Teste 4.3: Scanning do QR Code
- [ ] Pegar um celular com WhatsApp
- [ ] Abrir WhatsApp
- [ ] Ir em: **Configurações** → **Dispositivos conectados** → **Conectar um dispositivo**
- [ ] Abrir câmera e apontar para QR Code na tela

**Esperado:** ✅ WhatsApp detecta QR
**Falha:** ❌ Câmera não lê QR

### Teste 4.4: Confirmação de Conexão
- [ ] Após scanning bem-sucedido
- [ ] WhatsApp mostra: "Conectar como [seu_numero]"
- [ ] Clicar em "CONECTAR"

**Esperado:** ✅ WhatsApp inicia sincronização
**Falha:** ❌ WhatsApp rejeita QR

### Teste 4.5: Feedback Visual no Frontend
- [ ] Enquanto WhatsApp sincroniza
- [ ] Interface mostra: "Autenticando..."
- [ ] Barra de progresso ou spinner ativo

**Esperado:** ✅ Feedback visual contínuo
**Falha:** ❌ Tela congelada ou sem feedback

### Teste 4.6: Sucesso na Interface
- [ ] Após sincronização completa (~10-30 segundos)
- [ ] Mensagem aparece: "✅ Conectado com sucesso!"
- [ ] Mostra número conectado
- [ ] Mostra status "PRONTO"

**Esperado:** ✅ Mensagem de sucesso aparece
**Falha:** ❌ Timeout, nenhuma mensagem

### Teste 4.7: Auto-fechamento
- [ ] Após sucesso
- [ ] Aguardar 2 segundos
- [ ] Janela fecha automaticamente

**Esperado:** ✅ Janela fecha e retorna ao Pool Manager
**Falha:** ❌ Janela fica aberta indefinidamente

---

## 📊 Seção 5: Verificação no Pool Manager

### Teste 5.1: Nova Conexão Aparece
- [ ] De volta ao Pool Manager (janela fechou)
- [ ] Procurar na lista de conexões
- [ ] Deve aparecer entrada nova com:
  - Número conectado (ex: 5511999999999)
  - Status: ✅ CONECTADO
  - Ícone verde/checkmark

**Esperado:** ✅ Conexão listada com sucesso
**Falha:** ❌ Nenhuma conexão aparece

### Teste 5.2: Status Correto
- [ ] Clicar em "🔄 Atualizar Lista"
- [ ] Verificar: Status continua como CONECTADO
- [ ] Não desconecta sozinho

**Esperado:** ✅ Status permanece CONECTADO
**Falha:** ❌ Status muda para desconectado

### Teste 5.3: Validação de Persistência (5 minutos)
- [ ] Deixar aplicação rodando
- [ ] Verificar a cada 1 minuto: Status permanece CONECTADO?
- [ ] Fazer por 5 minutos

**Esperado:** ✅ Conexão persiste
**Falha:** ❌ Desconecta após alguns minutos (problema v2.0.1)

### Teste 5.4: Buttons Funcionam
- [ ] Clicar em "💬 Chat" - Deve abrir interface de chat
- [ ] Clicar em "🔄 Reconectar" - Deve reconectar se desconectado
- [ ] Clicar em "❌ Desconectar" - Deve desconectar com confirmação

**Esperado:** ✅ Todos os buttons funcionam
**Falha:** ❌ Buttons não responsivos

---

## 🔐 Seção 6: Método de QR Code Tradicional

### Teste 6.1: Abrir Modal Novamente
- [ ] Clicar em "➕ Adicionar Nova Conexão" de novo
- [ ] Modal de seleção aparece

**Esperado:** ✅ Modal funciona novamente
**Falha:** ❌ Modal não abre

### Teste 6.2: Escolher QR Code
- [ ] Clicar em "📷 Conectar por QR Code"
- [ ] Aguardar janela do QR tradicional abrir

**Esperado:** ✅ Janela de QR abre
**Falha:** ❌ Janela não abre, erro

### Teste 6.3: QR Tradicional Funciona
- [ ] Verificar: QR Code aparece
- [ ] Escanear com um número diferente
- [ ] Verificar: Conecta como esperado

**Esperado:** ✅ Método QR tradicional mantém funcionando
**Falha:** ❌ Quebrou método anterior

---

## 🛡️ Seção 7: Testes de Erro

### Teste 7.1: Desconexão Durante Conexão
- [ ] Iniciar processo de conexão por número
- [ ] Enquanto QR está em tela
- [ ] Desconectar internet ou rejeitar no WhatsApp

**Esperado:** ✅ Erro exibido, pode tentar novamente
**Falha:** ❌ Aplicação trava ou fica em estado indefinido

### Teste 7.2: Timeout de QR
- [ ] Iniciar processo de conexão
- [ ] QR aparece
- [ ] NÃO escanear
- [ ] Aguardar 5 minutos

**Esperado:** ✅ Mensagem: "Conexão expirou. Tente novamente"
**Falha:** ❌ Fica aguardando indefinidamente

### Teste 7.3: Múltiplas Conexões Simultâneas
- [ ] Iniciar 2 conexões ao mesmo tempo (em tabs diferentes)
- [ ] Conectar números diferentes
- [ ] Ambas devem ficar online

**Esperado:** ✅ Ambas as conexões funcionam independentemente
**Falha:** ❌ Uma interfere na outra

### Teste 7.4: Reconexão Automática
- [ ] Com uma conexão ativa
- [ ] Desconectar internet no celular
- [ ] Aguardar ~5 segundos
- [ ] Reconectar internet
- [ ] Verificar: App reconecta automaticamente

**Esperado:** ✅ Reconexão automática (hotfix v2.0.2)
**Falha:** ❌ Fica desconectado

---

## 📱 Seção 8: Testes de API Direta

### Teste 8.1: POST /api/whatsapp/conectar-por-numero

```bash
curl -X POST http://localhost:3333/api/whatsapp/conectar-por-numero \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999"}'
```

**Esperado Resposta (200):**
```json
{
  "success": true,
  "clientId": "cliente_abc123",
  "telefone": "5511999999999",
  "qrCode": "[base64_string]"
}
```

**Teste:** [ ] Execute o comando
**Resultado:** ✅ / ❌

### Teste 8.2: GET /api/whatsapp/status/:clientId

```bash
curl http://localhost:3333/api/whatsapp/status/cliente_abc123
```

**Esperado Resposta (200):**
```json
{
  "success": true,
  "clientId": "cliente_abc123",
  "status": "ready",
  "telefone": "5511999999999",
  "ativo": true
}
```

**Teste:** [ ] Execute o comando
**Resultado:** ✅ / ❌

### Teste 8.3: Validação de Erro - Formato Inválido

```bash
curl -X POST http://localhost:3333/api/whatsapp/conectar-por-numero \
  -H "Content-Type: application/json" \
  -d '{"telefone": "1199999999"}'
```

**Esperado Resposta (400):**
```json
{
  "success": false,
  "message": "Formato inválido. Use: 5511999999999"
}
```

**Teste:** [ ] Execute o comando
**Resultado:** ✅ / ❌

---

## 📝 Seção 9: Verificação de Logs

### Teste 9.1: Console Limpa
- [ ] Abrir DevTools (F12)
- [ ] Procurar por: `[ERRO] ƒöÑ UNCAUGHT`
- [ ] Deve haver ZERO erros críticos relacionados a WhatsApp

**Esperado:** ✅ Apenas [INFO] e [SUCESSO] logs
**Falha:** ❌ Erros visíveis na console

### Teste 9.2: Logs de Conexão
- [ ] Procurar por mensagens:
  - `"Conectado com sucesso"`
  - `"Status: ready"`
  - `"Health check"`

**Esperado:** ✅ Logs apropriados aparecem
**Falha:** ❌ Nenhum log relevante

### Teste 9.3: Arquivo de Logs
- [ ] Procurar em: `dados/logs/`
- [ ] Verificar último arquivo: `app_YYYY-MM-DD.log`
- [ ] Procurar por entradas de conexão

**Esperado:** ✅ Arquivo contém logs de conexão
**Falha:** ❌ Arquivo não existe ou vazio

---

## 🎯 Resumo de Testes

### ✅ Testes Passando
- [ ] Inicialização
- [ ] Login
- [ ] Modal de seleção
- [ ] Interface de número
- [ ] Validação de número
- [ ] Conexão WhatsApp
- [ ] QR Code display
- [ ] Feedback visual
- [ ] Sucesso e fechamento
- [ ] Pool Manager atualiza
- [ ] Persistência de conexão
- [ ] Método QR tradicional
- [ ] Tratamento de erro
- [ ] Timeout
- [ ] Múltiplas conexões
- [ ] Reconexão automática
- [ ] API endpoints
- [ ] Logs limpos

### ⚠️ Testes Falhando
- [ ] Anotar abaixo:

```
1. _________________________________
2. _________________________________
3. _________________________________
```

### 📊 Resultado Final

- **Total de Testes:** 60+
- **Testes Passando:** _____ / 60
- **Taxa de Sucesso:** _____%

---

## 🚀 Status de Deploy

### ✅ Pronto para Deploy?

- [ ] Todos os testes passando
- [ ] Sem erros críticos
- [ ] Logs limpos
- [ ] Performance ok
- [ ] Documentação atualizada
- [ ] Código revisado

### ❌ Bloqueadores?

- [ ] Descrever problemas encontrados:

```
1. _________________________________
2. _________________________________
3. _________________________________
```

---

## 📞 Suporte

Se algum teste falhar:

1. Anote o número do teste
2. Procure erro na console (F12)
3. Verifique logs em `dados/logs/`
4. Tente novamente (pode ser temporário)
5. Se persistir, entre em contato

---

**Data de Teste:** _______________  
**Testador:** _______________  
**Resultado Final:** ✅ / ❌

---

*Use este checklist para validar v2.0.2 antes de usar em produção.*
