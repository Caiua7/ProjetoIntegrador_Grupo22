# Contrato do motor — `POST /calculate`

## Fonte da verdade

| Conteúdo | Local |
| --- | --- |
| Schemas Pydantic e versão do contrato | `packages/pricing-core/src/pricing_core/contracts.py` |
| Endpoint e tradução de erro de domínio | `apps/api/app/routers/calculate.py` |
| Motor puro | `packages/pricing-core/src/pricing_core/engine.py` |
| Tipos usados pelo frontend | `apps/web/src/types/calculate.generated.ts` |

O endpoint exige autenticação e permissão `precificacao.ler`, e executa `pricing_core.engine.calcular`. Usuários com `custo.ler` recebem a resposta completa; os demais recebem preços, ROL, impostos destacados e metadata, sem custos, encargos, isenção de mão de obra ou margens. Erros de domínio são respondidos como HTTP 422 com `codigo`, `mensagem` e `detalhes`.

## Formato e precisão

Campos monetários e percentuais são decimais serializados como strings. Percentuais são frações (`0.18` representa 18%). O frontend deve enviar os campos conforme `CalculateRequest` e exibir os valores retornados sem reimplementar fórmulas. A resposta inclui custos, `PBsIPIsEncargo`, `PBsIPI`, `PBcIPI`, `PB`, `ROL`, `MaCo`, isenção de mão de obra e impostos destacados.

## Pendências de homologação

O motor implementa premissas provisórias ainda marcadas `TODO(PO)`:

1. `Base = CustoTotal` para a parcela de margem;
2. `Comissao$ = Comissao × PB`;
3. `MaterialCliente = CustoEnviadoCliente = valor_material_cliente`.

As bases usadas para destacar impostos também aguardam confirmação do PO. Portanto, `is_mock=false` significa que o código chama o motor implementado, não que as fórmulas já foram homologadas comercialmente. Os casos oficiais de conformidade e validação PO continuam necessários.

## Preço líquido de matéria-prima

`pricing_core.preco_liquido_mp` existe, mas não integra a cadeia de `engine.calcular`. O motor atual calcula custo de MP a partir de preço negociado, câmbio, margem de segurança e quantidade. Para aplicar créditos recuperáveis seriam necessárias as alíquotas de aquisição e flags de recuperabilidade por fornecedor/origem. Esses dados não fazem parte de `ItemInsumo` nem das cotações atuais. Não derive a recuperabilidade do regime tributário do cliente.

## Persistência de cenários

`POST /precificacoes/{precificacao_id}/cenarios` recebe `{ entrada, volume?, observacao? }`, calcula novamente no backend e persiste entrada, resultado e versão do motor. O cliente não envia preço calculado para persistência. O backend rejeita com HTTP 409 qualquer resultado que o próprio motor marque como mock. A confirmação da gravação também filtra custos e margem para quem não tem `custo.ler`. As rotas de consulta de detalhes e comparação exigem custo; a visão `/precos` mantém os preços para usuários com `precificacao.ler`. Volume habilita indicadores de rentabilidade absoluta.

## Demonstração explícita

`POST /calculate/demo` recebe `{ dados: { ... } }` e é habilitado somente com `DEMO_CALCULATION_ENABLED=true`. Campos ausentes são preenchidos por premissas deliberadamente demonstrativas em `app/services/demo_calculator.py`, sobrescrevíveis pela configuração `DEMO_CALCULATION_DEFAULTS_JSON`. A resposta sempre tem `metadata.is_mock=true`, `origem=demonstracao`, classificação e lista das premissas aplicadas. Dados recebidos do cliente são sinalizados como não verificados. O endpoint não persiste; a RPC de persistência aceita somente proveniência real validada no próprio banco.

## Benchmark local

`apps/api/scripts/benchmark_calculate.py --iterations 1000` mede o motor puro com o caso oficial `caso_000_template.json`, incluindo aquecimento e p50/p95/p99. O microbenchmark não mede rede, API ou banco e não substitui benchmark de carga.
