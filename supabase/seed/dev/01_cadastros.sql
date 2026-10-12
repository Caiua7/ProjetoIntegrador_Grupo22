-- Seed de DESENVOLVIMENTO: 01_cadastros.sql
-- Fornecedores, matérias-primas, embalagens, produtos, linhas de produção,
-- produtividade e clientes do segmento de suplementos, espelhando os dados
-- do protótipo (prototipo/neoprice-prototipo.html).
-- Idempotente: pode rodar mais de uma vez sem duplicar nem alterar registros.
--
-- ATENÇÃO — dados fictícios, só para desenvolvimento e demo. Clientes,
-- taxas e produtividades são inventados; o NCM de cada insumo é uma
-- classificação plausível, não validada pela área fiscal. Não aplicar em
-- produção.

-- ------------------------------------------------------------
-- Fornecedores
-- ------------------------------------------------------------
INSERT INTO fornecedor (codigo, razao_social, nome_fantasia, pais, uf_sigla) VALUES
    ('FOR-0001', 'Glanbia Nutritionals',          'Glanbia',         'IE', NULL),
    ('FOR-0002', 'Alibra Ingredientes Ltda',      'Alibra',          'BR', 'SP'),
    ('FOR-0003', 'Barry Callebaut Brasil',        'Barry Callebaut', 'BR', NULL),
    ('FOR-0004', 'AlzChem Trostberg GmbH',        'AlzChem',         'DE', NULL),
    ('FOR-0005', 'Tate & Lyle PLC',               'Tate & Lyle',     'GB', NULL),
    ('FOR-0006', 'Amano Enzyme Inc.',             'Amano Enzyme',    'JP', NULL),
    ('FOR-0007', 'Ingredion Brasil',              'Ingredion',       'BR', 'SP'),
    ('FOR-0008', 'Embalplast Embalagens Ltda',    'Embalplast',      'BR', 'SP'),
    ('FOR-0009', 'Etiqprint Rótulos Ltda',        'Etiqprint',       'BR', 'SP')
ON CONFLICT (codigo) DO UPDATE SET
    razao_social = EXCLUDED.razao_social,
    nome_fantasia = EXCLUDED.nome_fantasia,
    pais = EXCLUDED.pais,
    uf_sigla = EXCLUDED.uf_sigla
WHERE (fornecedor.razao_social, fornecedor.nome_fantasia, fornecedor.pais, fornecedor.uf_sigla)
    IS DISTINCT FROM (EXCLUDED.razao_social, EXCLUDED.nome_fantasia, EXCLUDED.pais, EXCLUDED.uf_sigla);

-- ------------------------------------------------------------
-- Matérias-primas
-- ------------------------------------------------------------
INSERT INTO materia_prima (codigo, descricao, unidade_medida, ncm_codigo) VALUES
    ('MP-0001', 'Whey protein concentrado 80%',           'kg', '04041000'),
    ('MP-0002', 'Whey protein isolado 90%',               'kg', '35022000'),
    ('MP-0003', 'Creatina monoidratada micronizada',      'kg', '29252990'),
    ('MP-0004', 'Cacau alcalino 10/12',                   'kg', '18050000'),
    ('MP-0005', 'Sucralose 25%',                          'kg', '29321400'),
    ('MP-0006', 'Maltodextrina DE 18',                    'kg', '17029000'),
    ('MP-0007', 'Colágeno hidrolisado',                   'kg', '35040090'),
    ('MP-0008', 'BCAA 2:1:1 instantâneo',                 'kg', '29224990'),
    ('MP-0009', 'Blend de enzimas digestivas',            'kg', '35079049'),
    ('MP-0010', 'Aroma idêntico ao natural de chocolate', 'kg', '33021000'),
    ('MP-0011', 'Ácido cítrico anidro',                   'kg', '29181400'),
    ('MP-0012', 'Vitamina C (ácido ascórbico)',           'kg', '29362710')
ON CONFLICT (codigo) DO UPDATE SET
    descricao = EXCLUDED.descricao,
    unidade_medida = EXCLUDED.unidade_medida,
    ncm_codigo = EXCLUDED.ncm_codigo
WHERE (materia_prima.descricao, materia_prima.unidade_medida, materia_prima.ncm_codigo)
    IS DISTINCT FROM (EXCLUDED.descricao, EXCLUDED.unidade_medida, EXCLUDED.ncm_codigo);

-- ------------------------------------------------------------
-- Embalagens
-- ------------------------------------------------------------
INSERT INTO embalagem (codigo, descricao, unidade_medida, ncm_codigo) VALUES
    ('EMB-0001', 'Pote PET 1200 ml + tampa',              'un', '39233090'),
    ('EMB-0002', 'Pote PEAD 500 ml + tampa',              'un', '39233090'),
    ('EMB-0003', 'Rótulo BOPP adesivo',                   'un', '39199010'),
    ('EMB-0004', 'Selo de indução em alumínio',           'un', '76072000'),
    ('EMB-0005', 'Scoop dosador 30 ml',                   'un', '39249000'),
    ('EMB-0006', 'Caixa de papelão ondulado — 12 potes',  'un', '48191000')
ON CONFLICT (codigo) DO UPDATE SET
    descricao = EXCLUDED.descricao,
    unidade_medida = EXCLUDED.unidade_medida,
    ncm_codigo = EXCLUDED.ncm_codigo
WHERE (embalagem.descricao, embalagem.unidade_medida, embalagem.ncm_codigo)
    IS DISTINCT FROM (EXCLUDED.descricao, EXCLUDED.unidade_medida, EXCLUDED.ncm_codigo);

-- ------------------------------------------------------------
-- Produtos
-- ------------------------------------------------------------
INSERT INTO produto (codigo, descricao, categoria, ncm_codigo, peso_liquido_g) VALUES
    ('PA-0001', 'WPC 80 — pote 600 g',              'Proteínas',      '21069030', 600),
    ('PA-0002', 'Whey isolado 900 g',               'Proteínas',      '21069030', 900),
    ('PA-0003', 'Creatina mono 300 g',              'Aminoácidos',    '21069030', 300),
    ('PA-0004', 'Pré-treino 300 g — marca própria', 'Pré-treino',     '21069030', 300),
    ('PA-0005', 'BCAA 2:1:1 — 250 g',               'Aminoácidos',    '21069030', 250),
    ('PA-0006', 'Hipercalórico 3 kg',               'Hipercalóricos', '21069030', 3000),
    ('PA-0007', 'Colágeno verisol 300 g',           'Colágeno',       '21069030', 300)
ON CONFLICT (codigo) DO UPDATE SET
    descricao = EXCLUDED.descricao,
    categoria = EXCLUDED.categoria,
    ncm_codigo = EXCLUDED.ncm_codigo,
    peso_liquido_g = EXCLUDED.peso_liquido_g
WHERE (produto.descricao, produto.categoria, produto.ncm_codigo, produto.peso_liquido_g)
    IS DISTINCT FROM (EXCLUDED.descricao, EXCLUDED.categoria, EXCLUDED.ncm_codigo, EXCLUDED.peso_liquido_g);

-- ------------------------------------------------------------
-- Linhas de produção (TaxaMOD por funcionário e TaxaGGF, em R$/h)
-- ------------------------------------------------------------
INSERT INTO linha_producao (codigo, descricao, taxa_mod, taxa_ggf) VALUES
    ('LIN-01', 'Envase de pós — potes até 1 kg',      58.20, 403.20),
    ('LIN-02', 'Envase de pós — potes acima de 1 kg', 58.20, 465.00)
ON CONFLICT (codigo) DO UPDATE SET
    descricao = EXCLUDED.descricao,
    taxa_mod = EXCLUDED.taxa_mod,
    taxa_ggf = EXCLUDED.taxa_ggf
WHERE (linha_producao.descricao, linha_producao.taxa_mod, linha_producao.taxa_ggf)
    IS DISTINCT FROM (EXCLUDED.descricao, EXCLUDED.taxa_mod, EXCLUDED.taxa_ggf);

-- ------------------------------------------------------------
-- Produtividade por produto e linha
-- PA-0001 na LIN-01 reproduz o cenário do protótipo: MOD R$ 1,94 e
-- GGF R$ 1,12 por unidade.
-- ------------------------------------------------------------
INSERT INTO produtividade (produto_id, linha_producao_id, unidades_por_hora, numero_funcionarios)
SELECT p.id, l.id, v.unidades_por_hora, v.numero_funcionarios
FROM (VALUES
    ('PA-0001', 'LIN-01', 360, 12),
    ('PA-0002', 'LIN-01', 300, 12),
    ('PA-0003', 'LIN-01', 480, 10),
    ('PA-0004', 'LIN-01', 480, 10),
    ('PA-0005', 'LIN-01', 520, 10),
    ('PA-0006', 'LIN-02', 140,  8),
    ('PA-0007', 'LIN-01', 480, 10)
) AS v (produto_codigo, linha_codigo, unidades_por_hora, numero_funcionarios)
JOIN produto        p ON p.codigo = v.produto_codigo
JOIN linha_producao l ON l.codigo = v.linha_codigo
ON CONFLICT (produto_id, linha_producao_id) DO UPDATE SET
    unidades_por_hora = EXCLUDED.unidades_por_hora,
    numero_funcionarios = EXCLUDED.numero_funcionarios
WHERE (produtividade.unidades_por_hora, produtividade.numero_funcionarios)
    IS DISTINCT FROM (EXCLUDED.unidades_por_hora, EXCLUDED.numero_funcionarios);

-- ------------------------------------------------------------
-- Clientes (sem CNPJ: são empresas fictícias)
-- ------------------------------------------------------------
INSERT INTO cliente (
    codigo, razao_social, nome_fantasia, regime_tributario, pais, uf_sigla, municipio_codigo_ibge, cep
) VALUES
    ('CLI-0001', 'Nutrafit Distribuidora Ltda',  'Nutrafit Distribuidora', 'lucro_real',       'BR', 'SP', 3550308, '01310100'),
    ('CLI-0002', 'Corpore Suplementos Ltda',     'Corpore Suplementos',    'lucro_presumido',  'BR', 'MG', 3106200, '30130100'),
    ('CLI-0003', 'Atlas Nutrition LLC',          'Atlas Nutrition',        NULL,               'US', NULL, NULL,    NULL),
    ('CLI-0004', 'Vita Prime Indústria Ltda',    'Vita Prime Indústria',   'lucro_real',       'BR', 'PR', 4106902, '80010000'),
    ('CLI-0005', 'Forma Natural Comércio Ltda',  'Forma Natural',          'simples_nacional', 'BR', 'RJ', 3304557, '20040020')
ON CONFLICT (codigo) DO UPDATE SET
    razao_social = EXCLUDED.razao_social,
    nome_fantasia = EXCLUDED.nome_fantasia,
    regime_tributario = EXCLUDED.regime_tributario,
    pais = EXCLUDED.pais,
    uf_sigla = EXCLUDED.uf_sigla,
    municipio_codigo_ibge = EXCLUDED.municipio_codigo_ibge,
    cep = EXCLUDED.cep
WHERE (cliente.razao_social, cliente.nome_fantasia, cliente.regime_tributario, cliente.pais,
       cliente.uf_sigla, cliente.municipio_codigo_ibge, cliente.cep)
    IS DISTINCT FROM
      (EXCLUDED.razao_social, EXCLUDED.nome_fantasia, EXCLUDED.regime_tributario, EXCLUDED.pais,
       EXCLUDED.uf_sigla, EXCLUDED.municipio_codigo_ibge, EXCLUDED.cep);
