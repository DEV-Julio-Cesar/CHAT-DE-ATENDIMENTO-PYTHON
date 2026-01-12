# 📦 GUIA DE COMMIT - v2.0.2

## Commits Recomendados

### Commit 1: Correção Principal
```bash
git add src/interfaces/gerenciador-pool.html \
         src/interfaces/pre-carregamento-gerenciador-pool.js \
         main.js

git commit -m "fix: Substitui window.open() por IPC para conexão por número

- Problema: Janela de conexão por número não abria no Electron
- Erro: ERR_FILE_NOT_FOUND ao tentar window.open('/interfaces/...')
- Solução: Usar IPC seguro (Inter-Process Communication)

Mudanças:
- Função abrirConexaoPorNumero() agora usa poolAPI.openConexaoPorNumeroWindow()
- Adicionado método openConexaoPorNumeroWindow em pre-carregamento-gerenciador-pool.js
- Adicionado function createConexaoPorNumeroWindow() em main.js
- Adicionado handler IPC 'open-conexao-por-numero-window' em main.js

Validação:
- 15/15 testes automatizados passaram
- Sem breaking changes
- Compatível com Electron

Fixes: #[issue-number]"
```

### Commit 2: Atualização do CHANGELOG
```bash
git add CHANGELOG.md

git commit -m "docs: Atualiza CHANGELOG com correção v2.0.2

Adicionado detalhes da correção do problema onde a janela de conexão
por número não abria quando clicado."
```

### Commit 3: Documentação
```bash
git add CORRECAO-RAPIDA.md \
         RESUMO-CORRECAO-V2-0-2.md \
         CORRECAO-CONEXAO-POR-NUMERO-V2-0-2.md \
         GUIA-TESTE-CONEXAO-NUMERO-V2-0-2.md \
         SUMARIO-MUDANCAS-V2-0-2.md \
         INDICE-CORRECAO-V2-0-2.md

git commit -m "docs: Adiciona documentação completa da correção v2.0.2

Documentos adicionados:
- CORRECAO-RAPIDA.md: Resumo rápido (2 min)
- RESUMO-CORRECAO-V2-0-2.md: Resumo executivo
- CORRECAO-CONEXAO-POR-NUMERO-V2-0-2.md: Documentação técnica
- GUIA-TESTE-CONEXAO-NUMERO-V2-0-2.md: Passo a passo de testes (10 testes)
- SUMARIO-MUDANCAS-V2-0-2.md: Detalhes das mudanças
- INDICE-CORRECAO-V2-0-2.md: Índice de referência

Todos os documentos incluem:
- Explicação do problema
- Solução implementada
- Como testar
- Troubleshooting"
```

### Commit 4: Testes Automatizados
```bash
git add teste-conexao-numero-v2-0-2.js

git commit -m "test: Adiciona testes automatizados para conexão por número

Novo arquivo de testes com 15 validações:
- Verifica existência de arquivos
- Valida funções IPC
- Confirma handlers registrados
- Testa carregamento correto
- Valida hotfix do v2.0.2

Resultado: 15/15 testes passaram ✅

Como executar:
npx node teste-conexao-numero-v2-0-2.js"
```

---

## Sequência de Commits Recomendada

```bash
# 1. Implementação
git commit -m "fix: Substitui window.open() por IPC para conexão por número ..."

# 2. Testes
git commit -m "test: Adiciona testes automatizados para conexão por número"

# 3. Documentação
git commit -m "docs: Atualiza CHANGELOG com correção v2.0.2"

# 4. Documentação Adicional
git commit -m "docs: Adiciona documentação completa da correção v2.0.2"

# 5. Tag de Release (opcional)
git tag -a v2.0.2 -m "Versão 2.0.2: Hotfix + Conexão por Número"
```

---

## Verificação Pré-Commit

Antes de fazer commit, execute:

```bash
# 1. Teste automatizado
npx node teste-conexao-numero-v2-0-2.js
# Resultado esperado: 15/15 PASSARAM

# 2. Verificar lint (se houver)
npm run lint

# 3. Verificar testes gerais (se houver)
npm test
```

---

## Mensagem de Release (para notas de versão)

```markdown
## v2.0.2 - 2026-01-11

### 🔴 Bug Corrigido
- **Janela de Conexão por Número não abria**
  - Problema: `window.open()` não funciona em Electron
  - Solução: Substituído por IPC seguro
  - Resultado: ✅ Funcionando corretamente

### 🎁 Novidades Incluídas
- Novo método de conexão por número de telefone
- Interface de seleção (QR vs Número)
- Validação de formato automática
- QR Code display após entrada

### 📝 Detalhes
- Arquivos modificados: 3
- Testes automatizados: 15 ✅
- Sem breaking changes
- Compatível com versões anteriores

### 📚 Documentação
- [Resumo Rápido](CORRECAO-RAPIDA.md)
- [Guia de Teste](GUIA-TESTE-CONEXAO-NUMERO-V2-0-2.md)
- [Detalhes Técnicos](CORRECAO-CONEXAO-POR-NUMERO-V2-0-2.md)
```

---

## Branch Workflow (recomendado)

```bash
# Criar branch de feature
git checkout -b fix/conexao-por-numero-window

# Trabalhar nas mudanças
# ... fazer commits ...

# Push para branch
git push origin fix/conexao-por-numero-window

# Pull request / Merge para main/develop
# Após merge, criar tag
git tag v2.0.2
git push origin v2.0.2
```

---

## Checklist Pré-Release

- ✅ Código implementado
- ✅ Testes passam (15/15)
- ✅ CHANGELOG atualizado
- ✅ Documentação completa
- ✅ Sem console.log de debug
- ✅ Sem arquivos temporários
- ✅ Testado em Electron
- ✅ Sem breaking changes

---

**Versão:** v2.0.2  
**Status:** ✅ Pronto para Release
