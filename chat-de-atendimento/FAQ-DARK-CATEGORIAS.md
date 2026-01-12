# ❓ FAQ - Dark Mode + Categorias

## Perguntas Frequentes

### 1. **Como o Dark Mode é ativado automaticamente?**

**Resposta:**
O Dark Mode detecta a preferência do seu sistema operacional usando:
```javascript
window.matchMedia('(prefers-color-scheme: dark)').matches
```

**Como funciona:**
1. Primeira visita → Detecta preferência do SO
2. Se escolher light/dark → Salva em `localStorage`
3. Próximas visitas → Usa preferência salva

**Configurar no Windows:**
- Configurações → Personalização → Cores
- Escolha "Claro" ou "Escuro"

**Configurar no macOS:**
- System Preferences → General
- Escolha "Light" ou "Dark"

**Configurar no Linux:**
- Varia por distribuição
- GNOME: Settings → Appearance

---

### 2. **O Dark Mode funciona em todos os navegadores?**

**Resposta:** ✅ **Sim**, em todos os navegadores modernos:
- Chrome 76+
- Firefox 67+
- Safari 12.1+
- Edge 76+

**Se não funcionar:**
1. Atualize o navegador
2. Limpe o cache (Ctrl+Shift+Delete)
3. Recarregue a página (F5)

---

### 3. **Posso usar Dark Mode só em certos horários?**

**Resposta:** ❌ **Não automaticamente**, mas você pode:

**Opção 1: Manual**
- Clique no botão 🌙/☀️ manualmente

**Opção 2: Sistema**
- Alguns SOs têm agendamento nativo
- Windows 11: Configurações → Personalização → Cores → "Mude automaticamente"
- macOS: System Preferences → General → Appearance → "Auto"

---

### 4. **O que são Categorias? Por que usar?**

**Resposta:**
Categorias são rótulos para organizar comandos por tipo.

**Exemplo:**
```
Sem categorias (desorganizado):
- oi
- olá
- bom dia
- qual horário
- qual preço
- problema
- obrigado

Com categorias (organizado):
📂 Saudações
  - oi
  - olá
  - bom dia

📂 Informações
  - qual horário
  - qual preço

📂 Suporte
  - problema

📂 Respostas
  - obrigado
```

**Vantagens:**
- Fácil localizar comandos
- Filtrar rapidamente
- Interface profissional
- Organize por tipo de resposta

---

### 5. **Posso deixar um comando sem categoria?**

**Resposta:** ✅ **Sim!**

**Como:**
- Deixe o campo "Categoria" vazio
- Salve o comando normalmente
- Aparecerá em "Sem categoria"

**Casos de uso:**
- Comandos genéricos
- Respostas padrão
- Testes

---

### 6. **Como adicionar uma categoria nova?**

**Resposta:**
Não precisa criar nada! Categorias são criadas automaticamente.

**Processo:**
1. Crie um comando
2. Digite uma categoria nova no campo
3. Salve
4. Botão novo aparece nos filtros automaticamente

**Exemplo:**
```
1. Campo categoria: "Minha Nova Categoria"
2. Salva o comando
3. Botão aparece: [Minha Nova Categoria]
```

---

### 7. **Posso renomear uma categoria?**

**Resposta:** ⚠️ **Indireto:**

Categorias são nomes que você digite, então:

**Para "renomear":**
1. Edite cada comando daquela categoria
2. Mude o nome
3. Pronto!

**Exemplo:**
```
Antes: "Saudações"
Depois: "Boas-vindas"

Todos os comandos com "Saudações" devem ser atualizados
```

**Dica:** Use nomes consistentes desde o início!

---

### 8. **Quantas categorias posso ter?**

**Resposta:** ✅ **Ilimitadas!**

**Recomendação:** 5-10 categorias é o ideal
- Menos: fácil navegar
- Mais: fica desordenado

**Exemplo de boa estrutura:**
- Saudações (3-5 comandos)
- Informações (5-10 comandos)
- Suporte (3-5 comandos)
- Vendas (3-5 comandos)
- Respostas (2-3 comandos)

---

### 9. **O Dark Mode usa mais bateria?**

**Resposta:** ✅ **Sim! Em telas OLED**

- OLED (telefone, alguns monitores): escuro usa menos
- LED/LCD (monitor comum): praticamente igual

**Para economizar bateria:**
- Use Dark Mode em dispositivos OLED
- Use Light Mode em LED/LCD

---

### 10. **Como faço backup das categorias?**

**Resposta:**
As categorias são salvas em `dados/base-conhecimento-robo.json`

**Backup manual:**
1. Vá até a pasta do projeto
2. Copie `dados/base-conhecimento-robo.json`
3. Cole em local seguro

**Backup automático:**
- O sistema já faz (verifique `dados/backups/`)

---

### 11. **Posso importar comandos com categorias?**

**Resposta:** ✅ **Sim!**

Se tiver um CSV ou JSON com categorias:

**Formato esperado:**
```json
{
  "id": "comando",
  "categoria": "Nome",
  "tipo": "saudacao",
  "resposta": "Texto",
  "palavras_chave": ["word1"],
  "prioridade": 5,
  "ativo": true
}
```

A API aceita o campo `categoria` automaticamente.

---

### 12. **O que acontece com comandos criados antes?**

**Resposta:** ✅ **Nada! Compatível com versões anteriores**

Comandos antigos sem categoria:
- Campo categoria fica vazio
- Aparecem em "Sem categoria"
- Você pode adicionar categoria depois

---

### 13. **Posso usar emojis na categoria?**

**Resposta:** ✅ **Sim!**

**Exemplos:**
- 👋 Saudações
- ℹ️ Informações
- 🔧 Suporte
- 🛒 Vendas
- 😊 Respostas

**Digitação:**
- Windows: Win + . (ponto)
- Mac: Cmd + Ctrl + Space
- Linux: Ctrl + ; (ponto-e-vírgula)

---

### 14. **Os filtros funcionam offline?**

**Resposta:** ✅ **Sim!**

Tudo acontece no navegador:
- Filtros são locais
- Sem chamadas de servidor
- Funciona offline (se dados já carregados)

---

### 15. **Como resetar tudo (tema + categorias)?**

**Resposta:**
Pode resetar de formas diferentes:

**Resetar apenas tema:**
```javascript
localStorage.removeItem('tema-gerenciador')
// Recarregue a página (F5)
```

**Resetar categorias:**
1. Edite cada comando
2. Limpe o campo de categoria
3. Salve

**Resetar tudo (localStorage):**
```javascript
localStorage.clear()
// Recarregue a página (F5)
```

---

### 16. **Qual é o limite de caracteres de uma categoria?**

**Resposta:** ~50 caracteres

**Recomendação:** Mantenha < 20 caracteres
- Fica melhor nos botões
- Fácil de ler
- Sem "quebra" de layout

**Exemplos:**
- ✅ "Saudações" (10)
- ✅ "Informações Gerais" (18)
- ❌ "Respostas muito longas e detalhadas que ficam estranhas" (50+)

---

### 17. **Posso pesquisar por categoria?**

**Resposta:** ✅ **Indiretamente com filtros**

**Processo:**
1. Clique no botão de categoria
2. Vê apenas aquela categoria
3. Use Ctrl+F do navegador para buscar palavra

**Busca avançada (futura):**
Pode ser adicionada em atualizações futuras.

---

### 18. **Dark Mode funciona em celular?**

**Resposta:** ✅ **Sim!**

**Em navegador mobile:**
1. Clique o botão 🌙/☀️
2. Mesma funcionalidade do desktop

**Dark Mode automático:**
- Android: Settings → Display → Dark theme
- iOS: Settings → Display & Brightness

---

### 19. **Existem atalhos de teclado?**

**Resposta:** ❌ **Não atualmente**

Mas você pode adicionar:
- `Ctrl+Shift+D` = Toggle Dark Mode
- `Ctrl+K` = Buscar
- Etc.

**Sugestão:** Abra issue no projeto para solicitar

---

### 20. **Que navegador você recomenda?**

**Resposta:**
Qualquer um moderno! Mas preferência:

**Ranking:**
1. **Chrome/Edge** - Melhor performance
2. **Firefox** - Privacidade excelente
3. **Safari** - Bom em macOS
4. **Opera** - Rápido

Evite navegadores antigos (IE11, etc).

---

## 🔧 Troubleshooting

### Dark Mode não funciona

**Passos:**
1. F5 (recarregar)
2. Ctrl+Shift+Delete (limpar cache)
3. Verificar console (F12 → Console) para erros
4. Testar em outro navegador

### Categorias desapareceram

**Causas:**
- localStorage foi limpo
- Dados não foram salvos
- Erro na API

**Solução:**
1. Verifique `base-conhecimento-robo.json`
2. Veja se há backup em `dados/backups/`
3. Recrie categorias se necessário

### Botão de tema não responde

**Causas:**
- JavaScript desativado
- Erro no console
- Navegador desatualizado

**Solução:**
1. Ative JavaScript
2. Atualize navegador
3. Tente navegador diferente

---

## 📚 Recursos Adicionais

### Documentação Completa
- [DARK-MODE-CATEGORIAS.md](./DARK-MODE-CATEGORIAS.md) - Visão geral
- [GUIA-USO-DARK-CATEGORIAS.md](./GUIA-USO-DARK-CATEGORIAS.md) - Como usar
- [TECNICO-DARK-CATEGORIAS.md](./TECNICO-DARK-CATEGORIAS.md) - Técnico
- [VISUAL-DARK-CATEGORIAS.md](./VISUAL-DARK-CATEGORIAS.md) - Visual

### Suporte
- Consulte documentação
- Verifique console (F12)
- Teste em outro navegador

---

**FAQ Atualizado:** 2026-01-11
**Versão:** 1.0.0
**Status:** ✅ Completo

