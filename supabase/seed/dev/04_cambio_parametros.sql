INSERT INTO cambio (moeda, data_referencia, taxa, margem_seguranca_percentual, fonte) VALUES
    ('USD', DATE '2026-09-09', 5.604000, 0.020000, 'manual'),
    ('EUR', DATE '2026-09-09', 6.093000, 0.020000, 'manual')
ON CONFLICT (moeda, data_referencia) DO UPDATE SET
    taxa = EXCLUDED.taxa,
    margem_seguranca_percentual = EXCLUDED.margem_seguranca_percentual,
    fonte = EXCLUDED.fonte
WHERE (cambio.taxa, cambio.margem_seguranca_percentual, cambio.fonte)
    IS DISTINCT FROM (EXCLUDED.taxa, EXCLUDED.margem_seguranca_percentual, EXCLUDED.fonte);

INSERT INTO parametro_global (codigo, valor, vigencia_inicio) VALUES
    ('perda_percentual',                  0.020000, DATE '2026-01-01'),
    ('taxa_financeira_mensal_percentual', 0.012000, DATE '2026-01-01'),
    ('prazo_medio_padrao_dias',           30,       DATE '2026-01-01'),
    ('desvio_maximo_cotacao_percentual',  0.100000, DATE '2026-01-01')
ON CONFLICT (codigo, vigencia_inicio) DO UPDATE SET
    valor = EXCLUDED.valor
WHERE parametro_global.valor IS DISTINCT FROM EXCLUDED.valor;
