# 📱 Como Enviar Mensagens pelo WhatsApp

## 🎯 Acesso Rápido

Abra no navegador:
```
http://localhost:8000/whatsapp
```

## ✅ Pré-requisitos

1. ✅ Serviço Node.js rodando (porta 3001)
2. ✅ WhatsApp conectado (QR Code escaneado)
3. ✅ Backend Python rodando (porta 8000)

## 📤 Como Enviar uma Mensagem

### Passo 1: Verificar Conexão

Ao abrir a página `/whatsapp`, você verá:

**Se conectado:**
- ✅ Ícone verde do WhatsApp
- ✅ Mensagem "WhatsApp Conectado!"
- ✅ Suas informações (nome e número)
- ✅ Formulário de envio aparece automaticamente

**Se desconectado:**
- ⏳ QR Code para escanear
- ⏳ Instruções de como conectar
- ❌ Formulário de envio oculto

### Passo 2: Preencher o Formulário

Quando conectado, você verá o formulário com 2 campos:

**1. Número do WhatsApp**
- Digite o número com código do país
- Formato: `5511999999999`
- Exemplo: `5584889868` (seu número)

**2. Mensagem**
- Digite a mensagem que deseja enviar
- Pode usar múltiplas linhas
- Contador de caracteres em tempo real

### Passo 3: Enviar

1. Clique no botão **"Enviar Mensagem"**
2. Aguarde a confirmação
3. Você verá uma notificação verde: ✅ "Mensagem enviada com sucesso!"

### Passo 4: Histórico

Após enviar, a mensagem aparecerá no histórico:
- 📱 Número do destinatário
- 💬 Texto da mensagem
- 🕐 Horário de envio
- Últimas 10 mensagens são mantidas

## 🎨 Interface

### Card 1: Status da Conexão
- Mostra se está conectado ou não
- QR Code (se desconectado)
- Informações da conta (se conectado)
- Botões: Atualizar Status, Desconectar, Testar Conexão

### Card 2: Enviar Mensagem (só aparece quando conectado)
- Campo de número
- Campo de mensagem
- Botões: Enviar, Limpar
- Histórico de mensagens enviadas

## 🔧 Funcionalidades

### Validações Automáticas
- ✅ Verifica se o número tem pelo menos 10 dígitos
- ✅ Remove caracteres especiais automaticamente
- ✅ Valida se os campos estão preenchidos
- ✅ Mostra mensagens de erro claras

### Feedback Visual
- 📤 "Enviando mensagem..." (durante envio)
- ✅ "Mensagem enviada com sucesso!" (sucesso)
- ❌ "Erro ao enviar: [motivo]" (erro)

### Histórico de Mensagens
- Mostra últimas 10 mensagens enviadas
- Ordenadas da mais recente para a mais antiga
- Inclui número, mensagem e horário
- Persiste durante a sessão

## 💡 Exemplos de Uso

### Exemplo 1: Enviar para seu próprio número
```
Número: 5584889868
Mensagem: Teste de envio pelo sistema CIANET
```

### Exemplo 2: Enviar para cliente
```
Número: 5511999999999
Mensagem: Olá! Seu boleto está disponível para pagamento.
Link: https://exemplo.com/boleto/123
```

### Exemplo 3: Mensagem com múltiplas linhas
```
Número: 5511999999999
Mensagem: 
Olá, [Nome]!

Seu atendimento foi finalizado.
Protocolo: #12345

Obrigado por entrar em contato!
```

## 🚨 Possíveis Erros

### "Número inválido. Use o formato: 5511999999999"
**Causa:** Número muito curto ou formato incorreto
**Solução:** Use o formato completo com código do país

### "Número não está registrado no WhatsApp"
**Causa:** O número não existe no WhatsApp
**Solução:** Verifique se o número está correto

### "WhatsApp não está conectado"
**Causa:** Serviço desconectado ou QR Code não escaneado
**Solução:** Escaneie o QR Code novamente

### "Serviço WhatsApp não está rodando"
**Causa:** Serviço Node.js parado
**Solução:** Execute `cd whatsapp-service && node server.js`

## 🎯 Dicas

1. **Teste primeiro com seu próprio número** para garantir que está funcionando
2. **Use números com código do país** (ex: 55 para Brasil)
3. **Mantenha o serviço Node.js sempre rodando** para não perder a conexão
4. **Marque "Manter-me conectado"** ao escanear o QR Code
5. **Verifique o histórico** para confirmar que a mensagem foi enviada

## 📊 Formato de Números por País

| País | Código | Exemplo |
|------|--------|---------|
| Brasil | 55 | 5511999999999 |
| EUA | 1 | 15551234567 |
| Portugal | 351 | 351912345678 |
| Argentina | 54 | 5491123456789 |

## 🔄 Fluxo Completo

```
1. Abrir /whatsapp
   ↓
2. Verificar se está conectado
   ↓
3. Se não: Escanear QR Code
   ↓
4. Se sim: Preencher formulário
   ↓
5. Clicar em "Enviar Mensagem"
   ↓
6. Aguardar confirmação
   ↓
7. Ver mensagem no histórico
   ↓
8. Destinatário recebe no WhatsApp
```

## ✅ Checklist Antes de Enviar

- [ ] Serviço Node.js rodando
- [ ] WhatsApp conectado (ícone verde)
- [ ] Número no formato correto (com código do país)
- [ ] Mensagem preenchida
- [ ] Formulário de envio visível na página

## 🎉 Pronto!

Agora você pode enviar mensagens pelo WhatsApp diretamente do sistema CIANET!

Para envios em massa ou automação, consulte a documentação da API em `/docs`.
