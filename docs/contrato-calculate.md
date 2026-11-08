# Contrato do motor — `POST /calculate`

## Fonte da verdade

| Conteúdo | Local |
| --- | --- |
| Schemas Pydantic e versão do contrato | `packages/pricing-core/src/pricing_core/contracts.py` |
| Endpoint e tradução de erro de domínio | `apps/api/app/routers/calculate.py` |
| Motor puro | `packages/pricing-core/src/pricing_core/engine.py` |
| Tipos usados pelo frontend | `apps/web/src/types/calculate.generated.ts` |

O endpoint executa `pricing_core.engine.calcular`. A resposta informa `metadata.is_mock=false` e registra a versão do motor. Erros de domínio são respondidos como HTTP 422 com `codigo`, `mensagem` e `detalhes`.

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

`POST /precificacoes/{precificacao_id}/cenarios` recebe `{ entrada, volume?, observacao? }`, calcula novamente no backend e persiste entrada, resultado e versão do motor. O cliente não envia preço calculado para persistência. As rotas de consulta e duplicação recuperam e versionam cenários; volume habilita indicadores de rentabilidade absoluta.
