"""Fixtures dos testes de banco: sobem migrations e seeds em um schema
temporário de um PostgreSQL 15+ apontado por NEOPRICE_TEST_DATABASE_URL e o
removem ao final. Sem a variável, os testes ficam com skip (ver README.md
desta pasta).
"""

import os
import uuid
from pathlib import Path

import pytest
from supabase_simulado import AUTH_SIMULADO, PAPEIS_SUPABASE

RAIZ = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((RAIZ / "supabase" / "migrations").glob("*.sql"))
# Mesma ordem do [db.seed] em supabase/config.toml
SEEDS = sorted((RAIZ / "supabase" / "seed" / "referencia").glob("*.sql")) + sorted(
    (RAIZ / "supabase" / "seed" / "dev").glob("*.sql")
)


def _rodar(conexao, arquivos: list[Path]) -> None:
    for arquivo in arquivos:
        conexao.execute(arquivo.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def conn():
    url = os.environ.get("NEOPRICE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("defina NEOPRICE_TEST_DATABASE_URL para rodar os testes de banco")
    psycopg = pytest.importorskip("psycopg")

    schema = f"teste_{uuid.uuid4().hex[:12]}"
    # ClientCursor: parâmetros interpolados no cliente, cada comando vai como
    # texto simples e os arquivos .sql com vários comandos rodam do mesmo jeito
    with psycopg.connect(url, autocommit=True, cursor_factory=psycopg.ClientCursor) as conexao:
        for papel in PAPEIS_SUPABASE:
            if not conexao.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel]).fetchone():
                conexao.execute(f"CREATE ROLE {papel} NOLOGIN")
        auth_simulado = not conexao.execute("SELECT to_regprocedure('auth.uid()')").fetchone()[0]
        if auth_simulado:
            conexao.execute(AUTH_SIMULADO)

        conexao.execute(f"CREATE SCHEMA {schema}")
        conexao.execute(f"GRANT USAGE ON SCHEMA {schema} TO anon, authenticated, service_role")
        conexao.execute(f"SET search_path TO {schema}")
        try:
            _rodar(conexao, MIGRATIONS)
            _rodar(conexao, SEEDS)
            yield conexao
        finally:
            conexao.execute("RESET ROLE")
            conexao.execute(f"DROP SCHEMA {schema} CASCADE")
            if auth_simulado:
                conexao.execute("DROP SCHEMA auth CASCADE")


@pytest.fixture
def rodar_seeds(conn):
    """Reexecuta todos os seeds, na ordem de carga."""
    return lambda: _rodar(conn, SEEDS)
