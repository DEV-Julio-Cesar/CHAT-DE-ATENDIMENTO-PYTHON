# 🤖 Gerenciador de Comandos do Robô - Documentação

## 📋 Visão Geral

O **Gerenciador de Comandos** é uma interface web intuitiva que permite criar, editar, deletar e organizar as respostas automáticas do seu chatbot sem necessidade de mexer em código.

## 🚀 Como Acessar

1. **Inicie o servidor:**
   ```bash
   npm start
   ```

2. **Abra em seu navegador:**
   ```
   http://localhost:3333/gerenciador-comandos.html
   ```

## 📝 Criando um Novo Comando

### Passo 1: Preencha os Campos
- **ID do Comando**: Identificador único (ex: `saudacao_boas_vindas`)
- **Tipo**: Selecione a categoria
  - `Saudação` - Para cumprimentos
  - `Informação` - Para dados gerais
  - `Problema` - Para issues
  - `Resposta Gentil` - Para agradecimentos
  - `Dúvida` - Para perguntas comuns
  - `Ação` - Para CTA (call-to-action)
  - `Genérico` - Para outros tipos

- **Resposta**: Digite a resposta que o robô dará (pode incluir emojis! 😊)
- **Palavras-Chave**: Digite cada palavra e pressione Enter

### Passo 2: Configure
- **Prioridade (1-10)**: Comandos com prioridade maior são usados primeiro
- **Comando Ativo**: Marque para o robô usar este comando

### Passo 3: Salve
Clique em "💾 Salvar Comando"

## 🎯 Exemplos Práticos

### Exemplo 1: Saudação
```
ID: saudacao_inicial
Tipo: Saudação
Resposta: Olá! 👋 Bem-vindo ao nosso atendimento. Como posso ajudá-lo?
Palavras-chave: oi, olá, opa, e aí, opa, bora
Prioridade: 10
```

### Exemplo 2: Horário de Funcionamento
```
ID: horario_funcionamento
Tipo: Informação
Resposta: 📅 Funcionamos de segunda a sexta, das 9h às 18h. Sábado e domingo oferecemos suporte limitado das 10h às 14h.
Palavras-chave: horário, funcionamento, que horas, aberto, open
Prioridade: 8
```

### Exemplo 3: Preços
```
ID: preco_produto
Tipo: Informação
Resposta: 💰 Nossos planos começam em R$ 99/mês. Enviamos um catálogo completo?
Palavras-chave: preço, valor, quanto custa, caro, valores
Prioridade: 7
```

## 🔧 Configurações Globais

Acesse a aba **"⚙️ Configurações"** para ajustar:

### Base de Conhecimento
- **Usar Base de Conhecimento**: Ativa/desativa o reconhecimento de comandos
- **Usar Gemini AI**: Ativa/desativa a IA para responder quando não há comando
- **Fallback para IA**: Se comando não encontrado, usa Gemini AI
- **Confiança Mínima (%)**: Quanto maior, mais rigoroso no reconhecimento (padrão: 70%)
- **Tempo Máximo de Resposta**: Timeout em segundos (padrão: 15s)
- **Resposta Padrão**: Mensagem quando nenhum comando é encontrado

### Exemplo de Configuração
```
✓ Usar Base de Conhecimento
✓ Usar Gemini AI
✓ Fallback para IA
Confiança Mínima: 75%
Tempo Máximo: 20 segundos
Resposta Padrão: Desculpe, não entendi. Poderia reformular a pergunta?
```

## 📊 Entendendo as Estatísticas

A página mostra:
- **Total**: Número total de comandos criados
- **Ativos**: Comandos que o robô está usando
- **Inativos**: Comandos que estão desabilitados

## 🔍 Buscando Comandos

Use a **barra de busca** no lado esquerdo para encontrar comandos por:
- ID do comando
- Conteúdo da resposta
- Palavras-chave

## ✏️ Editando um Comando

1. Clique no comando na lista à esquerda
2. Os campos serão preenchidos automaticamente
3. Faça suas alterações
4. Clique em "✏️ Atualizar Comando"

## 🗑️ Deletando um Comando

1. Clique no comando para editar
2. Clique em "🗑️ Deletar Comando"
3. Confirme a exclusão

## 🔄 Importar/Exportar

### Exportar Backup
1. Acesse a aba **"📥 Importar/Exportar"**
2. Clique em "📋 Copiar para Área de Transferência"
3. Cole em um arquivo `.json` para backup

### Importar Base
1. Copie o conteúdo de um arquivo `.json`
2. Cole no campo "📤 Importar Base de Conhecimento"
3. Clique em "📥 Importar"

## 🧪 Testando Comandos

Use o **endpoint de teste**:
```bash
POST /api/base-conhecimento/testar
Content-Type: application/json

{
  "mensagem": "Qual é o horário de funcionamento?"
}
```

Resposta:
```json
{
  "mensagem": "Qual é o horário de funcionamento?",
  "encontrado": true,
  "comando": {
    "id": "horario_funcionamento",
    "resposta": "📅 Funcionamos de segunda a sexta, das 9h às 18h...",
    "score": 85
  },
  "confidencia": 85
}
```

## 📡 Endpoints API

### Listar Todos os Comandos
```bash
GET /api/base-conhecimento
```

### Obter Um Comando
```bash
GET /api/base-conhecimento/:id
```

### Criar Comando
```bash
POST /api/base-conhecimento
Content-Type: application/json

{
  "id": "meu_comando",
  "tipo": "informacao",
  "resposta": "Resposta aqui",
  "palavras_chave": ["palavra1", "palavra2"],
  "prioridade": 5,
  "ativo": true
}
```

### Atualizar Comando
```bash
PUT /api/base-conhecimento/:id
Content-Type: application/json

{
  "tipo": "saudacao",
  "resposta": "Nova resposta",
  "prioridade": 8
}
```

### Deletar Comando
```bash
DELETE /api/base-conhecimento/:id
```

### Buscar Comandos
```bash
POST /api/base-conhecimento/buscar
Content-Type: application/json

{
  "termo": "horário",
  "tipo": "informacao"
}
```

### Obter Estatísticas
```bash
GET /api/base-conhecimento/estatisticas
```

### Ativar Comando
```bash
PATCH /api/base-conhecimento/:id/ativar
```

### Desativar Comando
```bash
PATCH /api/base-conhecimento/:id/desativar
```

### Exportar Base
```bash
GET /api/base-conhecimento/exportar
```

### Importar Base
```bash
POST /api/base-conhecimento/importar
Content-Type: application/json

{JSON aqui}
```

## 💡 Boas Práticas

### 1. Organize por Tipo
Agrupe comandos por categoria (saudações, informações, etc)

### 2. Use Prioridades Estrategicamente
- **Comandos urgentes (8-10)**: Saudações, erros críticos
- **Comandos comuns (5-7)**: Perguntas frequentes
- **Comandos raramente usados (1-4)**: Casos especiais

### 3. Palavras-Chave Relevantes
✅ Bom: `oi, olá, opa, e aí, oie, salve`
❌ Ruim: `a, o, palavra aleatória`

### 4. Respostas Clara
✅ Bom: "📅 Funcionamos de segunda a sexta, 9h-18h"
❌ Ruim: "estamos abertos"

### 5. Use Emojis com Moderação
Emojis tornam as mensagens mais amigáveis e legíveis, mas não abuse!

### 6. Teste Suas Alterações
Depois de criar/editar, teste a mensagem para garantir que funciona

## ⚙️ Inteligência do Reconhecimento

O sistema calcula um **score de confiança** baseado em:
- **Correspondência exata de palavras-chave**
- **Proporção de palavras correspondentes**
- **Ordem e proximidade das palavras**

### Exemplo:
- Mensagem: "Qual é o horário?"
- Palavras-chave do comando: `["horário", "funcionamento"]`
- Score: ~85% (correspondência parcial com uma palavra-chave)

## 🐛 Troubleshooting

### "Página não carrega"
- Verifique se o servidor está rodando (`npm start`)
- Confirme a porta (padrão: 3333)

### "Comando não está funcionando"
- Verifique se está **Ativo** ✓
- Confirme as palavras-chave
- Teste via endpoint `/api/base-conhecimento/testar`

### "Erro ao salvar"
- Verifique se todos os campos obrigatórios estão preenchidos
- Confirme se o ID é único (não há outro comando com o mesmo ID)

### "Dados desapareceram"
- Sempre faça backup antes de grandes alterações
- Use "📥 Exportar" para salvar seus dados

## 📞 Suporte

Se encontrar problemas:
1. Consulte os logs: `dados/logs/`
2. Verifique o console do navegador (F12)
3. Tire um backup dos dados (`📥 Exportar`)

## 🎓 Integração com Chat

Os comandos criados aqui são **automaticamente usados** pelo seu chatbot. O fluxo é:

1. Cliente envia mensagem
2. Sistema verifica Base de Conhecimento
3. Se encontrar comando com alta confiança → **Usa resposta do comando**
4. Se não encontrar → **Cai para Gemini AI**
5. Gemini gera resposta humanizada

## 📈 Próximos Passos

- Crie seus primeiros 5-10 comandos
- Configure as palavras-chave corretamente
- Ajuste as prioridades
- Teste com clientes reais
- Monitore e refine baseado no feedback

---

**Versão**: 1.0  
**Última Atualização**: 2024  
**Status**: ✅ Pronto para Produção
