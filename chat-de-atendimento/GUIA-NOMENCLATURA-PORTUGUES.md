# 🚀 Guia Rápido - Nomenclatura em Português

## 📖 Referência Rápida

### Tradução de Termos Comuns

| Inglês | Português |
|--------|-----------|
| manager | gerenciador |
| handler | manipulador / tratador |
| service | serviço |
| controller | controlador |
| provider | provedor |
| loader | carregador |
| builder | construtor |
| validator | validador |
| formatter | formatador |
| parser | analisador |
| client | cliente |
| server | servidor |
| pool | conjunto / pool |
| queue | fila |
| cache | cache / armazenamento |
| session | sessão |
| token | ficha / token |
| config | configuração |
| setting | ajuste / configuração |
| option | opção |
| feature | recurso / funcionalidade |
| flag | sinalizador / marcador |
| state | estado |
| status | situação / status |
| event | evento |
| callback | retorno / callback |
| promise | promessa |
| async | assíncrono |
| sync | síncrono |
| render | renderizar |
| preload | pré-carregamento |
| window | janela |
| modal | modal |
| toast | notificação toast |
| button | botão |
| input | entrada |
| output | saída |
| data | dados |
| info | informação |
| error | erro |
| warning | aviso / alerta |
| success | sucesso |
| loading | carregando |
| fetch | buscar |
| send | enviar |
| receive | receber |
| create | criar |
| update | atualizar |
| delete | excluir / remover |
| read | ler |
| write | escrever |
| list | listar |
| get | obter |
| set | definir |
| check | verificar |
| validate | validar |
| process | processar |
| execute | executar |
| run | executar / rodar |
| start | iniciar |
| stop | parar |
| restart | reiniciar |
| connect | conectar |
| disconnect | desconectar |
| open | abrir |
| close | fechar |
| save | salvar |
| load | carregar |
| reset | resetar / reiniciar |
| clear | limpar |
| filter | filtrar |
| sort | ordenar |
| search | buscar / pesquisar |
| find | encontrar |
| map | mapear |
| reduce | reduzir |
| forEach | paraCada |
| callback | aoCompletar / quandoPronto |

### Verbos para Funções

| Ação | Português |
|------|-----------|
| handle | manipular / tratar |
| process | processar |
| validate | validar |
| check | verificar |
| ensure | garantir |
| init/initialize | inicializar |
| setup | configurar |
| build | construir |
| parse | analisar |
| format | formatar |
| transform | transformar |
| convert | converter |
| calculate | calcular |
| compute | computar |
| generate | gerar |
| render | renderizar |
| display | exibir |
| show | mostrar |
| hide | ocultar |
| toggle | alternar |
| enable | habilitar |
| disable | desabilitar |
| activate | ativar |
| deactivate | desativar |
| register | registrar |
| unregister | desregistrar |
| subscribe | inscrever |
| unsubscribe | desinscrever |
| emit | emitir |
| dispatch | despachar |
| trigger | disparar / acionar |
| notify | notificar |
| alert | alertar |
| warn | avisar |
| log | registrar / logar |
| debug | depurar |
| trace | rastrear |
| monitor | monitorar |
| track | rastrear |
| measure | medir |
| count | contar |
| sum | somar |
| average | calcularMedia |
| min | minimo |
| max | maximo |

### Prefixos para Booleanos

| Prefixo | Uso | Exemplo |
|---------|-----|---------|
| esta | Estado atual | `estaConectado`, `estaValido` |
| possui | Posse/existência | `possuiErro`, `possuiPermissao` |
| tem | Similar a possui | `temDados`, `temAcesso` |
| pode | Capacidade | `podeEditar`, `podeExcluir` |
| deve | Obrigação | `deveValidar`, `deveAtualizar` |
| foi | Ação passada | `foiProcessado`, `foiEnviado` |

### Sufixos para Callbacks

| Sufixo | Uso | Exemplo |
|--------|-----|---------|
| ao... | Momento da ação | `aoClicar`, `aoCarregar` |
| quando... | Condição | `quandoPronto`, `quandoErro` |
| apos... | Depois da ação | `aposEnviar`, `aposSalvar` |
| antes... | Antes da ação | `antesFechar`, `antesExcluir` |

### Exemplos Práticos de Conversão

```javascript
// ❌ Antes (Inglês)
const userManager = require('./UserManager');
const isValid = userManager.checkUser(userId);
const userData = userManager.getUserData(userId);

if (isValid) {
  const messageList = userManager.getMessages();
  messageList.forEach(msg => handleMessage(msg));
}

function handleMessage(message) {
  if (message.hasError) {
    showError(message.error);
  }
}

// ✅ Depois (Português)
const gerenciadorUsuarios = require('./GerenciadorUsuarios');
const estaValido = gerenciadorUsuarios.verificarUsuario(idUsuario);
const dadosUsuario = gerenciadorUsuarios.obterDadosUsuario(idUsuario);

if (estaValido) {
  const listaMensagens = gerenciadorUsuarios.obterMensagens();
  listaMensagens.forEach(mensagem => manipularMensagem(mensagem));
}

function manipularMensagem(mensagem) {
  if (mensagem.possuiErro) {
    mostrarErro(mensagem.erro);
  }
}
```

### Constantes

```javascript
// ❌ Antes
const MAX_RETRY_COUNT = 3;
const DEFAULT_TIMEOUT = 5000;
const API_BASE_URL = 'https://api.example.com';

// ✅ Depois
const MAXIMO_TENTATIVAS = 3;
const TEMPO_EXPIRACAO_PADRAO = 5000;
const URL_BASE_API = 'https://api.example.com';
```

### Arrays e Coleções

```javascript
// ❌ Antes
const userList = [];
const messageArray = [];
const chatData = {};

// ✅ Depois
const listaUsuarios = [];
const listaMensagens = [];
const dadosChat = {};
```

## 💡 Dicas de Boas Práticas

1. **Seja descritivo**: `obterDadosUsuarioPorId` é melhor que `obterUsuario`
2. **Use verbos no infinitivo**: `carregar`, `validar`, `processar`
3. **Prefira clareza sobre brevidade**: `listaClientesAtivos` > `clientesAtv`
4. **Mantenha consistência**: escolha um padrão e siga-o em todo o código
5. **Evite abreviações obscuras**: `msg` pode virar `mensagem`, `usr` → `usuario`
6. **Use nomes autoexplicativos**: o código deve ser legível como uma narrativa

## 🔍 Como Refatorar

1. Identifique o tipo (variável, função, classe, etc.)
2. Traduza o termo principal
3. Aplique a convenção de nomenclatura apropriada
4. Verifique se o nome é claro e descritivo
5. Atualize todas as referências

---

**Lembre-se**: Código bom é código que se lê como português natural!
