"""Integridade transacional do salvamento da formulação de produto."""

import json
import uuid
from contextlib import contextmanager

import psycopg
import pytest


@pytest.fixture
def analista(conn):
    usuario_id = uuid.uuid4()
    with conn.transaction(force_rollback=True):
        conn.execute(
            "INSERT INTO usuario (id, nome, email, perfil_id) "
            "SELECT %s, 'Analista teste', %s, id FROM perfil WHERE codigo = 'analista_pricing'",
            [usuario_id, f"{usuario_id}@formulacao.test"],
        )
        yield usuario_id


@contextmanager
def como(conn, usuario_id):
    conn.execute(
        "SELECT set_config('request.jwt.claims', %s, true)",
        [json.dumps({"sub": str(usuario_id), "role": "authenticated"})],
    )
    conn.execute("SET LOCAL ROLE authenticated")
    try:
        yield
    finally:
        conn.execute("RESET ROLE")
        conn.execute("SELECT set_config('request.jwt.claims', '', true)")


def test_falha_no_item_reverte_cabecalho_e_composicao(conn, analista):
    produto_id = conn.execute("SELECT id FROM produto WHERE codigo = 'PA-0001'").fetchone()[0]
    item_invalido = [
        {
            "tipo_insumo": "materia_prima",
            "materia_prima_id": str(uuid.uuid4()),
            "embalagem_id": None,
            "quantidade": "1.234567",
            "unidade_medida": "kg",
            "perda_percentual": None,
        }
    ]

    with conn.transaction(force_rollback=True), como(conn, analista):
        with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
            conn.execute(
                "SELECT salvar_formulacao_produto(%s, %s::jsonb)",
                [produto_id, json.dumps(item_invalido)],
            )
        assert conn.execute("SELECT count(*) FROM formulacao WHERE produto_id = %s", [produto_id]).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM formulacao_item").fetchone()[0] == 0


def test_rpc_salva_quantidade_decimal_em_transacao(conn, analista):
    produto_id = conn.execute("SELECT id FROM produto WHERE codigo = 'PA-0001'").fetchone()[0]
    materia_id = conn.execute("SELECT id FROM materia_prima WHERE codigo = 'MP-0001'").fetchone()[0]
    itens = [
        {
            "tipo_insumo": "materia_prima",
            "materia_prima_id": str(materia_id),
            "embalagem_id": None,
            "quantidade": "12345678.123456",
            "unidade_medida": "kg",
            "perda_percentual": "99.9999",
        }
    ]

    with conn.transaction(force_rollback=True), como(conn, analista):
        conn.execute(
            "SELECT salvar_formulacao_produto(%s, %s::jsonb)",
            [produto_id, json.dumps(itens)],
        )
        row = conn.execute("SELECT quantidade::text, perda_percentual::text FROM formulacao_item").fetchone()
        assert row == ("12345678.123456", "99.9999")
