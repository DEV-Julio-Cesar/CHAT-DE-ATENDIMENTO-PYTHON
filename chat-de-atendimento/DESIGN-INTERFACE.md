# 🎨 VISUAL DA INTERFACE

## Layout da Página

```
┌─────────────────────────────────────────────────────────────────┐
│                  🤖 Gerenciador de Comandos                     │
│           Adicione, edite e gerencie as respostas automáticas   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   📊 ESTATÍSTICAS                                │
├────────────────┬────────────────┬────────────────┐               │
│      10        │       8        │       2        │               │
│     Total      │     Ativos     │    Inativos    │               │
└────────────────┴────────────────┴────────────────┘               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  [PAINEL ESQUERDO]           │  [PAINEL DIREITO]                │
│                              │                                  │
│ 🔍 Buscar comando...         │  ➕ Novo Comando | ⚙️ Config   │
│                              │                                  │
│ ┌────────────────────────┐   │  ID do Comando *                │
│ │ saudacao_oi     ✓      │   │  [________________]             │
│ │ Saudação               │   │                                  │
│ │ Olá! 👋 Bem-vindo...   │   │  Tipo *                         │
│ │                        │   │  [Saudação          ▼]          │
│ ├────────────────────────┤   │                                  │
│ │ horario        ✓       │   │  Resposta *                     │
│ │ Informação             │   │  ┌──────────────────────┐       │
│ │ 📅 Abrimos seg-sex...  │   │  │                      │       │
│ │                        │   │  │                      │       │
│ ├────────────────────────┤   │  └──────────────────────┘       │
│ │ preco          ✓       │   │                                  │
│ │ Informação             │   │  Palavras-Chave *              │
│ │ 💰 Começamos em R$...  │   │  [___________] [Enter]          │
│ │                        │   │  [ oi ] [ olá ] [ opa ] [ e aí ]│
│ │                        │   │                                  │
│ │                        │   │  Prioridade: [  5  ]             │
│ │ ... (mais comandos)    │   │  ☐ Comando Ativo              │
│ │                        │   │                                  │
│ └────────────────────────┘   │  [💾 Salvar] [🔄 Limpar]        │
│                              │  [🗑️ Deletar]                  │
│                              │                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Cores e Estilos

### Paleta de Cores
```
Principal (Roxa):      #667eea
Secundária (Roxo):     #764ba2
Sucesso (Verde):       #51cf66
Perigo (Vermelho):     #ff6b6b
Neutro (Cinza):        #e0e0e0
Texto (Escuro):        #333333
```

### Componentes Principais

```
┌─ BOTÕES
├─ Primário (Roxo): "💾 Salvar", "✏️ Atualizar"
├─ Secundário (Cinza): "🔄 Limpar"
├─ Perigo (Vermelho): "🗑️ Deletar"
└─ Sucesso (Verde): "✓ Confirmar"

┌─ CARDS
├─ Estatísticas: Gradiente roxo com números grandes
├─ Comandos: Lista com borda esquerda colorida
├─ Tags: Fundo roxo, texto branco, arredondado
└─ Alertas: Verde (sucesso), Vermelho (erro), Azul (info)

┌─ FORMULÁRIOS
├─ Inputs: Borda cinza, azul ao focar
├─ Textarea: Maior altura, scroll automático
├─ Selects: Dropdown padrão com setas
└─ Checkboxes: Customizadas com estilo moderno
```

---

## Estados Visuais

### Comando Ativo
```
┌─────────────────────────────────┐
│ saudacao_oi         [Saudação]  │
│ ✓ Ativo                         │
│ Olá! 👋 Bem-vindo!...           │
└─────────────────────────────────┘
  Cor: Azul claro (#e7f5ff)
  Borda: Verde (#40c057)
```

### Comando Inativo
```
┌─────────────────────────────────┐
│ comando_old         [Genérico]   │
│ ✗ Inativo                       │
│ Mensagem desativada...          │
└─────────────────────────────────┘
  Cor: Cinza
  Borda: Cinza (#999)
```

### Hovering
```
Comando: Desliza 5px para direita
Botão: Levanta 2px, sombra aumenta
```

---

## Abas

### Aba 1: Novo Comando
```
┌─ Visualização
├─ Formulário com 7 campos
├─ Validação em tempo real
└─ Botões de ação (Salvar, Limpar, Deletar)
```

### Aba 2: Configurações
```
┌─ Checkboxes para ativar/desativar:
│  ✓ Usar Base de Conhecimento
│  ✓ Usar Gemini AI
│  ✓ Fallback para IA
│
├─ Sliders/Inputs:
│  Confiança Mínima: [|--------|] 70%
│  Tempo de Resposta: [15] segundos
│
└─ Textarea:
   Resposta Padrão: [Desculpe, não entendi...]
```

### Aba 3: Importar/Exportar
```
┌─ Exportar
│  Textarea com JSON (read-only)
│  [📋 Copiar para Área de Transferência]
│
├─ Importar
│  Textarea para colar JSON
│  [📥 Importar]
│
└─ [🔄 Atualizar]
```

---

## Responsividade

### Desktop (> 1024px)
```
Grid 2 colunas:
┌──────────────────┬──────────────────┐
│  LISTA (40%)     │  FORMULÁRIO (60%) │
└──────────────────┴──────────────────┘
```

### Tablet (768px - 1024px)
```
Grid 2 colunas com ajustes:
┌──────────────────┬──────────────────┐
│  LISTA (35%)     │  FORMULÁRIO (65%) │
└──────────────────┴──────────────────┘
```

### Mobile (< 768px)
```
Stack vertical:
┌──────────────────┐
│  LISTA           │
├──────────────────┤
│  FORMULÁRIO      │
└──────────────────┘
```

---

## Animações

```
Transição padrão: 0.3s ease

Exemplos:
- Botão hover: translateY(-2px)
- Comando hover: translateX(5px)
- Cores mudam suavemente
- Sombras aumentam
- Sem efeitos pesados
```

---

## Acessibilidade

```
✅ Cores com contraste adequado
✅ Inputs com labels claros
✅ Foco visível em todos os elementos
✅ Mensagens de erro legíveis
✅ Botões com aria-labels
✅ Navegação com teclado funciona
```

---

## Ícones/Emojis Usados

```
🤖 - Robô (título)
📊 - Estatísticas
🔍 - Busca
➕ - Novo
⚙️ - Configurações
📥 - Importar
📤 - Exportar
💾 - Salvar
✏️ - Editar
✕ - Fechar/Deletar
🗑️ - Lixo
🔄 - Atualizar
✓ - Ativo
✗ - Inativo
📝 - Formulário
📋 - Copiar
🎮 - Jogar/Interface
```

---

## Exemplo de Alerta

```
┌──────────────────────────────────┐
│ ✅ Comando criado com sucesso!   │
└──────────────────────────────────┘
  Cor: Verde (#d4edda)
  Borda: Verde mais escuro (#c3e6cb)
  Texto: Verde escuro (#155724)
  Duration: 5 segundos depois desaparece
```

---

## Fluxo de Interação Completo

```
1. USUÁRIO ACESSA
   └─ Interface carrega (500ms)
   └─ Dados carregam da API (100ms)
   └─ Lista atualiza (instant)
   └─ Pronto para uso

2. USUÁRIO CRIA COMANDO
   ├─ Preenche campos
   ├─ Sistema valida em tempo real
   ├─ Icone de validação aparece
   └─ Botão fica ativo

3. USUÁRIO CLICA "SALVAR"
   ├─ Animação de carregamento
   ├─ API processa (100-200ms)
   ├─ Alerta de sucesso aparece
   ├─ Lista atualiza automaticamente
   └─ Campos limpam

4. USUÁRIO CLICA EM COMANDO EXISTENTE
   ├─ Comando é selecionado (visual)
   ├─ Campos preenchem (instant)
   ├─ Botão muda para "Atualizar"
   ├─ Botão "Deletar" aparece
   └─ Pronto para editar

5. USUÁRIO EDITA E SALVA
   ├─ Mesmo processo do passo 3
   ├─ Comando atualizado na lista
   └─ Interface reflete mudança
```

---

## Design System

### Espaçamento
```
xs: 5px
sm: 10px
md: 15px
lg: 20px
xl: 30px
```

### Typography
```
Body: 'Segoe UI', 14px, #333
Heading: 'Segoe UI', 32px, #333
Code: 'Courier New', 12px, #61dafb
```

### Border Radius
```
Small: 3px (inputs)
Medium: 5px (cards)
Large: 8px (panels)
Circular: 50% (tags)
```

### Shadows
```
Subtle: 0 2px 4px rgba(0, 0, 0, 0.1)
Medium: 0 4px 6px rgba(0, 0, 0, 0.1)
Strong: 0 10px 40px rgba(0, 0, 0, 0.3)
```

---

## Exemplo de JSON Visualizado

```
┌─────────────────────────────────┐
│ 📋 Exportar Base de Conhecimento │
├─────────────────────────────────┤
│ {                               │
│   "comandos": [                 │
│     {                           │
│       "id": "saudacao_oi",      │
│       "tipo": "saudacao",       │
│       "resposta": "Olá! 👋",    │
│       "palavras_chave": [       │
│         "oi", "olá", "opa"      │
│       ],                        │
│       "prioridade": 10,         │
│       "ativo": true             │
│     }                           │
│   ],                            │
│   "configuracoes": { ... }      │
│ }                               │
│                                 │
│ [📋 Copiar para Área de Transf. │
└─────────────────────────────────┘
  Fonte: monospace (Courier)
  Fundo: Cinza escuro (#282c34)
  Texto: Azul (#61dafb)
  Altura: 300px com scroll
```

---

## Performance Visual

```
Carregamento: Skeleton loaders (opcional)
Busca: Resultados instantâneos
API: Indicador de loading
Erros: Toasts não bloqueantes
Feedback: Resposta imediata ao clicar
```

---

## Temas Suportados

Atualmente: Light theme padrão

Futuramente possível:
- Dark mode
- High contrast
- Customização de cores

---

**Nota**: O design prioriza **usabilidade** sobre estética, com uma interface clara e intuitiva que funciona em todos os navegadores modernos.
