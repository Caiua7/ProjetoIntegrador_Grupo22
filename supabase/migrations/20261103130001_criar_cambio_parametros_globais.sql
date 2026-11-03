-- ============================================================
-- Migration: câmbio por moeda e parâmetros globais do cálculo
-- Issue #49 (US13, US14) — Sprint 2
-- Executar via: supabase db push
--
-- Os dois cadastros são históricos: cada valor vale a partir de uma data
-- e o vigente em uma data é o de data mais recente que não seja
-- posterior a ela. Pela aplicação (papel `authenticated`), o passado é
-- imutável: não se cria, altera nem apaga valor com data anterior a hoje.
-- Mudar um parâmetro é cadastrar uma nova vigência; assim um cálculo
-- feito em uma data, refeito por essa data, encontra os mesmos valores e
-- os cenários antigos não são reescritos.
-- ============================================================

-- ============================================================
-- PROTEÇÃO DO HISTÓRICO
-- Argumento: nome da coluna de data. Vale só para o papel da aplicação;
-- cargas de sistema (seed, migration) podem corrigir o histórico.
-- ============================================================
CREATE FUNCTION proteger_historico_vigente()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_coluna TEXT := TG_ARGV[0];
BEGIN
    IF current_user <> 'authenticated' THEN
        RETURN COALESCE(NEW, OLD);
    END IF;

    IF TG_OP IN ('UPDATE', 'DELETE') AND (to_jsonb(OLD) ->> v_coluna)::DATE < current_date THEN
        RAISE EXCEPTION 'valor de % já vigente em % faz parte do histórico e não pode ser alterado; cadastre uma nova vigência',
            TG_TABLE_NAME, to_jsonb(OLD) ->> v_coluna
            USING ERRCODE = 'restrict_violation';
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') AND (to_jsonb(NEW) ->> v_coluna)::DATE < current_date THEN
        RAISE EXCEPTION 'a vigência de % não pode começar no passado (%): isso mudaria cálculos já feitos',
            TG_TABLE_NAME, to_jsonb(NEW) ->> v_coluna
            USING ERRCODE = 'restrict_violation';
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$;

-- ============================================================
-- TABELA: cambio
-- `taxa` é quantos reais vale uma unidade da moeda. O custo usa
-- taxa × (1 + margem_seguranca_percentual).
-- ============================================================
CREATE TABLE cambio (
    id                          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    moeda                       CHAR(3)         NOT NULL,
    data_referencia             DATE            NOT NULL,
    taxa                        NUMERIC(14, 6)  NOT NULL,
    margem_seguranca_percentual NUMERIC(7, 6)   NOT NULL DEFAULT 0,
    fonte                       VARCHAR(10)     NOT NULL DEFAULT 'manual',

    created_by                  UUID            NULL,
    updated_by                  UUID            NULL,

    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_cambio_moeda_data UNIQUE (moeda, data_referencia),
    CONSTRAINT ck_cambio_moeda      CHECK (moeda ~ '^[A-Z]{3}$' AND moeda <> 'BRL'),
    CONSTRAINT ck_cambio_taxa       CHECK (taxa > 0),
    CONSTRAINT ck_cambio_margem     CHECK (margem_seguranca_percentual BETWEEN 0 AND 1),
    CONSTRAINT ck_cambio_fonte      CHECK (fonte IN ('manual', 'ptax'))
);

CREATE TRIGGER trg_cambio_updated_at
    BEFORE UPDATE ON cambio
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_cambio_historico
    BEFORE INSERT OR UPDATE OR DELETE ON cambio
    FOR EACH ROW
    EXECUTE FUNCTION proteger_historico_vigente('data_referencia');

-- ============================================================
-- TABELA: parametro_global
-- Percentuais em fração (0.012 = 1,2%), como no contrato do motor; o
-- prazo é em dias inteiros.
-- ============================================================
CREATE TABLE parametro_global (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(40)     NOT NULL,
    valor           NUMERIC(14, 6)  NOT NULL,
    vigencia_inicio DATE            NOT NULL,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_parametro_global UNIQUE (codigo, vigencia_inicio),
    CONSTRAINT ck_parametro_global_codigo CHECK (codigo IN (
        'perda_percentual',
        'taxa_financeira_mensal_percentual',
        'prazo_medio_padrao_dias',
        'desvio_maximo_cotacao_percentual'
    )),
    CONSTRAINT ck_parametro_global_valor CHECK (
        CASE codigo
            WHEN 'prazo_medio_padrao_dias' THEN valor >= 0 AND valor = trunc(valor)
            ELSE valor BETWEEN 0 AND 1
        END
    )
);

CREATE TRIGGER trg_parametro_global_updated_at
    BEFORE UPDATE ON parametro_global
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_parametro_global_historico
    BEFORE INSERT OR UPDATE OR DELETE ON parametro_global
    FOR EACH ROW
    EXECUTE FUNCTION proteger_historico_vigente('vigencia_inicio');

-- ============================================================
-- PERMISSÕES
-- Inseridas aqui para os bancos que já têm perfis; o seed
-- 06_perfil_permissao.sql repete os mesmos vínculos para banco novo.
-- ============================================================
INSERT INTO permissao (codigo, descricao) VALUES
    ('cambio.ler',              'Consultar o câmbio por moeda e data'),
    ('cambio.editar',           'Cadastrar e corrigir câmbio de hoje em diante'),
    ('parametro_global.ler',    'Consultar perda, taxa financeira, prazo padrão e desvio de cotação'),
    ('parametro_global.editar', 'Cadastrar novas vigências dos parâmetros globais')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO perfil_permissao (perfil_id, permissao_codigo)
SELECT p.id, m.permissao_codigo
FROM (VALUES
    ('analista_pricing',     'cambio.ler'),
    ('analista_pricing',     'parametro_global.ler'),
    ('analista_pricing',     'parametro_global.editar'),
    ('gerente_comercial',    'cambio.ler'),
    ('gerente_comercial',    'parametro_global.ler'),
    ('analista_suprimentos', 'cambio.ler'),
    ('analista_suprimentos', 'cambio.editar'),
    ('analista_suprimentos', 'parametro_global.ler'),
    ('administrador',        'cambio.ler'),
    ('administrador',        'cambio.editar'),
    ('administrador',        'parametro_global.ler'),
    ('administrador',        'parametro_global.editar')
) AS m (perfil_codigo, permissao_codigo)
JOIN perfil p ON p.codigo = m.perfil_codigo
ON CONFLICT (perfil_id, permissao_codigo) DO NOTHING;

-- ============================================================
-- RLS, GRANTS E AUDITORIA
-- Sem DELETE para a aplicação: histórico não se apaga.
-- ============================================================
ALTER TABLE cambio           ENABLE ROW LEVEL SECURITY;
ALTER TABLE parametro_global ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_cambio"
    ON cambio FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_parametro_global"
    ON parametro_global FOR ALL TO service_role
    USING (true) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON cambio, parametro_global TO authenticated;

CREATE POLICY cambio_leitura ON cambio FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('cambio.ler')));
CREATE POLICY cambio_insercao ON cambio FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('cambio.editar')));
CREATE POLICY cambio_alteracao ON cambio FOR UPDATE TO authenticated
    USING ((SELECT usuario_tem_permissao('cambio.editar')))
    WITH CHECK ((SELECT usuario_tem_permissao('cambio.editar')));

CREATE POLICY parametro_global_leitura ON parametro_global FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('parametro_global.ler')));
CREATE POLICY parametro_global_insercao ON parametro_global FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('parametro_global.editar')));
CREATE POLICY parametro_global_alteracao ON parametro_global FOR UPDATE TO authenticated
    USING ((SELECT usuario_tem_permissao('parametro_global.editar')))
    WITH CHECK ((SELECT usuario_tem_permissao('parametro_global.editar')));

SELECT habilitar_auditoria('cambio');
SELECT habilitar_auditoria('parametro_global');
