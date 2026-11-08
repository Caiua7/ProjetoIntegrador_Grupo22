-- ============================================================
-- Submissão controlada para aprovação (#66).
-- A política inicial é explicitamente DEMONSTRATIVA, não PO-homologada.
-- Ela exige todos os campos do cabeçalho e ao menos um cenário do motor real.
-- Configuração é alterável somente por service_role até uma tela administrativa
-- ser especificada. Ver docs/migracoes-seguranca-workflow.md.
-- ============================================================

ALTER TABLE precificacao
    ADD COLUMN homologacao_pendente BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE politica_submissao (
    id                  SMALLINT PRIMARY KEY CHECK (id = 1),
    modo                TEXT NOT NULL CHECK (modo IN ('demonstracao', 'homologada')),
    campos_obrigatorios TEXT[] NOT NULL,
    exige_cenario_real  BOOLEAN NOT NULL DEFAULT TRUE,
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_politica_submissao_campos CHECK (
        campos_obrigatorios <@ ARRAY['cliente_id','produto_id','modalidade_comercial','uf_destino','frete','regime_tributario']::TEXT[]
    )
);

INSERT INTO politica_submissao (id, modo, campos_obrigatorios, exige_cenario_real)
VALUES (1, 'demonstracao', ARRAY['cliente_id','produto_id','modalidade_comercial','uf_destino','frete','regime_tributario'], TRUE);

ALTER TABLE politica_submissao ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON politica_submissao FROM PUBLIC, anon, authenticated;
GRANT SELECT, UPDATE ON politica_submissao TO service_role;

CREATE TABLE historico_status_precificacao (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    precificacao_id     UUID NOT NULL REFERENCES precificacao(id),
    status_anterior     VARCHAR(20) NOT NULL,
    status_novo         VARCHAR(20) NOT NULL,
    modo                TEXT NOT NULL CHECK (modo IN ('demonstracao', 'homologada')),
    responsavel_id      UUID NOT NULL REFERENCES usuario(id),
    ocorrido_em         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_historico_status_precificacao
    ON historico_status_precificacao (precificacao_id, ocorrido_em DESC);
ALTER TABLE historico_status_precificacao ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON historico_status_precificacao TO authenticated, service_role;
CREATE POLICY historico_status_service_role
    ON historico_status_precificacao FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY historico_status_leitura
    ON historico_status_precificacao FOR SELECT TO authenticated
    USING (
        (SELECT usuario_tem_permissao('precificacao.ler'))
        AND EXISTS (SELECT 1 FROM precificacao p WHERE p.id = precificacao_id)
    );

CREATE FUNCTION avaliar_submissao_precificacao(p_usuario_id UUID, p_precificacao_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_status VARCHAR(20);
    v_cliente_id UUID;
    v_produto_id UUID;
    v_modalidade TEXT;
    v_uf TEXT;
    v_frete TEXT;
    v_regime TEXT;
    v_carteira_id UUID;
    v_modo TEXT;
    v_campos TEXT[];
    v_exige_cenario BOOLEAN;
    v_campo TEXT;
    v_falta BOOLEAN;
    v_faltantes TEXT[] := ARRAY[]::TEXT[];
    v_resultado JSONB;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM usuario u JOIN perfil_permissao pp ON pp.perfil_id = u.perfil_id
        WHERE u.id = p_usuario_id AND u.ativo AND pp.permissao_codigo = 'precificacao.editar'
    ) THEN
        RAISE EXCEPTION 'usuário ativo sem permissão para submeter precificações'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT p.status, p.cliente_id, p.produto_id, p.modalidade_comercial,
           p.uf_destino, p.frete, p.regime_tributario, c.carteira_id
      INTO v_status, v_cliente_id, v_produto_id, v_modalidade, v_uf, v_frete, v_regime, v_carteira_id
      FROM precificacao p JOIN cliente c ON c.id = p.cliente_id
     WHERE p.id = p_precificacao_id
       AND (
           EXISTS (SELECT 1 FROM usuario u JOIN perfil_permissao pp ON pp.perfil_id = u.perfil_id
                   WHERE u.id = p_usuario_id AND u.ativo AND pp.permissao_codigo = 'carteira.todas')
           OR (c.carteira_id IS NOT NULL AND EXISTS (
               SELECT 1 FROM usuario_carteira uc
               WHERE uc.usuario_id = p_usuario_id AND uc.carteira_id = c.carteira_id
           ))
       );
    IF NOT FOUND THEN
        RAISE EXCEPTION 'precificação não encontrada ou fora da carteira do usuário'
            USING ERRCODE = 'no_data_found';
    END IF;

    SELECT modo, campos_obrigatorios, exige_cenario_real
      INTO v_modo, v_campos, v_exige_cenario
      FROM politica_submissao WHERE id = 1;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'política de submissão não configurada'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    IF v_status NOT IN ('em_preenchimento', 'reprovado') THEN
        v_faltantes := array_append(v_faltantes, 'Status precisa ser Em Preenchimento ou Reprovado.');
    END IF;

    FOREACH v_campo IN ARRAY v_campos LOOP
        v_falta := CASE v_campo
            WHEN 'cliente_id' THEN v_cliente_id IS NULL
            WHEN 'produto_id' THEN v_produto_id IS NULL
            WHEN 'modalidade_comercial' THEN v_modalidade IS NULL OR btrim(v_modalidade) = ''
            WHEN 'uf_destino' THEN v_uf IS NULL OR btrim(v_uf) = ''
            WHEN 'frete' THEN v_frete IS NULL OR btrim(v_frete) = ''
            WHEN 'regime_tributario' THEN v_regime IS NULL OR btrim(v_regime) = ''
            ELSE TRUE
        END;
        IF v_falta THEN
            v_faltantes := array_append(v_faltantes, v_campo);
        END IF;
    END LOOP;

    IF v_exige_cenario THEN
        SELECT c.resultado INTO v_resultado
          FROM cenario c
         WHERE c.precificacao_id = p_precificacao_id
         ORDER BY c.versao DESC LIMIT 1;
        IF NOT FOUND THEN
            v_faltantes := array_append(v_faltantes, 'Salve um cenário calculado pelo motor real.');
        ELSIF (v_resultado #>> '{metadata,is_mock}') IS DISTINCT FROM 'false'
           OR (v_resultado #>> '{metadata,origem}') IS DISTINCT FROM 'pricing_core' THEN
            v_faltantes := array_append(v_faltantes, 'O cenário vigente não tem proveniência real válida; recalcule pelo motor real.');
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'pode_submeter', cardinality(v_faltantes) = 0,
        'modo_politica', v_modo,
        'homologacao_pendente', v_modo = 'demonstracao',
        'campos_obrigatorios', to_jsonb(v_campos),
        'motivos_bloqueio', to_jsonb(v_faltantes)
    );
END;
$$;

REVOKE ALL ON FUNCTION avaliar_submissao_precificacao(UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION avaliar_submissao_precificacao(UUID, UUID) TO service_role;

CREATE FUNCTION submeter_precificacao(p_usuario_id UUID, p_precificacao_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_avaliacao JSONB;
    v_anterior VARCHAR(20);
    v_novo VARCHAR(20) := 'em_aprovacao';
    v_modo TEXT;
    v_pendente BOOLEAN;
BEGIN
    SELECT status INTO v_anterior FROM precificacao
     WHERE id = p_precificacao_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'precificação não encontrada' USING ERRCODE = 'no_data_found';
    END IF;

    v_avaliacao := avaliar_submissao_precificacao(p_usuario_id, p_precificacao_id);
    IF NOT COALESCE((v_avaliacao ->> 'pode_submeter')::BOOLEAN, FALSE) THEN
        RAISE EXCEPTION 'submissão bloqueada: %', v_avaliacao -> 'motivos_bloqueio'
            USING ERRCODE = 'check_violation';
    END IF;

    v_modo := v_avaliacao ->> 'modo_politica';
    v_pendente := COALESCE((v_avaliacao ->> 'homologacao_pendente')::BOOLEAN, TRUE);
    PERFORM set_config('neoprice.usuario_id', p_usuario_id::TEXT, true);
    PERFORM set_config('neoprice.submissao_precificacao', 'true', true);
    UPDATE precificacao
       SET status = v_novo,
           homologacao_pendente = v_pendente,
           updated_by = p_usuario_id
     WHERE id = p_precificacao_id;
    INSERT INTO historico_status_precificacao (
        precificacao_id, status_anterior, status_novo, modo, responsavel_id
    ) VALUES (p_precificacao_id, v_anterior, v_novo, v_modo, p_usuario_id);

    RETURN v_avaliacao || jsonb_build_object('status', v_novo);
END;
$$;

REVOKE ALL ON FUNCTION submeter_precificacao(UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION submeter_precificacao(UUID, UUID) TO service_role;

CREATE FUNCTION proteger_transicao_e_edicao_precificacao()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF current_user IN ('anon', 'authenticated') THEN
        IF NEW.status IS DISTINCT FROM OLD.status
           AND NEW.status NOT IN ('aprovado', 'reprovado')
           AND NOT (NEW.status = 'em_aprovacao'
                    AND current_setting('neoprice.submissao_precificacao', true) = 'true') THEN
            RAISE EXCEPTION 'mudança de status exige o fluxo de submissão/decisão autorizado'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF OLD.status IN ('em_aprovacao', 'aprovado') AND (
            NEW.cliente_id IS DISTINCT FROM OLD.cliente_id
            OR NEW.produto_id IS DISTINCT FROM OLD.produto_id
            OR NEW.modalidade_comercial IS DISTINCT FROM OLD.modalidade_comercial
            OR NEW.uf_destino IS DISTINCT FROM OLD.uf_destino
            OR NEW.frete IS DISTINCT FROM OLD.frete
            OR NEW.regime_tributario IS DISTINCT FROM OLD.regime_tributario
        ) THEN
            RAISE EXCEPTION 'precificação submetida ou aprovada não pode ser editada'
                USING ERRCODE = 'object_not_in_prerequisite_state';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_precificacao_proteger_transicao_edicao
    BEFORE UPDATE ON precificacao
    FOR EACH ROW EXECUTE FUNCTION proteger_transicao_e_edicao_precificacao();

CREATE FUNCTION impedir_aprovacao_de_demo()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_pendente BOOLEAN;
    v_resultado JSONB;
BEGIN
    IF NEW.decisao <> 'aprovado' THEN
        RETURN NEW;
    END IF;
    SELECT homologacao_pendente INTO v_pendente
      FROM precificacao WHERE id = NEW.precificacao_id;
    IF COALESCE(v_pendente, FALSE) THEN
        RAISE EXCEPTION 'precificação submetida sob política demonstrativa não pode ser aprovada como homologada'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;
    SELECT resultado INTO v_resultado
      FROM cenario WHERE precificacao_id = NEW.precificacao_id
      ORDER BY versao DESC LIMIT 1;
    IF FOUND AND (
        (v_resultado #>> '{metadata,is_mock}') IS DISTINCT FROM 'false'
        OR (v_resultado #>> '{metadata,origem}') = 'demonstracao'
    ) THEN
        RAISE EXCEPTION 'cenário demonstrativo não pode ser aprovado como resultado real'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_decisao_aprovacao_bloquear_demo
    BEFORE INSERT ON decisao_aprovacao
    FOR EACH ROW EXECUTE FUNCTION impedir_aprovacao_de_demo();

REVOKE ALL ON FUNCTION impedir_aprovacao_de_demo() FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE politica_submissao IS
    'Critérios configuráveis de submissão; modo inicial demonstrativo e não homologado pelo PO.';
COMMENT ON COLUMN precificacao.homologacao_pendente IS
    'True quando submetida sob política demonstrativa; bloqueia decisão aprovada.';
