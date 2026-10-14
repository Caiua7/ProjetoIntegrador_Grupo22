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

TABELAS = [
    "uf",
    "municipio",
    "cep",
    "ncm",
    "aliquota_fiscal",
    "fornecedor",
    "materia_prima",
    "embalagem",
    "produto",
    "linha_producao",
    "produtividade",
    "cliente",
]

DATABASE_URL = os.environ.get("NEOPRICE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="defina NEOPRICE_TEST_DATABASE_URL para rodar os testes de banco")


def _rodar(conn, arquivos: list[Path]) -> None:
    for arquivo in arquivos:
        conn.execute(arquivo.read_text(encoding="utf-8"))


def _retrato(conn) -> dict[str, tuple]:
    return {
        tabela: conn.execute(
            f"SELECT count(*), md5(coalesce(string_agg(t::text, '|' ORDER BY t::text), '')) FROM {tabela} t"
        ).fetchone()
        for tabela in TABELAS
    }


@pytest.fixture(scope="module")
def conn():
    schema = f"teste_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(DATABASE_URL, autocommit=True) as conexao:
        if not conexao.execute("SELECT 1 FROM pg_roles WHERE rolname = 'service_role'").fetchone():
            conexao.execute("CREATE ROLE service_role NOLOGIN")
        conexao.execute(f"CREATE SCHEMA {schema}")
        conexao.execute(f"SET search_path TO {schema}")
        try:
            _rodar(conexao, MIGRATIONS)
            _rodar(conexao, SEEDS)
            yield conexao
        finally:
            conexao.execute(f"DROP SCHEMA {schema} CASCADE")


def test_schema_sobe_populado(conn):
    contagem = {tabela: total for tabela, (total, _) in _retrato(conn).items()}

    assert contagem["uf"] == 27
    assert contagem["municipio"] >= 5570
    assert contagem["ncm"] >= 10000
    assert contagem["cep"] >= 10
    assert contagem["aliquota_fiscal"] == 27 * 3 + 1
    assert all(total > 0 for total in contagem.values()), contagem


def test_seed_e_reexecutavel_sem_duplicar(conn):
    antes = _retrato(conn)

    _rodar(conn, SEEDS)

    assert _retrato(conn) == antes


def test_todas_as_tabelas_com_rls_ativo(conn):
    sem_rls = conn.execute(
        "SELECT relname FROM pg_class "
        "WHERE relnamespace = current_schema()::regnamespace AND relkind = 'r' AND NOT relrowsecurity"
    ).fetchall()

    assert sem_rls == []


@pytest.mark.parametrize(
    "sql, erro",
    [
        pytest.param(
            "INSERT INTO materia_prima (codigo, descricao, ncm_codigo) VALUES ('MP-X', 'Sem NCM válido', '00000000')",
            psycopg.errors.ForeignKeyViolation,
            id="mp_com_ncm_inexistente",
        ),
        pytest.param(
            "INSERT INTO materia_prima (codigo, descricao, ncm_codigo) VALUES ('MP-0001', 'Código repetido', '04041000')",
            psycopg.errors.UniqueViolation,
            id="mp_com_codigo_repetido",
        ),
        pytest.param(
            "INSERT INTO cliente (codigo, razao_social, regime_tributario) VALUES ('CLI-X', 'Nacional sem UF', 'lucro_real')",
            psycopg.errors.CheckViolation,
            id="cliente_nacional_sem_uf",
        ),
        pytest.param(
            "INSERT INTO municipio (codigo_ibge, nome, uf_sigla) VALUES (9999999, 'UF inexistente', 'XX')",
            psycopg.errors.ForeignKeyViolation,
            id="municipio_com_uf_inexistente",
        ),
        pytest.param(
            "INSERT INTO aliquota_fiscal (uf_destino, ncm_codigo, regime_tributario, vigencia_inicio) "
            "VALUES ('SP', NULL, 'lucro_real', DATE '2026-01-01')",
            psycopg.errors.UniqueViolation,
            id="regra_geral_de_aliquota_duplicada",
        ),
        pytest.param(
            "UPDATE aliquota_fiscal SET icms_percentual = 1.8 WHERE uf_destino = 'SP'",
            psycopg.errors.CheckViolation,
            id="percentual_fora_da_fracao_0_a_1",
        ),
    ],
)
def test_restricoes_de_integridade(conn, sql, erro):
    with pytest.raises(erro):
        with conn.transaction(force_rollback=True):
            conn.execute(sql)


def test_updated_at_muda_no_update(conn):
    with conn.transaction(force_rollback=True):
        antes, depois = conn.execute(
            "WITH alterado AS ("
            "  UPDATE produto SET descricao = descricao || ' (rev)' WHERE codigo = 'PA-0001' RETURNING updated_at"
            ") SELECT (SELECT updated_at FROM produto WHERE codigo = 'PA-0001'), (SELECT updated_at FROM alterado)"
        ).fetchone()

    assert depois > antes
