# Status das issues #57, #59, #62 e #66 após os merges

## #59 — integração do motor

`POST /calculate` exige autenticação e `precificacao.ler`, delega ao motor real e converte erros de domínio em HTTP 422. Sem `custo.ler`, a API devolve somente preços, ROL, impostos destacados e metadata; campos de custos, encargos, margem e denominadores internos são omitidos. A gravação do cenário também retorna uma projeção sem entrada, custos ou margens. Preços continuam disponíveis conforme a permissão de precificação.

`POST /precificacoes/{id}/cenarios` recalcula no backend e persiste a nova versão. A decisão de persistir usa `metadata.is_mock` do resultado produzido pelo motor no servidor, e não uma flag recebida do navegador; resultado mock é recusado com HTTP 409. Não foi necessária migração de banco. O motor ainda contém três premissas `TODO(PO)` e a interpretação das bases de impostos destacados precisa de homologação do PO.

## #57 — simulação

A tela pode preparar uma entrada a partir das APIs disponíveis, além de aceitar edição manual dos campos pendentes. Os mapeamentos automáticos são: UF, modalidade e regime do cabeçalho; itens e quantidades da formulação; NCM do produto; cotações de matéria-prima apenas quando unidade compatível, volume informado e resolvedor encontra uma cotação inequívoca; câmbio vigente para moedas estrangeiras; parâmetros globais de perda, taxa financeira e prazo; e alíquotas de venda resolvidas por UF, NCM e regime. O cálculo continua exclusivamente no motor e salvar cria nova versão com recálculo no backend.

Permanecem pendentes: cotação/preço de embalagem; margem de segurança por item; parâmetros MOD, GGF, produtividade e funcionários; margem desejada, comissão e frete percentual; confirmação de como perda percentual da formulação se relaciona ao descarte de embalagem; informação sobre material fornecido pelo cliente e seu valor. O contrato atual não dá origem nem valor fornecido por item. Dados sem correspondência segura são deixados vazios e listados para preenchimento, sem valores presumidos. Permissões de leitura de custos, câmbio, parâmetros globais e fiscais condicionam o preenchimento dos respectivos dados.

## #62 — editor de formulação

O editor lê e salva a formulação real. Também permite abrir uma precificação existente para ver o histórico e a rentabilidade calculada pelo motor; custos e margens só são apresentados a quem tem `custo.ler`.

`pricing_core.preco_liquido_mp` não participa do fluxo real. O motor usa preço negociado, câmbio, margem de segurança e quantidade. O contrato `ItemInsumo` não possui alíquotas de compra nem flags de recuperação de crédito. Integrar preço líquido exige definir alíquotas e recuperabilidade por fornecedor/origem; não se infere isso do regime tributário do cliente. Origem e valor de material fornecido pelo cliente também exigem extensão compatível do contrato e uma regra para variação por item.

## #66 — submissão para aprovação

Não há rota para transicionar `em_preenchimento` para `em_aprovacao`, e a completude obrigatória não está definida. A migração de decisões existente atribui a submissão à US35/#66. Não foi criada validação fictícia nem ação de submissão. A integração frontend/backend depende da rota e dos critérios de completude definidos pelo PO/backend. Aprovar e reprovar permanecem operações distintas e já conectadas para registros em aprovação; reprovar exige comentário.

## Outras integrações e dados demonstrativos

Dashboard agora consulta precificações reais e mostra contagens por status e registros recentes. Gráficos, alertas e fixtures antigos não são renderizados. Não há endpoint agregado nem base autorizada suficiente para séries mensais, alertas de margem ou receita operacional bruta; esses indicadores não são apresentados como dados reais.

Cotações podem alimentar preço de matéria-prima na simulação apenas pelo resolvedor existente, quando unidade, volume, vigência e resultado são inequívocos. Não há contrato de cotação de embalagem, e cotações não definem origem fiscal nem recuperabilidade de tributos. Parâmetros globais e alíquotas de venda são usados somente quando as APIs retornam dado vigente e o usuário tem a permissão de leitura correspondente.
