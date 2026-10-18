from copy import deepcopy
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import cotacoes

USUARIO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us25"}
MP_ID = uuid4()
FORNECEDOR_A = uuid4()
FORNECEDOR_B = uuid4()
PARAMS = {"materia_prima_id": str(MP_ID), "data_referencia": "2026-10-18"}


class ErroPostgrest(Exception):
    def __init__(self, code: str):
        self.code = code


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class ChamadaRpcFalsa:
    def __init__(self, cliente, nome, parametros):
        self.cliente, self.nome, self.parametros = cliente, nome, parametros

    def execute(self):
        self.cliente.chamadas.append((self.nome, self.parametros))
        if self.cliente.erro:
            raise self.cliente.erro
        return RespostaFalsa(deepcopy(self.cliente.linhas))


class ClienteFalso:
    def __init__(self):
        self.linhas: list[dict] = []
        self.erro: Exception | None = None
        self.chamadas: list[tuple[str, dict]] = []

    def rpc(self, nome, parametros):
        return ChamadaRpcFalsa(self, nome, parametros)


def linha(**campos) -> dict:
    base = {
        "id": str(uuid4()),
        "materia_prima_id": str(MP_ID),
        "fornecedor_id": str(FORNECEDOR_A),
        "moeda": "BRL",
        "preco": 10.5,
        "volume_minimo": 0,
        "validade_inicio": "2026-10-01",
        "validade_fim": "2026-10-31",
        "prazo_entrega_dias": 7,
        "ativo": True,
    }
    return {**base, **campos}


@pytest.fixture
def ambiente(monkeypatch):
    cliente = ClienteFalso()
    tokens: list[str] = []
    dados_usuario = {
        "nome": "Analista de pricing",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_pricing",
        "perfil_nome": "Analista de Pricing",
        "permissoes": ["custo.ler"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: USUARIO_ID if token == "token-us25" else UUID(int=0))
    monkeypatch.setattr(
        auth, "carregar_usuario", lambda _db, usuario_id: dados_usuario if usuario_id == USUARIO_ID else None
    )
    monkeypatch.setattr(cotacoes, "supabase_do_usuario", lambda token: tokens.append(token) or cliente)
    app.dependency_overrides[get_db] = lambda: None
    cliente.tokens = tokens
    yield TestClient(app), cliente, dados_usuario
    app.dependency_overrides.clear()


def test_resolve_a_segunda_faixa_para_250_kg(ambiente):
    http, cliente, _usuario = ambiente
    faixa_1 = linha(volume_minimo=0, preco=10.5)
    faixa_2 = linha(volume_minimo=101, preco=8.25)
    cliente.linhas = [faixa_1, faixa_2]

    resposta = http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": "250"})

    assert resposta.status_code == 200
    assert resposta.json()["id"] == faixa_2["id"]
    assert Decimal(resposta.json()["preco"]) == Decimal("8.25")
    assert cliente.chamadas == [("cotacoes_vigentes", {"p_materia_prima_id": str(MP_ID), "p_data": "2026-10-18"})]


@pytest.mark.parametrize(("quantidade", "faixa"), [("100", 0), ("101", 1)])
def test_borda_entre_as_faixas(ambiente, quantidade, faixa):
    http, cliente, _usuario = ambiente
    cliente.linhas = [linha(volume_minimo=0), linha(volume_minimo=101)]

    resposta = http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": quantidade})

    assert resposta.status_code == 200
    assert resposta.json()["id"] == cliente.linhas[faixa]["id"]


def test_sem_cotacao_vigente_devolve_404(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = []

    resposta = http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": "250"})

    assert resposta.status_code == 404
    assert "vigente" in resposta.json()["detail"]


def test_cotacao_vencida_na_data_devolve_404(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [linha(validade_inicio="2026-08-01", validade_fim="2026-09-30")]

    resposta = http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": "250"})

    assert resposta.status_code == 404


def test_quantidade_abaixo_do_menor_minimo_devolve_404(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [linha(volume_minimo=50)]

    resposta = http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": "30"})

    assert resposta.status_code == 404
    assert "volume mínimo" in resposta.json()["detail"]


def test_empate_entre_fornecedores_devolve_409_e_o_fornecedor_resolve(ambiente):
    http, cliente, _usuario = ambiente
    de_a = linha(fornecedor_id=str(FORNECEDOR_A))
    de_b = linha(fornecedor_id=str(FORNECEDOR_B))
    cliente.linhas = [de_a, de_b]

    ambigua = http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": "10"})
    assert ambigua.status_code == 409
    assert "empatadas" in ambigua.json()["detail"]

    resolvida = http.get(
        "/cotacoes/resolver",
        headers=TOKEN,
        params={**PARAMS, "quantidade": "10", "fornecedor_id": str(FORNECEDOR_B)},
    )
    assert resolvida.status_code == 200
    assert resolvida.json()["id"] == de_b["id"]


@pytest.mark.parametrize("quantidade", ["0", "-5", "abc", "NaN"])
def test_quantidade_invalida_devolve_422(ambiente, quantidade):
    http, _cliente, _usuario = ambiente

    resposta = http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": quantidade})

    assert resposta.status_code == 422


def test_quantidade_e_materia_prima_sao_obrigatorias(ambiente):
    http, _cliente, _usuario = ambiente
    assert http.get("/cotacoes/resolver", headers=TOKEN, params={"materia_prima_id": str(MP_ID)}).status_code == 422
    assert http.get("/cotacoes/resolver", headers=TOKEN, params={"quantidade": "10"}).status_code == 422


def test_lista_as_vigentes_da_menor_para_a_maior_faixa(ambiente):
    http, cliente, _usuario = ambiente
    faixa_2 = linha(volume_minimo=101)
    faixa_1 = linha(volume_minimo=0)
    vencida = linha(validade_inicio="2026-08-01", validade_fim="2026-09-30")
    cliente.linhas = [faixa_2, vencida, faixa_1]

    resposta = http.get("/cotacoes/vigentes", headers=TOKEN, params=PARAMS)

    assert resposta.status_code == 200
    assert [item["id"] for item in resposta.json()] == [faixa_1["id"], faixa_2["id"]]


def test_consulta_repassa_o_token_do_usuario(ambiente):
    http, cliente, _usuario = ambiente

    resposta = http.get("/cotacoes/vigentes", headers=TOKEN, params=PARAMS)

    assert resposta.status_code == 200
    assert cliente.tokens == ["token-us25"]


def test_exige_sessao_e_permissao_de_leitura_de_custo(ambiente):
    http, _cliente, dados_usuario = ambiente
    assert http.get("/cotacoes/vigentes", params=PARAMS).status_code == 401
    assert http.get("/cotacoes/resolver", params={**PARAMS, "quantidade": "10"}).status_code == 401

    dados_usuario["permissoes"] = ["cadastro.ler"]
    assert http.get("/cotacoes/vigentes", headers=TOKEN, params=PARAMS).status_code == 403
    assert http.get("/cotacoes/resolver", headers=TOKEN, params={**PARAMS, "quantidade": "10"}).status_code == 403


def test_falhas_do_banco_viram_403_e_503(ambiente):
    http, cliente, _usuario = ambiente

    cliente.erro = ErroPostgrest("42501")
    assert http.get("/cotacoes/vigentes", headers=TOKEN, params=PARAMS).status_code == 403

    cliente.erro = RuntimeError("conexão perdida")
    assert http.get("/cotacoes/vigentes", headers=TOKEN, params=PARAMS).status_code == 503
