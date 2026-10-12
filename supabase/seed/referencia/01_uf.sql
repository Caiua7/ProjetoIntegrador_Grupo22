-- Seed: 01_uf.sql
-- GERADO por scripts/gerar_seed_referencia.py — não editar à mão.
-- Fonte: https://servicodados.ibge.gov.br/api/v1/localidades/estados
-- Idempotente: pode rodar mais de uma vez sem duplicar nem alterar registros.

INSERT INTO uf (sigla, codigo_ibge, nome, regiao) VALUES
    ('RO', 11, 'Rondônia', 'N'),
    ('AC', 12, 'Acre', 'N'),
    ('AM', 13, 'Amazonas', 'N'),
    ('RR', 14, 'Roraima', 'N'),
    ('PA', 15, 'Pará', 'N'),
    ('AP', 16, 'Amapá', 'N'),
    ('TO', 17, 'Tocantins', 'N'),
    ('MA', 21, 'Maranhão', 'NE'),
    ('PI', 22, 'Piauí', 'NE'),
    ('CE', 23, 'Ceará', 'NE'),
    ('RN', 24, 'Rio Grande do Norte', 'NE'),
    ('PB', 25, 'Paraíba', 'NE'),
    ('PE', 26, 'Pernambuco', 'NE'),
    ('AL', 27, 'Alagoas', 'NE'),
    ('SE', 28, 'Sergipe', 'NE'),
    ('BA', 29, 'Bahia', 'NE'),
    ('MG', 31, 'Minas Gerais', 'SE'),
    ('ES', 32, 'Espírito Santo', 'SE'),
    ('RJ', 33, 'Rio de Janeiro', 'SE'),
    ('SP', 35, 'São Paulo', 'SE'),
    ('PR', 41, 'Paraná', 'S'),
    ('SC', 42, 'Santa Catarina', 'S'),
    ('RS', 43, 'Rio Grande do Sul', 'S'),
    ('MS', 50, 'Mato Grosso do Sul', 'CO'),
    ('MT', 51, 'Mato Grosso', 'CO'),
    ('GO', 52, 'Goiás', 'CO'),
    ('DF', 53, 'Distrito Federal', 'CO')
ON CONFLICT (sigla) DO UPDATE SET
    codigo_ibge = EXCLUDED.codigo_ibge,
    nome = EXCLUDED.nome,
    regiao = EXCLUDED.regiao
WHERE (uf.codigo_ibge, uf.nome, uf.regiao) IS DISTINCT FROM (EXCLUDED.codigo_ibge, EXCLUDED.nome, EXCLUDED.regiao);
