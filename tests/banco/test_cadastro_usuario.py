"""Linha em `usuario` criada pelo cadastro no Supabase Auth (issue #44 / US03).

Critério: quem se cadastra ganha a linha com o mesmo id, inativa e com o
perfil de menor alcance; e-mail repetido não bloqueia o cadastro.
"""

import uuid

import pytest

psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def tx(conn):
    """Transação desfeita ao final: os cadastros não sobram para os outros testes."""
    with conn.transaction(force_rollback=True):
        yield conn


def _cadastrar(tx, email: str, metadados: str = "{}") -> uuid.UUID:
    usuario_id = uuid.uuid4()
    tx.execute(
        "INSERT INTO auth.users (id, email, raw_user_meta_data) VALUES (%s, %s, %s::jsonb)",
        [usuario_id, email, metadados],
    )
    return usuario_id


def _usuario(tx, usuario_id: uuid.UUID):
    return tx.execute(
        "SELECT u.nome, u.email, u.ativo, p.codigo FROM usuario u JOIN perfil p ON p.id = u.perfil_id WHERE u.id = %s",
        [usuario_id],
    ).fetchone()


def test_cadastro_cria_usuario_inativo_com_perfil_minimo(tx):
    usuario_id = _cadastrar(tx, "rafael.costa@empresa.com", '{"nome": "Rafael Costa"}')
    assert _usuario(tx, usuario_id) == ("Rafael Costa", "rafael.costa@empresa.com", False, "executiva_contas")


def test_sem_nome_usa_o_inicio_do_email(tx):
    usuario_id = _cadastrar(tx, "ana.souza@empresa.com")
    assert _usuario(tx, usuario_id)[0] == "ana.souza"


def test_email_repetido_nao_bloqueia_o_cadastro(tx):
    _cadastrar(tx, "duplicado@empresa.com")
    segundo = _cadastrar(tx, "duplicado@empresa.com")
    assert _usuario(tx, segundo) is None
