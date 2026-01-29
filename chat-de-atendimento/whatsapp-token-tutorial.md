# 🔑 COMO OBTER TOKEN WHATSAPP BUSINESS API - TUTORIAL COMPLETO

## PASSO 1: ACESSAR META FOR DEVELOPERS

### 1.1 Abrir o Site
🔗 **Acesse**: https://developers.facebook.com/

### 1.2 Fazer Login
- Use sua conta Facebook/Meta
- Se não tiver, crie uma conta gratuita

### 1.3 Aceitar Termos
- Aceite os termos de desenvolvedor
- Confirme seu email se necessário

---

## PASSO 2: CRIAR UM APP

### 2.1 Criar Novo App
1. Clique em **"Meus Apps"** (canto superior direito)
2. Clique em **"Criar App"**
3. Selecione **"Business"** (não Consumer)
4. Clique **"Avançar"**

### 2.2 Configurar App
- **Nome do App**: `ISP Customer Support`
- **Email de Contato**: seu email
- **Categoria**: `Comunicação`
- Clique **"Criar App"**

---

## PASSO 3: ADICIONAR WHATSAPP

### 3.1 Adicionar Produto
1. Na página do seu app, procure **"Adicionar Produto"**
2. Encontre **"WhatsApp Business API"**
3. Clique em **"Configurar"**

### 3.2 Configuração Inicial
- O Meta vai configurar automaticamente
- Aguarde alguns segundos

---

## PASSO 4: OBTER AS CREDENCIAIS

### 4.1 Localizar o Token
Na página do WhatsApp Business API, você verá:

```
📱 PHONE NUMBER ID: 1234567890123456
🔑 ACCESS TOKEN: EAABwzLixnjYBOxxxxxxxxxxxxxxxxxxxxx
```

### 4.2 Copiar Credenciais
1. **ACCESS TOKEN**: Clique no botão "Copiar" ao lado do token
2. **PHONE NUMBER ID**: Copie os números longos
3. **Salve em um arquivo temporário** (bloco de notas)

---

## PASSO 5: CONFIGURAR NÚMERO DE TESTE

### 5.1 Adicionar Número de Teste
1. Na seção **"Para"**, clique em **"Gerenciar números de telefone"**
2. Clique **"Adicionar número de telefone"**
3. Digite seu número: `+5511999999999` (com código do país)
4. Você receberá um código no WhatsApp
5. Digite o código para verificar

---

## EXEMPLO PRÁTICO

### Suas credenciais ficarão assim:
```
ACCESS TOKEN: EAABwzLixnjYBOxxxxxxxxxxxxxxxxxxxxx
PHONE NUMBER ID: 1234567890123456
SEU NÚMERO TESTE: +5511999999999
```

---

## PASSO 6: TESTAR NA APLICAÇÃO

### 6.1 Configurar no .env
```env
WHATSAPP_ACCESS_TOKEN="EAABwzLixnjYBOxxxxxxxxxxxxxxxxxxxxx"
WHATSAPP_PHONE_NUMBER_ID="1234567890123456"
WHATSAPP_WEBHOOK_VERIFY_TOKEN="webhook_verify_token_123"
```

### 6.2 Reiniciar Aplicação
```bash
docker-compose -f docker-compose.dev.yml restart api
```

### 6.3 Testar
```bash
curl http://localhost:8000/api/v1/whatsapp/status
```

---

## ❓ PROBLEMAS COMUNS

### "Não encontro o WhatsApp Business API"
- Certifique-se de criar um app **Business** (não Consumer)
- Aguarde alguns minutos após criar o app

### "Token não funciona"
- Tokens de teste expiram em 24 horas
- Copie o token completo (muito longo)
- Não compartilhe o token com ninguém

### "Não consigo adicionar meu número"
- Use formato internacional: +5511999999999
- Certifique-se que o WhatsApp está instalado
- Verifique se recebeu o código

---

## 🎯 RESUMO RÁPIDO

1. ✅ Acesse: https://developers.facebook.com/
2. ✅ Crie App Business
3. ✅ Adicione WhatsApp Business API
4. ✅ Copie ACCESS TOKEN e PHONE NUMBER ID
5. ✅ Adicione seu número de teste
6. ✅ Configure no .env da aplicação

---

## 💡 DICA IMPORTANTE

**O token de teste é GRATUITO e permite:**
- ✅ 1.000 mensagens por mês
- ✅ Enviar para números verificados
- ✅ Receber mensagens
- ✅ Testar todas as funcionalidades

**Perfeito para desenvolvimento e testes!**