# Contrato do motor — `POST /calculate`

Entregável da tarefa "Definir e versionar o contrato do motor" (Sprint 1,
semanas 1 e 2 — Victor e Mateus). Sem isso o Squad B ficaria bloqueado até
o motor real (US16/US19, Sprint 3).

## Onde está cada coisa

| O quê | Onde |
| :--- | :--- |
| Schemas Pydantic (fonte da verdade) | `packages/pricing-core/src/pricing_core/contracts.py` |
| Endpoint mock para o Squad B | `apps/api/app/routers/calculate.py` |
| Tipos TypeScript para o front | `apps/web/src/types/calculate.generated.ts` |
| Script para regenerar os tipos TS | `scripts/generate_ts_types.py` |
| Script para exportar o OpenAPI versionado | `scripts/export_openapi.py` |
| Scaffold da homologação dos 30 casos | `tests/conformidade/` |

## Decisão de forma: por que Decimal-como-string

Todo campo monetário/percentual é `decimal.Decimal` no back-end, mas
trafega como `string` em JSON (`DecimalComoString` em `contracts.py`, via
`PlainSerializer`). Isso evita o problema clássico de `JSON.parse` em JS
converter para `number` de ponto flutuante e perder precisão — o mesmo
motivo pelo qual o motor usa `Decimal` em vez de `float` (README.md,
seção "Arquitetura"). O front-end deve tratar esses campos com uma lib
decimal (ex.: `decimal.js`), nunca com `Number()` direto.

## O que o mock faz e o que ele não é

O endpoint `/calculate` já implementa a cadeia de fórmulas da seção 2.3
do planejamento de produto, então os números devolvidos têm magnitude
realista (úteis para desenhar telas, formatar moeda, montar gráficos).
Mas `CalculateMetadata.is_mock` vem sempre `true`, porque três pontos da
especificação são ambíguos e foram resolvidos aqui por suposição, não por
homologação:

1. `Base` em `m × Base` — assumida como `CustoTotal`.
2. `Comissao$` — assumida como `Comissao × PB`.
3. `MaterialCliente` (usado em `CustoPerda`) e `CustoEnviadoCliente`
   (usado em `PBsIPIsEncargo`) — assumidos como o mesmo valor.

Essas suposições não afetam a **forma** do contrato (os campos e tipos
abaixo não mudam), só a fórmula por trás. Elas devem ser confirmadas na
sessão de homologação dos 30 casos com o PO — ver
`tests/conformidade/README.md`.

O mock também já implementa o caso de erro do RNF08: se o denominador `D`
da fórmula de preço for `<= 0`, a API responde `422` com
`DomainErrorResponse` (código `DENOMINADOR_INVALIDO`), não uma exceção
genérica.

## Rodando localmente

```bash
cd apps/api
pip install -e ../../packages/pricing-core fastapi uvicorn
uvicorn app.main:app --reload
# POST http://localhost:8000/calculate
# Schema interativo em http://localhost:8000/docs
```

## Quando o contrato mudar

1. Edite `contracts.py` (única fonte da verdade).
2. Rode `python scripts/generate_ts_types.py` para atualizar o `.ts`.
3. Rode `python scripts/export_openapi.py` para atualizar o JSON versionado
   em `docs/openapi/` — assim o PR mostra o diff do schema.
4. Bata a versão em `ENGINE_CONTRACT_VERSION` se a mudança for de formato
   ou de fórmula (fica registrada em `CalculateMetadata.versao_motor` e,
   mais adiante, no cenário persistido — RF09).

## Próximo passo (Sprint 3 — US16/US19)

Implementar `pricing_core/engine.py` com `calcular(entrada: CalculateRequest) -> CalculateResponse`
usando a lógica já homologada (não mais as suposições do mock), e trocar
o endpoint em `apps/api/app/routers/calculate.py` para chamá-lo com
`is_mock=False`. A suíte em `tests/conformidade/` já está pronta para
validar essa implementação assim que `pricing_core.engine` existir.
