-- ============================================================
-- Migration: tabelas de referência (UF, município IBGE, CEP, NCM e
-- alíquotas por UF/NCM/regime)
-- Issue #43 (US05) — Sprint 1
-- Executar via: supabase db push
--
-- Convenções deste schema:
--   - Todo percentual é fração decimal (0.18 representa 18%), igual ao
--     contrato do motor (packages/pricing-core/.../contracts.py).
--   - Códigos oficiais (UF, IBGE, CEP, NCM) são a própria chave primária e
--     ficam sem máscara, só dígitos.
-- ============================================================

-- Trigger para manter updated_at sincronizado automaticamente
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TABELA: uf
-- ============================================================
CREATE TABLE uf (
    sigla           CHAR(2)         PRIMARY KEY,
    codigo_ibge     SMALLINT        NOT NULL,
    nome            VARCHAR(60)     NOT NULL,
    regiao          VARCHAR(2)      NOT NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_uf_codigo_ibge UNIQUE (codigo_ibge),
    CONSTRAINT ck_uf_sigla       CHECK (sigla ~ '^[A-Z]{2}$'),
    CONSTRAINT ck_uf_regiao      CHECK (regiao IN ('N', 'NE', 'CO', 'SE', 'S'))
);

CREATE TRIGGER trg_uf_updated_at
    BEFORE UPDATE ON uf
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: municipio
-- Código IBGE de 7 dígitos como chave.
-- ============================================================
CREATE TABLE municipio (
    codigo_ibge     INTEGER         PRIMARY KEY,
    nome            VARCHAR(120)    NOT NULL,
    uf_sigla        CHAR(2)         NOT NULL REFERENCES uf (sigla),

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT ck_municipio_codigo_ibge CHECK (codigo_ibge BETWEEN 1000000 AND 9999999)
);

-- Listagem de municípios de uma UF em ordem alfabética (combo de cadastro)
CREATE INDEX idx_municipio_uf_nome ON municipio (uf_sigla, nome);

CREATE TRIGGER trg_municipio_updated_at
    BEFORE UPDATE ON municipio
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: cep
-- Tabela de consulta CEP -> município/UF. Não é a base completa dos
-- Correios: recebe os CEPs usados nos cadastros, por isso cliente.cep
-- não tem FK para cá.
-- ============================================================
CREATE TABLE cep (
    cep                     CHAR(8)         PRIMARY KEY,
    logradouro              VARCHAR(200)    NULL,
    bairro                  VARCHAR(120)    NULL,
    municipio_codigo_ibge   INTEGER         NOT NULL REFERENCES municipio (codigo_ibge),

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT ck_cep_formato CHECK (cep ~ '^[0-9]{8}$')
);

CREATE INDEX idx_cep_municipio ON cep (municipio_codigo_ibge);

CREATE TRIGGER trg_cep_updated_at
    BEFORE UPDATE ON cep
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: ncm
-- Itens de 8 dígitos da Nomenclatura Comum do Mercosul.
-- ============================================================
CREATE TABLE ncm (
    codigo          CHAR(8)         PRIMARY KEY,
    descricao       TEXT            NOT NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT ck_ncm_codigo CHECK (codigo ~ '^[0-9]{8}$')
);

CREATE TRIGGER trg_ncm_updated_at
    BEFORE UPDATE ON ncm
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: aliquota_fiscal
-- Alíquotas por UF de destino, NCM e regime tributário (RF05/US12).
-- ncm_codigo NULL é a regra geral da UF; uma linha com NCM preenchido
-- tem precedência sobre ela.
-- ============================================================
CREATE TABLE aliquota_fiscal (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    uf_destino              CHAR(2)         NOT NULL REFERENCES uf (sigla),
    ncm_codigo              CHAR(8)         NULL REFERENCES ncm (codigo),
    regime_tributario       VARCHAR(20)     NOT NULL,
    vigencia_inicio         DATE            NOT NULL,

    pis_percentual          NUMERIC(7, 6)   NOT NULL DEFAULT 0,
    cofins_percentual       NUMERIC(7, 6)   NOT NULL DEFAULT 0,
    icms_percentual         NUMERIC(7, 6)   NOT NULL DEFAULT 0,
    ipi_percentual          NUMERIC(7, 6)   NOT NULL DEFAULT 0,
    icms_interno_percentual NUMERIC(7, 6)   NOT NULL DEFAULT 0,
    fcp_percentual          NUMERIC(7, 6)   NOT NULL DEFAULT 0,
    mva_percentual          NUMERIC(8, 6)   NOT NULL DEFAULT 0,   -- MVA pode passar de 100%

    created_by              UUID            NULL,
    updated_by              UUID            NULL,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),

    -- NULLS NOT DISTINCT: só pode existir uma regra geral (NCM nulo) por
    -- UF, regime e início de vigência
    CONSTRAINT uq_aliquota_fiscal UNIQUE NULLS NOT DISTINCT
        (uf_destino, ncm_codigo, regime_tributario, vigencia_inicio),
    CONSTRAINT ck_aliquota_regime CHECK
        (regime_tributario IN ('lucro_real', 'lucro_presumido', 'simples_nacional')),
    CONSTRAINT ck_aliquota_pis          CHECK (pis_percentual          BETWEEN 0 AND 1),
    CONSTRAINT ck_aliquota_cofins       CHECK (cofins_percentual       BETWEEN 0 AND 1),
    CONSTRAINT ck_aliquota_icms         CHECK (icms_percentual         BETWEEN 0 AND 1),
    CONSTRAINT ck_aliquota_ipi          CHECK (ipi_percentual          BETWEEN 0 AND 1),
    CONSTRAINT ck_aliquota_icms_interno CHECK (icms_interno_percentual BETWEEN 0 AND 1),
    CONSTRAINT ck_aliquota_fcp          CHECK (fcp_percentual          BETWEEN 0 AND 1),
    CONSTRAINT ck_aliquota_mva          CHECK (mva_percentual >= 0)
);

CREATE INDEX idx_aliquota_fiscal_ncm ON aliquota_fiscal (ncm_codigo);

CREATE TRIGGER trg_aliquota_fiscal_updated_at
    BEFORE UPDATE ON aliquota_fiscal
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- RLS (Row Level Security)
-- Ativado já na criação, com acesso só para o service_role (backend).
-- As políticas por perfil e carteira de clientes entram com a story de
-- RLS (US04).
-- ============================================================
ALTER TABLE uf              ENABLE ROW LEVEL SECURITY;
ALTER TABLE municipio       ENABLE ROW LEVEL SECURITY;
ALTER TABLE cep             ENABLE ROW LEVEL SECURITY;
ALTER TABLE ncm             ENABLE ROW LEVEL SECURITY;
ALTER TABLE aliquota_fiscal ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_uf"
    ON uf FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_municipio"
    ON municipio FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_cep"
    ON cep FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_ncm"
    ON ncm FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_aliquota_fiscal"
    ON aliquota_fiscal FOR ALL TO service_role
    USING (true) WITH CHECK (true);
