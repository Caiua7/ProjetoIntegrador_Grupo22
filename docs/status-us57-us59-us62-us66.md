# Status das US57, US59, US62 e US66

## US57 — simulação

O cabeçalho cria uma linha persistida em `precificacao` no status `em_preenchimento`. Cliente e produto vêm dos cadastros acessíveis ao usuário. UF de destino, frete e regime tributário são armazenados no cabeçalho, e a listagem mostra dados reais retornados pela API. A migration adiciona os três campos sem invalidar registros anteriores. O cálculo e o detalhamento fiscal continuam ausentes desta etapa.

## US59 — integração com o motor

`POST /calculate` segue documentado e identificado na resposta por `metadata.is_mock=true`. O endpoint não é o motor homologado: o módulo `pricing_core.engine` ainda não existe, e a documentação do contrato mantém três premissas sem homologação. A suíte de conformidade de 30 casos aguarda a homologação com PO. O frontend pode chamar o endpoint usando os tipos gerados, mas não deve apresentar sua resposta como resultado comercial real. Portanto, o critério de aceite da US59 não está cumprido.

## US62 — editor de formulação

O editor foi integrado à `main` pelo PR #93. A issue permanece aberta e os critérios de origem por componente, recálculo reativo e painel de rentabilidade não foram implementados. O contrato atual do motor só recebe um indicador global `material_fornecido_pelo_cliente` e um valor global `valor_material_cliente`; não associa origem e valor a cada item da formulação. Além disso, a resposta do cálculo continua mock. Armazenar origem por item na formulação do produto faria esse dado variar entre clientes dentro de um cadastro global de produto. É necessário modelar esses dados no cenário antes de deduzir valores, e homologar a regra financeira com o PO. Nenhuma dedução financeira foi adicionada.

## US66 — submissão para aprovação

A base de dados ainda não tem entidade de cenário; a tabela `precificacao` só guarda cabeçalho. A issue #63 prevê versionamento de cenários, também ausente, e as issues #67/#68 tratam da fila e da decisão de aprovação. A US66 requer validar completude do cenário, mas não define a lista de campos obrigatórios. Não há regra segura para transição nem cenário persistido para submeter. A implementação foi adiada até que o modelo de cenários/versionamento e os critérios de completude sejam definidos. Nenhuma regra de negócio foi inferida.

## Operação de banco

A migration nova não foi aplicada em nenhum ambiente compartilhado. A revisão de deploy/aplicação deve ocorrer no fluxo normal de revisão, staging e validação do PO.
