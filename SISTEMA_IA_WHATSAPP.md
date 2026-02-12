# Sistema de Controle de IA por Canal WhatsApp

## Visão Geral

Sistema implementado para ativar/desativar a IA (Inteligência Artificial) por canal WhatsApp, com configuração de horário de funcionamento e mensagens personalizadas.

## Funcionalidades Implementadas

### 1. Toggle de IA por Canal
- Cada canal WhatsApp pode ter a IA ativada ou desativada individualmente
- Interface visual com switch toggle para fácil ativação/desativação
- Configurações salvas no localStorage do navegador

### 2. Horário de Funcionamento
- Configuração de horário de início (ex: 08:00)
- Configuração de horário de fim (ex: 18:00)
- IA só responde dentro do horário configurado
- Suporta horários que atravessam meia-noite

### 3. Mensagem Personalizada
- Mensagem enviada quando IA está desativada
- Mensagem enviada fora do horário de atendimento
- Totalmente personalizável por canal

### 4. Interface Visual
- Página dedicada em `/mensagens`
- Lista todos os canais WhatsApp conectados
- Design moderno e responsivo
- Feedback visual imediato

## Como Usar

### Acessar Configurações
1. Faça login no sistema
2. Acesse o menu lateral e clique em "Mensagens"
3. Role até a seção "Configuração de IA por WhatsApp"

### Configurar um Canal
1. Localize o canal WhatsApp desejado na lista
2. Use o toggle para ativar/desativar a IA
3. Quando ativado, configure:
   - Horário de início do atendimento
   - Horário de fim do atendimento
   - Mensagem quando IA está desativada
4. Clique em "Salvar Configuração"

### Exemplo de Configuração
```
Canal: 558488986845 (Anjo)
IA Ativa: Sim
Horário: 08:00 - 18:00
Mensagem: "No momento estamos fora do horário de atendimento automático. Um atendente irá responder em breve."
```

## Estrutura de Dados

### LocalStorage
As configurações são salvas com a chave: `config_ia_whatsapp_{whatsapp_id}`

```json
{
  "iaAtiva": true,
  "horarioInicio": "08:00",
  "horarioFim": "18:00",
  "mensagemDesativada": "Mensagem personalizada..."
}
```

## Arquivos Modificados

### Frontend
- `app/web/templates/mensagens_config.html`
  - Adicionada seção de configuração de IA
  - Estilos CSS para toggle switch e formulários
  - JavaScript para gerenciar configurações

### Backend
- `app/api/endpoints/atendimento.py`
  - Função `verificar_ia_ativa()` - verifica se IA está ativa
  - Função `esta_no_horario_atendimento()` - valida horário
  - Endpoint `/atendimento/verificar-ia/{whatsapp_id}` - API para verificação

## Fluxo de Funcionamento

### Quando uma mensagem chega:
1. Sistema identifica o canal WhatsApp de origem
2. Verifica se IA está ativada para aquele canal
3. Se ativada, verifica se está no horário de atendimento
4. Se ambos OK, IA responde automaticamente
5. Se não, envia mensagem configurada ou encaminha para fila de espera

### Diagrama de Decisão
```
Mensagem Recebida
    ↓
IA Ativa? → NÃO → Envia mensagem desativada → Fila de Espera
    ↓ SIM
No Horário? → NÃO → Envia mensagem fora de horário → Fila de Espera
    ↓ SIM
IA Responde Automaticamente
```

## Próximos Passos (Futuro)

1. **Persistência em Banco de Dados**
   - Migrar configurações do localStorage para banco
   - Permitir configuração centralizada

2. **Configurações Avançadas**
   - Dias da semana específicos
   - Feriados
   - Múltiplos horários por dia

3. **Relatórios**
   - Quantas mensagens foram atendidas pela IA
   - Quantas foram encaminhadas para humanos
   - Taxa de resolução da IA

4. **Integração com CRM**
   - Regras baseadas em tipo de cliente
   - Priorização automática
   - Escalação inteligente

## Suporte

Para dúvidas ou problemas:
- Verifique se o serviço WhatsApp está rodando (porta 3001)
- Verifique se há canais conectados
- Limpe o cache do navegador se necessário
- Consulte os logs do sistema

## Credenciais Demo
- Email: admin@empresa.com.br
- Senha: Admin@123
