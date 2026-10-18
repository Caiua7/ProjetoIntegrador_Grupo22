# Cotação de matéria-prima

Cotação de MP por fornecedor, com moeda, validade, prazo de entrega e faixa de volume mínimo (US25, RF12). Alimenta o custo de MP do motor de preço.

Migration: `supabase/migrations/20261018000001_criar_cotacao.sql`. Domínio: `packages/pricing-core/src/pricing_core/cotacao.py`. API: `apps/api/app/routers/cotacoes.py`.

## Modelo

| Coluna | Significado |
| :--- | :--- |
| `materia_prima_id`, `fornecedor_id` | Quem cotou o quê |
| `moeda`, `preco` | Preço por unidade da MP, na moeda da cotação (ISO de 3 letras). A conversão para BRL é do câmbio (US13) |
| `volume_minimo` | Limite inferior da faixa, inclusive. A faixa vai até o mínimo da próxima; a última é aberta |
| `validade_inicio`, `validade_fim` | Período de vigência, ambos inclusivos. `validade_fim` nulo = sem fim |
| `prazo_entrega_dias` | Prazo de entrega informado pelo fornecedor |
| `ativo` | Cotação não se apaga: inativa-se |

Faixas 0–100 kg e 101–500 kg são duas cotações, com `volume_minimo` 0 e 101.

## Garantias do banco

- Não existem duas cotações ativas do mesmo fornecedor, MP e faixa com vigências sobrepostas (constraint de exclusão `cotacao_sem_sobreposicao`).
- Preço, volume mínimo e prazo não negativos; fim de validade não anterior ao início.
- RLS: `custo.ler` lê, `custo.editar` grava. Sem `DELETE`. Auditoria habilitada.

## Cotações vigentes

```sql
SELECT * FROM cotacoes_vigentes('<id da MP>', DATE '2026-10-18');
```

Devolve as cotações ativas vigentes na data, da menor para a maior faixa.

## Resolução pela faixa de volume

`resolver_cotacao(cotacoes, materia_prima_id, quantidade, data_referencia, fornecedor_id=None)`, nesta ordem:

1. Entram só as cotações da MP vigentes na data (e do fornecedor, se informado).
2. Vence a faixa de maior `volume_minimo` que não passa da quantidade. 101 kg já está na segunda faixa; 100,5 kg ainda está na primeira.
3. Na mesma faixa, desempata o início de validade mais recente.
4. Se ainda empatar (tipicamente dois fornecedores), levanta `CotacaoAmbigua` e o chamador informa o `fornecedor_id`. Não se escolhe pelo menor preço porque isso exigiria câmbio entre moedas (US13).

A faixa é decidida antes da validade e a comparação vale entre fornecedores: se o fornecedor A tem faixa de 101 e o B só tem a faixa 0, a quantidade 250 resolve para o A.

Sem cotação vigente, ou com quantidade abaixo do menor mínimo vigente, levanta `CotacaoNaoEncontrada`. Quantidade deve ser positiva.

## Endpoints (permissão `custo.ler`)

| Rota | Resposta |
| :--- | :--- |
| `GET /cotacoes/vigentes?materia_prima_id=&data_referencia=` | Cotações vigentes da MP, da menor para a maior faixa |
| `GET /cotacoes/resolver?materia_prima_id=&quantidade=&data_referencia=&fornecedor_id=` | Cotação aplicável. `404` sem cotação vigente ou abaixo do menor mínimo; `409` em empate |

`data_referencia` assume hoje quando omitida. `preco` e `volume_minimo` trafegam como string, como os demais valores `Decimal` da API.