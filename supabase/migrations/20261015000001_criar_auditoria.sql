-- ============================================================
-- Migration: log imutável de mutações (trilha de auditoria)
-- Issue #58 (US51, RNF05) — Sprint 3
-- Executar via: supabase db push
--
-- Toda criação, alteração e exclusão em tabela do schema gera uma linha
-- em `auditoria`, com usuário, momento, papel do banco e diff. O registro
-- é feito por gatilho no próprio banco: não depende de a API lembrar de
-- auditar, e vale também para quem escreve direto pelo PostgREST.
--
-- Garantias:
--   - A trilha é só de inserção: UPDATE, DELETE e TRUNCATE em `auditoria`
--     são recusados por gatilho, inclusive para o service_role.
--   - Ninguém insere em `auditoria` diretamente; só o gatilho, que roda
--     como dono da tabela (SECURITY DEFINER).
--   - A linha de auditoria nasce na mesma transação da mutação: se a
--     mutação for desfeita, a auditoria também é, e vice-versa.
--
-- Tabela nova: chame `SELECT habilitar_auditoria('<tabela>');` na mesma
-- migration. O teste `test_toda_tabela_tem_auditoria` barra a que ficar
-- sem gatilho.
-- ============================================================

-- ============================================================
-- TABELA: auditoria
-- `registro_id` é a chave primária do registro alterado, em texto; em
-- chave composta, os valores vêm na ordem da chave, separados por '|'.
-- ============================================================
CREATE TABLE auditoria (
    id              BIGINT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    tabela          VARCHAR(63)     NOT NULL,
    registro_id     TEXT            NOT NULL,
    operacao        VARCHAR(6)      NOT NULL,

    usuario_id      UUID            NULL,       -- NULL em carga de seed e tarefa de sistema
    papel           VARCHAR(63)     NOT NULL,   -- authenticated, service_role, postgres...
    transacao_id    BIGINT          NOT NULL DEFAULT txid_current(),

    dados_antes     JSONB           NULL,
    dados_depois    JSONB           NULL,
    diff            JSONB           NULL,       -- só no UPDATE: {"coluna": {"de": ..., "para": ...}}

    ocorrido_em     TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT ck_auditoria_operacao CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE')),
    CONSTRAINT ck_auditoria_dados CHECK (
        (operacao = 'INSERT' AND dados_antes IS NULL     AND dados_depois IS NOT NULL AND diff IS NULL)
     OR (operacao = 'UPDATE' AND dados_antes IS NOT NULL AND dados_depois IS NOT NULL AND diff IS NOT NULL)
     OR (operacao = 'DELETE' AND dados_antes IS NOT NULL AND dados_depois IS NULL     AND diff IS NULL)
    )
);

-- Trilha de um registro em ordem cronológica (consulta por entidade)
CREATE INDEX idx_auditoria_registro ON auditoria (tabela, registro_id, id);
-- O que um usuário alterou em um período
CREATE INDEX idx_auditoria_usuario  ON auditoria (usuario_id, ocorrido_em);

-- ============================================================
-- Imutabilidade
-- ============================================================
CREATE FUNCTION impedir_alteracao_auditoria()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'a trilha de auditoria é imutável: % não é permitido', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

CREATE TRIGGER trg_auditoria_imutavel
    BEFORE UPDATE OR DELETE ON auditoria
    FOR EACH ROW
    EXECUTE FUNCTION impedir_alteracao_auditoria();

CREATE TRIGGER trg_auditoria_sem_truncate
    BEFORE TRUNCATE ON auditoria
    FOR EACH STATEMENT
    EXECUTE FUNCTION impedir_alteracao_auditoria();

-- service_role (backend) só lê. anon e authenticated não têm política:
-- com RLS ativo, não leem nem escrevem nada. A leitura por perfil
-- (permissão de auditoria) entra junto com as políticas da US04.
REVOKE ALL ON auditoria FROM PUBLIC;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON auditoria FROM service_role;
GRANT SELECT ON auditoria TO service_role;

ALTER TABLE auditoria ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_leitura_auditoria"
    ON auditoria FOR SELECT TO service_role
    USING (true);

-- ============================================================
-- FUNÇÕES DE APOIO
-- ============================================================

-- Quem está mutando. Pelo PostgREST é o `sub` do JWT (o mesmo que
-- auth.uid() devolve). O backend, que conecta como service_role, informa
-- o usuário da requisição com:
--     SELECT set_config('neoprice.usuario_id', '<uuid>', true);
CREATE FUNCTION usuario_da_sessao()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(
        nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub',
        nullif(current_setting('neoprice.usuario_id', true), '')
    )::uuid;
$$;

-- Colunas que mudaram entre duas versões do registro. `updated_at` fica de
-- fora: muda em todo UPDATE e já está em `ocorrido_em`.
CREATE FUNCTION auditoria_diff(p_antes JSONB, p_depois JSONB)
RETURNS JSONB
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT COALESCE(
        jsonb_object_agg(coluna, jsonb_build_object('de', p_antes -> coluna, 'para', p_depois -> coluna)),
        '{}'::jsonb
    )
    FROM (SELECT jsonb_object_keys(p_antes) UNION SELECT jsonb_object_keys(p_depois)) AS c (coluna)
    WHERE coluna <> 'updated_at'
      AND (p_antes -> coluna) IS DISTINCT FROM (p_depois -> coluna);
$$;

-- ============================================================
-- GATILHO DE AUDITORIA
-- Recebe como argumentos as colunas da chave primária (passadas por
-- habilitar_auditoria). SECURITY DEFINER para gravar em `auditoria` sem
-- que o papel da sessão tenha INSERT nela; por isso o papel registrado
-- vem do JWT e, sem ele, do usuário da conexão.
-- ============================================================
CREATE FUNCTION registrar_auditoria()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path FROM CURRENT
AS $$
DECLARE
    v_antes     JSONB := CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END;
    v_depois    JSONB := CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END;
    v_diff      JSONB;
    v_registro  TEXT;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        v_diff := auditoria_diff(v_antes, v_depois);
        -- UPDATE que não muda nada não é mutação
        IF v_diff = '{}'::jsonb THEN
            RETURN NULL;
        END IF;
    END IF;

    SELECT string_agg(COALESCE(v_depois, v_antes) ->> coluna, '|' ORDER BY ordem)
    INTO v_registro
    FROM unnest(TG_ARGV) WITH ORDINALITY AS chave (coluna, ordem);

    INSERT INTO auditoria (tabela, registro_id, operacao, usuario_id, papel, dados_antes, dados_depois, diff)
    VALUES (
        TG_TABLE_NAME,
        v_registro,
        TG_OP,
        usuario_da_sessao(),
        COALESCE(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', session_user),
        v_antes,
        v_depois,
        v_diff
    );

    RETURN NULL;
END;
$$;

-- TRUNCATE não passa pelos gatilhos de linha e apagaria sem deixar trilha
CREATE FUNCTION impedir_truncate_auditado()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'TRUNCATE em % não deixa trilha de auditoria; apague as linhas com DELETE', TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

-- Liga a auditoria em uma tabela, identificando o registro pela chave
-- primária. Pode rodar de novo na mesma tabela (recria os gatilhos).
CREATE FUNCTION habilitar_auditoria(p_tabela REGCLASS)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_nome      TEXT;
    v_chave     TEXT;
BEGIN
    SELECT c.relname INTO v_nome FROM pg_class c WHERE c.oid = p_tabela;

    SELECT string_agg(quote_literal(a.attname), ', ' ORDER BY k.ordem)
    INTO v_chave
    FROM pg_index i
    CROSS JOIN LATERAL unnest(i.indkey::int2[]) WITH ORDINALITY AS k (attnum, ordem)
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
    WHERE i.indrelid = p_tabela
      AND i.indisprimary;

    IF v_chave IS NULL THEN
        RAISE EXCEPTION 'tabela % sem chave primária: a auditoria identifica o registro por ela', v_nome;
    END IF;

    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', 'trg_' || v_nome || '_auditoria', p_tabela);
    EXECUTE format(
        'CREATE TRIGGER %I AFTER INSERT OR UPDATE OR DELETE ON %s '
        'FOR EACH ROW EXECUTE FUNCTION registrar_auditoria(%s)',
        'trg_' || v_nome || '_auditoria', p_tabela, v_chave);

    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', 'trg_' || v_nome || '_sem_truncate', p_tabela);
    EXECUTE format(
        'CREATE TRIGGER %I BEFORE TRUNCATE ON %s '
        'FOR EACH STATEMENT EXECUTE FUNCTION impedir_truncate_auditado()',
        'trg_' || v_nome || '_sem_truncate', p_tabela);
END;
$$;

REVOKE EXECUTE ON FUNCTION habilitar_auditoria(REGCLASS) FROM PUBLIC;

-- ============================================================
-- CONSULTA DA TRILHA POR ENTIDADE
-- SECURITY INVOKER: quem consulta só vê o que o RLS de `auditoria` deixa.
-- ============================================================
CREATE FUNCTION trilha_auditoria(p_tabela TEXT, p_registro_id TEXT)
RETURNS SETOF auditoria
LANGUAGE sql
STABLE
AS $$
    SELECT *
    FROM auditoria
    WHERE tabela = p_tabela
      AND registro_id = p_registro_id
    ORDER BY id;
$$;

-- ============================================================
-- Auditoria ligada em todas as tabelas que já existem no schema
-- ============================================================
DO $$
DECLARE
    v_tabela REGCLASS;
BEGIN
    FOR v_tabela IN
        SELECT c.oid::regclass
        FROM pg_class c
        WHERE c.relnamespace = current_schema()::regnamespace
          AND c.relkind = 'r'
          AND c.relname <> 'auditoria'
        ORDER BY c.relname
    LOOP
        PERFORM habilitar_auditoria(v_tabela);
    END LOOP;
END;
$$;
