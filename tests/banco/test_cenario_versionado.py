"""Versionamento de cenários (issue #63, US31).

Critério de aceite: dada a criação de uma nova versão, quando ela é salva,
então a anterior permanece consultável e inalterada.

Usa as precificações da carga de desenvolvimento: PRC-2026-0148 é da
carteira Sudeste e PRC-2026-0145 da carteira Sul. Cada teste roda numa
transação desfeita ao final.
"""

import json
import uuid
from contextlib import contextmanager

import pytest

psycopg = pytest.importorskip("psycopg")

ANALISTA_SUDESTE = uuid.UUID("77777777-7777-7777-7777-777777777771")
ANALISTA_SUL = uuid.UUID("77777777-7777-7777-7777-777777777772")
EXECUTIVA_SUDESTE = uuid.UUID("77777777-7777-7777-7777-777777777773")

USUARIOS = {
    ANALISTA_SUDESTE: ("analista_pricing", "CART-SUDESTE"),
    ANALISTA_SUL: ("analista_pricing", "CART-SUL"),
    EXECUTIVA_SUDESTE: ("executiva_contas", "CART-SUDESTE"),
}

ENTRADA = {"cliente_uf": "SP", "comercial": {"margem_desejada_percentual": "0.30"}}


def _resultado(preco_bruto: str) -> dict:
    return {
        "preco_bruto": preco_bruto,
        "preco_bruto_sem_ipi": "52.18",
        "custo_total": "32.46",
        "margem_contribuicao_valor": "11.67",
        "margem_contribuicao_percentual": "0.284",
        "metadata": {"versao_motor": "0.1.0-mock"},
    }


@pytest.fixture
def tx(conn):
    with conn.transaction(force_rollback=True):
        for usuario_id, (perfil, carteira) in USUARIOS.items():
            conn.execute(
                "INSERT INTO usuario (id, nome, email, perfil_id) SELECT %s, %s, %s, id FROM perfil WHERE codigo = %s",
                [usuario_id, perfil, f"{usuario_id}@neoprice.test", perfil],
            )
            conn.execute(
                "INSERT INTO usuario_carteira (usuario_id, carteira_id) SELECT %s, id FROM carteira WHERE codigo = %s",
                [usuario_id, carteira],
            )
        yield conn


@contextmanager
def como(conn, usuario_id, papel="authenticated"):
    claims = json.dumps({"sub": str(usuario_id), "role": papel})
    conn.execute("SELECT set_config('request.jwt.claims', %s, true)", [claims])
    conn.execute(f"SET LOCAL ROLE {papel}")
    try:
        yield
    finally:
        conn.execute("RESET ROLE")
        conn.execute("SELECT set_config('request.jwt.claims', '', true)")


def _precificacao(conn, codigo: str) -> str:
    return str(conn.execute("SELECT id FROM precificacao WHERE codigo = %s", [codigo]).fetchone()[0])


def _salvar(conn, precificacao_id: str, preco_bruto: str = "57.94", volume=None, origem_id=None) -> dict:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        return cur.execute(
            "SELECT * FROM salvar_cenario(%s, %s::jsonb, %s::jsonb, '0.1.0-mock', %s, NULL, %s)",
            [precificacao_id, json.dumps(ENTRADA), json.dumps(_resultado(preco_bruto)), volume, origem_id],
        ).fetchone()


def _foto(conn, cenario_id) -> str:
    return conn.execute("SELECT to_jsonb(c)::text FROM cenario c WHERE id = %s", [cenario_id]).fetchone()[0]


def _recusa(conn, erro, sql: str, parametros=None) -> None:
    with pytest.raises(erro), conn.transaction():
        conn.execute(sql, parametros)


# ------------------------------------------------------------ critério de aceite


def test_nova_versao_mantem_a_anterior_consultavel_e_inalterada(tx):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, ANALISTA_SUDESTE):
        v1 = _salvar(tx, prc, "61.12", volume=30000)
        foto_v1 = _foto(tx, v1["id"])
        v2 = _salvar(tx, prc, "59.80", volume=30000, origem_id=v1["id"])

        assert (v1["versao"], v2["versao"]) == (1, 2)
        assert v2["cenario_origem_id"] == v1["id"]
        assert _foto(tx, v1["id"]) == foto_v1
        assert tx.execute("SELECT count(*) FROM cenario WHERE precificacao_id = %s", [prc]).fetchone()[0] == 2


def test_indicadores_vem_do_resultado_salvo(tx):
    with como(tx, ANALISTA_SUDESTE):
        salvo = _salvar(tx, _precificacao(tx, "PRC-2026-0148"), "57.94")

    assert str(salvo["preco_bruto"]) == "57.94"
    assert str(salvo["margem_contribuicao_percentual"]) == "0.284"
    assert salvo["created_by"] == ANALISTA_SUDESTE


# ------------------------------------------------------------ imutabilidade


def test_aplicacao_nao_altera_nem_apaga_versao(tx):
    with como(tx, ANALISTA_SUDESTE):
        salvo = _salvar(tx, _precificacao(tx, "PRC-2026-0148"))
        _recusa(
            tx, psycopg.errors.InsufficientPrivilege, "UPDATE cenario SET observacao = 'x' WHERE id = %s", [salvo["id"]]
        )
        _recusa(tx, psycopg.errors.InsufficientPrivilege, "DELETE FROM cenario WHERE id = %s", [salvo["id"]])


@pytest.mark.parametrize(
    "sql",
    [
        pytest.param("UPDATE cenario SET volume = 1 WHERE id = %s", id="update"),
        pytest.param("DELETE FROM cenario WHERE id = %s", id="delete"),
    ],
)
def test_nem_o_dono_do_banco_altera_versao_salva(tx, sql):
    with como(tx, ANALISTA_SUDESTE):
        salvo = _salvar(tx, _precificacao(tx, "PRC-2026-0148"))

    _recusa(tx, psycopg.errors.RestrictViolation, sql, [salvo["id"]])


def test_truncate_e_recusado(tx):
    _recusa(tx, psycopg.errors.InsufficientPrivilege, "TRUNCATE cenario")


def test_gravacao_fica_na_auditoria(tx):
    with como(tx, ANALISTA_SUDESTE):
        salvo = _salvar(tx, _precificacao(tx, "PRC-2026-0148"))

    assert tx.execute(
        "SELECT operacao, usuario_id FROM auditoria WHERE tabela = 'cenario' AND registro_id = %s", [str(salvo["id"])]
    ).fetchall() == [("INSERT", ANALISTA_SUDESTE)]


# ------------------------------------------------------------ regras da gravação


def test_origem_precisa_ser_da_mesma_precificacao(tx):
    with como(tx, ANALISTA_SUDESTE):
        de_outra = _salvar(tx, _precificacao(tx, "PRC-2026-0144"))
        with pytest.raises(psycopg.errors.InvalidParameterValue), tx.transaction():
            _salvar(tx, _precificacao(tx, "PRC-2026-0148"), origem_id=de_outra["id"])


def test_precificacao_inexistente_e_recusada(tx):
    with como(tx, ANALISTA_SUDESTE), pytest.raises(psycopg.errors.NoDataFound), tx.transaction():
        _salvar(tx, str(uuid.uuid4()))


def test_numeracao_e_por_precificacao(tx):
    with como(tx, ANALISTA_SUDESTE):
        _salvar(tx, _precificacao(tx, "PRC-2026-0148"))
        _salvar(tx, _precificacao(tx, "PRC-2026-0148"))
        primeira_da_outra = _salvar(tx, _precificacao(tx, "PRC-2026-0144"))

    assert primeira_da_outra["versao"] == 1


# ------------------------------------------------------------ acesso


def test_analista_de_outra_carteira_nao_ve_nem_grava(tx):
    prc_sudeste = _precificacao(tx, "PRC-2026-0148")
    with como(tx, ANALISTA_SUDESTE):
        _salvar(tx, prc_sudeste)

    with como(tx, ANALISTA_SUL):
        assert tx.execute("SELECT count(*) FROM cenario").fetchone()[0] == 0
        assert tx.execute("SELECT count(*) FROM cenario_preco").fetchone()[0] == 0
        with pytest.raises(psycopg.errors.NoDataFound), tx.transaction():
            _salvar(tx, prc_sudeste)


def test_executiva_ve_o_preco_mas_nao_o_custo(tx):
    prc = _precificacao(tx, "PRC-2026-0148")
    with como(tx, ANALISTA_SUDESTE):
        _salvar(tx, prc, "61.12")
        _salvar(tx, prc, "57.94")

    with como(tx, EXECUTIVA_SUDESTE):
        assert tx.execute("SELECT count(*) FROM cenario").fetchone()[0] == 0
        with tx.cursor(row_factory=psycopg.rows.dict_row) as cur:
            precos = cur.execute(
                "SELECT * FROM cenario_preco WHERE precificacao_id = %s ORDER BY versao", [prc]
            ).fetchall()
        with pytest.raises(psycopg.errors.NoDataFound), tx.transaction():
            _salvar(tx, prc)

    assert [(linha["versao"], str(linha["preco_bruto"]), linha["vigente"]) for linha in precos] == [
        (1, "61.12", False),
        (2, "57.94", True),
    ]
    assert not {"custo_total", "margem_contribuicao_valor", "resultado", "entrada"} & set(precos[0])


def test_anonimo_nao_ve_precos(tx):
    with como(tx, uuid.uuid4(), papel="anon"):
        _recusa(tx, psycopg.errors.InsufficientPrivilege, "SELECT count(*) FROM cenario_preco")
