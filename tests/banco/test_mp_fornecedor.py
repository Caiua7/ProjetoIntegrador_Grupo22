"""Vínculo matéria-prima × fornecedor e busca nos cadastros (issue #50).

Cobre a migration 20261102000001: no máximo um fornecedor principal por MP,
principal só se ativo, sem DELETE (desvincular é inativar), RLS igual ao dos
cadastros e os índices trigram da busca por "contém".
"""

import uuid

import pytest

psycopg = pytest.importorskip("psycopg")


def _mp(conn) -> str:
    return str(conn.execute("SELECT id FROM materia_prima ORDER BY codigo LIMIT 1").fetchone()[0])


def _fornecedor(conn, codigo: str) -> str:
    return str(
        conn.execute(
            "INSERT INTO fornecedor (codigo, razao_social, pais) VALUES (%s, %s, 'BR') RETURNING id",
            [codigo, f"Fornecedor {codigo}"],
        ).fetchone()[0]
    )


def _vincular(conn, mp: str, fornecedor: str, principal: bool = False, ativo: bool = True) -> None:
    conn.execute(
        "INSERT INTO materia_prima_fornecedor (materia_prima_id, fornecedor_id, principal, ativo) VALUES (%s, %s, %s, %s)",
        [mp, fornecedor, principal, ativo],
    )


@pytest.fixture
def tx(conn):
    with conn.transaction(force_rollback=True):
        yield conn


def _como(conn, perfil: str) -> None:
    usuario = uuid.uuid4()
    conn.execute(
        "INSERT INTO usuario (id, nome, email, perfil_id, ativo) SELECT %s, %s, %s, id, true FROM perfil WHERE codigo = %s",
        [usuario, perfil, f"{usuario.hex[:8]}@neoprice.test", perfil],
    )
    conn.execute(
        "SELECT set_config('request.jwt.claims', %s, true)", [f'{{"sub": "{usuario}", "role": "authenticated"}}']
    )
    conn.execute("SET LOCAL ROLE authenticated")


def test_um_unico_fornecedor_principal_por_mp(tx):
    mp = _mp(tx)
    _vincular(tx, mp, _fornecedor(tx, "FOR-A"), principal=True)
    _vincular(tx, mp, _fornecedor(tx, "FOR-B"))
    with pytest.raises(psycopg.errors.UniqueViolation), tx.transaction():
        _vincular(tx, mp, _fornecedor(tx, "FOR-C"), principal=True)


def test_principal_precisa_estar_ativo(tx):
    with pytest.raises(psycopg.errors.CheckViolation), tx.transaction():
        _vincular(tx, _mp(tx), _fornecedor(tx, "FOR-D"), principal=True, ativo=False)


def test_vinculo_e_auditado(tx):
    mp, fornecedor = _mp(tx), _fornecedor(tx, "FOR-E")
    _vincular(tx, mp, fornecedor)
    trilha = tx.execute("SELECT operacao FROM trilha_auditoria('materia_prima_fornecedor', %s)", [f"{mp}|{fornecedor}"])
    assert [linha[0] for linha in trilha] == ["INSERT"]


def test_suprimentos_vincula_e_ninguem_apaga(tx):
    mp, fornecedor = _mp(tx), _fornecedor(tx, "FOR-F")
    _como(tx, "analista_suprimentos")
    _vincular(tx, mp, fornecedor, principal=True)
    assert tx.execute("SELECT count(*) FROM materia_prima_fornecedor").fetchone()[0] == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege), tx.transaction():
        tx.execute("DELETE FROM materia_prima_fornecedor")


def test_executiva_nao_vincula(tx):
    mp, fornecedor = _mp(tx), _fornecedor(tx, "FOR-G")
    _como(tx, "executiva_contas")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), tx.transaction():
        _vincular(tx, mp, fornecedor)


@pytest.mark.parametrize("indice", ["idx_materia_prima_busca", "idx_embalagem_busca", "idx_fornecedor_busca"])
def test_indices_de_busca_existem(conn, indice):
    definicao = conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE schemaname = current_schema() AND indexname = %s", [indice]
    ).fetchone()
    assert definicao and "gin_trgm_ops" in definicao[0]
