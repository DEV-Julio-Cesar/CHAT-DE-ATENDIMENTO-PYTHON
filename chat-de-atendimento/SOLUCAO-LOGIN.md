# 🔧 GUIA DE SOLUÇÃO DE PROBLEMAS - LOGIN

## ✅ O que já foi feito:
1. ✅ Usuário admin resetado com credenciais corretas
2. ✅ Senha testada e funcionando no backend
3. ✅ Sistema de validação verificado e OK

## 🎯 SOLUÇÃO PASSO A PASSO

### MÉTODO 1: Reinício Limpo (MAIS RÁPIDO)

1. **Feche o aplicativo Electron completamente**
   - Clique no X da janela
   - OU pressione Alt+F4

2. **Execute o script de reinício limpo:**
   ```powershell
   .\reiniciar-limpo.bat
   ```

3. **Quando o aplicativo abrir:**
   - Usuário: `admin`
   - Senha: `admin`
   - Clique em "Entrar"

---

### MÉTODO 2: Verificação com DevTools

1. **Abra o aplicativo** (`npm start`)

2. **Abra o DevTools** (pressione F12)

3. **Vá para a aba Console**

4. **Cole este comando e pressione Enter:**
   ```javascript
   await window.authAPI.tentarLogin('admin', 'admin')
   ```

5. **Veja o resultado:**
   - ✅ Se mostrar `{success: true, ...}` → Login funciona, problema é no formulário
   - ❌ Se mostrar erro → Me envie a mensagem de erro

---

### MÉTODO 3: Teste Manual

1. **Abra o aplicativo**

2. **Digite EXATAMENTE:**
   - Usuário: `admin` (minúsculas)
   - Senha: `admin` (minúsculas)

3. **Certifique-se:**
   - Não há espaços extras
   - Não há CapsLock ativado
   - Não há caracteres especiais

4. **Clique em "Entrar"**

---

## 🔍 DIAGNÓSTICO

### Se AINDA não funcionar:

**Abra o DevTools (F12) e verifique:**

1. **Aba Console** - Erros em vermelho?
   - Me envie print ou copie a mensagem

2. **Aba Network** - Requisição "login-attempt" aparece?
   - Qual o status?

3. **Aba Application** → Local Storage
   - Limpe tudo
   - Tente novamente

---

## 📝 INFORMAÇÕES DO SISTEMA

**Credenciais válidas:**
- Usuário: `admin`
- Senha: `admin`
- Hash: `8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918`

**Arquivo de usuários:**
- Localização: `dados/usuarios.json`
- Backup criado: `dados/usuarios.json.backup.1768115494055`

**Testes realizados:**
```
✅ Validação de credenciais: PASSOU
✅ Hash SHA-256: CORRETO
✅ IPC Handler: FUNCIONANDO
✅ Registro de login: OK
```

---

## 🆘 SE NADA FUNCIONAR

Execute este comando no DevTools (F12 → Console):

```javascript
// Teste completo
console.log('=== TESTE DE LOGIN ===');
console.log('authAPI disponível:', !!window.authAPI);
console.log('navigationAPI disponível:', !!window.navigationAPI);

try {
    const resultado = await window.authAPI.tentarLogin('admin', 'admin');
    console.log('Resultado:', resultado);
    
    if (resultado.success) {
        console.log('✅ LOGIN OK! Navegando...');
        await window.navigationAPI.navigate('principal');
    } else {
        console.log('❌ Login falhou:', resultado.message);
    }
} catch (error) {
    console.error('❌ ERRO:', error);
}
```

**Me envie todo o output que aparecer!**

---

## 🚀 ATALHOS

- **Reiniciar limpo:** `.\reiniciar-limpo.bat`
- **Resetar admin:** `node resetar-admin.js`
- **Testar credenciais:** `node teste-login-completo.js`
- **DevTools:** Pressione `F12` no aplicativo
