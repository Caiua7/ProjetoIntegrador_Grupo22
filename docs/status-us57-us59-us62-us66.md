# Entregas #57, #59, #62 e #66

## #59 — motor, permissões e proveniência

`POST /calculate` executa o motor real. Sem `custo.ler`, a resposta omite custo de MP, embalagem, perdas, MOD, GGF, custo total e margem; mantém os preços autorizados por `precificacao.ler`. A API de persistência recalcula no servidor e encaminha o identificador do usuário autenticado a uma RPC restrita a `service_role`. A função no banco valida ator, permissão, carteira e proveniência `is_mock=false`/`origem=pricing_core`; inserções diretas da aplicação são revogadas.

`POST /calculate/demo` só está disponível com `DEMO_CALCULATION_ENABLED=true`. Premissas padrão e possíveis sobrescritas ficam centralizadas em `app/services/demo_calculator.py` e `DEMO_CALCULATION_DEFAULTS_JSON`. A resposta sempre marca origem demonstrativa, lista parâmetros preenchidos por padrão e sinaliza dados recebidos não verificados. O endpoint não persiste resultados.

## #57 — formulário de simulação

O painel monta uma entrada real com os campos que têm correspondência inequívoca nas APIs atuais, incluindo cabeçalho e formulação. Campos sem fonte segura são listados como pendências; salvar formulação dispara recálculo real apenas se a entrada estiver completa. Para explorar uma entrada incompleta existe o endpoint de demonstração explicitamente marcado. Salvar cenário segue criando uma nova versão e recalculando no backend.

Continuam pendentes contratos/origens para cotação de embalagem, margem de segurança por item, parâmetros de produção, premissas comerciais, impostos de aquisição e recuperação de crédito. O motor representa origem de material globalmente, enquanto a formulação a registra por item; reduzir origens mistas ao contrato atual só é permitido no modo demonstrativo.

## #62 — editor de formulação

O editor permite informar origem `fabricante`/`cliente` por item e persiste essa informação em coluna aditiva. Formulações antigas permanecem com origem nula até serem revisadas; não se presume a origem. A rentabilidade continua sendo apresentada a partir de resultados persistidos do motor e só a usuários com `custo.ler`.

Decisões pendentes: valor de material fornecido pelo cliente por item; semântica para formulações com origens mistas no motor; alíquotas e recuperabilidade fiscal por fornecedor/origem. O contrato atual não inclui esses dados, e o regime do cliente não é usado para inferi-los.

## #66 — submissão

Há rotas de verificação e submissão, histórico de mudança de status e proteção no banco. A política é configurável em `politica_submissao`, mas o registro inicial está explicitamente como `demonstracao`, exige campos do cabeçalho e um cenário real e marca `homologacao_pendente`. A aprovação fica bloqueada nessa condição; aprovar/reprovar continuam separados da submissão.

O modo demonstrativo não representa critérios de completude aprovados pelo PO. Para produção, PO/backend devem revisar os campos obrigatórios, cenário exigido e modo `homologada`, e então ajustar a política com credencial de serviço. Não há endpoint administrativo exposto à aplicação.

## Dashboard e cotações

Use somente os dados reais já disponíveis nas APIs de precificações, formulação, cotações, parâmetros e impostos com as permissões correspondentes. Séries históricas, alertas e indicadores sem contrato agregado continuam fora do dashboard real. Cotações só são usadas quando o resolvedor existente determina uma cotação inequívoca e compatível; não definem origem fiscal nem recuperação tributária.
