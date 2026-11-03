-- Composicao atual de cada produto, consumida futuramente pelo motor de calculo.
CREATE TABLE formulacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id UUID NOT NULL UNIQUE REFERENCES produto(id),
    created_by UUID NULL,
    updated_by UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE formulacao_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formulacao_id UUID NOT NULL REFERENCES formulacao(id) ON DELETE CASCADE,
    tipo_insumo VARCHAR(20) NOT NULL,
    materia_prima_id UUID NULL REFERENCES materia_prima(id),
    embalagem_id UUID NULL REFERENCES embalagem(id),
    quantidade NUMERIC(14, 6) NOT NULL,
    unidade_medida VARCHAR(5) NOT NULL,
    perda_percentual NUMERIC(7, 4) NULL,
    ordem INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_formulacao_item_tipo CHECK (tipo_insumo IN ('materia_prima', 'embalagem')),
    CONSTRAINT ck_formulacao_item_referencia CHECK (
        (tipo_insumo = 'materia_prima' AND materia_prima_id IS NOT NULL AND embalagem_id IS NULL)
        OR (tipo_insumo = 'embalagem' AND embalagem_id IS NOT NULL AND materia_prima_id IS NULL)
    ),
    CONSTRAINT ck_formulacao_item_quantidade CHECK (quantidade > 0),
    CONSTRAINT ck_formulacao_item_unidade CHECK (unidade_medida IN ('kg', 'g', 'l', 'ml', 'un')),
    CONSTRAINT ck_formulacao_item_perda CHECK (perda_percentual IS NULL OR perda_percentual BETWEEN 0 AND 100),
    CONSTRAINT ck_formulacao_item_ordem CHECK (ordem >= 0)
);

CREATE INDEX idx_formulacao_item_formulacao ON formulacao_item(formulacao_id, ordem);
CREATE TRIGGER trg_formulacao_updated_at BEFORE UPDATE ON formulacao
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE formulacao ENABLE ROW LEVEL SECURITY;
ALTER TABLE formulacao_item ENABLE ROW LEVEL SECURITY;
CREATE POLICY service_role_full_access_formulacao ON formulacao FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_full_access_formulacao_item ON formulacao_item FOR ALL TO service_role USING (true) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON formulacao TO authenticated;
GRANT SELECT, INSERT, DELETE ON formulacao_item TO authenticated;
CREATE POLICY formulacao_leitura ON formulacao FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('precificacao.ler')
            OR usuario_tem_permissao('precificacao.editar')));
CREATE POLICY formulacao_insercao ON formulacao FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('precificacao.editar')));
CREATE POLICY formulacao_alteracao ON formulacao FOR UPDATE TO authenticated
    USING ((SELECT usuario_tem_permissao('precificacao.editar')))
    WITH CHECK ((SELECT usuario_tem_permissao('precificacao.editar')));
CREATE POLICY formulacao_item_leitura ON formulacao_item FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM formulacao f WHERE f.id = formulacao_id));
CREATE POLICY formulacao_item_insercao ON formulacao_item FOR INSERT TO authenticated
    WITH CHECK (EXISTS (SELECT 1 FROM formulacao f WHERE f.id = formulacao_id)
                AND (SELECT usuario_tem_permissao('precificacao.editar')));
CREATE POLICY formulacao_item_exclusao ON formulacao_item FOR DELETE TO authenticated
    USING (EXISTS (SELECT 1 FROM formulacao f WHERE f.id = formulacao_id)
           AND (SELECT usuario_tem_permissao('precificacao.editar')));

-- Substitui a lista toda em uma transacao; validacoes/FKs tambem sao aplicadas no banco.
CREATE FUNCTION salvar_itens_formulacao(p_formulacao_id UUID, p_itens JSONB)
RETURNS VOID LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
    IF NOT usuario_tem_permissao('precificacao.editar') THEN
        RAISE EXCEPTION 'Permissao insuficiente' USING ERRCODE = '42501';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM formulacao WHERE id = p_formulacao_id) THEN
        RAISE EXCEPTION 'Formulacao nao encontrada' USING ERRCODE = 'P0002';
    END IF;
    IF jsonb_typeof(p_itens) <> 'array' THEN
        RAISE EXCEPTION 'Itens deve ser uma lista' USING ERRCODE = '22023';
    END IF;
    UPDATE formulacao SET updated_by = auth.uid() WHERE id = p_formulacao_id;
    DELETE FROM formulacao_item WHERE formulacao_id = p_formulacao_id;
    INSERT INTO formulacao_item (
        formulacao_id, tipo_insumo, materia_prima_id, embalagem_id,
        quantidade, unidade_medida, perda_percentual, ordem
    )
    SELECT p_formulacao_id, item->>'tipo_insumo',
           NULLIF(item->>'materia_prima_id', '')::UUID,
           NULLIF(item->>'embalagem_id', '')::UUID,
           (item->>'quantidade')::NUMERIC, item->>'unidade_medida',
           NULLIF(item->>'perda_percentual', '')::NUMERIC, posicao - 1
    FROM jsonb_array_elements(p_itens) WITH ORDINALITY AS entrada(item, posicao);
END;
$$;
REVOKE EXECUTE ON FUNCTION salvar_itens_formulacao(UUID, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION salvar_itens_formulacao(UUID, JSONB) TO authenticated;
