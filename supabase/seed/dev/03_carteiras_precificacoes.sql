-- Seed de DESENVOLVIMENTO: 03_carteiras_precificacoes.sql
-- Carteiras, clientes/produtos fictícios e precificações de demonstração
-- para testes locais. Os valores fiscais/comerciais também são fixtures e
-- não representam negociações reais.
-- Idempotente: pode rodar mais de uma vez sem duplicar nem alterar registros.
--
-- Não cria usuários: `usuario.id` precisa ser o id de um usuário real do
-- Supabase Auth (ver docs/controle-de-acesso.md).

INSERT INTO carteira (codigo, nome) VALUES
    ('CART-SUDESTE',    'Carteira Sudeste'),
    ('CART-SUL',        'Carteira Sul'),
    ('CART-EXPORTACAO', 'Carteira Exportação')
ON CONFLICT (codigo) DO UPDATE SET
    nome = EXCLUDED.nome
WHERE carteira.nome IS DISTINCT FROM EXCLUDED.nome;

UPDATE cliente c
SET carteira_id = ca.id
FROM (VALUES
    ('CLI-0001', 'CART-SUDESTE'),
    ('CLI-0002', 'CART-SUDESTE'),
    ('CLI-0003', 'CART-EXPORTACAO'),
    ('CLI-0004', 'CART-SUL'),
    ('CLI-0005', 'CART-SUDESTE')
) AS v (cliente_codigo, carteira_codigo)
JOIN carteira ca ON ca.codigo = v.carteira_codigo
WHERE c.codigo = v.cliente_codigo
  AND c.carteira_id IS DISTINCT FROM ca.id;

INSERT INTO precificacao (
    codigo, cliente_id, produto_id, modalidade_comercial, status,
    uf_destino, frete, regime_tributario
)
SELECT v.codigo, c.id, p.id, v.modalidade_comercial, v.status,
       COALESCE(c.uf_sigla, 'EX'), 'cif', COALESCE(c.regime_tributario, 'lucro_real')
FROM (VALUES
    ('PRC-2026-0148', 'CLI-0001', 'PA-0001', 'full_service_nacional',          'em_aprovacao'),
    ('PRC-2026-0147', 'CLI-0002', 'PA-0003', 'full_service_nacional',          'em_aprovacao'),
    ('PRC-2026-0146', 'CLI-0003', 'PA-0002', 'full_service_exportacao',        'aprovado'),
    ('PRC-2026-0145', 'CLI-0004', 'PA-0004', 'industrializacao_por_encomenda', 'reprovado'),
    ('PRC-2026-0144', 'CLI-0001', 'PA-0005', 'full_service_nacional',          'em_preenchimento'),
    ('PRC-2026-0143', 'CLI-0002', 'PA-0006', 'full_service_nacional',          'aprovado'),
    ('PRC-2026-0142', 'CLI-0005', 'PA-0007', 'full_service_nacional',          'aprovado')
) AS v (codigo, cliente_codigo, produto_codigo, modalidade_comercial, status)
JOIN cliente c ON c.codigo = v.cliente_codigo
JOIN produto p ON p.codigo = v.produto_codigo
ON CONFLICT (codigo) DO UPDATE SET
    cliente_id = EXCLUDED.cliente_id,
    produto_id = EXCLUDED.produto_id,
    modalidade_comercial = EXCLUDED.modalidade_comercial,
    status = EXCLUDED.status,
    uf_destino = EXCLUDED.uf_destino,
    frete = EXCLUDED.frete,
    regime_tributario = EXCLUDED.regime_tributario
WHERE (precificacao.cliente_id, precificacao.produto_id, precificacao.modalidade_comercial, precificacao.status,
       precificacao.uf_destino, precificacao.frete, precificacao.regime_tributario)
    IS DISTINCT FROM (EXCLUDED.cliente_id, EXCLUDED.produto_id, EXCLUDED.modalidade_comercial, EXCLUDED.status,
                      EXCLUDED.uf_destino, EXCLUDED.frete, EXCLUDED.regime_tributario);
