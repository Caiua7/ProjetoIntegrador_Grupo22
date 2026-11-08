-- ============================================================
-- Migration: decisão de aprovação e reprovação da precificação
-- Issue #68 (US37) — Sprint 5
-- Executar via: supabase db push
--
-- Fecha a trilha do workflow de aprovação: quem decidiu, quando, sobre
-- qual versão de cenário e com qual justificativa. Reprovar sem
-- comentário é recusado pelo banco, senão a decisão volta a ser informal.
--
-- Regras:
--   * só se decide uma precificação em `em_aprovacao` (a submissão, que
--     leva de `em_preenchimento` a `em_aprovacao`, é da US35/#66);
--   * decidir exige `precificacao.aprovar` na carteira do cliente;
--   * a reprovação exige comentário; na aprovação ele é opcional;
--   * o responsável e a data vêm da sessão, nunca de quem chama;
--   * a decisão grava o novo status da precificação na mesma transação;
--   * pela aplicação, o status só vira `aprovado` ou `reprovado` por uma
--     decisão registrada aqui;
--   * a decisão salva é imutável e entra na trilha de auditoria (#58).
-- ============================================================

CREATE TABLE decisao_aprovacao (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    precificacao_id     UUID            NOT NULL REFERENCES precificacao (id),
    -- Versão vigente no momento da decisão (#63); nula se não havia cenário
    cenario_id          UUID            NULL REFERENCES cenario (id),
    decisao             VARCHAR(10)     NOT NULL,
    comentario          VARCHAR(2000)   NULL,

    responsavel_id      UUID            NOT NULL REFERENCES usuario (id),
    decidido_em         TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT ck_decisao_aprovacao_decisao CHECK (decisao IN ('aprovado', 'reprovado')),
    CONSTRAINT ck_decisao_aprovacao_comentario_reprovacao
        CHECK (decisao <> 'reprovado' OR (comentario IS NOT NULL AND btrim(comentario, E' \t\r\n') <> ''))
);

CREATE INDEX idx_decisao_aprovacao_precificacao ON decisao_aprovacao (precificacao_id, decidido_em DESC);
CREATE INDEX idx_decisao_aprovacao_responsavel  ON decisao_aprovacao (responsavel_id);
CREATE INDEX idx_decisao_aprovacao_cenario      ON decisao_aprovacao (cenario_id);

-- ============================================================
-- VALIDAÇÃO DA DECISÃO
-- SECURITY INVOKER: o SELECT ... FOR UPDATE passa pelo RLS de quem
-- decide (precificacao.aprovar na carteira) e serializa duas decisões
-- simultâneas sobre a mesma precificação.
-- ============================================================
CREATE FUNCTION validar_decisao_aprovacao()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_status VARCHAR(20);
BEGIN
    NEW.responsavel_id := usuario_da_sessao();
    NEW.decidido_em := now();
    -- Espaço, tabulação e quebra de linha não contam como justificativa
    NEW.comentario := nullif(btrim(NEW.comentario, E' \t\r\n'), '');

    IF NEW.decisao = 'reprovado' AND NEW.comentario IS NULL THEN
        RAISE EXCEPTION 'a reprovação exige um comentário com a justificativa'
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.responsavel_id IS NULL THEN
        RAISE EXCEPTION 'não há usuário na sessão para registrar como responsável pela decisão'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT status INTO v_status FROM precificacao WHERE id = NEW.precificacao_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'precificação não encontrada' USING ERRCODE = 'no_data_found';
    END IF;

    IF v_status <> 'em_aprovacao' THEN
        RAISE EXCEPTION 'só é possível decidir uma precificação em aprovação; esta está em "%"', v_status
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    SELECT id INTO NEW.cenario_id
    FROM cenario
    WHERE precificacao_id = NEW.precificacao_id
    ORDER BY versao DESC
    LIMIT 1;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_decisao_aprovacao_validar
    BEFORE INSERT ON decisao_aprovacao
    FOR EACH ROW
    EXECUTE FUNCTION validar_decisao_aprovacao();

-- ============================================================
-- STATUS DA PRECIFICAÇÃO
-- A decisão grava o status. O marcador `neoprice.decisao_aprovacao` vale
-- só dentro desta transação e diz à guarda abaixo qual decisão autoriza
-- a mudança.
-- ============================================================
CREATE FUNCTION aplicar_decisao_aprovacao()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path FROM CURRENT
AS $$
BEGIN
    PERFORM set_config('neoprice.decisao_aprovacao', NEW.id::text, true);
    UPDATE precificacao
       SET status = NEW.decisao,
           updated_by = NEW.responsavel_id
     WHERE id = NEW.precificacao_id;
    PERFORM set_config('neoprice.decisao_aprovacao', '', true);
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_decisao_aprovacao_aplicar
    AFTER INSERT ON decisao_aprovacao
    FOR EACH ROW
    EXECUTE FUNCTION aplicar_decisao_aprovacao();

-- Pela aplicação (papéis anon e authenticated, que é como o PostgREST
-- conecta), `aprovado` e `reprovado` só se alcançam por uma decisão
-- registrada. Carga de dados e manutenção, que rodam como dono do banco
-- ou service_role, ficam de fora.
CREATE FUNCTION exigir_decisao_para_status()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_decisao TEXT := nullif(current_setting('neoprice.decisao_aprovacao', true), '');
BEGIN
    IF current_user NOT IN ('anon', 'authenticated')
       OR NEW.status NOT IN ('aprovado', 'reprovado')
       OR (TG_OP = 'UPDATE' AND NEW.status IS NOT DISTINCT FROM OLD.status) THEN
        RETURN NEW;
    END IF;

    IF v_decisao IS NOT NULL AND EXISTS (
        SELECT 1
        FROM decisao_aprovacao d
        WHERE d.id = v_decisao::uuid
          AND d.precificacao_id = NEW.id
          AND d.decisao = NEW.status
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'aprovar ou reprovar exige registrar a decisão (decidir_aprovacao), com responsável e comentário'
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

CREATE TRIGGER trg_precificacao_status_por_decisao
    BEFORE INSERT OR UPDATE OF status ON precificacao
    FOR EACH ROW
    EXECUTE FUNCTION exigir_decisao_para_status();

-- ============================================================
-- IMUTABILIDADE
-- Decisão registrada não muda nem some, para nenhum papel. Uma nova
-- rodada de aprovação gera outra decisão. TRUNCATE é barrado pela
-- auditoria.
-- ============================================================
CREATE FUNCTION impedir_alteracao_decisao_aprovacao()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'a decisão de aprovação já foi registrada e não pode ser alterada nem excluída'
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TRIGGER trg_decisao_aprovacao_imutavel
    BEFORE UPDATE OR DELETE ON decisao_aprovacao
    FOR EACH ROW
    EXECUTE FUNCTION impedir_alteracao_decisao_aprovacao();

-- ============================================================
-- REGISTRO PELA API
-- Atalho para o PostgREST (rpc). As regras estão nos gatilhos, então um
-- INSERT direto na tabela segue exatamente o mesmo caminho.
-- ============================================================
CREATE FUNCTION decidir_aprovacao(
    p_precificacao_id UUID,
    p_decisao         TEXT,
    p_comentario      TEXT DEFAULT NULL
)
RETURNS decisao_aprovacao
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_decisao decisao_aprovacao;
BEGIN
    INSERT INTO decisao_aprovacao (precificacao_id, decisao, comentario)
    VALUES (p_precificacao_id, p_decisao, p_comentario)
    RETURNING * INTO v_decisao;

    RETURN v_decisao;
END;
$$;

REVOKE EXECUTE ON FUNCTION decidir_aprovacao(UUID, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decidir_aprovacao(UUID, TEXT, TEXT) TO authenticated, service_role;

-- ============================================================
-- RLS
-- Lê a decisão quem lê a precificação (a subconsulta passa pelo RLS dela,
-- com precificacao.ler e a carteira). Registra quem tem
-- precificacao.aprovar na carteira. Sem UPDATE e DELETE.
-- ============================================================
ALTER TABLE decisao_aprovacao ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_decisao_aprovacao"
    ON decisao_aprovacao FOR ALL TO service_role
    USING (true) WITH CHECK (true);

GRANT SELECT, INSERT ON decisao_aprovacao TO authenticated;

CREATE POLICY decisao_aprovacao_leitura ON decisao_aprovacao FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('precificacao.ler'))
           AND EXISTS (SELECT 1 FROM precificacao p WHERE p.id = precificacao_id));

CREATE POLICY decisao_aprovacao_registro ON decisao_aprovacao FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('precificacao.aprovar'))
                AND EXISTS (SELECT 1 FROM precificacao p WHERE p.id = precificacao_id));

-- ============================================================
-- HISTÓRICO DE DECISÕES COM O NOME DO RESPONSÁVEL
-- O RLS de `usuario` só deixa cada um ler o próprio cadastro, então o nome
-- de quem decidiu vem por esta visão. Ela roda como dona das tabelas e
-- aplica ela mesma a permissão e a carteira; security_barrier impede que
-- um filtro do usuário vaze linhas.
-- ============================================================
CREATE VIEW decisao_aprovacao_historico WITH (security_barrier = true) AS
SELECT
    d.id,
    d.precificacao_id,
    d.cenario_id,
    c.versao AS cenario_versao,
    d.decisao,
    d.comentario,
    d.responsavel_id,
    u.nome AS responsavel_nome,
    d.decidido_em
FROM decisao_aprovacao d
JOIN precificacao p ON p.id = d.precificacao_id
JOIN usuario u ON u.id = d.responsavel_id
LEFT JOIN cenario c ON c.id = d.cenario_id
WHERE usuario_tem_permissao('precificacao.ler')
  AND usuario_acessa_cliente(p.cliente_id);

REVOKE ALL ON decisao_aprovacao_historico FROM PUBLIC, anon;
GRANT SELECT ON decisao_aprovacao_historico TO authenticated, service_role;

SELECT habilitar_auditoria('decisao_aprovacao');
