"""Decisão de aprovação e reprovação com comentário (issue #68, US37).

Critério de aceite: dada uma reprovação sem comentário, quando o gerente
confirma, então a ação é recusada.

Usa as precificações da carga de desenvolvimento: PRC-2026-0148 é da
carteira Sudeste e está em aprovação; PRC-2026-0144, também do Sudeste,
ainda está em preenchimento. Cada teste roda numa transação desfeita ao
final.
"""

import json
import uuid
from contextlib import contextmanager

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg.rows import dict_row  # noqa: E402

GERENTE_SUDESTE = uuid.UUID("88888888-8888-8888-8888-888888888881")
GERENTE_SUL = uuid.UUID("88888888-8888-8888-8888-888888888882")
ANALISTA_SUDESTE = uuid.UUID("88888888-8888-8888-8888-888888888883")
EXECUTIVA_SUDESTE = uuid.UUID("88888888-8888-8888-8888-888888888884")
ANALISTA_SUL = uuid.UUID("88888888-8888-8888-8888-888888888885")

USUARIOS = {
    GERENTE_SUDESTE: ("Gerente Sudeste", "gerente_comercial", "CART-SUDESTE"),
    GERENTE_SUL: ("Gerente Sul", "gerente_comercial", "CART-SUL"),
    ANALISTA_SUDESTE: ("Analista Sudeste", "analista_pricing", "CART-SUDESTE"),
    EXECUTIVA_SUDESTE: ("Executiva Sudeste", "executiva_contas", "CART-SUDESTE"),
    ANALISTA_SUL: ("Analista Sul", "analista_pricing", "CART-SUL"),
}

ENTRADA = {"cliente_uf": "SP", "comercial": {"margem_desejada_percentual": "0.30"}}
RESULTADO = {
    "preco_bruto": "57.94",
    "preco_bruto_sem_ipi": "52.18",
    "custo_total": "32.46",
    "margem_contribuicao_valor": "11.67",
    "margem_contribuicao_percentual": "0.284",
    "metadata": {"versao_motor": "0.3.0", "is_mock": False, "origem": "pricing_core"},
}


@pytest.fixture
def tx(conn):
    with conn.transaction(force_rollback=True):
        for usuario_id, (nome, perfil, carteira) in USUARIOS.items():
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


def _status(conn, precificacao_id: str) -> str:
    return conn.execute("SELECT status FROM precificacao WHERE id = %s", [precificacao_id]).fetchone()[0]


def _decidir(conn, precificacao_id: str, decisao: str, comentario: str | None = None) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT * FROM decidir_aprovacao(%s, %s, %s)", [precificacao_id, decisao, comentario]
        ).fetchone()


def _recusa(conn, erro, sql: str, parametros=None) -> None:
    with pytest.raises(erro), conn.transaction():
        conn.execute(sql, parametros)


def _recusa_decisao(conn, erro, precificacao_id: str, decisao: str, comentario: str | None = None) -> None:
    _recusa(conn, erro, "SELECT decidir_aprovacao(%s, %s, %s)", [precificacao_id, decisao, comentario])


# ------------------------------------------------------------ critério de aceite


@pytest.mark.parametrize("comentario", [None, "", "   \n\t"])
def test_reprovar_sem_comentario_e_recusado(tx, comentario):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUDESTE):
        _recusa_decisao(tx, psycopg.errors.CheckViolation, prc, "reprovado", comentario)

    assert _status(tx, prc) == "em_aprovacao"
    assert tx.execute("SELECT count(*) FROM decisao_aprovacao WHERE precificacao_id = %s", [prc]).fetchone()[0] == 0


def test_insert_direto_sem_comentario_tambem_e_recusado(tx):
    """As regras ficam nos gatilhos: a tabela não aceita atalho."""
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUDESTE):
        _recusa(
            tx,
            psycopg.errors.CheckViolation,
            "INSERT INTO decisao_aprovacao (precificacao_id, decisao) VALUES (%s, 'reprovado')",
            [prc],
        )

    # Nem o dono do banco grava reprovação sem justificativa
    _recusa(
        tx,
        psycopg.errors.CheckViolation,
        "INSERT INTO decisao_aprovacao (precificacao_id, decisao, responsavel_id) VALUES (%s, 'reprovado', %s)",
        [prc, GERENTE_SUDESTE],
    )


# ------------------------------------------------------------ registro da decisão


def test_reprovacao_registra_responsavel_data_comentario_e_status(tx):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUDESTE):
        decisao = _decidir(tx, prc, "reprovado", "  Margem abaixo da política para este cliente.  ")
        agora = tx.execute("SELECT now()").fetchone()[0]

    assert decisao["decisao"] == "reprovado"
    assert decisao["comentario"] == "Margem abaixo da política para este cliente."
    assert decisao["responsavel_id"] == GERENTE_SUDESTE
    assert decisao["decidido_em"] == agora
    assert _status(tx, prc) == "reprovado"


def test_aprovacao_pode_ir_sem_comentario(tx):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUDESTE):
        decisao = _decidir(tx, prc, "aprovado")

    assert decisao["comentario"] is None
    assert _status(tx, prc) == "aprovado"


def test_decisao_aponta_para_a_versao_vigente_do_cenario(tx):
    prc = _precificacao(tx, "PRC-2026-0148")
    with tx.cursor() as cur:
        cur.execute(
            "INSERT INTO cenario (precificacao_id, versao, versao_motor, entrada, resultado) "
            "VALUES (%s, 1, '0.3.0', %s::jsonb, %s::jsonb) RETURNING id",
            [prc, json.dumps(ENTRADA), json.dumps(RESULTADO)],
        )
        cur.fetchone()
        vigente = cur.execute(
            "INSERT INTO cenario (precificacao_id, versao, versao_motor, entrada, resultado) "
            "VALUES (%s, 2, '0.3.0', %s::jsonb, %s::jsonb) RETURNING id",
            [prc, json.dumps(ENTRADA), json.dumps(RESULTADO)],
        ).fetchone()[0]

    with como(tx, GERENTE_SUDESTE):
        decisao = _decidir(tx, prc, "aprovado", "Dentro da política.")

    assert decisao["cenario_id"] == vigente


def test_resultado_mock_nao_pode_ser_aprovado(tx):
    prc = _precificacao(tx, "PRC-2026-0148")
    resultado_mock = {**RESULTADO, "metadata": {"versao_motor": "demo", "is_mock": True, "origem": "demonstracao"}}
    tx.execute(
        "INSERT INTO cenario (precificacao_id, versao, versao_motor, entrada, resultado) "
        "VALUES (%s, 1, 'demo', %s::jsonb, %s::jsonb)",
        [prc, json.dumps(ENTRADA), json.dumps(resultado_mock)],
    )
    with como(tx, GERENTE_SUDESTE):
        _recusa_decisao(tx, psycopg.errors.ObjectNotInPrerequisiteState, prc, "aprovado")


def test_submissao_demo_nao_pode_ser_aprovada(tx):
    prc = _precificacao(tx, "PRC-2026-0148")
    tx.execute("UPDATE precificacao SET homologacao_pendente = TRUE WHERE id = %s", [prc])
    with como(tx, GERENTE_SUDESTE):
        _recusa_decisao(tx, psycopg.errors.ObjectNotInPrerequisiteState, prc, "aprovado")


def test_responsavel_vem_da_sessao_e_nao_de_quem_chama(tx):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUDESTE), tx.cursor(row_factory=dict_row) as cur:
        decisao = cur.execute(
            "INSERT INTO decisao_aprovacao (precificacao_id, decisao, comentario, responsavel_id, decidido_em) "
            "VALUES (%s, 'aprovado', 'ok', %s, '2020-01-01') RETURNING *",
            [prc, GERENTE_SUL],
        ).fetchone()

    assert decisao["responsavel_id"] == GERENTE_SUDESTE
    assert decisao["decidido_em"].year != 2020


# ------------------------------------------------------------ estado e permissão


def test_so_se_decide_precificacao_em_aprovacao(tx):
    em_preenchimento = _precificacao(tx, "PRC-2026-0144")
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUDESTE):
        _recusa_decisao(tx, psycopg.errors.ObjectNotInPrerequisiteState, em_preenchimento, "aprovado")
        _decidir(tx, prc, "aprovado")
        # Decidida, sai da fila: não se decide de novo sem nova submissão
        _recusa_decisao(tx, psycopg.errors.ObjectNotInPrerequisiteState, prc, "reprovado", "Mudei de ideia.")

    assert _status(tx, em_preenchimento) == "em_preenchimento"
    assert _status(tx, prc) == "aprovado"


def test_decisao_invalida_e_recusada(tx):
    with como(tx, GERENTE_SUDESTE):
        _recusa_decisao(tx, psycopg.errors.CheckViolation, _precificacao(tx, "PRC-2026-0148"), "talvez", "?")


def test_quem_nao_aprova_nao_registra_decisao(tx):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, ANALISTA_SUDESTE):
        _recusa_decisao(tx, psycopg.errors.InsufficientPrivilege, prc, "aprovado")
    with como(tx, EXECUTIVA_SUDESTE):
        # Sem permissão de alterar a precificação, ela nem é encontrada para decidir
        _recusa_decisao(tx, psycopg.errors.NoDataFound, prc, "aprovado")

    assert _status(tx, prc) == "em_aprovacao"


def test_gerente_de_outra_carteira_nao_decide(tx):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUL):
        _recusa_decisao(tx, psycopg.errors.NoDataFound, prc, "aprovado")

    assert _status(tx, prc) == "em_aprovacao"


@pytest.mark.parametrize("usuario", [GERENTE_SUDESTE, ANALISTA_SUDESTE])
@pytest.mark.parametrize("status", ["aprovado", "reprovado"])
def test_aplicacao_nao_aprova_mudando_o_status_direto(tx, usuario, status):
    """Sem decisão registrada não há aprovação: pela aplicação, o status só
    vira aprovado ou reprovado por decidir_aprovacao."""
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, usuario):
        _recusa(
            tx, psycopg.errors.InsufficientPrivilege, "UPDATE precificacao SET status = %s WHERE id = %s", [status, prc]
        )

    assert _status(tx, prc) == "em_aprovacao"


def test_outras_alteracoes_da_precificacao_continuam_livres(tx):
    prc = _precificacao(tx, "PRC-2026-0144")

    with como(tx, ANALISTA_SUDESTE):
        assert tx.execute("UPDATE precificacao SET frete = 'fob' WHERE id = %s", [prc]).rowcount == 1


# ------------------------------------------------------------ imutabilidade e trilha


def test_aplicacao_nao_altera_nem_apaga_decisao(tx):
    with como(tx, GERENTE_SUDESTE):
        decisao = _decidir(tx, _precificacao(tx, "PRC-2026-0148"), "reprovado", "Prazo fora da política.")
        _recusa(
            tx,
            psycopg.errors.InsufficientPrivilege,
            "UPDATE decisao_aprovacao SET comentario = 'x' WHERE id = %s",
            [decisao["id"]],
        )
        _recusa(
            tx, psycopg.errors.InsufficientPrivilege, "DELETE FROM decisao_aprovacao WHERE id = %s", [decisao["id"]]
        )


@pytest.mark.parametrize(
    "sql",
    [
        pytest.param("UPDATE decisao_aprovacao SET comentario = 'x' WHERE id = %s", id="update"),
        pytest.param("DELETE FROM decisao_aprovacao WHERE id = %s", id="delete"),
    ],
)
def test_nem_o_dono_do_banco_altera_decisao(tx, sql):
    with como(tx, GERENTE_SUDESTE):
        decisao = _decidir(tx, _precificacao(tx, "PRC-2026-0148"), "aprovado")

    _recusa(tx, psycopg.errors.RestrictViolation, sql, [decisao["id"]])


def test_decisao_e_status_entram_na_trilha_de_auditoria(tx):
    prc = _precificacao(tx, "PRC-2026-0148")

    with como(tx, GERENTE_SUDESTE):
        decisao = _decidir(tx, prc, "reprovado", "Volume não justifica o desconto.")

    with tx.cursor(row_factory=dict_row) as cur:
        [registro] = cur.execute(
            "SELECT * FROM trilha_auditoria('decisao_aprovacao', %s)", [str(decisao["id"])]
        ).fetchall()
        mudancas_status = [
            linha
            for linha in cur.execute("SELECT * FROM trilha_auditoria('precificacao', %s)", [prc]).fetchall()
            if "status" in (linha["diff"] or {})
        ]

    assert registro["operacao"] == "INSERT"
    assert registro["usuario_id"] == GERENTE_SUDESTE
    assert registro["dados_depois"]["comentario"] == "Volume não justifica o desconto."
    [mudanca] = mudancas_status
    assert mudanca["usuario_id"] == GERENTE_SUDESTE
    assert mudanca["diff"]["status"] == {"de": "em_aprovacao", "para": "reprovado"}


# ------------------------------------------------------------ histórico


def test_historico_mostra_o_nome_do_responsavel_a_quem_le_a_precificacao(tx):
    prc = _precificacao(tx, "PRC-2026-0148")
    consulta = "SELECT * FROM decisao_aprovacao_historico WHERE precificacao_id = %s"

    with como(tx, GERENTE_SUDESTE):
        _decidir(tx, prc, "reprovado", "Rever o frete.")

    with como(tx, EXECUTIVA_SUDESTE), tx.cursor(row_factory=dict_row) as cur:
        [linha] = cur.execute(consulta, [prc]).fetchall()
    with como(tx, ANALISTA_SUL):
        outra_carteira = tx.execute(consulta, [prc]).fetchall()

    assert (linha["decisao"], linha["comentario"], linha["responsavel_nome"]) == (
        "reprovado",
        "Rever o frete.",
        "Gerente Sudeste",
    )
    assert outra_carteira == []
