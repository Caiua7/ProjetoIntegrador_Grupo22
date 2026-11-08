# Implantação das migrations de integração e workflow

Aplicar em ordem, depois da migration de submissão já existente (`20261108000001`):

1. `20261108000002_proteger_gravacao_cenario.sql`
2. `20261108000003_submissao_precificacao_demo.sql`
3. `20261108000004_origem_formulacao_item.sql`

As funções `salvar_cenario_seguro`, `avaliar_submissao_precificacao` e `submeter_precificacao` são executadas pelo backend usando `service_role`; as migrations revogam execução de `anon`/`authenticated`. A função de salvamento recebe o ator como argumento, mas valida no banco permissão, carteira, status e proveniência real antes de gravar. A aplicação não deve expor a chave de serviço ao navegador.

Após aplicar as migrations, atualizar o schema cache do PostgREST/Supabase e implantar API e frontend compatíveis. Antes de liberar, conferir que o cliente autenticado não executa as RPCs privilegiadas nem insere diretamente em `cenario`; verificar a gravação pelo backend com ator/auditoria; validar que chamadas ao endpoint demo estão desativadas por padrão; e validar a avaliação/submissão com a política demonstrativa. A política pode ser alterada apenas por operador autorizado via banco, até existir um fluxo administrativo especificado.

A migration de origem é aditiva e mantém `NULL` para itens legados. O editor exige que itens sem origem sejam revisados antes de salvar nova formulação.
