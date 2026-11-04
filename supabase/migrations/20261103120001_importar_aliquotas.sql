-- ============================================================
-- Migration: importação em massa de alíquotas fiscais
-- Issue #48 (US12) — Sprint 2
-- Executar via: supabase db push
--
-- `importar_aliquotas` grava um lote inteiro de alíquotas em um único
-- comando: ou entra tudo, ou nada. A chave de cada linha é a mesma da
-- tabela (UF de destino, NCM, regime e início de vigência): linha nova é
-- inserida, linha existente com outro valor é atualizada e linha igual
-- não é tocada, para não gerar auditoria à toa.
--
-- SECURITY INVOKER: roda com o papel de quem chama, então o RLS de
-- `aliquota_fiscal` vale (só quem tem `parametro_fiscal.editar` grava) e
-- a auditoria registra o usuário do JWT.
-- ============================================================

CREATE FUNCTION importar_aliquotas(p_linhas JSONB, p_simular BOOLEAN DEFAULT FALSE)
RETURNS TABLE (novas INTEGER, atualizadas INTEGER, inalteradas INTEGER)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_usuario UUID := usuario_da_sessao();
BEGIN
    IF jsonb_typeof(p_linhas) IS DISTINCT FROM 'array' THEN
        RAISE EXCEPTION 'p_linhas precisa ser um array JSON de alíquotas'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    SELECT
        count(*) FILTER (WHERE a.id IS NULL),
        count(*) FILTER (WHERE a.id IS NOT NULL AND
            (a.pis_percentual, a.cofins_percentual, a.icms_percentual, a.ipi_percentual,
             a.icms_interno_percentual, a.fcp_percentual, a.mva_percentual)
            IS DISTINCT FROM
            (e.pis_percentual, e.cofins_percentual, e.icms_percentual, e.ipi_percentual,
             e.icms_interno_percentual, e.fcp_percentual, e.mva_percentual)),
        count(*) FILTER (WHERE a.id IS NOT NULL AND
            (a.pis_percentual, a.cofins_percentual, a.icms_percentual, a.ipi_percentual,
             a.icms_interno_percentual, a.fcp_percentual, a.mva_percentual)
            IS NOT DISTINCT FROM
            (e.pis_percentual, e.cofins_percentual, e.icms_percentual, e.ipi_percentual,
             e.icms_interno_percentual, e.fcp_percentual, e.mva_percentual))
    INTO novas, atualizadas, inalteradas
    FROM jsonb_to_recordset(p_linhas) AS e (
        uf_destino CHAR(2), ncm_codigo CHAR(8), regime_tributario VARCHAR(20), vigencia_inicio DATE,
        pis_percentual NUMERIC(7, 6), cofins_percentual NUMERIC(7, 6), icms_percentual NUMERIC(7, 6),
        ipi_percentual NUMERIC(7, 6), icms_interno_percentual NUMERIC(7, 6), fcp_percentual NUMERIC(7, 6),
        mva_percentual NUMERIC(8, 6)
    )
    LEFT JOIN aliquota_fiscal a
           ON a.uf_destino = e.uf_destino
          AND a.ncm_codigo IS NOT DISTINCT FROM e.ncm_codigo
          AND a.regime_tributario = e.regime_tributario
          AND a.vigencia_inicio = e.vigencia_inicio;

    IF NOT p_simular THEN
        INSERT INTO aliquota_fiscal (
            uf_destino, ncm_codigo, regime_tributario, vigencia_inicio,
            pis_percentual, cofins_percentual, icms_percentual, ipi_percentual,
            icms_interno_percentual, fcp_percentual, mva_percentual,
            created_by, updated_by
        )
        SELECT
            uf_destino, ncm_codigo, regime_tributario, vigencia_inicio,
            pis_percentual, cofins_percentual, icms_percentual, ipi_percentual,
            icms_interno_percentual, fcp_percentual, mva_percentual,
            v_usuario, v_usuario
        FROM jsonb_to_recordset(p_linhas) AS e (
            uf_destino CHAR(2), ncm_codigo CHAR(8), regime_tributario VARCHAR(20), vigencia_inicio DATE,
            pis_percentual NUMERIC(7, 6), cofins_percentual NUMERIC(7, 6), icms_percentual NUMERIC(7, 6),
            ipi_percentual NUMERIC(7, 6), icms_interno_percentual NUMERIC(7, 6), fcp_percentual NUMERIC(7, 6),
            mva_percentual NUMERIC(8, 6)
        )
        ON CONFLICT (uf_destino, ncm_codigo, regime_tributario, vigencia_inicio) DO UPDATE SET
            pis_percentual = EXCLUDED.pis_percentual,
            cofins_percentual = EXCLUDED.cofins_percentual,
            icms_percentual = EXCLUDED.icms_percentual,
            ipi_percentual = EXCLUDED.ipi_percentual,
            icms_interno_percentual = EXCLUDED.icms_interno_percentual,
            fcp_percentual = EXCLUDED.fcp_percentual,
            mva_percentual = EXCLUDED.mva_percentual,
            updated_by = EXCLUDED.updated_by
        WHERE (aliquota_fiscal.pis_percentual, aliquota_fiscal.cofins_percentual, aliquota_fiscal.icms_percentual,
               aliquota_fiscal.ipi_percentual, aliquota_fiscal.icms_interno_percentual, aliquota_fiscal.fcp_percentual,
               aliquota_fiscal.mva_percentual)
            IS DISTINCT FROM
              (EXCLUDED.pis_percentual, EXCLUDED.cofins_percentual, EXCLUDED.icms_percentual,
               EXCLUDED.ipi_percentual, EXCLUDED.icms_interno_percentual, EXCLUDED.fcp_percentual,
               EXCLUDED.mva_percentual);
    END IF;

    RETURN NEXT;
END;
$$;

REVOKE EXECUTE ON FUNCTION importar_aliquotas(JSONB, BOOLEAN) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION importar_aliquotas(JSONB, BOOLEAN) TO authenticated, service_role;
