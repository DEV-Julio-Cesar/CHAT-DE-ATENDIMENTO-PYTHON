# Código Legado

Esta pasta contém código legado que foi movido para manter compatibilidade temporária.

## Arquivos Movidos

### Versões V2 (SQL Server)
- `auth_v2.py` - Autenticação com SQL Server (substituído por auth.py com MariaDB)
- `conversations_v2.py` - Conversas com SQL Server (substituído por conversations.py)
- `dashboard_v2.py` - Dashboard com SQL Server (substituído por dashboard.py)
- `users_v2.py` - Usuários com SQL Server (substituído por users.py)
- `whatsapp_v2.py` - WhatsApp com SQL Server (substituído por whatsapp.py)
- `whatsapp_send_v2.py` - Envio WhatsApp com SQL Server (substituído)
- `chatbot_admin_v2.py` - Admin chatbot com SQL Server (substituído por chatbot_admin.py)
- `reports_v2.py` - Relatórios com SQL Server (substituído)

## Motivo da Remoção

O sistema foi consolidado para usar apenas **MariaDB/MySQL** como banco de dados principal.
As versões V2 foram criadas para suportar SQL Server, mas isso criou:

1. **Duplicação de código** - Mesma lógica em múltiplos arquivos
2. **Confusão** - Desenvolvedores não sabiam qual versão usar
3. **Manutenção difícil** - Bugs precisavam ser corrigidos em 2 lugares
4. **Complexidade desnecessária** - SQL Server não é mais usado

## Plano de Migração

### Fase 1: Mover para _legacy (CONCLUÍDO)
- ✅ Arquivos movidos para esta pasta
- ✅ Rotas desabilitadas em routes.py
- ✅ Documentação criada

### Fase 2: Período de Transição (30 dias)
- Monitorar se algum cliente ainda usa endpoints V2
- Avisar clientes sobre deprecação
- Fornecer guia de migração

### Fase 3: Remoção Completa (após 30 dias)
- Deletar esta pasta completamente
- Remover imports de routes.py
- Atualizar documentação

## Se Você Precisa de SQL Server

Se realmente precisa de SQL Server, use a versão V1 dos endpoints e configure:

```python
# app/core/config.py
SQLSERVER_HOST = "seu-servidor"
SQLSERVER_DATABASE = "seu-banco"
SQLSERVER_USER = "seu-usuario"
SQLSERVER_PASSWORD = "sua-senha"
```

## Data de Remoção Planejada

**12 de Março de 2026** (30 dias a partir de hoje)

Após esta data, os arquivos serão permanentemente removidos.
