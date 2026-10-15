INSERT INTO cep (cep, logradouro, bairro, municipio_codigo_ibge) VALUES
    ('01310100', 'Avenida Paulista', 'Bela Vista', 3550308),
    ('04538133', 'Avenida Brigadeiro Faria Lima', 'Itaim Bibi', 3550308),
    ('06454000', 'Alameda Rio Negro', 'Alphaville Centro Industrial e Empresarial/Alphaville.', 3505708),
    ('13010111', 'Rua General Osório', 'Centro', 3509502),
    ('13087571', 'Rua Professor Doutor Euryclides de Jesus Zerbini', 'Parque Rural Fazenda Santa Cândida', 3509502),
    ('20040020', 'Praça Pio X', 'Centro', 3304557),
    ('30130100', 'Avenida Professor Alfredo Balena', 'Santa Efigênia', 3106200),
    ('80010000', 'Rua José Loureiro', 'Centro', 4106902),
    ('89010000', 'Rua 15 de Novembro', 'Centro', 4202404),
    ('90010150', 'Praça da Alfândega', 'Centro Histórico', 4314902)
ON CONFLICT (cep) DO UPDATE SET
    logradouro = EXCLUDED.logradouro,
    bairro = EXCLUDED.bairro,
    municipio_codigo_ibge = EXCLUDED.municipio_codigo_ibge
WHERE (cep.logradouro, cep.bairro, cep.municipio_codigo_ibge) IS DISTINCT FROM (EXCLUDED.logradouro, EXCLUDED.bairro, EXCLUDED.municipio_codigo_ibge);
