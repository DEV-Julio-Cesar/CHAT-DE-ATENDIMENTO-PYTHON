# 📱 Guia de Uso - Dark Mode + Categorias

## 🌙 Dark Mode - Passo a Passo

### Ativar Dark Mode

1. **Procure o botão na barra superior**
   - Localização: Canto direito do cabeçalho
   - Ícone: 🌙 (lua) ou ☀️ (sol)

2. **Clique no botão**
   - Light Mode → ícone mostra 🌙
   - Dark Mode → ícone mostra ☀️

3. **A mudança é instantânea**
   - Todas as cores mudam suavemente
   - Pano de fundo escurece/clareia
   - Textos se adaptam automaticamente

### Preferências

- **Primeira vez?** O app usa a preferência do seu sistema
- **Escolheu light/dark?** Fica salvo para próximas visitas
- **Quer resetar?** Mude a preferência do sistema operacional

---

## 📂 Categorias - Passo a Passo

### Criar Comando com Categoria

1. **Preencha o formulário:**
   ```
   ID do Comando: saudacao_bom_dia
   Tipo: Saudação
   ✨ NOVO: Categoria: Saudações
   Resposta: Bom dia! Tudo bem?
   Prioridade: 10
   ```

2. **Adicione as palavras-chave:**
   - Digite: "bom dia"
   - Clique em "Adicionar"
   - Digite: "bom"
   - Clique em "Adicionar"

3. **Salve o comando**
   - Clique em "➕ Adicionar Comando"
   - Verá mensagem: "✅ Comando criado!"

### Visualizar Comandos por Categoria

1. **Abra a aba "Lista de Comandos"**
   - Veja todos os comandos agrupados
   - Cada grupo tem um título de categoria

2. **Use os filtros:**
   - **Tudo** - mostra todas as categorias
   - **Saudações** - apenas saudações
   - **Informações** - dúvidas e dados
   - **Suporte** - problemas técnicos
   - **Vendas** - pedidos
   - **Respostas** - agradecimentos

3. **Clique para filtrar:**
   ```
   [Tudo] [Saudações] [Informações] [Suporte] [Vendas] [Respostas]
   ```

### Editar Comando

1. **Clique no comando que quer editar**
   - Formulário se preenche automaticamente
   - Categoria aparece no campo

2. **Mude a categoria se desejar**
   - Campo "Categoria" está disponível
   - Deixe vazio se não quer categoria

3. **Clique em "✏️ Atualizar Comando"**
   - Categoria é salva

---

## 🎯 Exemplos de Categorias

### Saudações
- Oi, olá, bom dia
- Bem-vindo
- Despedidas

### Informações
- Horário de funcionamento
- Preços e valores
- Como funciona
- Dúvidas gerais

### Suporte
- Problemas técnicos
- Erros
- Não funciona
- Travou

### Vendas
- Quero comprar
- Fazer pedido
- Contratar serviço
- Carrinho de compras

### Respostas
- Obrigado
- Agradecimentos
- Feedback positivo
- Respostas gentis

---

## 💡 Dicas Pro

✅ **Use nomes de categorias claros**
- "Saudações" em vez de "S1"
- "Suporte Técnico" em vez de "ST"

✅ **Mantenha consistência**
- Use os mesmos nomes sempre
- Não crie "Suporte" e "Suporte Técnico" separados

✅ **Deixe campos vazios quando apropriado**
- Nem todo comando precisa de categoria
- Comandos genéricos podem não ter categoria

✅ **Use filtros para navegar**
- Não role em listas longas
- Use os botões de filtro rápido

✅ **Aproveite Dark Mode**
- Use à noite para menos cansar visão
- Alterna automaticamente se Sistema usar dark mode

---

## ⚙️ Configurações do Navegador

### Se dark mode não funcionar

1. **Verifique se JavaScript está ativado**
2. **Limpe o cache (Ctrl+Shift+Delete)**
3. **Recarregue a página (F5)**
4. **Se usar Firefox:** Verifique preferência no about:config

### localStorage

Seus dados ficam em:
- `localStorage.tema-gerenciador` = 'dark' | 'light'

Para resetar:
```javascript
localStorage.removeItem('tema-gerenciador')
```

---

## 🐛 Troubleshooting

### Dark Mode não aplica
- **Solução:** Recarregue a página (F5)
- **Alternativa:** Limpe o localStorage

### Categoria não aparece ao editar
- **Solução:** Certifique-se que salvou o comando
- **Verificar:** Abra a aba "Lista" primeiro

### Cores estranhas em Dark Mode
- **Solução:** Use navegador mais recente
- **Alternativa:** Use Firefox ou Chrome

### Filtro não funciona
- **Solução:** Verifique se há comandos com aquela categoria
- **Dica:** Crie alguns comandos primeiro com categorias

---

## 📊 Keyboard Shortcuts (Opcionais)

Atualmente sem atalhos de teclado, mas pode ser adicionado:
- `Ctrl+Shift+D` = Toggle Dark Mode
- `Ctrl+K` = Buscar comando
- `Ctrl+N` = Novo comando

---

## 🎨 Customizar Cores

Se quiser mudar as cores do tema:

1. **Abra:** `src/interfaces/gerenciador-comandos.html`
2. **Procure por:** `:root { --primary-color: ...}`
3. **Altere os valores** (ex: `#667eea` para `#5d4e9f`)
4. **Dark Mode:** mude `:root.dark-mode { ... }`
5. **Salve e recarregue**

### Cores disponíveis para customizar:
- `--primary-color` - Cor principal (botões, links)
- `--bg-color` - Fundo geral
- `--text-color` - Texto principal
- `--success-color` - Verde (sucesso)
- `--error-color` - Vermelho (erro)
- `--warning-color` - Laranja (aviso)
- `--info-color` - Azul (informação)

---

## 📞 Suporte

Se tiver dúvidas:
1. Consulte este guia
2. Verifique o console (F12) para erros
3. Teste em navegador diferente
4. Limpe cache e cookies

---

**Última atualização:** 2026-01-11
**Versão:** 1.0.0
**Status:** ✅ Operacional

