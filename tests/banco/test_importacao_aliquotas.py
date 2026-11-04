"""Importação em massa de alíquotas (issue #48, US12): a função
`importar_aliquotas` grava o lote inteiro ou nada, respeita o RLS de quem
chama e só toca as linhas que mudaram.

Cada teste roda numa transação desfeita ao final.
"""

import json
import uuid
from contextlib import contextmanager

import pytest

psycopg = pytest.importorskip("psycopg")

ANALISTA = uuid.UUID("22222222-2222-2222-2222-222222222222")
EXECUTIVA = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _aliquota(**campos) -> dict:
    base = {
        "uf_destino": "SP",
        "ncm_codigo": None,
        "regime_tributario": "lucro_real",
        "vigencia_inicio": "2026-01-01",
        "pis_percentual": "0.0165",
        "cofins_percentual": "0.076",
        "icms_percentual": "0.18",
        "ipi_percentual": "0",
        "icms_interno_percentual": "0.18",
        "fcp_percentual": "0",
        "mva_percentual": "0",
    }
    return {**base, **campos}


# Igual à regra geral de SP / Lucro Presumido do seed: não muda nada
INALTERADA = _aliquota(regime_tributario="lucro_presumido")
# Regra geral de SP / Lucro Real do seed com outro ICMS
ATUALIZADA = _aliquota(icms_percentual="0.17")
# Regra de MG para um NCM que o seed não tem
NOVA = _aliquota(uf_destino="MG", ncm_codigo="04041000", regime_tributario="lucro_presumido", mva_percentual="0.25")
LOTE = [NOVA, ATUALIZADA, INALTERADA]


@pytest.fixture
def tx(conn):
    with conn.transaction(force_rollback=True):
        for usuario_id, perfil in ((ANALISTA, "analista_pricing"), (EXECUTIVA, "executiva_contas")):
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


def _importar(conn, lote: list[dict], simular: bool) -> tuple[int, int, int]:
    return conn.execute(
        "SELECT novas, atualizadas, inalteradas FROM importar_aliquotas(%s::jsonb, %s)", [json.dumps(lote), simular]
    ).fetchone()


def _retrato(conn) -> tuple:
    return conn.execute(
        "SELECT count(*), md5(string_agg(a::text, '|' ORDER BY a::text)) FROM aliquota_fiscal a"
    ).fetchone()


def test_simulacao_conta_sem_gravar(tx):
    antes = _retrato(tx)

    with como(tx, ANALISTA):
        contagem = _importar(tx, LOTE, simular=True)

    assert contagem == (1, 1, 1)
    assert _retrato(tx) == antes


def test_importacao_insere_a_nova_e_atualiza_a_alterada(tx):
    total_antes = _retrato(tx)[0]

    with como(tx, ANALISTA):
        assert _importar(tx, LOTE, simular=False) == (1, 1, 1)

    assert _retrato(tx)[0] == total_antes + 1
    nova = tx.execute(
        "SELECT mva_percentual, created_by, updated_by FROM aliquota_fiscal "
        "WHERE uf_destino = 'MG' AND ncm_codigo = '04041000'"
    ).fetchone()
    assert (str(nova[0]), nova[1], nova[2]) == ("0.250000", ANALISTA, ANALISTA)
    icms_sp, atualizou = tx.execute(
        "SELECT icms_percentual, updated_by FROM aliquota_fiscal "
        "WHERE uf_destino = 'SP' AND ncm_codigo IS NULL AND regime_tributario = 'lucro_real' "
        "AND vigencia_inicio = DATE '2026-01-01'"
    ).fetchone()
    assert (str(icms_sp), atualizou) == ("0.170000", ANALISTA)


def test_reimportar_o_mesmo_lote_nao_muda_nada(tx):
    with como(tx, ANALISTA):
        _importar(tx, LOTE, simular=False)
    depois_da_primeira = _retrato(tx)

    with como(tx, ANALISTA):
        assert _importar(tx, LOTE, simular=False) == (0, 0, 3)

    assert _retrato(tx) == depois_da_primeira


def test_auditoria_registra_so_o_que_mudou_com_o_usuario(tx):
    with como(tx, ANALISTA):
        _importar(tx, LOTE, simular=False)

    operacoes = tx.execute(
        "SELECT operacao, usuario_id FROM auditoria WHERE tabela = 'aliquota_fiscal' AND usuario_id IS NOT NULL "
        "ORDER BY id"
    ).fetchall()
    assert operacoes == [("INSERT", ANALISTA), ("UPDATE", ANALISTA)]


def test_uma_linha_invalida_desfaz_o_lote_inteiro(tx):
    antes = _retrato(tx)
    lote = [NOVA, _aliquota(uf_destino="XX")]

    with como(tx, ANALISTA), pytest.raises(psycopg.errors.ForeignKeyViolation), tx.transaction():
        _importar(tx, lote, simular=False)

    assert _retrato(tx) == antes


def test_perfil_sem_permissao_de_edicao_nao_importa(tx):
    antes = _retrato(tx)

    with como(tx, EXECUTIVA), pytest.raises(psycopg.errors.InsufficientPrivilege), tx.transaction():
        _importar(tx, [NOVA], simular=False)

    assert _retrato(tx) == antes


def test_lote_que_nao_e_array_e_recusado(tx):
    with como(tx, ANALISTA), pytest.raises(psycopg.errors.InvalidParameterValue), tx.transaction():
        tx.execute("SELECT * FROM importar_aliquotas('{}'::jsonb, true)")
