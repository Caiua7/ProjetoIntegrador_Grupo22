-- Administrador global: alcança todas as funções do sistema.
--
-- Até aqui o administrador não tinha precificacao.editar nem precificacao.aprovar
-- (criar, calcular, submeter e decidir ficavam só com o analista e o gerente).
-- Decisão do grupo: o administrador é global e faz tudo o que qualquer cargo faz.
-- Liga ao perfil todas as permissões que existem hoje; as rotas, o RLS e o
-- conector MCP passam a liberar as ações automaticamente.

INSERT INTO perfil_permissao (perfil_id, permissao_codigo)
SELECT p.id, perm.codigo
FROM perfil p
CROSS JOIN permissao perm
WHERE p.codigo = 'administrador'
ON CONFLICT (perfil_id, permissao_codigo) DO NOTHING;
