# Status das issues #57, #59, #62 e #66 após os merges

## #59 — integração do motor

`POST /calculate` delega a `pricing_core.engine.calcular`, devolve `metadata.is_mock=false` e traduz `ErroDominioPricing` em HTTP 422 com código, mensagem e detalhes. A versão atual do contrato é `0.2.0`. O frontend agora permite enviar uma entrada `CalculateRequest` completa, exibe custos, PBsIPIsEncargo, PBsIPI, PBcIPI, PB, ROL, MaCo e impostos destacados; erros HTTP e JSON inválido aparecem junto ao formulário.

O resultado pode ser persistido como nova versão via `POST /precificacoes/{id}/cenarios`, que recalcula no backend e guarda entrada e resultado. Respostas marcadas `is_mock=true` são identificadas e não podem ser persistidas pelo fluxo da interface. Não há regra de cálculo no frontend.

O motor ainda contém três premissas `TODO(PO)` e interpretação das bases de impostos destacados pendente de confirmação. A conformidade comercial exige homologação dos casos oficiais com o PO.

## #57 — simulação

A simulação real está conectada à API e pode gerar uma nova versão persistida, com volume e observação opcionais. O histórico existente recupera versões, resultados, impostos, custos e rentabilidade por volume.

A composição automática da entrada ainda não é possível: o cabeçalho e a formulação não fornecem todos os valores de entrada do motor. O formulário recebe o objeto do contrato explicitamente até que exista um contrato que associe composição, cotações, parâmetros de produção e regras fiscais ao cenário.

## #62 — editor de formulação

O editor lê e salva a formulação real do produto. Ele ainda não recalcula automaticamente: itens guardam quantidade e referência de insumo, mas não carregam cotação selecionada, câmbio, margem de segurança, origem fiscal individual nem dados de produção.

`pricing_core.preco_liquido_mp` não participa do fluxo real. O motor chama `calcular_custo_mp` usando preço negociado, câmbio, margem de segurança e quantidade. A função de preço líquido exige alíquotas e flags de recuperação de crédito; o contrato `ItemInsumo` não possui essas informações, e as cotações não identificam por si só a recuperabilidade dos tributos. Integrá-la requer campos/regra homologada para alíquotas de compra e recuperação por fornecedor/origem. Não se deve inferir essas flags do regime do cliente.

Para habilitar a origem por matéria-prima, o contrato do cenário precisa carregar origem e valor fornecido pelo cliente por item, além da política para a mesma matéria-prima variar por cliente. Hoje o motor só recebe `material_fornecido_pelo_cliente` e `valor_material_cliente` globais.

## #66 — submissão para aprovação

Ainda não há rota para transicionar `em_preenchimento` para `em_aprovacao`; a migração de decisões declara explicitamente que a submissão pertence à US35/#66. A interface não simula essa transição nem desbloqueia edição sem suporte do backend. A completude obrigatória também não está definida.

As decisões do PR #109 estão conectadas: usuários com `precificacao.aprovar` podem aprovar ou reprovar registros já `em_aprovacao`; reprovar exige comentário, e status/erros vêm do endpoint e da regra do banco.

## Outras integrações e dados de demonstração

As telas de câmbio/parâmetros, formulações, alíquotas, precificações e histórico usam endpoints reais disponíveis. Cotações têm endpoints reais de consulta, mas ainda não há tela de cotações conectada ao fluxo.

Dashboard, alertas, gráficos e listas de atividade continuam usando fixtures em `pricingList.mock.ts` e `dashboard.data.ts`, porque não existe endpoint agregado correspondente. O código do dashboard identifica os dados como demonstração.
