# WHATSAPP BUSINESS API - GUIA COMPLETO DE CONFIGURAÇÃO

## PASSO 1: CRIAR CONTA META FOR DEVELOPERS

### 1.1 Acesse o Portal
🔗 **Link**: https://developers.facebook.com/

### 1.2 Criar App Business
1. Clique em "Meus Apps" → "Criar App"
2. Selecione "Business" 
3. Nome do App: "ISP Customer Support"
4. Email de contato: seu email
5. Clique "Criar App"

### 1.3 Adicionar WhatsApp Business
1. No painel do app, clique "Adicionar Produto"
2. Encontre "WhatsApp Business API"
3. Clique "Configurar"

## PASSO 2: CONFIGURAR WHATSAPP BUSINESS

### 2.1 Obter Credenciais
Após configurar, você verá:

```
📱 PHONE NUMBER ID: 1234567890123456
🔑 ACCESS TOKEN: EAAxxxxxxxxxxxxxxxxxxxxx
🔐 WEBHOOK VERIFY TOKEN: (você define)
```

### 2.2 Configurar Webhook (Importante!)
1. URL do Webhook: `https://seu-dominio.com/api/v1/whatsapp/webhook`
2. Verify Token: `webhook_verify_token_123` (você define)
3. Campos: `messages`, `message_deliveries`, `message_reads`

## PASSO 3: CONFIGURAR NA APLICAÇÃO

### 3.1 Atualizar .env
```env
# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=1234567890123456
WHATSAPP_WEBHOOK_VERIFY_TOKEN=webhook_verify_token_123
```

### 3.2 Testar Configuração
```bash
# Testar envio de mensagem
curl -X POST "http://localhost:8000/api/v1/whatsapp/send" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "5511999999999",
    "message": "Olá! Teste do sistema ISP Customer Support"
  }'
```

## PASSO 4: VERIFICAÇÃO E TESTES

### 4.1 Verificar Status
```bash
curl http://localhost:8000/api/v1/whatsapp/status
```

### 4.2 Enviar Mensagem de Teste
```bash
curl -X POST "http://localhost:8000/api/v1/whatsapp/test" \
  -H "Content-Type: application/json" \
  -d '{"phone": "seu_numero_teste"}'
```

## LIMITES E CUSTOS

### Conta de Teste (Gratuita)
- ✅ 1.000 mensagens/mês grátis
- ✅ Apenas números verificados
- ✅ Perfeito para desenvolvimento

### Conta Produção
- 💰 $0.005 por mensagem (R$ 0,025)
- 📈 Sem limite de mensagens
- 🌍 Qualquer número mundial
- 📊 Analytics avançados

## TROUBLESHOOTING

### Erro: "Invalid Access Token"
- Verifique se o token está correto no .env
- Token expira em 24h (modo desenvolvimento)

### Erro: "Phone Number Not Verified"
- Adicione seu número na lista de teste
- Ou configure conta de produção

### Erro: "Webhook Failed"
- Verifique se a URL está acessível
- Confirme o verify token

## PRÓXIMOS PASSOS
1. ✅ Configurar credenciais
2. ✅ Testar envio de mensagem
3. ✅ Configurar webhook
4. ✅ Integrar com chatbot IA