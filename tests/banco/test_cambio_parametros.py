"""Câmbio e parâmetros globais (issue #49, US13 e US14).

Critério de aceite: dado um parâmetro alterado, quando um novo cenário é
calculado, então usa o valor novo e os antigos permanecem intactos. No
banco isso é garantido assim: pela aplicação, o histórico (data anterior a
hoje) não pode ser criado, alterado nem apagado; mudar um valor é
cadastrar uma nova vigência.

Cada teste roda numa transação desfeita ao final.
"""

import json
import uuid
from contextlib import contextmanager

import pytest

psycopg = pytest.importorskip("psycopg")

SUPRIMENTOS = uuid.UUID("44444444-4444-4444-4444-444444444444")
PRICING = uuid.UUID("55555555-5555-5555-5555-555555555555")
EXECUTIVA = uuid.UUID("66666666-6666-6666-6666-666666666666")


@pytest.fixture
def tx(conn):
    with conn.transaction(force_rollback=True):
        for usuario_id, perfil in (
            (SUPRIMENTOS, "analista_suprimentos"),
            (PRICING, "analista_pricing"),
            (EXECUTIVA, "executiva_contas"),
        ):
            conn.execute(
                "INSERT INTO usuario (id, nome, email, perfil_id) SELECT %s, %s, %s, id FROM perfil WHERE codigo = %s",
                [usuario_id, perfil, f"{perfil}@neoprice.test", perfil],
            )
        yield conn


@contextmanager
def como(conn, usuario_id):
    claims = json.dumps({"sub": str(usuario_id), "role": "authenticated"})
    conn.execute("SELECT set_config('request.jwt.claims', %s, true)", [claims])
    conn.execute("SET LOCAL ROLE authenticated")
    try:
        yield
    finally:
        conn.execute("RESET ROLE")
        conn.execute("SELECT set_config('request.jwt.claims', '', true)")


def _recusa(conn, erro, sql: str, parametros=None) -> None:
    with pytest.raises(erro), conn.transaction():
        conn.execute(sql, parametros)


def _vigente(conn, codigo: str, data: str):
    return conn.execute(
        "SELECT valor FROM parametro_global WHERE codigo = %s AND vigencia_inicio <= %s::date "
        "ORDER BY vigencia_inicio DESC LIMIT 1",
        [codigo, data],
    ).fetchone()[0]


# ------------------------------------------------------------ critério de aceite


def test_nova_vigencia_vale_para_o_calculo_novo_e_o_antigo_fica_intacto(tx):
    data_do_cenario_antigo = "2026-10-20"
    valor_antigo = _vigente(tx, "taxa_financeira_mensal_percentual", data_do_cenario_antigo)

    with como(tx, PRICING):
        tx.execute(
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) "
            "VALUES ('taxa_financeira_mensal_percentual', 0.015, current_date)"
        )
        assert str(_vigente(tx, "taxa_financeira_mensal_percentual", "9999-12-31")) == "0.015000"
        assert _vigente(tx, "taxa_financeira_mensal_percentual", data_do_cenario_antigo) == valor_antigo


def test_valor_ja_vigente_nao_pode_ser_alterado_pela_aplicacao(tx):
    with como(tx, PRICING):
        _recusa(
            tx,
            psycopg.errors.RestrictViolation,
            "UPDATE parametro_global SET valor = 0.05 WHERE codigo = 'perda_percentual' AND vigencia_inicio = DATE '2026-01-01'",
        )


def test_vigencia_nao_pode_comecar_no_passado(tx):
    with como(tx, PRICING):
        _recusa(
            tx,
            psycopg.errors.RestrictViolation,
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) "
            "VALUES ('perda_percentual', 0.03, current_date - 1)",
        )
    with como(tx, SUPRIMENTOS):
        _recusa(
            tx,
            psycopg.errors.RestrictViolation,
            "INSERT INTO cambio (moeda, data_referencia, taxa) VALUES ('USD', current_date - 1, 5.9)",
        )


def test_vigencia_de_hoje_ou_futura_ainda_pode_ser_corrigida(tx):
    with como(tx, SUPRIMENTOS):
        tx.execute("INSERT INTO cambio (moeda, data_referencia, taxa) VALUES ('USD', current_date, 5.70)")
        alteradas = tx.execute(
            "UPDATE cambio SET taxa = 5.72 WHERE moeda = 'USD' AND data_referencia = current_date"
        ).rowcount

    assert alteradas == 1


def test_vigencia_futura_nao_pode_ser_movida_para_o_passado(tx):
    with como(tx, PRICING):
        tx.execute(
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) VALUES ('perda_percentual', 0.03, current_date + 30)"
        )
        _recusa(
            tx,
            psycopg.errors.RestrictViolation,
            "UPDATE parametro_global SET vigencia_inicio = current_date - 30 "
            "WHERE codigo = 'perda_percentual' AND vigencia_inicio = current_date + 30",
        )


def test_historico_nao_se_apaga(tx):
    with como(tx, SUPRIMENTOS):
        _recusa(tx, psycopg.errors.InsufficientPrivilege, "DELETE FROM cambio WHERE moeda = 'USD'")


# ------------------------------------------------------------ permissões


def test_so_suprimentos_edita_cambio_e_so_pricing_edita_parametro(tx):
    with como(tx, PRICING):
        _recusa(
            tx,
            psycopg.errors.InsufficientPrivilege,
            "INSERT INTO cambio (moeda, data_referencia, taxa) VALUES ('USD', current_date, 5.7)",
        )
    with como(tx, SUPRIMENTOS):
        _recusa(
            tx,
            psycopg.errors.InsufficientPrivilege,
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) VALUES ('perda_percentual', 0.03, current_date)",
        )


def test_executiva_nao_enxerga_cambio_nem_parametros(tx):
    with como(tx, EXECUTIVA):
        assert tx.execute("SELECT count(*) FROM cambio").fetchone()[0] == 0
        assert tx.execute("SELECT count(*) FROM parametro_global").fetchone()[0] == 0

    with como(tx, PRICING):
        assert tx.execute("SELECT count(*) FROM cambio").fetchone()[0] > 0


def test_alteracao_fica_na_auditoria_com_o_usuario(tx):
    with como(tx, SUPRIMENTOS):
        tx.execute("INSERT INTO cambio (moeda, data_referencia, taxa) VALUES ('USD', current_date, 5.70)")

    assert tx.execute(
        "SELECT operacao, usuario_id FROM auditoria WHERE tabela = 'cambio' AND usuario_id IS NOT NULL"
    ).fetchall() == [("INSERT", SUPRIMENTOS)]


# ------------------------------------------------------------ restrições


@pytest.mark.parametrize(
    "sql",
    [
        pytest.param("INSERT INTO cambio (moeda, data_referencia, taxa) VALUES ('BRL', current_date, 1)", id="real"),
        pytest.param(
            "INSERT INTO cambio (moeda, data_referencia, taxa) VALUES ('USD', current_date, 0)", id="taxa_zero"
        ),
        pytest.param(
            "INSERT INTO cambio (moeda, data_referencia, taxa, margem_seguranca_percentual) VALUES ('USD', current_date, 5, 1.5)",
            id="margem_acima_de_1",
        ),
        pytest.param(
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) VALUES ('prazo_medio_padrao_dias', 30.5, current_date)",
            id="prazo_fracionado",
        ),
        pytest.param(
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) VALUES ('perda_percentual', 2, current_date)",
            id="percentual_acima_de_1",
        ),
        pytest.param(
            "INSERT INTO parametro_global (codigo, valor, vigencia_inicio) VALUES ('margem_minima', 0.2, current_date)",
            id="codigo_desconhecido",
        ),
    ],
)
def test_valores_invalidos_sao_recusados(tx, sql):
    _recusa(tx, psycopg.errors.CheckViolation, sql)


def test_mesma_moeda_e_data_so_uma_vez(tx):
    _recusa(
        tx,
        psycopg.errors.UniqueViolation,
        "INSERT INTO cambio (moeda, data_referencia, taxa) VALUES ('USD', DATE '2026-09-09', 5.9)",
    )
