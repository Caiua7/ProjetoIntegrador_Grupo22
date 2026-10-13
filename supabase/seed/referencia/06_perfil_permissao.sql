-- Seed: 06_perfil_permissao.sql
-- Perfis (um por persona), permissões nomeadas e a matriz de acesso.
-- Idempotente: pode rodar mais de uma vez sem duplicar nem alterar registros.
--
-- A matriz é a proposta inicial do time, documentada em
-- docs/controle-de-acesso.md; falta a revisão com o PO (RNF09).
-- O seed só ACRESCENTA vínculos: para tirar uma permissão de um perfil,
-- remova a linha daqui e apague o vínculo em perfil_permissao.

INSERT INTO perfil (codigo, nome, descricao) VALUES
    ('analista_pricing',     'Analista de Pricing',     'Forma o preço: cria precificações e cenários e mantém os parâmetros fiscais.'),
    ('executiva_contas',     'Executiva de Contas',     'Negocia com o cliente: consulta clientes e precificações da própria carteira, sem ver custo.'),
    ('gerente_comercial',    'Gerente Comercial',       'Aprova ou reprova precificações da própria carteira e enxerga custo e margem.'),
    ('analista_suprimentos', 'Analista de Suprimentos', 'Mantém os cadastros de insumos e os dados de custo; não acessa clientes nem precificações.'),
    ('administrador',        'Administrador',           'Administra usuários, perfis e carteiras e alcança todas as carteiras.')
ON CONFLICT (codigo) DO UPDATE SET
    nome = EXCLUDED.nome,
    descricao = EXCLUDED.descricao
WHERE (perfil.nome, perfil.descricao) IS DISTINCT FROM (EXCLUDED.nome, EXCLUDED.descricao);

INSERT INTO permissao (codigo, descricao) VALUES
    ('cadastro.ler',            'Consultar cadastros mestres: insumos, produtos, fornecedores, NCM, CEP, municípios e UFs'),
    ('cadastro.editar',         'Incluir e alterar cadastros mestres'),
    ('custo.ler',               'Consultar dados de custo: linhas de produção, taxas de MOD e GGF e produtividade'),
    ('custo.editar',            'Incluir e alterar dados de custo'),
    ('parametro_fiscal.ler',    'Consultar alíquotas por UF, NCM e regime'),
    ('parametro_fiscal.editar', 'Incluir e alterar alíquotas'),
    ('cliente.ler',             'Consultar clientes das carteiras a que tem acesso'),
    ('cliente.editar',          'Incluir e alterar clientes das carteiras a que tem acesso'),
    ('precificacao.ler',        'Consultar precificações das carteiras a que tem acesso'),
    ('precificacao.editar',     'Criar e alterar precificações das carteiras a que tem acesso'),
    ('precificacao.aprovar',    'Aprovar ou reprovar precificações das carteiras a que tem acesso'),
    ('carteira.todas',          'Alcançar todas as carteiras, inclusive clientes sem carteira'),
    ('acesso.administrar',      'Administrar usuários, perfis, permissões e carteiras')
ON CONFLICT (codigo) DO UPDATE SET
    descricao = EXCLUDED.descricao
WHERE permissao.descricao IS DISTINCT FROM EXCLUDED.descricao;

INSERT INTO perfil_permissao (perfil_id, permissao_codigo)
SELECT p.id, m.permissao_codigo
FROM (VALUES
    ('analista_pricing',     'cadastro.ler'),
    ('analista_pricing',     'custo.ler'),
    ('analista_pricing',     'parametro_fiscal.ler'),
    ('analista_pricing',     'parametro_fiscal.editar'),
    ('analista_pricing',     'cliente.ler'),
    ('analista_pricing',     'precificacao.ler'),
    ('analista_pricing',     'precificacao.editar'),

    ('executiva_contas',     'cadastro.ler'),
    ('executiva_contas',     'cliente.ler'),
    ('executiva_contas',     'precificacao.ler'),

    ('gerente_comercial',    'cadastro.ler'),
    ('gerente_comercial',    'custo.ler'),
    ('gerente_comercial',    'parametro_fiscal.ler'),
    ('gerente_comercial',    'cliente.ler'),
    ('gerente_comercial',    'precificacao.ler'),
    ('gerente_comercial',    'precificacao.aprovar'),

    ('analista_suprimentos', 'cadastro.ler'),
    ('analista_suprimentos', 'cadastro.editar'),
    ('analista_suprimentos', 'custo.ler'),
    ('analista_suprimentos', 'custo.editar'),

    ('administrador',        'cadastro.ler'),
    ('administrador',        'cadastro.editar'),
    ('administrador',        'custo.ler'),
    ('administrador',        'custo.editar'),
    ('administrador',        'parametro_fiscal.ler'),
    ('administrador',        'parametro_fiscal.editar'),
    ('administrador',        'cliente.ler'),
    ('administrador',        'cliente.editar'),
    ('administrador',        'precificacao.ler'),
    ('administrador',        'carteira.todas'),
    ('administrador',        'acesso.administrar')
) AS m (perfil_codigo, permissao_codigo)
JOIN perfil p ON p.codigo = m.perfil_codigo
ON CONFLICT (perfil_id, permissao_codigo) DO NOTHING;
