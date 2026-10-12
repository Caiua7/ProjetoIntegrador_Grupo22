-- ============================================================
-- Migration: cadastros do núcleo (fornecedor, matéria-prima, embalagem,
-- produto, linha de produção, produtividade e cliente)
-- Issue #43 (US05) — Sprint 1
-- Executar via: supabase db push
--
-- Todo cadastro tem `codigo` de negócio único (é a chave usada pelo seed
-- e pelo contrato do motor) e `ativo` no lugar de exclusão física.
-- ============================================================

-- ============================================================
-- TABELA: fornecedor
-- ============================================================
CREATE TABLE fornecedor (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(30)     NOT NULL,
    razao_social    VARCHAR(180)    NOT NULL,
    nome_fantasia   VARCHAR(180)    NULL,
    cnpj            CHAR(14)        NULL,               -- fornecedor estrangeiro não tem
    pais            CHAR(2)         NOT NULL DEFAULT 'BR',   -- ISO 3166-1 alfa-2
    uf_sigla        CHAR(2)         NULL REFERENCES uf (sigla),

    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_fornecedor_codigo UNIQUE (codigo),
    CONSTRAINT uq_fornecedor_cnpj   UNIQUE (cnpj),
    CONSTRAINT ck_fornecedor_cnpj   CHECK (cnpj ~ '^[0-9]{14}$'),
    CONSTRAINT ck_fornecedor_pais   CHECK (pais ~ '^[A-Z]{2}$'),
    CONSTRAINT ck_fornecedor_uf_so_brasil CHECK (pais = 'BR' OR uf_sigla IS NULL)
);

CREATE INDEX idx_fornecedor_razao_social ON fornecedor (razao_social);
CREATE INDEX idx_fornecedor_ativo        ON fornecedor (ativo);

CREATE TRIGGER trg_fornecedor_updated_at
    BEFORE UPDATE ON fornecedor
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: materia_prima
-- ============================================================
CREATE TABLE materia_prima (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(30)     NOT NULL,
    descricao       VARCHAR(200)    NOT NULL,
    unidade_medida  VARCHAR(5)      NOT NULL DEFAULT 'kg',
    ncm_codigo      CHAR(8)         NOT NULL REFERENCES ncm (codigo),

    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_materia_prima_codigo  UNIQUE (codigo),
    CONSTRAINT ck_materia_prima_unidade CHECK (unidade_medida IN ('kg', 'g', 'l', 'ml', 'un'))
);

CREATE INDEX idx_materia_prima_descricao ON materia_prima (descricao);
CREATE INDEX idx_materia_prima_ncm       ON materia_prima (ncm_codigo);
CREATE INDEX idx_materia_prima_ativo     ON materia_prima (ativo);

CREATE TRIGGER trg_materia_prima_updated_at
    BEFORE UPDATE ON materia_prima
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: embalagem
-- ============================================================
CREATE TABLE embalagem (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(30)     NOT NULL,
    descricao       VARCHAR(200)    NOT NULL,
    unidade_medida  VARCHAR(5)      NOT NULL DEFAULT 'un',
    ncm_codigo      CHAR(8)         NOT NULL REFERENCES ncm (codigo),

    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_embalagem_codigo  UNIQUE (codigo),
    CONSTRAINT ck_embalagem_unidade CHECK (unidade_medida IN ('kg', 'g', 'l', 'ml', 'un'))
);

CREATE INDEX idx_embalagem_descricao ON embalagem (descricao);
CREATE INDEX idx_embalagem_ncm       ON embalagem (ncm_codigo);
CREATE INDEX idx_embalagem_ativo     ON embalagem (ativo);

CREATE TRIGGER trg_embalagem_updated_at
    BEFORE UPDATE ON embalagem
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: produto
-- ============================================================
CREATE TABLE produto (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(30)     NOT NULL,
    descricao       VARCHAR(200)    NOT NULL,
    categoria       VARCHAR(80)     NOT NULL,
    ncm_codigo      CHAR(8)         NOT NULL REFERENCES ncm (codigo),
    peso_liquido_g  NUMERIC(12, 3)  NULL,

    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_produto_codigo UNIQUE (codigo),
    CONSTRAINT ck_produto_peso   CHECK (peso_liquido_g > 0)
);

CREATE INDEX idx_produto_descricao ON produto (descricao);
CREATE INDEX idx_produto_categoria ON produto (categoria);
CREATE INDEX idx_produto_ncm       ON produto (ncm_codigo);
CREATE INDEX idx_produto_ativo     ON produto (ativo);

CREATE TRIGGER trg_produto_updated_at
    BEFORE UPDATE ON produto
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: linha_producao
-- Guarda TaxaMOD e TaxaGGF da linha (US10), ambas em R$ por hora; a
-- TaxaMOD é por funcionário.
-- ============================================================
CREATE TABLE linha_producao (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(30)     NOT NULL,
    descricao       VARCHAR(200)    NOT NULL,
    taxa_mod        NUMERIC(14, 4)  NOT NULL,
    taxa_ggf        NUMERIC(14, 4)  NOT NULL,

    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_linha_producao_codigo   UNIQUE (codigo),
    CONSTRAINT ck_linha_producao_taxa_mod CHECK (taxa_mod >= 0),
    CONSTRAINT ck_linha_producao_taxa_ggf CHECK (taxa_ggf >= 0)
);

CREATE TRIGGER trg_linha_producao_updated_at
    BEFORE UPDATE ON linha_producao
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: produtividade
-- Produtividade de um produto em uma linha. Com as taxas da linha,
-- fecha os ParametrosProducao do contrato do motor:
--   CustoMOD = (TaxaMOD / Produtividade) × NumFunc
--   CustoGGF = TaxaGGF / Produtividade
-- ============================================================
CREATE TABLE produtividade (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    produto_id          UUID            NOT NULL REFERENCES produto (id),
    linha_producao_id   UUID            NOT NULL REFERENCES linha_producao (id),
    unidades_por_hora   NUMERIC(14, 4)  NOT NULL,
    numero_funcionarios NUMERIC(6, 2)   NOT NULL,

    created_by          UUID            NULL,
    updated_by          UUID            NULL,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_produtividade UNIQUE (produto_id, linha_producao_id),
    CONSTRAINT ck_produtividade_unidades     CHECK (unidades_por_hora > 0),
    CONSTRAINT ck_produtividade_funcionarios CHECK (numero_funcionarios >= 0)
);

CREATE INDEX idx_produtividade_linha ON produtividade (linha_producao_id);

CREATE TRIGGER trg_produtividade_updated_at
    BEFORE UPDATE ON produtividade
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: cliente
-- Cliente de exportação tem pais <> 'BR' e fica sem UF, município, CEP
-- e regime tributário.
-- ============================================================
CREATE TABLE cliente (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo                  VARCHAR(30)     NOT NULL,
    razao_social            VARCHAR(180)    NOT NULL,
    nome_fantasia           VARCHAR(180)    NULL,
    cnpj                    CHAR(14)        NULL,
    regime_tributario       VARCHAR(20)     NULL,
    pais                    CHAR(2)         NOT NULL DEFAULT 'BR',   -- ISO 3166-1 alfa-2
    uf_sigla                CHAR(2)         NULL REFERENCES uf (sigla),
    municipio_codigo_ibge   INTEGER         NULL REFERENCES municipio (codigo_ibge),
    cep                     CHAR(8)         NULL,

    ativo                   BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by              UUID            NULL,
    updated_by              UUID            NULL,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_cliente_codigo UNIQUE (codigo),
    CONSTRAINT uq_cliente_cnpj   UNIQUE (cnpj),
    CONSTRAINT ck_cliente_cnpj   CHECK (cnpj ~ '^[0-9]{14}$'),
    CONSTRAINT ck_cliente_cep    CHECK (cep ~ '^[0-9]{8}$'),
    CONSTRAINT ck_cliente_pais   CHECK (pais ~ '^[A-Z]{2}$'),
    CONSTRAINT ck_cliente_regime CHECK
        (regime_tributario IN ('lucro_real', 'lucro_presumido', 'simples_nacional')),
    -- UF e regime definem a tributação do cenário: obrigatórios no Brasil
    CONSTRAINT ck_cliente_nacional CHECK
        (pais <> 'BR' OR (uf_sigla IS NOT NULL AND regime_tributario IS NOT NULL)),
    CONSTRAINT ck_cliente_exterior CHECK
        (pais = 'BR' OR (uf_sigla IS NULL AND municipio_codigo_ibge IS NULL))
);

CREATE INDEX idx_cliente_razao_social ON cliente (razao_social);
CREATE INDEX idx_cliente_uf           ON cliente (uf_sigla);
CREATE INDEX idx_cliente_municipio    ON cliente (municipio_codigo_ibge);
CREATE INDEX idx_cliente_ativo        ON cliente (ativo);

CREATE TRIGGER trg_cliente_updated_at
    BEFORE UPDATE ON cliente
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- RLS (Row Level Security)
-- Mesmo critério da migration anterior: só service_role até a US04.
-- ============================================================
ALTER TABLE fornecedor     ENABLE ROW LEVEL SECURITY;
ALTER TABLE materia_prima  ENABLE ROW LEVEL SECURITY;
ALTER TABLE embalagem      ENABLE ROW LEVEL SECURITY;
ALTER TABLE produto        ENABLE ROW LEVEL SECURITY;
ALTER TABLE linha_producao ENABLE ROW LEVEL SECURITY;
ALTER TABLE produtividade  ENABLE ROW LEVEL SECURITY;
ALTER TABLE cliente        ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_fornecedor"
    ON fornecedor FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_materia_prima"
    ON materia_prima FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_embalagem"
    ON embalagem FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_produto"
    ON produto FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_linha_producao"
    ON linha_producao FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_produtividade"
    ON produtividade FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_cliente"
    ON cliente FOR ALL TO service_role
    USING (true) WITH CHECK (true);
