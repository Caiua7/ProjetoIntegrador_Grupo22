"""Fila de aprovação do gerente (issue #67, US36).

O recorte de quem vê o quê (carteira, aprovar e custo) é da visão
`fila_aprovacao` e está em tests/banco/test_fila_aprovacao.py; aqui ficam a
regra de política, os filtros, a ordenação e o contrato HTTP.
"""

from copy import deepcopy
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import fila_aprovacao
from app.routers.fila_aprovacao import classificar, montar_fila

GERENTE_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us36"}
NUTRAFIT, CORPORE = uuid4(), uuid4()


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class ConsultaFalsa:
    def __init__(self, cliente, tabela):
        self.cliente, self.tabela = cliente, tabela

    def __getattr__(self, _nome):
        return lambda *_args, **_kwargs: self

    def execute(self):
        dados = self.cliente.fila if self.tabela == "fila_aprovacao" else self.cliente.politica
        return RespostaFalsa(deepcopy(dados))


class ClienteFalso:
    def __init__(self):
        self.fila: list[dict] = []
        self.politica: list[dict] = [{"valor": "0.24", "vigencia_inicio": "2026-01-01"}]

    def table(self, nome):
        return ConsultaFalsa(self, nome)


def item(codigo: str, cliente_id, margem: str | None, submetido_em: str) -> dict:
    return {
        "precificacao_id": str(uuid4()),
        "codigo": codigo,
        "cliente_id": str(cliente_id),
        "cliente_nome": "Nutrafit Distribuidora" if cliente_id == NUTRAFIT else "Corpore Suplementos",
        "produto_id": str(uuid4()),
        "produto_descricao": "WPC 80 — pote 600 g",
        "modalidade_comercial": "full_service_nacional",
        "uf_destino": "SP",
        "homologacao_pendente": False,
        "submetido_em": submetido_em,
        "submetido_por_nome": "Rafael Costa",
        "cenario_versao": None if margem is None else 3,
        "versao_anterior": None if margem is None else 2,
        "volume": None if margem is None else "42000",
        "preco_bruto": None if margem is None else "57.94",
        "margem_contribuicao_valor": None if margem is None else "11.67",
        "margem_contribuicao_percentual": margem,
    }


# Dentro da política (28,4%), abaixo (19,2%), sem cenário, e Corpore abaixo (15%)
PRC_148 = item("PRC-0148", NUTRAFIT, "0.284", "2026-11-12T10:00:00Z")
PRC_147 = item("PRC-0147", NUTRAFIT, "0.192", "2026-11-10T09:00:00Z")
PRC_146 = item("PRC-0146", NUTRAFIT, None, "2026-11-11T09:00:00Z")
PRC_145 = item("PRC-0145", CORPORE, "0.15", "2026-11-13T09:00:00Z")
FILA = [PRC_148, PRC_147, PRC_146, PRC_145]


@pytest.fixture
def ambiente(monkeypatch):
    cliente = ClienteFalso()
    dados_usuario = {
        "nome": "Marcos Tavares",
        "email": "gerente@example.com",
        "ativo": True,
        "perfil_codigo": "gerente_comercial",
        "perfil_nome": "Gerente Comercial",
        "permissoes": ["precificacao.ler", "precificacao.aprovar", "custo.ler", "parametro_global.ler"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: GERENTE_ID if token == "token-us36" else UUID(int=0))
    monkeypatch.setattr(
        auth, "carregar_usuario", lambda _db, usuario_id: dados_usuario if usuario_id == GERENTE_ID else None
    )
    monkeypatch.setattr(fila_aprovacao, "supabase_do_usuario", lambda _token: cliente)
    app.dependency_overrides[get_db] = lambda: None
    cliente.fila = deepcopy(FILA)
    yield TestClient(app), cliente, dados_usuario
    app.dependency_overrides.clear()


def _codigos(resposta) -> list[str]:
    return [linha["codigo"] for linha in resposta.json()["itens"]]


# ------------------------------------------------------------ critério de aceite


def test_filtro_abaixo_da_politica_traz_so_os_cenarios_fora_dela(ambiente):
    http, _cliente, _usuario = ambiente

    resposta = http.get("/aprovacoes/fila", headers=TOKEN, params={"situacao": "abaixo_da_politica"})

    assert resposta.status_code == 200
    assert _codigos(resposta) == ["PRC-0147", "PRC-0145"]
    assert all(linha["abaixo_da_politica"] for linha in resposta.json()["itens"])
    assert resposta.json()["politica"] == {"margem_minima": "0.24", "vigencia_inicio": "2026-01-01"}


# ------------------------------------------------------------ regra pura


def test_distancia_da_politica_em_fracao():
    classificado = classificar(PRC_147, Decimal("0.24"))

    assert classificado["abaixo_da_politica"] is True
    assert classificado["distancia_da_politica"] == Decimal("-0.048")


def test_margem_igual_a_politica_esta_dentro():
    assert classificar(item("X", NUTRAFIT, "0.24", "2026-11-01"), Decimal("0.24"))["abaixo_da_politica"] is False


def test_sem_politica_ou_sem_cenario_nao_ha_classificacao():
    assert classificar(PRC_148, None)["abaixo_da_politica"] is None
    assert classificar(PRC_146, Decimal("0.24"))["distancia_da_politica"] is None


def test_fila_ordena_pela_submissao_mais_antiga_primeiro():
    fila = montar_fila(FILA, Decimal("0.24"))

    assert [linha["codigo"] for linha in fila] == ["PRC-0147", "PRC-0146", "PRC-0148", "PRC-0145"]
    assert [linha["codigo"] for linha in montar_fila(FILA, Decimal("0.24"), ordem="mais_recentes")] == [
        "PRC-0145",
        "PRC-0148",
        "PRC-0146",
        "PRC-0147",
    ]


def test_dentro_da_politica_exclui_o_que_nao_tem_cenario():
    fila = montar_fila(FILA, Decimal("0.24"), situacao="dentro_da_politica")

    assert [linha["codigo"] for linha in fila] == ["PRC-0148"]


def test_filtros_de_cliente_e_teto_de_margem_se_combinam():
    fila = montar_fila(FILA, Decimal("0.24"), cliente_id=NUTRAFIT, margem_ate=Decimal("0.20"))

    assert [linha["codigo"] for linha in fila] == ["PRC-0147"]


# ------------------------------------------------------------ rota


def test_fila_sem_filtro_traz_todas_e_a_lista_de_clientes(ambiente):
    http, _cliente, _usuario = ambiente

    resposta = http.get("/aprovacoes/fila", headers=TOKEN)

    corpo = resposta.json()
    assert corpo["total_em_aprovacao"] == 4
    assert _codigos(resposta) == ["PRC-0147", "PRC-0146", "PRC-0148", "PRC-0145"]
    assert [c["nome"] for c in corpo["clientes"]] == ["Corpore Suplementos", "Nutrafit Distribuidora"]
    primeira = corpo["itens"][0]
    assert (primeira["versao_anterior"], primeira["cenario_versao"]) == (2, 3)
    assert Decimal(primeira["distancia_da_politica"]) == Decimal("-0.048")


def test_filtro_por_cliente(ambiente):
    http, _cliente, _usuario = ambiente

    resposta = http.get("/aprovacoes/fila", headers=TOKEN, params={"cliente_id": str(CORPORE)})

    assert _codigos(resposta) == ["PRC-0145"]
    assert resposta.json()["total_em_aprovacao"] == 4


def test_sem_politica_cadastrada_o_filtro_por_ela_e_recusado_mas_a_fila_abre(ambiente):
    http, cliente, _usuario = ambiente
    cliente.politica = []

    sem_filtro = http.get("/aprovacoes/fila", headers=TOKEN)
    com_filtro = http.get("/aprovacoes/fila", headers=TOKEN, params={"situacao": "abaixo_da_politica"})

    assert sem_filtro.status_code == 200
    assert sem_filtro.json()["politica"] is None
    assert sem_filtro.json()["itens"][0]["abaixo_da_politica"] is None
    assert com_filtro.status_code == 409
    assert "margem mínima" in com_filtro.json()["detail"]


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"situacao": "qualquer"}, id="situacao_invalida"),
        pytest.param({"margem_ate": "1.5"}, id="margem_acima_de_100"),
        pytest.param({"ordem": "alfabetica"}, id="ordem_invalida"),
    ],
)
def test_parametros_invalidos_devolvem_422(ambiente, params):
    http, _cliente, _usuario = ambiente

    assert http.get("/aprovacoes/fila", headers=TOKEN, params=params).status_code == 422


def test_fila_exige_permissao_de_aprovar(ambiente):
    http, _cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.ler", "custo.ler"]

    assert http.get("/aprovacoes/fila", headers=TOKEN).status_code == 403
