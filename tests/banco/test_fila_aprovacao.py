"""Visão da fila de aprovação (issue #67, US36).

A visão `fila_aprovacao` decide quem vê o quê: só precificações em
aprovação, só para quem aprova e enxerga custo, e só na carteira dele. Traz
a margem da versão vigente, a versão anterior para comparar e a data da
última submissão. O filtro pela política fica na API
(apps/api/tests/test_fila_aprovacao.py).

Usa a carga de desenvolvimento: PRC-2026-0148 e PRC-2026-0147 estão em
aprovação na carteira Sudeste; PRC-2026-0145 (Sul) está reprovada e
PRC-2026-0146 (Exportação) aprovada. Cada teste roda numa transação
desfeita ao final.
"""

import json
import uuid
from contextlib import contextmanager

import pytest

psycopg = pytest.importorskip("psycopg")

GERENTE_SUDESTE = uuid.UUID("88888888-8888-8888-8888-888888888881")
GERENTE_SUL = uuid.UUID("88888888-8888-8888-8888-888888888882")
ANALISTA_SUDESTE = uuid.UUID("88888888-8888-8888-8888-888888888883")
EXECUTIVA_SUDESTE = uuid.UUID("88888888-8888-8888-8888-888888888884")

USUARIOS = {
    GERENTE_SUDESTE: ("gerente_comercial", "CART-SUDESTE", "Marcos Tavares"),
    GERENTE_SUL: ("gerente_comercial", "CART-SUL", "Gerente Sul"),
    ANALISTA_SUDESTE: ("analista_pricing", "CART-SUDESTE", "Rafael Costa"),
    EXECUTIVA_SUDESTE: ("executiva_contas", "CART-SUDESTE", "Juliana Marques"),
}


@pytest.fixture
def tx(conn):
    with conn.transaction(force_rollback=True):
        for usuario_id, (perfil, carteira, nome) in USUARIOS.items():
            conn.execute(
                "INSERT INTO usuario (id, nome, email, perfil_id) SELECT %s, %s, %s, id FROM perfil WHERE codigo = %s",
                [usuario_id, nome, f"{usuario_id}@neoprice.test", perfil],
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


def _cenario(conn, codigo: str, versao: int, margem: str) -> None:
    """Grava a versão como dono do banco (a gravação pela aplicação exige o
    motor real e é testada na #63)."""
    resultado = {"preco_bruto": "57.94", "margem_contribuicao_valor": "11.67", "margem_contribuicao_percentual": margem}
    conn.execute(
        "INSERT INTO cenario (precificacao_id, versao, versao_motor, entrada, resultado, volume) "
        "VALUES (%s, %s, '1.0.0', '{}'::jsonb, %s::jsonb, 42000)",
        [_precificacao(conn, codigo), versao, json.dumps(resultado)],
    )


def _submissao(conn, codigo: str, quando: str) -> None:
    conn.execute(
        "INSERT INTO historico_status_precificacao "
        "(precificacao_id, status_anterior, status_novo, modo, responsavel_id, ocorrido_em) "
        "VALUES (%s, 'em_preenchimento', 'em_aprovacao', 'homologada', %s, %s::timestamptz)",
        [_precificacao(conn, codigo), ANALISTA_SUDESTE, quando],
    )


def _fila(conn) -> dict[str, dict]:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        return {linha["codigo"]: linha for linha in cur.execute("SELECT * FROM fila_aprovacao").fetchall()}


def test_gerente_ve_as_em_aprovacao_da_carteira_com_a_margem_da_vigente(tx):
    _cenario(tx, "PRC-2026-0148", 1, "0.261")
    _cenario(tx, "PRC-2026-0148", 2, "0.255")
    _cenario(tx, "PRC-2026-0148", 3, "0.284")
    _submissao(tx, "PRC-2026-0148", "2026-11-01T10:00:00Z")
    _submissao(tx, "PRC-2026-0148", "2026-11-12T10:00:00Z")

    with como(tx, GERENTE_SUDESTE):
        fila = _fila(tx)

    assert set(fila) == {"PRC-2026-0148", "PRC-2026-0147"}
    linha = fila["PRC-2026-0148"]
    assert (linha["cenario_versao"], linha["versao_anterior"]) == (3, 2)
    assert str(linha["margem_contribuicao_percentual"]) == "0.284"
    assert linha["submetido_em"].isoformat().startswith("2026-11-12")
    assert linha["submetido_por_nome"] == "Rafael Costa"
    assert linha["cliente_nome"] == "Nutrafit Distribuidora Ltda"


def test_sem_cenario_nem_submissao_registrada_a_linha_aparece_sem_margem(tx):
    with como(tx, GERENTE_SUDESTE):
        linha = _fila(tx)["PRC-2026-0147"]

    assert linha["cenario_versao"] is None
    assert linha["margem_contribuicao_percentual"] is None
    assert linha["submetido_em"] is not None
    assert linha["submetido_por_nome"] is None


def test_versao_unica_nao_tem_anterior(tx):
    _cenario(tx, "PRC-2026-0147", 1, "0.192")

    with como(tx, GERENTE_SUDESTE):
        linha = _fila(tx)["PRC-2026-0147"]

    assert (linha["cenario_versao"], linha["versao_anterior"]) == (1, None)


def test_gerente_de_outra_carteira_nao_ve_a_fila_alheia(tx):
    with como(tx, GERENTE_SUL):
        assert _fila(tx) == {}


@pytest.mark.parametrize("usuario_id", [ANALISTA_SUDESTE, EXECUTIVA_SUDESTE], ids=["analista", "executiva"])
def test_quem_nao_aprova_nao_ve_a_fila(tx, usuario_id):
    with como(tx, usuario_id):
        assert _fila(tx) == {}


def test_precificacao_decidida_sai_da_fila(tx):
    with como(tx, GERENTE_SUDESTE):
        tx.execute(
            "SELECT * FROM decidir_aprovacao(%s, 'reprovado', 'Margem abaixo da política.')",
            [_precificacao(tx, "PRC-2026-0147")],
        )
        assert set(_fila(tx)) == {"PRC-2026-0148"}


def test_anonimo_nao_le_a_fila(tx):
    with como(tx, uuid.uuid4(), papel="anon"), pytest.raises(psycopg.errors.InsufficientPrivilege), tx.transaction():
        tx.execute("SELECT count(*) FROM fila_aprovacao")


def test_margem_minima_da_politica_e_um_parametro_valido(tx):
    with como(tx, ANALISTA_SUDESTE):
        tx.execute(
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) "
            "VALUES ('margem_minima_contribuicao_percentual', 0.25, current_date)"
        )
    with pytest.raises(psycopg.errors.CheckViolation), tx.transaction():
        tx.execute(
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) "
            "VALUES ('margem_minima_contribuicao_percentual', 1.5, current_date + 1)"
        )
