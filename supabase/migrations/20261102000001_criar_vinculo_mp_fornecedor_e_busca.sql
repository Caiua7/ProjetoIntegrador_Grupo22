-- ============================================================
-- Migration: vínculo matéria-prima × fornecedor e busca nos cadastros
-- Issue #50 (US06, US11) — Sprint 2
-- Executar via: supabase db push
--
-- - `materia_prima_fornecedor`: de quais fornecedores a MP é comprada, com
--   o código do item no catálogo do fornecedor e no máximo um principal.
--   Desvincular é inativar (ativo = false): o histórico fica, como no
--   restante do cadastro.
-- - Índices trigram (pg_trgm) para a busca por "contém" em código e
--   descrição de MP e embalagem e na razão social do fornecedor: a listagem
--   paginada filtra com ILIKE '%termo%', que o índice B-tree não atende.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA extensions;

-- ============================================================
-- TABELA: materia_prima_fornecedor
-- ============================================================
CREATE TABLE materia_prima_fornecedor (
    materia_prima_id        UUID            NOT NULL REFERENCES materia_prima (id),
    fornecedor_id           UUID            NOT NULL REFERENCES fornecedor (id),

    codigo_no_fornecedor    VARCHAR(60)     NULL,
    principal               BOOLEAN         NOT NULL DEFAULT FALSE,

    ativo                   BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by              UUID            NULL,
    updated_by              UUID            NULL,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT pk_materia_prima_fornecedor PRIMARY KEY (materia_prima_id, fornecedor_id),
    CONSTRAINT ck_mp_fornecedor_principal_ativo CHECK (NOT principal OR ativo)
);

CREATE INDEX idx_mp_fornecedor_fornecedor ON materia_prima_fornecedor (fornecedor_id);

-- Um único fornecedor principal (ativo) por matéria-prima
CREATE UNIQUE INDEX uq_mp_fornecedor_principal
    ON materia_prima_fornecedor (materia_prima_id)
    WHERE principal;

CREATE TRIGGER trg_materia_prima_fornecedor_updated_at
    BEFORE UPDATE ON materia_prima_fornecedor
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Mesma regra das demais tabelas de cadastro (ver 20261012000003): ler com
-- cadastro.ler, inserir e alterar com cadastro.editar, sem DELETE.
ALTER TABLE materia_prima_fornecedor ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE ON materia_prima_fornecedor TO authenticated;

CREATE POLICY materia_prima_fornecedor_servico ON materia_prima_fornecedor
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY materia_prima_fornecedor_leitura ON materia_prima_fornecedor
    FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('cadastro.ler')));

CREATE POLICY materia_prima_fornecedor_insercao ON materia_prima_fornecedor
    FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('cadastro.editar')));

CREATE POLICY materia_prima_fornecedor_alteracao ON materia_prima_fornecedor
    FOR UPDATE TO authenticated
    USING ((SELECT usuario_tem_permissao('cadastro.editar')))
    WITH CHECK ((SELECT usuario_tem_permissao('cadastro.editar')));

SELECT habilitar_auditoria('materia_prima_fornecedor');

-- ============================================================
-- ÍNDICES DE BUSCA
-- ============================================================
CREATE INDEX idx_materia_prima_busca ON materia_prima
    USING gin (codigo extensions.gin_trgm_ops, descricao extensions.gin_trgm_ops);

CREATE INDEX idx_embalagem_busca ON embalagem
    USING gin (codigo extensions.gin_trgm_ops, descricao extensions.gin_trgm_ops);

CREATE INDEX idx_fornecedor_busca ON fornecedor
    USING gin (codigo extensions.gin_trgm_ops, razao_social extensions.gin_trgm_ops);
