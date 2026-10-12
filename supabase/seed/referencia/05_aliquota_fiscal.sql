-- Seed: 05_aliquota_fiscal.sql
-- Regra geral de alíquotas por UF de destino (ncm_codigo NULL), uma linha
-- por UF e regime tributário.
-- Idempotente: pode rodar mais de uma vez sem duplicar nem alterar registros.
--
-- ATENÇÃO — valores de SIMULAÇÃO para desenvolvimento, ainda não
-- homologados com o PO nem conferidos contra a legislação de cada UF:
--   - icms: assume fabricante em SP. 18% na operação interna (SP), 12%
--     para Sul e Sudeste e 7% para Norte, Nordeste, Centro-Oeste e ES.
--   - icms_interno: alíquota modal interna da UF de destino.
--   - fcp: só o adicional geral conhecido (RJ); os demais ficam em zero.
--   - pis/cofins: regime não cumulativo do fabricante (1,65% e 7,6%),
--     iguais nos três regimes até a regra por regime ser definida (US12).
--   - ipi e mva: zero na regra geral; ST e IPI entram por NCM.
-- A manutenção destes valores pela interface é a US12 (Sprint 2).

INSERT INTO aliquota_fiscal (
    uf_destino, ncm_codigo, regime_tributario, vigencia_inicio,
    pis_percentual, cofins_percentual, icms_percentual, ipi_percentual,
    icms_interno_percentual, fcp_percentual, mva_percentual
)
SELECT
    a.uf_destino, NULL, r.regime_tributario, DATE '2026-01-01',
    0.0165, 0.076, a.icms, 0,
    a.icms_interno, a.fcp, 0
FROM (VALUES
    -- uf, icms da operação, icms interno, fcp
    ('AC', 0.07, 0.19,  0),
    ('AL', 0.07, 0.19,  0),
    ('AM', 0.07, 0.20,  0),
    ('AP', 0.07, 0.18,  0),
    ('BA', 0.07, 0.205, 0),
    ('CE', 0.07, 0.20,  0),
    ('DF', 0.07, 0.20,  0),
    ('ES', 0.07, 0.17,  0),
    ('GO', 0.07, 0.19,  0),
    ('MA', 0.07, 0.23,  0),
    ('MG', 0.12, 0.18,  0),
    ('MS', 0.07, 0.17,  0),
    ('MT', 0.07, 0.17,  0),
    ('PA', 0.07, 0.19,  0),
    ('PB', 0.07, 0.20,  0),
    ('PE', 0.07, 0.205, 0),
    ('PI', 0.07, 0.225, 0),
    ('PR', 0.12, 0.195, 0),
    ('RJ', 0.12, 0.20,  0.02),
    ('RN', 0.07, 0.20,  0),
    ('RO', 0.07, 0.195, 0),
    ('RR', 0.07, 0.20,  0),
    ('RS', 0.12, 0.17,  0),
    ('SC', 0.12, 0.17,  0),
    ('SE', 0.07, 0.19,  0),
    ('SP', 0.18, 0.18,  0),
    ('TO', 0.07, 0.20,  0)
) AS a (uf_destino, icms, icms_interno, fcp)
CROSS JOIN (VALUES
    ('lucro_real'),
    ('lucro_presumido'),
    ('simples_nacional')
) AS r (regime_tributario)
ON CONFLICT (uf_destino, ncm_codigo, regime_tributario, vigencia_inicio) DO UPDATE SET
    pis_percentual = EXCLUDED.pis_percentual,
    cofins_percentual = EXCLUDED.cofins_percentual,
    icms_percentual = EXCLUDED.icms_percentual,
    ipi_percentual = EXCLUDED.ipi_percentual,
    icms_interno_percentual = EXCLUDED.icms_interno_percentual,
    fcp_percentual = EXCLUDED.fcp_percentual,
    mva_percentual = EXCLUDED.mva_percentual
WHERE (aliquota_fiscal.pis_percentual, aliquota_fiscal.cofins_percentual, aliquota_fiscal.icms_percentual,
       aliquota_fiscal.ipi_percentual, aliquota_fiscal.icms_interno_percentual, aliquota_fiscal.fcp_percentual,
       aliquota_fiscal.mva_percentual)
    IS DISTINCT FROM
      (EXCLUDED.pis_percentual, EXCLUDED.cofins_percentual, EXCLUDED.icms_percentual,
       EXCLUDED.ipi_percentual, EXCLUDED.icms_interno_percentual, EXCLUDED.fcp_percentual,
       EXCLUDED.mva_percentual);
