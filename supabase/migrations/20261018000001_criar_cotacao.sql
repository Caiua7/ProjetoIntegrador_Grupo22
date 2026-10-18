-- US25: cotação de matéria-prima por fornecedor, moeda, validade, prazo e faixa de volume mínimo.

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE cotacao (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    materia_prima_id   uuid NOT NULL REFERENCES materia_prima (id),
    fornecedor_id      uuid NOT NULL REFERENCES fornecedor (id),
    moeda              text NOT NULL DEFAULT 'BRL',
    preco              numeric(18, 6) NOT NULL,
    volume_minimo      numeric(18, 3) NOT NULL DEFAULT 0,
    validade_inicio    date NOT NULL,
    validade_fim       date,
    prazo_entrega_dias integer NOT NULL DEFAULT 0,
    ativo              boolean NOT NULL DEFAULT true,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    created_by         uuid REFERENCES usuario (id),
    updated_by         uuid REFERENCES usuario (id),

    CONSTRAINT cotacao_moeda_iso CHECK (moeda ~ '^[A-Z]{3}$'),
    CONSTRAINT cotacao_preco_nao_negativo CHECK (preco >= 0),
    CONSTRAINT cotacao_volume_minimo_nao_negativo CHECK (volume_minimo >= 0),
    CONSTRAINT cotacao_prazo_nao_negativo CHECK (prazo_entrega_dias >= 0),
    CONSTRAINT cotacao_validade_coerente CHECK (validade_fim IS NULL OR validade_fim >= validade_inicio),
    -- Mesma MP, fornecedor e faixa não pode ter duas cotações ativas vigentes ao mesmo tempo.
    CONSTRAINT cotacao_sem_sobreposicao EXCLUDE USING gist (
        materia_prima_id WITH =,
        fornecedor_id WITH =,
        volume_minimo WITH =,
        daterange(validade_inicio, validade_fim, '[]') WITH &&
    ) WHERE (ativo)
);

COMMENT ON TABLE cotacao IS 'Cotação de MP por fornecedor. A faixa de volume é definida pelo volume_minimo (limite inferior, inclusive).';
COMMENT ON COLUMN cotacao.validade_fim IS 'Último dia de validade (inclusive). Nulo = sem data de fim.';

CREATE INDEX cotacao_materia_prima_validade_idx ON cotacao (materia_prima_id, validade_inicio);
CREATE INDEX cotacao_fornecedor_idx ON cotacao (fornecedor_id);

CREATE FUNCTION cotacao_tocar_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_cotacao_updated_at
    BEFORE UPDATE ON cotacao
    FOR EACH ROW EXECUTE FUNCTION cotacao_tocar_updated_at();

-- Cotações vigentes de uma MP numa data, da menor para a maior faixa.
-- SECURITY INVOKER (padrão): o RLS de quem chama continua valendo.
CREATE FUNCTION cotacoes_vigentes(p_materia_prima_id uuid, p_data date DEFAULT current_date)
RETURNS SETOF cotacao
LANGUAGE sql STABLE AS $$
    SELECT *
    FROM cotacao
    WHERE ativo
      AND materia_prima_id = p_materia_prima_id
      AND validade_inicio <= p_data
      AND (validade_fim IS NULL OR validade_fim >= p_data)
    ORDER BY volume_minimo, validade_inicio DESC, id
$$;

-- Acesso: custo.ler lê, custo.editar grava; ninguém apaga (inativa-se).
ALTER TABLE cotacao ENABLE ROW LEVEL SECURITY;

CREATE POLICY cotacao_select ON cotacao FOR SELECT TO authenticated
    USING (usuario_tem_permissao('custo.ler'));
CREATE POLICY cotacao_insert ON cotacao FOR INSERT TO authenticated
    WITH CHECK (usuario_tem_permissao('custo.editar'));
CREATE POLICY cotacao_update ON cotacao FOR UPDATE TO authenticated
    USING (usuario_tem_permissao('custo.editar'))
    WITH CHECK (usuario_tem_permissao('custo.editar'));

REVOKE ALL ON cotacao FROM anon;
GRANT SELECT, INSERT, UPDATE ON cotacao TO authenticated;
GRANT ALL ON cotacao TO service_role;

REVOKE ALL ON FUNCTION cotacoes_vigentes(uuid, date) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION cotacoes_vigentes(uuid, date) TO authenticated, service_role;

SELECT habilitar_auditoria('cotacao');