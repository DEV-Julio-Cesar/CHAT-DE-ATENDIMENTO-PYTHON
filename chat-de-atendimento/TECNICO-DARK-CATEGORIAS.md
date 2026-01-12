# 🔧 Documentação Técnica - Dark Mode + Categorias

## Índice
1. [Arquitetura](#arquitetura)
2. [Implementação CSS](#implementação-css)
3. [Implementação JavaScript](#implementação-javascript)
4. [API REST](#api-rest)
5. [Banco de Dados](#banco-de-dados)
6. [Fluxo de Dados](#fluxo-de-dados)

---

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Navegador)                   │
│  ┌──────────────┐      ┌──────────────────┐         │
│  │ HTML + CSS   │      │  JavaScript      │         │
│  │              │      │                  │         │
│  │ - Dark Mode  │      │ - inicializarTema│         │
│  │ - Categorias │      │ - toggleDarkMode │         │
│  │ - Formulário │      │ - filtrarCategoria│        │
│  └──────────────┘      └──────────────────┘         │
└─────────────────────────────────────────────────────┘
           ↓ Fetch API (JSON)
┌─────────────────────────────────────────────────────┐
│              Backend (Express.js)                   │
│  ┌──────────────────────────────────────┐           │
│  │  REST API Routes                     │           │
│  │                                      │           │
│  │  POST   /api/base-conhecimento       │           │
│  │  PUT    /api/base-conhecimento/:id   │           │
│  │  GET    /api/base-conhecimento       │           │
│  │  DELETE /api/base-conhecimento/:id   │           │
│  └──────────────────────────────────────┘           │
└─────────────────────────────────────────────────────┘
           ↓ Read/Write
┌─────────────────────────────────────────────────────┐
│          Banco de Dados (JSON File)                 │
│  dados/base-conhecimento-robo.json                  │
│                                                     │
│  {                                                  │
│    "comandos": [                                    │
│      { "id": "...", "categoria": "...", ... }      │
│    ]                                                │
│  }                                                  │
└─────────────────────────────────────────────────────┘
```

---

## Implementação CSS

### CSS Variables (Custom Properties)

#### Light Mode (Default)
```css
:root {
  --primary-color: #667eea;      /* Cor principal */
  --bg-color: #ffffff;           /* Fundo */
  --text-color: #333333;         /* Texto */
  --border-color: #e0e0e0;       /* Bordas */
  --bg-secondary: #f5f5f5;       /* Fundo secundário */
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  --success-color: #4caf50;
  --error-color: #f44336;
  --warning-color: #ff9800;
  --info-color: #2196f3;
  --light-gray: #f0f0f0;
}
```

#### Dark Mode Override
```css
:root.dark-mode {
  --primary-color: #7c8ff5;
  --bg-color: #1e1e2e;
  --text-color: #e0e0e0;
  --border-color: #3a3a4a;
  --bg-secondary: #2a2a3a;
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  /* ... resto das cores */
}
```

### Transição Suave
```css
body {
  transition: background-color 0.3s ease, color 0.3s ease;
}
```

### Aplicação das Variáveis
```css
header {
  background-color: var(--bg-color);
  color: var(--text-color);
  border-bottom: 1px solid var(--border-color);
}

.panel {
  background-color: var(--bg-color);
  box-shadow: var(--shadow);
}

.btn-primary {
  background-color: var(--primary-color);
  color: white;
}
```

---

## Implementação JavaScript

### 1. Inicializar Tema
```javascript
function inicializarTema() {
  const html = document.documentElement;
  const body = document.body;
  const icon = document.getElementById('themeIcon');
  
  // Carregar preferência salva ou detectar do sistema
  let temaSalvo = localStorage.getItem('tema-gerenciador');
  
  if (!temaSalvo) {
    // Detectar preferência do sistema
    const preferDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    temaSalvo = preferDark ? 'dark' : 'light';
  }
  
  // Aplicar tema
  if (temaSalvo === 'dark') {
    html.classList.add('dark-mode');
    body.classList.add('dark-mode');
    icon.textContent = '☀️';
  } else {
    html.classList.remove('dark-mode');
    body.classList.remove('dark-mode');
    icon.textContent = '🌙';
  }
  
  tema = temaSalvo;
}
```

### 2. Toggle Dark Mode
```javascript
function toggleDarkMode() {
  const html = document.documentElement;
  const body = document.body;
  const icon = document.getElementById('themeIcon');
  
  // Alternar classe
  html.classList.toggle('dark-mode');
  body.classList.toggle('dark-mode');
  
  // Determinar novo estado
  const estaDark = html.classList.contains('dark-mode');
  
  // Salvar preferência
  localStorage.setItem('tema-gerenciador', estaDark ? 'dark' : 'light');
  
  // Atualizar ícone
  icon.textContent = estaDark ? '☀️' : '🌙';
}
```

### 3. Filtrar Categorias
```javascript
function filtrarCategoria(categoria) {
  if (categoriaFiltro === categoria) {
    categoriaFiltro = null; // Desativar filtro
  } else {
    categoriaFiltro = categoria;
  }
  
  atualizarLista();
}

function atualizarLista() {
  const container = document.getElementById('commandList');
  container.innerHTML = '';
  
  // Agrupar por categoria
  const porCategoria = {};
  baseConhecimento.forEach(cmd => {
    // Respeitar filtro
    if (categoriaFiltro && cmd.categoria !== categoriaFiltro) {
      return;
    }
    
    const cat = cmd.categoria || 'Sem categoria';
    if (!porCategoria[cat]) {
      porCategoria[cat] = [];
    }
    porCategoria[cat].push(cmd);
  });
  
  // Renderizar cada categoria
  Object.entries(porCategoria).forEach(([categoria, comandos]) => {
    // Header da categoria
    const header = document.createElement('div');
    header.className = 'category-header';
    header.textContent = categoria;
    container.appendChild(header);
    
    // Comandos da categoria
    comandos.forEach(cmd => {
      const div = document.createElement('div');
      div.className = 'command-item';
      div.innerHTML = `
        <div class="command-header">
          <span class="command-category">${cmd.categoria}</span>
          <span class="command-type">${cmd.tipo}</span>
        </div>
        <div>${cmd.resposta}</div>
      `;
      container.appendChild(div);
    });
  });
}
```

### 4. Gerar Botões de Filtro
```javascript
function atualizarFiltrosCategoria() {
  // Extrair categorias únicas
  const categorias = new Set();
  baseConhecimento.forEach(cmd => {
    if (cmd.categoria) {
      categorias.add(cmd.categoria);
    }
  });
  
  // Renderizar botões
  const filterDiv = document.getElementById('categoryFilter');
  filterDiv.innerHTML = `
    <button class="category-btn ${!categoriaFiltro ? 'active' : ''}" 
            onclick="filtrarCategoria(null)">
      Tudo
    </button>
  `;
  
  categorias.forEach(cat => {
    const btn = document.createElement('button');
    btn.className = `category-btn ${categoriaFiltro === cat ? 'active' : ''}`;
    btn.textContent = cat;
    btn.onclick = () => filtrarCategoria(cat);
    filterDiv.appendChild(btn);
  });
}
```

---

## API REST

### GET /api/base-conhecimento
**Obtém toda a base de conhecimento**

```
Resposta (200):
{
  "comandos": [
    {
      "id": "saudacao_padrao",
      "categoria": "Saudações",
      "tipo": "saudacao",
      "resposta": "Olá!",
      "palavras_chave": ["oi", "olá"],
      "prioridade": 10,
      "ativo": true
    }
  ],
  "total": 8,
  "ativos": 8
}
```

### POST /api/base-conhecimento
**Cria novo comando**

```
Request (Content-Type: application/json):
{
  "id": "novo_comando",
  "tipo": "saudacao",
  "categoria": "Saudações",
  "resposta": "Resposta...",
  "palavras_chave": ["palavra1", "palavra2"],
  "prioridade": 5,
  "ativo": true
}

Resposta (201):
{
  "id": "novo_comando",
  "categoria": "Saudações",
  "tipo": "saudacao",
  "resposta": "Resposta...",
  "palavras_chave": ["palavra1", "palavra2"],
  "prioridade": 5,
  "ativo": true,
  "criado_em": "2026-01-11T06:30:00.000Z"
}
```

### PUT /api/base-conhecimento/:id
**Atualiza comando existente**

```
Request:
{
  "categoria": "Nova Categoria",
  "resposta": "Nova resposta..."
}

Resposta (200):
{
  "id": "comando_id",
  "categoria": "Nova Categoria",
  ...
  "atualizado_em": "2026-01-11T06:31:00.000Z"
}
```

### DELETE /api/base-conhecimento/:id
**Deleta comando**

```
Resposta (200):
{ "message": "Comando deletado com sucesso" }
```

---

## Banco de Dados

### Estrutura base-conhecimento-robo.json

```json
{
  "comandos": [
    {
      "id": "comando_unico",
      "categoria": "Nome da Categoria",
      "tipo": "saudacao|informacao|problema|resposta_gentil|duvida|acao|generico",
      "resposta": "Texto que será respondido",
      "palavras_chave": ["palavra1", "palavra2", "palavra3"],
      "prioridade": 1-10,
      "ativo": true,
      "criado_em": "2026-01-11T06:30:00.000Z",
      "atualizado_em": "2026-01-11T06:30:00.000Z"
    }
  ],
  "configuracoes": {
    "usar_base_conhecimento": true,
    "usar_ia_gemini": false,
    "fazer_fallback_ia": true
  }
}
```

### Validações

**Campo `categoria`:**
- Tipo: String
- Obrigatório: Não
- Padrão: "" (vazio)
- Comprimento: até 50 caracteres

**Campo `tipo`:**
- Tipos válidos: `saudacao`, `informacao`, `problema`, `resposta_gentil`, `duvida`, `acao`, `generico`
- Obrigatório: Sim

**Campo `prioridade`:**
- Tipo: Number
- Intervalo: 1-10
- Padrão: 5

---

## Fluxo de Dados

### Criar Comando com Categoria

```
1. Usuário preenche formulário
   ├─ ID: "meu_comando"
   ├─ Tipo: "saudacao"
   ├─ Categoria: "Saudações"
   ├─ Resposta: "Olá!"
   └─ Palavras-chave: ["oi", "olá"]

2. JavaScript valida entrada
   ├─ ID não vazio?
   ├─ Tipo válido?
   ├─ Categoria válida?
   └─ Palavras-chave presentes?

3. Enviar para API via Fetch
   POST /api/base-conhecimento
   {
     "id": "meu_comando",
     "tipo": "saudacao",
     "categoria": "Saudações",
     ...
   }

4. Backend valida
   ├─ ID não duplicado?
   ├─ Categoria é string ou vazia?
   └─ Tipo está em lista válida?

5. Salvar em JSON
   ├─ Ler arquivo
   ├─ Adicionar comando
   ├─ Escrever arquivo
   └─ Retornar resposta 201

6. Frontend atualiza lista
   ├─ Carregar lista atualizada
   ├─ Agrupar por categoria
   ├─ Renderizar com botões de filtro
   └─ Limpar formulário
```

### Filtrar por Categoria

```
1. Usuário clica botão de categoria
   onclick="filtrarCategoria('Saudações')"

2. JavaScript define variável global
   categoriaFiltro = 'Saudações'

3. Recarrega lista
   ├─ Itera baseConhecimento
   ├─ Filtra por categoriaFiltro
   ├─ Agrupa por categoria
   └─ Renderiza na tela

4. Botão ativo muda cor
   ├─ Button com classe 'active'
   ├─ CSS adiciona background
   └─ Indica categoria selecionada
```

### Editar Comando

```
1. Usuário clica em comando na lista
   onclick="editarComando('meu_comando')"

2. JavaScript busca comando
   const cmd = baseConhecimento.find(c => c.id === id)

3. Preenche formulário
   ├─ ID: cmd.id
   ├─ Tipo: cmd.tipo
   ├─ Categoria: cmd.categoria
   ├─ Resposta: cmd.resposta
   └─ Palavras-chave: cmd.palavras_chave

4. Muda botão para "Atualizar"
   document.querySelector('button').textContent = '✏️ Atualizar'

5. Usuário modifica categoria e salva
   PUT /api/base-conhecimento/meu_comando
   { "categoria": "Nova Categoria" }

6. Backend atualiza JSON
   ├─ Encontra comando pelo ID
   ├─ Atualiza campo categoria
   ├─ Salva arquivo
   └─ Retorna comando atualizado

7. Frontend limpa e recarrega
   ├─ limparFormulario()
   ├─ atualizarLista()
   └─ Mostra sucesso
```

---

## localStorage Estrutura

```javascript
// Tema salvo
{
  "tema-gerenciador": "dark" // ou "light"
}

// Acesso em JavaScript
localStorage.getItem('tema-gerenciador')  // Ler
localStorage.setItem('tema-gerenciador', 'dark')  // Escrever
localStorage.removeItem('tema-gerenciador')  // Deletar
localStorage.clear()  // Limpar tudo
```

---

## Performance

### Otimizações Implementadas

1. **CSS Variables**
   - Uma mudança de tema afeta toda a interface
   - Não recarrega página
   - Transição suave (0.3s)

2. **localStorage**
   - Lê uma única vez na inicialização
   - Escreve apenas quando muda tema
   - Sem chamadas Ajax desnecessárias

3. **Filtragem Local**
   - Filtra no cliente (não no servidor)
   - Sem latência de rede
   - Instantâneo

4. **Set de Categorias**
   - Usa `Set` para remover duplicatas
   - Gera botões apenas uma vez
   - Renderização eficiente

---

## Compatibilidade

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| CSS Variables | ✅ | ✅ | ✅ | ✅ |
| localStorage | ✅ | ✅ | ✅ | ✅ |
| matchMedia | ✅ | ✅ | ✅ | ✅ |
| Fetch API | ✅ | ✅ | ✅ | ✅ |
| classList | ✅ | ✅ | ✅ | ✅ |

---

## Testing

### Testes Manuais Recomendados

```javascript
// Console browser (F12)

// 1. Verificar tema
console.log(localStorage.getItem('tema-gerenciador'))

// 2. Testar toggle
toggleDarkMode()

// 3. Verificar categorias carregadas
console.log(baseConhecimento)

// 4. Testar filtro
filtrarCategoria('Saudações')

// 5. Ver variáveis CSS
getComputedStyle(document.documentElement).getPropertyValue('--primary-color')
```

---

**Versão:** 1.0.0
**Data:** 2026-01-11
**Status:** ✅ Production Ready

