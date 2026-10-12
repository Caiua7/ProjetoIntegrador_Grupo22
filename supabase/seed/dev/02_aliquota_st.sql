-- Seed de DESENVOLVIMENTO: 02_aliquota_st.sql
-- Regra por NCM com substituição tributária, para o time ter um cenário de
-- ICMS-ST (US21) antes de a tela de alíquotas existir. Reproduz a
-- "Tributação resolvida" do protótipo: NCM 2106.90.30, destino SP, Lucro
-- Real, vigência a partir de 01/09/2026.
-- Idempotente: pode rodar mais de uma vez sem duplicar nem alterar registros.
--
-- ATENÇÃO — valores fictícios do protótipo, não são a regra fiscal real.

INSERT INTO aliquota_fiscal (
    uf_destino, ncm_codigo, regime_tributario, vigencia_inicio,
    pis_percentual, cofins_percentual, icms_percentual, ipi_percentual,
    icms_interno_percentual, fcp_percentual, mva_percentual
) VALUES
    ('SP', '21069030', 'lucro_real', DATE '2026-09-01', 0.0165, 0.076, 0.12, 0, 0.18, 0.02, 0.4134)
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
