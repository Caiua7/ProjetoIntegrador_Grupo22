-- ============================================================
-- Migration: perfis, permissões nomeadas, carteiras de clientes e
-- políticas de RLS por perfil e por carteira
-- Issue #45 (US04) — Sprint 1
-- Executar via: supabase db push
--
-- Abordagem (ver docs/controle-de-acesso.md):
--   - O usuário autentica pelo Supabase Auth; `usuario.id` é o mesmo UUID
--     de auth.users e as políticas identificam quem consulta por auth.uid().
--   - O perfil do usuário dá um conjunto de permissões nomeadas; a
--     carteira limita QUAIS clientes e precificações ele alcança.
--   - As políticas valem para o papel `authenticated`. O `service_role`
--     (backend) continua com acesso total e o `anon` não recebe nada.
-- ============================================================

-- ============================================================
-- TABELA: perfil
-- ============================================================
CREATE TABLE perfil (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(40)     NOT NULL,
    nome            VARCHAR(80)     NOT NULL,
    descricao       VARCHAR(300)    NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_perfil_codigo UNIQUE (codigo)
);

CREATE TRIGGER trg_perfil_updated_at
    BEFORE UPDATE ON perfil
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: permissao
-- Permissão nomeada no formato <recurso>.<ação>; o código é a chave,
-- porque é ele que as políticas e a API citam.
-- ============================================================
CREATE TABLE permissao (
    codigo          VARCHAR(60)     PRIMARY KEY,
    descricao       VARCHAR(300)    NOT NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT ck_permissao_codigo CHECK (codigo ~ '^[a-z_]+\.[a-z_]+$')
);

CREATE TRIGGER trg_permissao_updated_at
    BEFORE UPDATE ON permissao
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: perfil_permissao
-- ============================================================
CREATE TABLE perfil_permissao (
    perfil_id           UUID            NOT NULL REFERENCES perfil (id) ON DELETE CASCADE,
    permissao_codigo    VARCHAR(60)     NOT NULL REFERENCES permissao (codigo) ON DELETE CASCADE,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT pk_perfil_permissao PRIMARY KEY (perfil_id, permissao_codigo)
);

CREATE INDEX idx_perfil_permissao_permissao ON perfil_permissao (permissao_codigo);

-- ============================================================
-- TABELA: usuario
-- Dados de aplicação do usuário. O id é o de auth.users do Supabase
-- (sem FK hard, para o schema não depender do schema auth).
-- ============================================================
CREATE TABLE usuario (
    id              UUID            PRIMARY KEY,

    nome            VARCHAR(150)    NOT NULL,
    email           VARCHAR(180)    NOT NULL,
    perfil_id       UUID            NOT NULL REFERENCES perfil (id),

    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_usuario_email UNIQUE (email)
);

CREATE INDEX idx_usuario_perfil ON usuario (perfil_id);
CREATE INDEX idx_usuario_ativo  ON usuario (ativo);

CREATE TRIGGER trg_usuario_updated_at
    BEFORE UPDATE ON usuario
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: carteira
-- ============================================================
CREATE TABLE carteira (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo          VARCHAR(30)     NOT NULL,
    nome            VARCHAR(120)    NOT NULL,

    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_by      UUID            NULL,
    updated_by      UUID            NULL,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_carteira_codigo UNIQUE (codigo)
);

CREATE TRIGGER trg_carteira_updated_at
    BEFORE UPDATE ON carteira
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABELA: usuario_carteira
-- ============================================================
CREATE TABLE usuario_carteira (
    usuario_id      UUID            NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    carteira_id     UUID            NOT NULL REFERENCES carteira (id) ON DELETE CASCADE,

    created_by      UUID            NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT pk_usuario_carteira PRIMARY KEY (usuario_id, carteira_id)
);

CREATE INDEX idx_usuario_carteira_carteira ON usuario_carteira (carteira_id);

-- ============================================================
-- cliente.carteira_id
-- Cliente sem carteira só aparece para quem tem `carteira.todas`.
-- ============================================================
ALTER TABLE cliente ADD COLUMN carteira_id UUID NULL REFERENCES carteira (id);

CREATE INDEX idx_cliente_carteira ON cliente (carteira_id);

-- ============================================================
-- TABELA: precificacao
-- Cabeçalho mínimo, só com o que a regra de acesso precisa: a carteira
-- vem do cliente. Os campos comerciais e fiscais do cabeçalho e os
-- cenários entram na US29.
-- ============================================================
CREATE TABLE precificacao (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    codigo                  VARCHAR(30)     NOT NULL,
    cliente_id              UUID            NOT NULL REFERENCES cliente (id),
    produto_id              UUID            NOT NULL REFERENCES produto (id),
    modalidade_comercial    VARCHAR(40)     NOT NULL,
    status                  VARCHAR(20)     NOT NULL DEFAULT 'em_preenchimento',

    created_by              UUID            NULL,
    updated_by              UUID            NULL,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_precificacao_codigo UNIQUE (codigo),
    -- Mesmos valores de ModalidadeComercial no contrato do motor
    CONSTRAINT ck_precificacao_modalidade CHECK (modalidade_comercial IN
        ('full_service_nacional', 'full_service_exportacao', 'industrializacao_por_encomenda')),
    CONSTRAINT ck_precificacao_status CHECK (status IN
        ('em_preenchimento', 'em_aprovacao', 'aprovado', 'reprovado'))
);

CREATE INDEX idx_precificacao_cliente ON precificacao (cliente_id);
CREATE INDEX idx_precificacao_produto ON precificacao (produto_id);
CREATE INDEX idx_precificacao_status  ON precificacao (status);

CREATE TRIGGER trg_precificacao_updated_at
    BEFORE UPDATE ON precificacao
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- FUNÇÕES DE AUTORIZAÇÃO
-- SECURITY DEFINER: leem usuario, perfil_permissao e usuario_carteira
-- sem passar pelo RLS dessas tabelas (evita recursão entre políticas) e
-- só devolvem um booleano sobre quem está consultando.
-- ============================================================

-- O usuário autenticado está ativo e seu perfil tem a permissão?
CREATE FUNCTION usuario_tem_permissao(p_permissao TEXT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path FROM CURRENT
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM usuario u
        JOIN perfil_permissao pp ON pp.perfil_id = u.perfil_id
        WHERE u.id = auth.uid()
          AND u.ativo
          AND pp.permissao_codigo = p_permissao
    );
$$;

-- O usuário autenticado alcança a carteira? (NULL = cliente sem carteira)
CREATE FUNCTION usuario_acessa_carteira(p_carteira_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path FROM CURRENT
AS $$
    SELECT usuario_tem_permissao('carteira.todas')
        OR EXISTS (
            SELECT 1
            FROM usuario u
            JOIN usuario_carteira uc ON uc.usuario_id = u.id
            WHERE u.id = auth.uid()
              AND u.ativo
              AND uc.carteira_id = p_carteira_id
        );
$$;

-- O usuário autenticado alcança a carteira do cliente?
CREATE FUNCTION usuario_acessa_cliente(p_cliente_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path FROM CURRENT
AS $$
    SELECT COALESCE(
        (SELECT usuario_acessa_carteira(c.carteira_id) FROM cliente c WHERE c.id = p_cliente_id),
        FALSE
    );
$$;

REVOKE EXECUTE ON FUNCTION usuario_tem_permissao(TEXT)   FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION usuario_acessa_carteira(UUID) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION usuario_acessa_cliente(UUID)  FROM PUBLIC;

GRANT EXECUTE ON FUNCTION usuario_tem_permissao(TEXT)   TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION usuario_acessa_carteira(UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION usuario_acessa_cliente(UUID)  TO authenticated, service_role;

-- ============================================================
-- RLS nas tabelas novas (service_role segue com acesso total)
-- ============================================================
ALTER TABLE perfil           ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissao        ENABLE ROW LEVEL SECURITY;
ALTER TABLE perfil_permissao ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuario          ENABLE ROW LEVEL SECURITY;
ALTER TABLE carteira         ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuario_carteira ENABLE ROW LEVEL SECURITY;
ALTER TABLE precificacao     ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_perfil"
    ON perfil FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_permissao"
    ON permissao FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_perfil_permissao"
    ON perfil_permissao FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_usuario"
    ON usuario FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_carteira"
    ON carteira FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_usuario_carteira"
    ON usuario_carteira FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access_precificacao"
    ON precificacao FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================
-- POLÍTICAS POR PERFIL — tabelas sem recorte de carteira
-- Uma permissão para ler e outra para inserir/alterar. Não há política
-- nem GRANT de DELETE: cadastro é inativado, não apagado.
-- O (SELECT ...) em volta da função faz o Postgres avaliá-la uma vez por
-- consulta, e não uma vez por linha.
-- ============================================================
DO $$
DECLARE
    regra RECORD;
BEGIN
    FOR regra IN
        SELECT * FROM (VALUES
            -- tabela,          permissão de leitura,   permissão de escrita
            ('uf',              'cadastro.ler',         'cadastro.editar'),
            ('municipio',       'cadastro.ler',         'cadastro.editar'),
            ('cep',             'cadastro.ler',         'cadastro.editar'),
            ('ncm',             'cadastro.ler',         'cadastro.editar'),
            ('fornecedor',      'cadastro.ler',         'cadastro.editar'),
            ('materia_prima',   'cadastro.ler',         'cadastro.editar'),
            ('embalagem',       'cadastro.ler',         'cadastro.editar'),
            ('produto',         'cadastro.ler',         'cadastro.editar'),
            ('aliquota_fiscal', 'parametro_fiscal.ler', 'parametro_fiscal.editar'),
            ('linha_producao',  'custo.ler',            'custo.editar'),
            ('produtividade',   'custo.ler',            'custo.editar')
        ) AS r (tabela, ler, editar)
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE ON %I TO authenticated', regra.tabela);

        EXECUTE format(
            'CREATE POLICY %I ON %I FOR SELECT TO authenticated '
            'USING ((SELECT usuario_tem_permissao(%L)))',
            regra.tabela || '_leitura', regra.tabela, regra.ler);

        EXECUTE format(
            'CREATE POLICY %I ON %I FOR INSERT TO authenticated '
            'WITH CHECK ((SELECT usuario_tem_permissao(%L)))',
            regra.tabela || '_insercao', regra.tabela, regra.editar);

        EXECUTE format(
            'CREATE POLICY %I ON %I FOR UPDATE TO authenticated '
            'USING ((SELECT usuario_tem_permissao(%L))) '
            'WITH CHECK ((SELECT usuario_tem_permissao(%L)))',
            regra.tabela || '_alteracao', regra.tabela, regra.editar, regra.editar);
    END LOOP;
END;
$$;

-- ============================================================
-- POLÍTICAS POR PERFIL E CARTEIRA — cliente
-- ============================================================
GRANT SELECT, INSERT, UPDATE ON cliente TO authenticated;

CREATE POLICY "cliente_leitura"
    ON cliente FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('cliente.ler'))
           AND usuario_acessa_carteira(carteira_id));

CREATE POLICY "cliente_insercao"
    ON cliente FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('cliente.editar'))
                AND usuario_acessa_carteira(carteira_id));

-- WITH CHECK impede mover o cliente para uma carteira fora do alcance
CREATE POLICY "cliente_alteracao"
    ON cliente FOR UPDATE TO authenticated
    USING ((SELECT usuario_tem_permissao('cliente.editar'))
           AND usuario_acessa_carteira(carteira_id))
    WITH CHECK ((SELECT usuario_tem_permissao('cliente.editar'))
                AND usuario_acessa_carteira(carteira_id));

-- ============================================================
-- POLÍTICAS POR PERFIL E CARTEIRA — precificacao
-- A carteira é a do cliente da precificação. Quem aprova também altera
-- (muda o status); a regra de transição de status é do workflow de
-- aprovação, não do RLS. Sem DELETE: o histórico não se apaga (RF09).
-- ============================================================
GRANT SELECT, INSERT, UPDATE ON precificacao TO authenticated;

CREATE POLICY "precificacao_leitura"
    ON precificacao FOR SELECT TO authenticated
    USING ((SELECT usuario_tem_permissao('precificacao.ler'))
           AND usuario_acessa_cliente(cliente_id));

CREATE POLICY "precificacao_insercao"
    ON precificacao FOR INSERT TO authenticated
    WITH CHECK ((SELECT usuario_tem_permissao('precificacao.editar'))
                AND usuario_acessa_cliente(cliente_id));

CREATE POLICY "precificacao_alteracao"
    ON precificacao FOR UPDATE TO authenticated
    USING (((SELECT usuario_tem_permissao('precificacao.editar'))
            OR (SELECT usuario_tem_permissao('precificacao.aprovar')))
           AND usuario_acessa_cliente(cliente_id))
    WITH CHECK (((SELECT usuario_tem_permissao('precificacao.editar'))
                 OR (SELECT usuario_tem_permissao('precificacao.aprovar')))
                AND usuario_acessa_cliente(cliente_id));

-- ============================================================
-- POLÍTICAS — tabelas de controle de acesso
-- Qualquer usuário autenticado lê o catálogo de perfis e permissões (a
-- interface usa para montar o menu); de usuário e carteira, cada um lê
-- só o que é seu. Só `acesso.administrar` altera.
-- ============================================================
GRANT SELECT, INSERT, UPDATE         ON perfil, permissao, usuario, carteira TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON perfil_permissao, usuario_carteira   TO authenticated;

CREATE POLICY "perfil_leitura"
    ON perfil FOR SELECT TO authenticated
    USING (true);

CREATE POLICY "permissao_leitura"
    ON permissao FOR SELECT TO authenticated
    USING (true);

CREATE POLICY "perfil_permissao_leitura"
    ON perfil_permissao FOR SELECT TO authenticated
    USING (true);

CREATE POLICY "usuario_leitura"
    ON usuario FOR SELECT TO authenticated
    USING (id = (SELECT auth.uid())
           OR (SELECT usuario_tem_permissao('acesso.administrar')));

CREATE POLICY "carteira_leitura"
    ON carteira FOR SELECT TO authenticated
    USING (usuario_acessa_carteira(id)
           OR (SELECT usuario_tem_permissao('acesso.administrar')));

CREATE POLICY "usuario_carteira_leitura"
    ON usuario_carteira FOR SELECT TO authenticated
    USING (usuario_id = (SELECT auth.uid())
           OR (SELECT usuario_tem_permissao('acesso.administrar')));

DO $$
DECLARE
    tabela TEXT;
BEGIN
    FOREACH tabela IN ARRAY ARRAY['perfil', 'permissao', 'perfil_permissao', 'usuario', 'carteira', 'usuario_carteira']
    LOOP
        EXECUTE format(
            'CREATE POLICY %I ON %I FOR ALL TO authenticated '
            'USING ((SELECT usuario_tem_permissao(''acesso.administrar''))) '
            'WITH CHECK ((SELECT usuario_tem_permissao(''acesso.administrar'')))',
            tabela || '_administracao', tabela);
    END LOOP;
END;
$$;
