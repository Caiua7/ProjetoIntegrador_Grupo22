-- ============================================================
-- Fecha o bypass de persistência de cenários pela API do banco.
-- A partir desta migration, somente a API (service_role) pode executar a
-- função de gravação. A função valida de novo usuário, permissão, carteira,
-- estado da precificação e provenance do resultado antes de persistir.
-- Aplicar em janela coordenada com o deploy da API que chama
-- `salvar_cenario_seguro`; ver docs/migracoes-seguranca-workflow.md.
-- ============================================================

REVOKE EXECUTE ON FUNCTION salvar_cenario(UUID, JSONB, JSONB, TEXT, NUMERIC, TEXT, UUID)
    FROM PUBLIC, anon, authenticated, service_role;
DROP FUNCTION salvar_cenario(UUID, JSONB, JSONB, TEXT, NUMERIC, TEXT, UUID);

REVOKE INSERT ON cenario FROM anon, authenticated;

CREATE FUNCTION salvar_cenario_seguro(
    p_usuario_id        UUID,
    p_precificacao_id   UUID,
    p_entrada           JSONB,
    p_resultado         JSONB,
    p_versao_motor      TEXT,
    p_volume            NUMERIC,
    p_observacao        TEXT,
    p_cenario_origem_id UUID
)
RETURNS cenario
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_versao      INTEGER;
    v_status      VARCHAR(20);
    v_cenario     cenario;
    v_carteira_id UUID;
BEGIN
    IF p_usuario_id IS NULL OR NOT EXISTS (
        SELECT 1
        FROM usuario u
        JOIN perfil_permissao pp ON pp.perfil_id = u.perfil_id
        WHERE u.id = p_usuario_id
          AND u.ativo
          AND pp.permissao_codigo = 'precificacao.editar'
    ) THEN
        RAISE EXCEPTION 'usuário ativo sem permissão para editar precificações'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT p.status, c.carteira_id
      INTO v_status, v_carteira_id
      FROM precificacao p
      JOIN cliente c ON c.id = p.cliente_id
     WHERE p.id = p_precificacao_id
       AND (
           EXISTS (
               SELECT 1 FROM perfil_permissao pp
               JOIN usuario u ON u.perfil_id = pp.perfil_id
               WHERE u.id = p_usuario_id AND u.ativo
                 AND pp.permissao_codigo = 'carteira.todas'
           )
           OR (
               c.carteira_id IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM usuario_carteira uc
                   WHERE uc.usuario_id = p_usuario_id AND uc.carteira_id = c.carteira_id
               )
           )
       )
     FOR UPDATE OF p;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'precificação não encontrada ou fora da carteira do usuário'
            USING ERRCODE = 'no_data_found';
    END IF;

    IF v_status NOT IN ('em_preenchimento', 'reprovado') THEN
        RAISE EXCEPTION 'só é permitido salvar cenários enquanto a precificação está em preenchimento ou reprovada'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    IF jsonb_typeof(p_entrada) IS DISTINCT FROM 'object'
       OR jsonb_typeof(p_resultado) IS DISTINCT FROM 'object'
       OR (p_resultado #>> '{metadata,is_mock}') IS DISTINCT FROM 'false'
       OR (p_resultado #>> '{metadata,origem}') IS DISTINCT FROM 'pricing_core'
       OR (p_resultado #>> '{metadata,versao_motor}') IS DISTINCT FROM p_versao_motor THEN
        RAISE EXCEPTION 'somente resultado calculado pelo motor real pode ser salvo como cenário'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    IF p_cenario_origem_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM cenario
        WHERE id = p_cenario_origem_id AND precificacao_id = p_precificacao_id
    ) THEN
        RAISE EXCEPTION 'o cenário de origem não pertence a esta precificação'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    SELECT COALESCE(max(versao), 0) + 1
      INTO v_versao
      FROM cenario
     WHERE precificacao_id = p_precificacao_id;

    PERFORM set_config('neoprice.usuario_id', p_usuario_id::text, true);

    INSERT INTO cenario (
        precificacao_id, versao, cenario_origem_id, observacao, volume,
        versao_motor, entrada, resultado, created_by
    )
    VALUES (
        p_precificacao_id, v_versao, p_cenario_origem_id, p_observacao, p_volume,
        p_versao_motor, p_entrada, p_resultado, p_usuario_id
    )
    RETURNING * INTO v_cenario;

    RETURN v_cenario;
END;
$$;

REVOKE ALL ON FUNCTION salvar_cenario_seguro(UUID, UUID, JSONB, JSONB, TEXT, NUMERIC, TEXT, UUID)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION salvar_cenario_seguro(UUID, UUID, JSONB, JSONB, TEXT, NUMERIC, TEXT, UUID)
    TO service_role;
