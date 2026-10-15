# Auditoria

Log imutável de mutações do NeoPrice (US51, RNF05, issue #58). Responde quem alterou o quê e quando, para qualquer registro de cadastro ou de precificação.

Migration: `supabase/migrations/20261015000001_criar_auditoria.sql`.

## Como funciona

Cada tabela do schema tem um gatilho `trg_<tabela>_auditoria` que, a cada `INSERT`, `UPDATE` ou `DELETE`, grava uma linha em `auditoria`. O registro acontece no banco, então vale para a API, para o PostgREST e para quem conectar direto.

| Coluna | Conteúdo |
| :--- | :--- |
| `tabela`, `registro_id` | Registro alterado. `registro_id` é a chave primária em texto; em chave composta, os valores separados por `\|` |
| `operacao` | `INSERT`, `UPDATE` ou `DELETE` |
| `usuario_id` | Quem fez. Nulo em carga de seed e tarefa de sistema |
| `papel` | Papel do banco: `authenticated`, `service_role`, `postgres`... |
| `transacao_id` | Agrupa as mutações de uma mesma transação |
| `dados_antes`, `dados_depois` | O registro inteiro antes e depois, em JSON |
| `diff` | Só no `UPDATE`: `{"coluna": {"de": ..., "para": ...}}`, sem `updated_at` |
| `ocorrido_em` | Momento da transação |

`UPDATE` que não muda nenhum valor não gera linha.

## Quem é o usuário

- Pelo PostgREST (front com o JWT do Supabase Auth): o `sub` do JWT, o mesmo de `auth.uid()`.
- Pelo backend, que conecta como `service_role`: a API informa o usuário da requisição no início da transação.

```sql
SELECT set_config('neoprice.usuario_id', '<uuid do usuário>', true);
```

O `true` deixa o valor só na transação atual. Sem ele, a conexão do pool levaria o usuário para a próxima requisição.

## Garantias de imutabilidade

- `UPDATE`, `DELETE` e `TRUNCATE` em `auditoria` são recusados por gatilho, inclusive para o `service_role` e para o dono da tabela.
- Ninguém tem `INSERT` em `auditoria`. Só o gatilho grava, como dono da tabela (`SECURITY DEFINER`).
- `TRUNCATE` nas tabelas auditadas também é recusado, porque não passa pelos gatilhos de linha. Para apagar, use `DELETE`.
- A auditoria fica na mesma transação da mutação: se uma for desfeita, a outra também é.

## Consultar a trilha de um registro

```sql
SELECT operacao, usuario_id, ocorrido_em, diff
FROM trilha_auditoria('produto', '<id do produto>');
```

Por enquanto só o `service_role` lê `auditoria`. A leitura pela interface entra com uma permissão nomeada de auditoria, junto das políticas por perfil da US04.

## Tabela nova

Na mesma migration que cria a tabela:

```sql
SELECT habilitar_auditoria('nome_da_tabela');
```

A tabela precisa de chave primária. O teste `test_toda_tabela_tem_auditoria` (em `tests/banco/test_auditoria.py`) falha se alguma tabela ficar sem o gatilho.
