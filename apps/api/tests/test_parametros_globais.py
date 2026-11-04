from copy import deepcopy
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import parametros_globais
from app.routers.parametros_globais import escolher_vigente, parametros_vigentes

USUARIO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us13"}


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class ErroPostgrest(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message


class ConsultaFalsa:
    """Aceita a cadeia do supabase-py e guarda o que foi gravado; quem filtra
    pela data são as funções puras do router."""

    def __init__(self, cliente, tabela):
        self.cliente, self.tabela = cliente, tabela

    def insert(self, dados):
        self.cliente.gravacoes.append(("insert", self.tabela, dados))
        return self

    def update(self, dados):
        self.cliente.gravacoes.append(("update", self.tabela, dados))
        return self

    def __getattr__(self, _nome):
        return lambda *_args, **_kwargs: self

    def execute(self):
        if self.cliente.erro:
            raise self.cliente.erro
        return RespostaFalsa(deepcopy(self.cliente.linhas))


class ClienteFalso:
    def __init__(self):
        self.linhas: list[dict] = []
        self.gravacoes: list[tuple] = []
        self.erro: Exception | None = None

    def table(self, nome):
        return ConsultaFalsa(self, nome)


def cambio(**campos) -> dict:
    base = {
        "id": str(uuid4()),
        "moeda": "USD",
        "data_referencia": "2026-09-09",
        "taxa": "5.604",
        "margem_seguranca_percentual": "0.02",
        "fonte": "manual",
        "created_by": None,
        "updated_by": None,
        "created_at": "2026-09-09T00:00:00Z",
        "updated_at": "2026-09-09T00:00:00Z",
    }
    return {**base, **campos}


def parametro(codigo: str, valor: str, vigencia: str) -> dict:
    return {
        "id": str(uuid4()),
        "codigo": codigo,
        "valor": valor,
        "vigencia_inicio": vigencia,
        "created_by": None,
        "updated_by": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.fixture
def ambiente(monkeypatch):
    cliente = ClienteFalso()
    dados_usuario = {
        "nome": "Analista de suprimentos",
        "email": "suprimentos@example.com",
        "ativo": True,
        "perfil_codigo": "analista_suprimentos",
        "perfil_nome": "Analista de Suprimentos",
        "permissoes": ["cambio.ler", "cambio.editar", "parametro_global.ler", "parametro_global.editar"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: USUARIO_ID if token == "token-us13" else UUID(int=0))
    monkeypatch.setattr(
        auth, "carregar_usuario", lambda _db, usuario_id: dados_usuario if usuario_id == USUARIO_ID else None
    )
    monkeypatch.setattr(parametros_globais, "supabase_do_usuario", lambda _token: cliente)
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), cliente, dados_usuario
    app.dependency_overrides.clear()


# ------------------------------------------------------------ critério de aceite


def test_parametro_alterado_vale_para_o_calculo_novo_e_o_antigo_fica_intacto():
    """Dado um parâmetro alterado, quando um novo cenário é calculado, então usa
    o valor novo, e o cálculo antigo, refeito pela sua data, usa o original."""
    historico = [
        parametro("taxa_financeira_mensal_percentual", "0.012", "2026-01-01"),
        parametro("perda_percentual", "0.02", "2026-01-01"),
    ]
    calculo_antigo = parametros_vigentes(historico, date(2026, 10, 20))

    historico.append(parametro("taxa_financeira_mensal_percentual", "0.015", "2026-11-01"))

    assert parametros_vigentes(historico, date(2026, 11, 3))["taxa_financeira_mensal_percentual"]["valor"] == "0.015"
    assert parametros_vigentes(historico, date(2026, 10, 20)) == calculo_antigo
    assert calculo_antigo["taxa_financeira_mensal_percentual"]["valor"] == "0.012"


# ------------------------------------------------------------ regras puras


def test_vigente_e_a_data_mais_recente_que_nao_passa_da_referencia():
    setembro, outubro, dezembro = (
        cambio(data_referencia="2026-09-09"),
        cambio(data_referencia="2026-10-01"),
        cambio(data_referencia="2026-12-01"),
    )
    registros = [outubro, dezembro, setembro]

    assert escolher_vigente(registros, "data_referencia", date(2026, 9, 30)) == setembro
    assert escolher_vigente(registros, "data_referencia", date(2026, 10, 1)) == outubro
    assert escolher_vigente(registros, "data_referencia", date(2026, 11, 30)) == outubro
    assert escolher_vigente(registros, "data_referencia", date(2026, 9, 1)) is None


def test_parametros_vigentes_escolhe_um_valor_por_codigo():
    registros = [
        parametro("perda_percentual", "0.02", "2026-01-01"),
        parametro("perda_percentual", "0.03", "2026-06-01"),
        parametro("prazo_medio_padrao_dias", "30", "2026-01-01"),
        parametro("prazo_medio_padrao_dias", "45", "2027-01-01"),
    ]

    vigentes = parametros_vigentes(registros, date(2026, 11, 3))

    assert {codigo: item["valor"] for codigo, item in vigentes.items()} == {
        "perda_percentual": "0.03",
        "prazo_medio_padrao_dias": "30",
    }


# ------------------------------------------------------------ câmbio


def test_cambio_vigente_devolve_a_taxa_com_margem_de_seguranca(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [cambio(taxa="5.604", margem_seguranca_percentual="0.02")]

    resposta = http.get("/cambios/vigente", headers=TOKEN, params={"moeda": "USD", "data_referencia": "2026-11-03"})

    assert resposta.status_code == 200
    assert Decimal(resposta.json()["taxa_com_margem"]) == Decimal("5.71608")


def test_sem_cambio_ate_a_data_devolve_404(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [cambio(data_referencia="2026-12-01")]

    resposta = http.get("/cambios/vigente", headers=TOKEN, params={"moeda": "USD", "data_referencia": "2026-11-03"})

    assert resposta.status_code == 404
    assert "USD" in resposta.json()["detail"]


def test_cadastro_de_cambio_grava_quem_criou(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [cambio(data_referencia="2026-11-03", taxa="5.7")]

    resposta = http.post(
        "/cambios",
        headers=TOKEN,
        json={"moeda": "USD", "data_referencia": "2026-11-03", "taxa": "5.7", "margem_seguranca_percentual": "0.02"},
    )

    assert resposta.status_code == 201
    [(operacao, tabela, dados)] = cliente.gravacoes
    assert (operacao, tabela) == ("insert", "cambio")
    assert dados["created_by"] == dados["updated_by"] == str(USUARIO_ID)


@pytest.mark.parametrize(
    "corpo",
    [
        pytest.param({"moeda": "BRL", "data_referencia": "2026-11-03", "taxa": "1"}, id="real_nao_tem_cambio"),
        pytest.param({"moeda": "usd", "data_referencia": "2026-11-03", "taxa": "5"}, id="moeda_fora_do_iso"),
        pytest.param({"moeda": "USD", "data_referencia": "2026-11-03", "taxa": "0"}, id="taxa_zero"),
        pytest.param(
            {"moeda": "USD", "data_referencia": "2026-11-03", "taxa": "5", "margem_seguranca_percentual": "2"},
            id="margem_acima_de_100",
        ),
    ],
)
def test_cambio_invalido_devolve_422_sem_gravar(ambiente, corpo):
    http, cliente, _usuario = ambiente

    assert http.post("/cambios", headers=TOKEN, json=corpo).status_code == 422
    assert cliente.gravacoes == []


def test_alterar_cambio_do_passado_devolve_409_com_o_motivo_do_banco(ambiente):
    http, cliente, _usuario = ambiente
    cliente.erro = ErroPostgrest("23001", "valor de cambio já vigente em 2026-09-09 faz parte do histórico")

    resposta = http.patch(f"/cambios/{uuid4()}", headers=TOKEN, json={"taxa": "5.9"})

    assert resposta.status_code == 409
    assert "histórico" in resposta.json()["detail"]


def test_cambio_da_mesma_moeda_e_data_devolve_409(ambiente):
    http, cliente, _usuario = ambiente
    cliente.erro = ErroPostgrest("23505")

    resposta = http.post("/cambios", headers=TOKEN, json={"moeda": "USD", "data_referencia": "2026-11-03", "taxa": "5"})

    assert resposta.status_code == 409


def test_editar_cambio_exige_permissao(ambiente):
    http, cliente, usuario = ambiente
    usuario["permissoes"] = ["cambio.ler"]

    resposta = http.post("/cambios", headers=TOKEN, json={"moeda": "USD", "data_referencia": "2026-11-03", "taxa": "5"})

    assert resposta.status_code == 403
    assert cliente.gravacoes == []


# ------------------------------------------------------------ parâmetros globais


def test_vigentes_lista_o_que_falta_cadastrar(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [
        parametro("perda_percentual", "0.02", "2026-01-01"),
        parametro("taxa_financeira_mensal_percentual", "0.012", "2026-01-01"),
    ]

    resposta = http.get("/parametros-globais/vigentes", headers=TOKEN, params={"data_referencia": "2026-11-03"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert Decimal(corpo["parametros"]["taxa_financeira_mensal_percentual"]["valor"]) == Decimal("0.012")
    assert corpo["faltando"] == ["prazo_medio_padrao_dias", "desvio_maximo_cotacao_percentual"]


@pytest.mark.parametrize(
    "corpo",
    [
        pytest.param(
            {"codigo": "perda_percentual", "valor": "2", "vigencia_inicio": "2026-12-01"}, id="percentual_acima_de_1"
        ),
        pytest.param(
            {"codigo": "prazo_medio_padrao_dias", "valor": "30.5", "vigencia_inicio": "2026-12-01"},
            id="prazo_fracionado",
        ),
        pytest.param(
            {"codigo": "margem_minima", "valor": "0.2", "vigencia_inicio": "2026-12-01"}, id="codigo_desconhecido"
        ),
    ],
)
def test_parametro_invalido_devolve_422(ambiente, corpo):
    http, cliente, _usuario = ambiente

    assert http.post("/parametros-globais", headers=TOKEN, json=corpo).status_code == 422
    assert cliente.gravacoes == []


def test_nova_vigencia_de_parametro_e_gravada(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [parametro("prazo_medio_padrao_dias", "45", "2026-12-01")]

    resposta = http.post(
        "/parametros-globais",
        headers=TOKEN,
        json={"codigo": "prazo_medio_padrao_dias", "valor": "45", "vigencia_inicio": "2026-12-01"},
    )

    assert resposta.status_code == 201
    assert cliente.gravacoes[0][:2] == ("insert", "parametro_global")


def test_ler_parametros_exige_permissao(ambiente):
    http, _cliente, usuario = ambiente
    usuario["permissoes"] = ["cadastro.ler"]

    assert http.get("/parametros-globais/vigentes", headers=TOKEN).status_code == 403
