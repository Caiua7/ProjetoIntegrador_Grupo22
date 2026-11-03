-- Cria/atualiza a formulação do produto e substitui todos os itens em uma
-- única transação. Uma falha em qualquer item desfaz também o cabeçalho.
CREATE FUNCTION salvar_formulacao_produto(p_produto_id UUID, p_itens JSONB)
RETURNS VOID
LANGUAGE plpgsql
SET search_path FROM CURRENT
AS $$
DECLARE
    v_formulacao_id UUID;
BEGIN
    IF NOT usuario_tem_permissao('precificacao.editar') THEN
        RAISE EXCEPTION 'Permissao insuficiente' USING ERRCODE = '42501';
    END IF;
    IF p_itens IS NULL OR jsonb_typeof(p_itens) <> 'array' THEN
        RAISE EXCEPTION 'Itens deve ser uma lista' USING ERRCODE = '22023';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM produto WHERE id = p_produto_id AND ativo) THEN
        RAISE EXCEPTION 'Produto ativo nao encontrado' USING ERRCODE = 'P0002';
    END IF;

    INSERT INTO formulacao (produto_id, created_by, updated_by)
    VALUES (p_produto_id, auth.uid(), auth.uid())
    ON CONFLICT (produto_id) DO UPDATE SET updated_by = auth.uid()
    RETURNING id INTO v_formulacao_id;

    DELETE FROM formulacao_item WHERE formulacao_id = v_formulacao_id;
    INSERT INTO formulacao_item (
        formulacao_id, tipo_insumo, materia_prima_id, embalagem_id,
        quantidade, unidade_medida, perda_percentual, ordem
    )
    SELECT v_formulacao_id, item->>'tipo_insumo',
           NULLIF(item->>'materia_prima_id', '')::UUID,
           NULLIF(item->>'embalagem_id', '')::UUID,
           (item->>'quantidade')::NUMERIC, item->>'unidade_medida',
           NULLIF(item->>'perda_percentual', '')::NUMERIC, posicao - 1
    FROM jsonb_array_elements(p_itens) WITH ORDINALITY AS entrada(item, posicao);
END;
$$;

REVOKE EXECUTE ON FUNCTION salvar_formulacao_produto(UUID, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION salvar_formulacao_produto(UUID, JSONB) TO authenticated;
