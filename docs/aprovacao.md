# Decisão de aprovação

Registro da aprovação e da reprovação de uma precificação (US37, issue #68). Fecha a trilha do workflow: quem decidiu, quando, sobre qual versão de cenário e com qual justificativa. Reprovar sem comentário não é possível, senão a decisão volta a ser informal.

Migration: `supabase/migrations/20261108000001_registrar_decisao_aprovacao.sql`.

## Fluxo de status

```
em_preenchimento ──submissão (US35/#66)──▶ em_aprovacao ──decisão (#68)──▶ aprovado
                                                         └──────────────▶ reprovado
```

A decisão só acontece em `em_aprovacao`. Levar a precificação até lá, com a validação de completude, é a submissão da US35 (#66). A fila do gerente, com os filtros por cliente e margem, é a US36 (#67).

## Regras

| Regra | Onde é garantida |
| :--- | :--- |
| Só se decide precificação em `em_aprovacao` | gatilho `trg_decisao_aprovacao_validar` (erro `55000`) |
| Decidir exige `precificacao.aprovar` na carteira do cliente | RLS de `decisao_aprovacao` e de `precificacao` |
| Reprovar exige comentário; só espaços, tabulação ou quebra de linha não contam | gatilho e restrição `ck_decisao_aprovacao_comentario_reprovacao` (erro `23514`) |
| Responsável e data vêm da sessão, nunca de quem chama | gatilho (`usuario_da_sessao()` e `now()`) |
| A decisão aponta para a versão vigente do cenário (#63) | gatilho |
| O status da precificação muda na mesma transação | gatilho `trg_decisao_aprovacao_aplicar` |
| Pela aplicação, `aprovado` e `reprovado` só se alcançam por uma decisão | gatilho `trg_precificacao_status_por_decisao` (erro `42501`) |
| Decisão registrada não muda nem some | gatilho `trg_decisao_aprovacao_imutavel`, sem `UPDATE`/`DELETE` para `authenticated` |
| A decisão e a mudança de status entram na trilha de auditoria (#58) | `habilitar_auditoria('decisao_aprovacao')` e auditoria de `precificacao` |

As regras ficam nos gatilhos, então `decidir_aprovacao(...)` e um `INSERT` direto em `decisao_aprovacao` seguem o mesmo caminho. A guarda de status vale para os papéis `anon` e `authenticated`, que são os do PostgREST; carga de dados e manutenção (dono do banco, `service_role`) ficam de fora, para que os seeds de demonstração continuem gravando precificações já aprovadas.

## Banco

```sql
-- Aprovar (comentário opcional)
SELECT * FROM decidir_aprovacao('<precificacao_id>', 'aprovado');

-- Reprovar (comentário obrigatório)
SELECT * FROM decidir_aprovacao('<precificacao_id>', 'reprovado', 'Margem abaixo da política para este cliente.');

-- Histórico com o nome de quem decidiu e a versão do cenário
SELECT * FROM decisao_aprovacao_historico WHERE precificacao_id = '<precificacao_id>' ORDER BY decidido_em DESC;

-- Trilha de auditoria da decisão
SELECT * FROM trilha_auditoria('decisao_aprovacao', '<decisao_id>');
```

`decisao_aprovacao_historico` existe porque o RLS de `usuario` só deixa cada um ler o próprio cadastro: a visão traz o nome do responsável e aplica ela mesma `precificacao.ler` e a carteira.

## API

| Método e rota | Permissão | Operação |
| :--- | :--- | :--- |
| `POST /precificacoes/{id}/decisoes` | `precificacao.aprovar` | Registra a decisão: `{"decisao": "aprovado" \| "reprovado", "comentario": "..."}` |
| `GET /precificacoes/{id}/decisoes` | `precificacao.ler` | Lista as decisões da mais recente para a mais antiga |

Respostas de erro: `422` para reprovação sem comentário (a API recusa antes de ir ao banco) ou decisão fora do domínio; `409` quando a precificação não está em aprovação; `404` quando ela não existe ou está fora da carteira de quem decide; `403` sem a permissão.

## Testes

- Banco: `tests/banco/test_decisao_aprovacao.py` (critério de aceite, estado, carteira, guarda de status, imutabilidade, auditoria e histórico).
- API: `apps/api/tests/test_aprovacoes.py`.
