"""Log imutável de mutações (issue #58, US51, RNF05).

Critério de aceite: dada qualquer mutação em precificação ou cadastro,
quando ela ocorre, então existe registro de auditoria correspondente. E a
trilha não pode ser alterada pela aplicação.

Cada teste roda dentro de uma transação desfeita ao final, para não
deixar dados nem linhas de auditoria para o seguinte.
"""

import json
import os
from pathlib import Path
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

RAIZ = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((RAIZ / "supabase" / "migrations").glob("*.sql"))
SEEDS = sorted((RAIZ / "supabase" / "seed" / "referencia").glob("*.sql")) + sorted(
    (RAIZ / "supabase" / "seed" / "dev").glob("*.sql")
)

DATABASE_URL = os.environ.get("NEOPRICE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="defina NEOPRICE_TEST_DATABASE_URL para rodar os testes de banco")

USUARIO = uuid.UUID("11111111-1111-1111-1111-111111111111")


# Papéis e auth.uid() que só existem prontos no Supabase. As migrations de
# RLS (US04) usam os dois; sem eles, o schema não sobe num Postgres puro.
PAPEIS_SUPABASE = ["anon", "authenticated", "service_role"]
AUTH_UID_SIMULADO = """
CREATE SCHEMA auth;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
    SELECT (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')::uuid
$$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
"""


@pytest.fixture(scope="module")
def conn():
    schema = f"teste_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(DATABASE_URL, autocommit=True) as conexao:
        for papel in PAPEIS_SUPABASE:
            if not conexao.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel]).fetchone():
                conexao.execute(f"CREATE ROLE {papel} NOLOGIN")
        auth_simulado = not conexao.execute("SELECT to_regprocedure('auth.uid()')").fetchone()[0]
        if auth_simulado:
            conexao.execute(AUTH_UID_SIMULADO)

        conexao.execute(f"CREATE SCHEMA {schema}")
        conexao.execute(f"GRANT USAGE ON SCHEMA {schema} TO anon, authenticated, service_role")
        # Mesmo privilégio padrão do Supabase: o service_role recebe tudo em
        # tabela nova, e a migration é que precisa tirar o que não deve ter
        conexao.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON TABLES TO service_role")
        conexao.execute(f"SET search_path TO {schema}")
        try:
            for arquivo in MIGRATIONS + SEEDS:
                conexao.execute(arquivo.read_text(encoding="utf-8"))
            yield conexao
        finally:
            conexao.execute("RESET ROLE")
            conexao.execute(f"DROP SCHEMA {schema} CASCADE")
            if auth_simulado:
                conexao.execute("DROP SCHEMA auth CASCADE")


@pytest.fixture
def tx(conn):
    """Transação desfeita ao final, já com o usuário da requisição informado
    como o backend faz."""
    with conn.transaction(force_rollback=True):
        conn.execute("SELECT set_config('neoprice.usuario_id', %s, true)", [str(USUARIO)])
        yield conn


def _trilha(conn, tabela: str, registro_id: str) -> list[dict]:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        return cur.execute("SELECT * FROM trilha_auditoria(%s, %s)", [tabela, registro_id]).fetchall()


def _novo_fornecedor(conn) -> str:
    return str(
        conn.execute(
            "INSERT INTO fornecedor (codigo, razao_social, pais) VALUES ('FOR-AUD', 'Fornecedor Auditado', 'BR') RETURNING id"
        ).fetchone()[0]
    )


def test_toda_tabela_tem_auditoria(conn):
    sem_auditoria = conn.execute(
        "SELECT c.relname FROM pg_class c "
        "WHERE c.relnamespace = current_schema()::regnamespace AND c.relkind = 'r' AND c.relname <> 'auditoria' "
        "AND NOT EXISTS (SELECT 1 FROM pg_trigger t WHERE t.tgrelid = c.oid AND t.tgname = 'trg_' || c.relname || '_auditoria')"
    ).fetchall()

    assert sem_auditoria == []


def test_insercao_registra_dados_e_usuario(tx):
    fornecedor_id = _novo_fornecedor(tx)

    [linha] = _trilha(tx, "fornecedor", fornecedor_id)
    assert linha["operacao"] == "INSERT"
    assert linha["usuario_id"] == USUARIO
    assert linha["dados_antes"] is None
    assert linha["dados_depois"]["razao_social"] == "Fornecedor Auditado"
    assert linha["diff"] is None


def test_alteracao_registra_diff_so_do_que_mudou(tx):
    fornecedor_id = _novo_fornecedor(tx)

    tx.execute("UPDATE fornecedor SET razao_social = 'Novo Nome', nome_fantasia = 'NN' WHERE id = %s", [fornecedor_id])

    insercao, alteracao = _trilha(tx, "fornecedor", fornecedor_id)
    assert alteracao["operacao"] == "UPDATE"
    assert alteracao["diff"] == {
        "razao_social": {"de": "Fornecedor Auditado", "para": "Novo Nome"},
        "nome_fantasia": {"de": None, "para": "NN"},
    }
    assert alteracao["dados_antes"]["razao_social"] == "Fornecedor Auditado"
    assert alteracao["dados_depois"]["razao_social"] == "Novo Nome"
    assert alteracao["id"] > insercao["id"]


def test_alteracao_sem_mudanca_nao_registra(tx):
    fornecedor_id = _novo_fornecedor(tx)

    tx.execute("UPDATE fornecedor SET razao_social = razao_social WHERE id = %s", [fornecedor_id])

    assert [linha["operacao"] for linha in _trilha(tx, "fornecedor", fornecedor_id)] == ["INSERT"]


def test_exclusao_registra_o_registro_apagado(tx):
    fornecedor_id = _novo_fornecedor(tx)

    tx.execute("DELETE FROM fornecedor WHERE id = %s", [fornecedor_id])

    exclusao = _trilha(tx, "fornecedor", fornecedor_id)[-1]
    assert exclusao["operacao"] == "DELETE"
    assert exclusao["dados_antes"]["codigo"] == "FOR-AUD"
    assert exclusao["dados_depois"] is None


def test_chave_natural_identifica_o_registro(tx):
    tx.execute("UPDATE uf SET nome = 'São Paulo (rev)' WHERE sigla = 'SP'")

    carga_do_seed, alteracao = _trilha(tx, "uf", "SP")
    assert carga_do_seed["operacao"] == "INSERT"
    assert carga_do_seed["usuario_id"] is None
    assert alteracao["diff"] == {"nome": {"de": "São Paulo", "para": "São Paulo (rev)"}}


def test_usuario_do_jwt_tem_precedencia(tx):
    outro = uuid.uuid4()
    tx.execute(
        "SELECT set_config('request.jwt.claims', %s, true)",
        [json.dumps({"sub": str(outro), "role": "authenticated"})],
    )

    fornecedor_id = _novo_fornecedor(tx)

    [linha] = _trilha(tx, "fornecedor", fornecedor_id)
    assert linha["usuario_id"] == outro
    assert linha["papel"] == "authenticated"


def test_mutacao_desfeita_nao_deixa_auditoria(conn):
    with conn.transaction(force_rollback=True):
        fornecedor_id = _novo_fornecedor(conn)

    assert _trilha(conn, "fornecedor", fornecedor_id) == []


def test_service_role_audita_mas_nao_escreve_na_trilha(tx):
    # No Supabase o service_role já tem esses privilégios por padrão
    tx.execute("GRANT SELECT, INSERT ON fornecedor TO service_role")
    tx.execute("SELECT set_config('request.jwt.claims', %s, true)", [json.dumps({"role": "service_role"})])
    tx.execute("SET LOCAL ROLE service_role")

    fornecedor_id = _novo_fornecedor(tx)
    [linha] = _trilha(tx, "fornecedor", fornecedor_id)
    assert linha["papel"] == "service_role"
    assert linha["usuario_id"] == USUARIO

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with tx.transaction():
            tx.execute(
                "INSERT INTO auditoria (tabela, registro_id, operacao, papel, dados_depois) "
                "VALUES ('fornecedor', 'x', 'INSERT', 'service_role', '{}')"
            )


@pytest.mark.parametrize(
    "sql",
    [
        pytest.param("UPDATE auditoria SET usuario_id = NULL", id="update"),
        pytest.param("DELETE FROM auditoria", id="delete"),
        pytest.param("TRUNCATE auditoria", id="truncate"),
    ],
)
def test_trilha_e_imutavel_ate_para_o_dono(tx, sql):
    _novo_fornecedor(tx)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with tx.transaction():
            tx.execute(sql)


def test_truncate_em_tabela_auditada_e_recusado(tx):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with tx.transaction():
            tx.execute("TRUNCATE produtividade")
