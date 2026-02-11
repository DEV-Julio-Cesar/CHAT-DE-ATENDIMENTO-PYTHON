# 📱 Guia WhatsApp Python - CIANET PROVEDOR

Sistema de envio de mensagens WhatsApp usando biblioteca Python (pywhatkit).

## 🎯 Características

- ✅ **Sem API paga**: Usa WhatsApp Web gratuitamente
- ✅ **Simples**: Não precisa de tokens ou credenciais complexas
- ✅ **Funcional**: Envia mensagens, imagens e agendamentos
- ✅ **Python puro**: Biblioteca nativa Python

## 📋 Requisitos

1. **Google Chrome** instalado
2. **WhatsApp Web** logado no Chrome
3. **Python 3.8+** com as bibliotecas instaladas

## 🚀 Como Usar

### 1. Primeira Configuração

```bash
# Instalar dependências (já feito)
pip install pywhatkit pyautogui qrcode pillow
```

### 2. Logar no WhatsApp Web

1. Abra o Google Chrome
2. Acesse https://web.whatsapp.com
3. Escaneie o QR Code com seu celular
4. Mantenha o WhatsApp Web logado

### 3. Enviar Mensagem via API

**Endpoint:** `POST /api/v1/whatsapp/send`

```json
{
  "phone_number": "+5511999999999",
  "message": "Olá! Esta é uma mensagem de teste.",
  "wait_time": 15,
  "close_tab": true
}
```

**Resposta:**
```json
{
  "success": true,
  "phone_number": "+5511999999999",
  "message": "Olá! Esta é uma mensagem de teste.",
  "sent_at": "2026-02-10T19:45:00"
}
```

### 4. Agendar Mensagem

**Endpoint:** `POST /api/v1/whatsapp/schedule`

```json
{
  "phone_number": "+5511999999999",
  "message": "Lembrete: Reunião às 15h",
  "hour": 14,
  "minute": 30,
  "close_tab": true
}
```

### 5. Enviar Imagem

**Endpoint:** `POST /api/v1/whatsapp/send-image`

```json
{
  "phone_number": "+5511999999999",
  "image_path": "C:/imagens/foto.jpg",
  "caption": "Confira esta imagem!",
  "wait_time": 15
}
```

### 6. Envio em Massa

**Endpoint:** `POST /api/v1/whatsapp/send-bulk`

```json
{
  "contacts": [
    {
      "phone": "+5511999999999",
      "message": "Olá João! Mensagem personalizada."
    },
    {
      "phone": "+5511888888888",
      "message": "Olá Maria! Outra mensagem."
    }
  ],
  "wait_time": 15
}
```

**Resposta:**
```json
{
  "total": 2,
  "success": 2,
  "failed": 0,
  "errors": []
}
```

## ⚠️ Avisos Importantes

### Limitações

1. **Navegador abre automaticamente**: O Chrome será aberto para enviar mensagens
2. **Delay necessário**: Há um tempo de espera (padrão 15s) para carregar o WhatsApp Web
3. **WhatsApp Web deve estar logado**: Mantenha sempre logado
4. **Envios em massa**: Use com moderação para evitar bloqueio do WhatsApp

### Boas Práticas

- ✅ Mantenha o WhatsApp Web sempre logado
- ✅ Use delay de pelo menos 5 segundos entre mensagens em massa
- ✅ Não envie spam ou mensagens não solicitadas
- ✅ Respeite as políticas do WhatsApp
- ❌ Não abuse do envio em massa
- ❌ Não envie mensagens para números não salvos em excesso

## 🔧 Troubleshooting

### Erro: "Chrome not found"
**Solução**: Instale o Google Chrome

### Erro: "WhatsApp Web not logged in"
**Solução**: Abra https://web.whatsapp.com e faça login

### Mensagem não enviada
**Solução**: 
1. Verifique se o número está correto (com código do país)
2. Aumente o `wait_time` para 20-30 segundos
3. Verifique sua conexão com a internet

### Navegador não fecha
**Solução**: Defina `close_tab: true` na requisição

## 📊 Status do Serviço

**Endpoint:** `GET /api/v1/whatsapp/status`

```json
{
  "service": "WhatsApp Python (pywhatkit)",
  "status": "active",
  "type": "whatsapp_web",
  "features": [
    "send_message",
    "send_scheduled",
    "send_image",
    "send_bulk"
  ],
  "requirements": [
    "WhatsApp Web deve estar logado no navegador",
    "Navegador Chrome deve estar instalado"
  ]
}
```

## 🎓 Exemplos de Uso

### Python
```python
import requests

# Enviar mensagem
response = requests.post(
    "http://localhost:8000/api/v1/whatsapp/send",
    json={
        "phone_number": "+5511999999999",
        "message": "Olá do Python!",
        "wait_time": 15
    }
)

print(response.json())
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/whatsapp/send" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+5511999999999",
    "message": "Olá do cURL!",
    "wait_time": 15
  }'
```

### JavaScript
```javascript
fetch('http://localhost:8000/api/v1/whatsapp/send', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    phone_number: '+5511999999999',
    message: 'Olá do JavaScript!',
    wait_time: 15
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

## 📝 Notas

- O sistema usa WhatsApp Web, não a API oficial do WhatsApp Business
- É gratuito mas tem limitações de automação
- Ideal para pequenos volumes de mensagens
- Para grandes volumes, considere a API oficial do WhatsApp Business

## 🆘 Suporte

Para dúvidas ou problemas:
1. Verifique este guia
2. Consulte a documentação da API em `/docs`
3. Verifique os logs do servidor
