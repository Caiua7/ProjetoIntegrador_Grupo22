-- ============================================================
-- Migration: cenários versionados da precificação
-- Issue #63 (US31) — Sprint 4
-- Executar via: supabase db push
--
-- Cada negociação gera várias versões de cenário. Uma versão salva é
-- imutável: guarda a entrada do motor, o resultado, o volume, a versão do
-- motor e a data do cálculo (a data em que câmbio e parâmetros globais
-- foram lidos, ver #49). Corrigir um cenário é salvar uma nova versão; a
-- anterior continua consultável e igual, para reconstruir a decisão meses
-- depois.
--
-- A vigente de uma precificação é a de maior número de versão.
-- ============================================================

CREATE TABLE cenario (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    precificacao_id     UUID            NOT NULL REFERENCES precificacao (id),
    versao              INTEGER         NOT NULL,
    cenario_origem_id   UUID            NULL REFERENCES cenario (id),
    observacao          VARCHAR(500)    NULL,

    volume              NUMERIC(14, 3)  NULL,
    data_calculo        DATE            NOT NULL DEFAULT current_date,
    versao_motor        VARCHAR(30)     NOT NULL,
    entrada             JSONB           NOT NULL,
    resultado           JSONB           NOT NULL,

    -- Indicadores lidos do resultado, para listar e comparar sem abrir o JSON
    preco_bruto                     NUMERIC GENERATED ALWAYS AS ((resultado ->> 'preco_bruto')::NUMERIC) STORED,
    preco_bruto_sem_ipi             NUMERIC GENERATED ALWAYS AS ((resultado ->> 'preco_bruto_sem_ipi')::NUMERIC) STORED,
    custo_total                     NUMERIC GENERATED ALWAYS AS ((resultado ->> 'custo_total')::NUMERIC) STORED,
    margem_contribuicao_valor       NUMERIC GENERATED ALWAYS AS ((resultado ->> 'margem_contribuicao_valor')::NUMERIC) STORED,
    margem_contribuicao_percentual  NUMERIC GENERATED ALWAYS AS ((resultado ->> 'margem_contribuicao_percentual')::NUMERIC) STORED,

    created_by          UUID            NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_cenario_versao       UNIQUE (precificacao_id, versao),
    CONSTRAINT ck_cenario_versao       CHECK (versao > 0),
    CONSTRAINT ck_cenario_volume       CHECK (volume IS NULL OR volume > 0),
    CONSTRAINT ck_cenario_json         CHECK (jsonb_typeof(entrada) = 'object' AND jsonb_typeof(resultado) = 'object'),
    CONSTRAINT ck_cenario_origem       CHECK (cenario_origem_id IS DISTINCT FROM id)
);

CREATE INDEX idx_cenario_origem ON cenario (cenario_origem_id);

-- ============================================================
-- IMUTABILIDADE
-- Vale para todos os papéis, inclusive o backend (service_role): versão
-- salva não muda nem some. TRUNCATE é barrado pela auditoria.
-- ============================================================
CREATE FUNCTION impedir_alteracao_cenario()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'a versão % do cenário já foi salva e não pode ser alterada nem excluída; salve uma nova versão',
        OLD.versao
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TRIGGER trg_cenario_imutavel
    BEFORE UPDATE OR DELETE ON cenario
    FOR EACH ROW
    EXECUTE FUNCTION impedir_alteracao_cenario();

-- ============================================================
-- GRAVAÇÃO DE UMA NOVA VERSÃO
-- SECURITY INVOKER: o RLS de quem chama vale. O SELECT ... FOR UPDATE na
-- precificação exige poder alterá-la (precificacao.editar na carteira) e
-- serializa duas gravações simultâneas, para o número da versão não se
-- repetir.
-- ============================================================
CREATE FUNCTION salvar_cenario(
    p_precificacao_id   UUID,
    p_entrada           JSONB,
    p_resultado         JSONB,
    p_versao_motor      TEXT,
    p_volume            NUMERIC DEFAULT NULL,
    p_observacao        TEXT DEFAULT NULL,
    p_cenario_origem_id UUID DEFAULT NULL
)
RETURNS cenario
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_versao  INTEGER;
    v_cenario cenario;
BEGIN
    PERFORM 1 FROM precificacao WHERE id = p_precificacao_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'precificação não encontrada' USING ERRCODE = 'no_data_found';
    END IF;

    IF p_cenario_origem_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM cenario WHERE id = p_cenario_origem_id AND precificacao_id = p_precificacao_id
    ) THEN
        RAISE EXCEPTION 'o cenário de origem não pertence a esta precificação' USING ERRCODE = 'invalid_parameter_value';
    END IF;

    SELECT COALESCE(max(versao), 0) + 1 INTO v_versao FROM cenario WHERE precificacao_id = p_precificacao_id;

    INSERT INTO cenario (
        precificacao_id, versao, cenario_origem_id, observacao, volume,
        versao_motor, entrada, resultado, created_by
    )
    VALUES (
        p_precificacao_id, v_versao, p_cenario_origem_id, p_observacao, p_volume,
        p_versao_motor, p_entrada, p_resultado, usuario_da_sessao()
    )
    RETURNING * INTO v_cenario;

    RETURN v_cenario;
END;
$$;

REVOKE EXECUTE ON FUNCTION salvar_cenario(UUID, JSONB, JSONB, TEXT, NUMERIC, TEXT, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION salvar_cenario(UUID, JSONB, JSONB, TEXT, NUMERIC, TEXT, UUID) TO authenticated, service_role;

-- ============================================================
-- RLS
-- A versão guarda custo e margem, então ler a tabela exige `custo.ler`,
-- além de alcançar a precificação (a subconsulta passa pelo RLS dela,
-- que aplica precificacao.ler e a carteira). Sem UPDATE e DELETE.
-- ============================================================
ALTER TABLE cenario ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_cenario"
    ON cenario FOR ALL TO service_role
    USING (true) WITH CHECK (true);

GRANT SELECT, INSERT ON cenario TO authenticated;

CREATE POLICY cenario_leitura ON cenario FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('custo.ler'))
           AND EXISTS (SELECT 1 FROM precificacao p WHERE p.id = precificacao_id));

CREATE POLICY cenario_insercao ON cenario FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('precificacao.editar'))
                AND EXISTS (SELECT 1 FROM precificacao p WHERE p.id = precificacao_id));

-- ============================================================
-- PREÇO DAS VERSÕES SEM CUSTO
-- Para quem negocia (precificacao.ler sem custo.ler, como a executiva de
-- contas): número da versão, volume e preço, nunca custo nem margem. A
-- visão roda como dona da tabela e aplica ela mesma a permissão e a
-- carteira; security_barrier impede que um filtro do usuário vaze linhas.
-- ============================================================
CREATE VIEW cenario_preco WITH (security_barrier = true) AS
SELECT
    c.id,
    c.precificacao_id,
    c.versao,
    c.volume,
    c.data_calculo,
    c.preco_bruto,
    c.preco_bruto_sem_ipi,
    c.versao_motor,
    c.created_at,
    c.versao = max(c.versao) OVER (PARTITION BY c.precificacao_id) AS vigente
FROM cenario c
JOIN precificacao p ON p.id = c.precificacao_id
WHERE usuario_tem_permissao('precificacao.ler')
  AND usuario_acessa_cliente(p.cliente_id);

REVOKE ALL ON cenario_preco FROM PUBLIC, anon;
GRANT SELECT ON cenario_preco TO authenticated, service_role;

SELECT habilitar_auditoria('cenario');
