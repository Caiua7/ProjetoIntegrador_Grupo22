# Registro de avanço — 05/11/2026

## Estado do repositório

- O trabalho parte do `origin/main` no commit `4b574ab`, que já contém o salvamento atômico da US62 (`2a41d06`) e os merges recentes.
- A implementação está isolada na branch `feature/us62-cenarios-e-integracao-ui`.
- O banco local não estava acessível durante esta sessão: o CLI `supabase` não está instalado e a porta local `127.0.0.1:54322` não respondeu. Não foi possível verificar a tabela de histórico de migrations nem aplicar migrations.

## Entregue nesta etapa

- A lista de precificações abre o histórico real de cenários por precificação.
- A tela consome as rotas existentes de lista para usuários com e sem `custo.ler`, detalhes, comparação e duplicação.
- A versão vigente, o volume, preços, indicadores e variações vêm da API. A comparação exibe percentuais como porcentagens e diferenças de margem como pontos percentuais sem converter os valores decimais para `Number`.
- Detalhes respeitam `custo.ler`. Resultados que carregam `metadata.is_mock` são identificados como demonstrativos.
- A duplicação só aparece para quem tem `precificacao.editar`.

## Migrations novas revisadas

- `20261103000001_completar_cabecalho_precificacao.sql` altera `precificacao`, criada pela migration base de 12/10.
- `20261103120001_importar_aliquotas.sql` depende de `aliquota_fiscal` e das funcoes de sessao/permissao criadas nas migrations base.
- `20261103130001_criar_cambio_parametros_globais.sql` cria as tabelas historicas e usa as funcoes de auditoria, sessao e permissao existentes.
- `20261104000001_criar_cenario_versionado.sql` depende de `precificacao`, `usuario_tem_permissao` e `usuario_acessa_cliente`.
- A ordem pelo timestamp respeita essas dependencias. A verificacao contra `supabase_migrations.schema_migrations` e a aplicacao local continuam pendentes porque o Supabase local nao esta disponivel.

## Bloqueios sem regra inventada

- **US62 — origem por componente e custo na formulação:** `formulacao_item` não tem campo de origem; o contrato de cálculo guarda `material_fornecido_pelo_cliente` e `valor_material_cliente` uma única vez no cenário. Não há regra que associe essa dedução global a itens individuais. O cadastro de insumos também não fornece ao editor um conjunto completo de preço, câmbio, margem e descarte para montar `ItemInsumo`; os parâmetros MOD/GGF não estão ligados à tela. A origem por item e o painel de custo da fórmula aguardam contrato e dados de cálculo definidos.
- **US57 — criar cenário pela tela:** o backend aceita entrada completa de cálculo, mas a tela de criação só coleta cabeçalho comercial. Ainda não existe mapeamento implementado e validado para preço/câmbio, produção, tributos e parâmetros comerciais. O histórico pode consultar cenários existentes; não gera um cálculo real a partir do cabeçalho.
- **US66 — submissão:** o banco conhece `em_preenchimento`, `em_aprovacao`, `aprovado` e `reprovado`, mas a documentação de acesso reserva as transições ao workflow de aprovação. Critérios de completude e transições ainda não estão definidos para a US66; aprovação/rejeição também pertencem às US67/US68.
- **US59 — motor:** `/calculate` e as versões salvas continuam carregando o indicador de mock. O motor homologado e a suíte de conformidade dependem da resolução das premissas do contrato com PO e da entrega compartilhada da US59.

## Validações

- Frontend: `npm.cmd test` — 27 testes passaram (inclui os testes de caminhos dos endpoints de cenários).
- Frontend: `npm.cmd run lint` — passou.
- Frontend: `npm.cmd run build` — passou.
- API, pricing-core, Ruff e testes de banco não puderam ser executados: o executável Python configurado pelo `.venv` aponta para uma instalação inexistente (`C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`), e não há `py`, `python` ou `ruff` disponíveis no PATH.
- Não houve conexão nem aplicação de migrations em staging ou produção.

## Próximas ações independentes

1. Restaurar uma instalação Python compatível e refazer testes de API, pricing-core, banco e Ruff.
2. Iniciar o Supabase local, confirmar o histórico de migrations e aplicar nele as migrations pendentes.
3. Adicionar cenários de demonstração em ambiente local e revisar a tela de histórico com perfis com e sem `custo.ler`.
4. Com os contratos de preços e custos disponíveis, integrar a fórmula do produto ao `pricing-core` sem transferir origem individual para o cadastro global.

## Alinhamentos necessários

- PO: resolver as premissas financeiras e confirmar critérios de completude/submissão.
- Responsáveis pelas US59/US62: confirmar o contrato do motor, a entrada por item e como custo fornecido pelo cliente se relaciona com os componentes.
- Equipe: confirmar o fluxo de geração de cenários pela tela e os parâmetros vigentes que devem ser congelados em cada versão.
