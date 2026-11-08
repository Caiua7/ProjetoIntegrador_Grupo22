"""Rotas de decisão de aprovação (issue #68, US37).

As regras de estado, carteira e imutabilidade são do banco e estão em
tests/banco/test_decisao_aprovacao.py; aqui se confere o contrato HTTP: o
comentário obrigatório na reprovação, a permissão e a tradução dos erros.
"""

from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import aprovacoes

GERENTE_ID = uuid4()
PRECIFICACAO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us37"}
BASE = f"/precificacoes/{PRECIFICACAO_ID}/decisoes"


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class ErroPostgrest(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message)
        self.code, self.message = code, message


class ConsultaFalsa:
    def __init__(self, cliente, tabela):
        self.cliente, self.tabela = cliente, tabela

    def __getattr__(self, _nome):
        return lambda *_args, **_kwargs: self

    def execute(self):
        self.cliente.consultas.append(self.tabela)
        return RespostaFalsa(deepcopy(self.cliente.historico))


class RpcFalsa:
    def __init__(self, cliente, nome, parametros):
        self.cliente, self.nome, self.parametros = cliente, nome, parametros

    def execute(self):
        self.cliente.chamadas.append((self.nome, self.parametros))
        if self.cliente.erro:
            raise self.cliente.erro
        return RespostaFalsa(
            {
                "id": str(uuid4()),
                "precificacao_id": self.parametros["p_precificacao_id"],
                "cenario_id": None,
                "decisao": self.parametros["p_decisao"],
                "comentario": self.parametros["p_comentario"],
                "responsavel_id": str(GERENTE_ID),
                "decidido_em": "2026-11-09T14:30:00Z",
            }
        )


class ClienteFalso:
    def __init__(self):
        self.chamadas: list[tuple[str, dict]] = []
        self.consultas: list[str] = []
        self.historico: list[dict] = []
        self.erro: Exception | None = None

    def table(self, nome):
        return ConsultaFalsa(self, nome)

    def rpc(self, nome, parametros):
        return RpcFalsa(self, nome, parametros)


@pytest.fixture
def ambiente(monkeypatch):
    cliente = ClienteFalso()
    dados_usuario = {
        "nome": "Gerente Comercial",
        "email": "gerente@example.com",
        "ativo": True,
        "perfil_codigo": "gerente_comercial",
        "perfil_nome": "Gerente Comercial",
        "permissoes": ["precificacao.ler", "precificacao.aprovar", "custo.ler"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: GERENTE_ID if token == "token-us37" else UUID(int=0))
    monkeypatch.setattr(
        auth, "carregar_usuario", lambda _db, usuario_id: dados_usuario if usuario_id == GERENTE_ID else None
    )
    monkeypatch.setattr(aprovacoes, "supabase_do_usuario", lambda _token: cliente)
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), cliente, dados_usuario
    app.dependency_overrides.clear()


# ------------------------------------------------------------ critério de aceite


@pytest.mark.parametrize("corpo", [{}, {"comentario": None}, {"comentario": ""}, {"comentario": "  \n "}])
def test_reprovar_sem_comentario_e_recusado_sem_ir_ao_banco(ambiente, corpo):
    http, cliente, _usuario = ambiente

    resposta = http.post(BASE, headers=TOKEN, json={"decisao": "reprovado", **corpo})

    assert resposta.status_code == 422
    assert "comentário" in resposta.text
    assert cliente.chamadas == []


def test_reprovacao_com_comentario_e_registrada(ambiente):
    http, cliente, _usuario = ambiente

    resposta = http.post(BASE, headers=TOKEN, json={"decisao": "reprovado", "comentario": "  Margem abaixo.  "})

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert (corpo["decisao"], corpo["comentario"]) == ("reprovado", "Margem abaixo.")
    assert (corpo["responsavel_id"], corpo["responsavel_nome"]) == (str(GERENTE_ID), "Gerente Comercial")
    assert cliente.chamadas == [
        (
            "decidir_aprovacao",
            {"p_precificacao_id": str(PRECIFICACAO_ID), "p_decisao": "reprovado", "p_comentario": "Margem abaixo."},
        )
    ]


def test_aprovacao_pode_ir_sem_comentario(ambiente):
    http, cliente, _usuario = ambiente

    resposta = http.post(BASE, headers=TOKEN, json={"decisao": "aprovado"})

    assert resposta.status_code == 201
    assert cliente.chamadas[0][1]["p_comentario"] is None


def test_responsavel_e_data_nao_vem_do_cliente(ambiente):
    http, cliente, _usuario = ambiente

    resposta = http.post(
        BASE, headers=TOKEN, json={"decisao": "aprovado", "responsavel_id": str(uuid4()), "decidido_em": "2020-01-01"}
    )

    assert resposta.status_code == 422
    assert cliente.chamadas == []


@pytest.mark.parametrize("decisao", ["talvez", "em_aprovacao", ""])
def test_decisao_fora_do_dominio_e_recusada(ambiente, decisao):
    http, cliente, _usuario = ambiente

    assert http.post(BASE, headers=TOKEN, json={"decisao": decisao, "comentario": "x"}).status_code == 422
    assert cliente.chamadas == []


# ------------------------------------------------------------ permissão e erros


def test_decidir_exige_precificacao_aprovar(ambiente):
    http, cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.ler", "precificacao.editar", "custo.ler"]

    assert http.post(BASE, headers=TOKEN, json={"decisao": "aprovado"}).status_code == 403
    assert cliente.chamadas == []


@pytest.mark.parametrize(
    ("codigo", "status_esperado"),
    [("P0002", 404), ("55000", 409), ("23514", 422), ("42501", 403), ("XX000", 503)],
)
def test_erros_do_banco_viram_resposta_tratada(ambiente, codigo, status_esperado):
    http, cliente, _usuario = ambiente
    cliente.erro = ErroPostgrest(codigo, "detalhe do banco")

    assert http.post(BASE, headers=TOKEN, json={"decisao": "aprovado"}).status_code == status_esperado


def test_precificacao_fora_de_aprovacao_devolve_409_com_o_motivo(ambiente):
    http, cliente, _usuario = ambiente
    cliente.erro = ErroPostgrest("55000", "só é possível decidir uma precificação em aprovação; esta está em aprovado")

    resposta = http.post(BASE, headers=TOKEN, json={"decisao": "aprovado"})

    assert resposta.status_code == 409
    assert "em aprovação" in resposta.json()["detail"]


# ------------------------------------------------------------ histórico


def test_historico_le_a_visao_com_o_nome_do_responsavel(ambiente):
    http, cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.ler"]
    cliente.historico = [
        {
            "id": str(uuid4()),
            "precificacao_id": str(PRECIFICACAO_ID),
            "cenario_id": str(uuid4()),
            "cenario_versao": 3,
            "decisao": "reprovado",
            "comentario": "Rever o frete.",
            "responsavel_id": str(GERENTE_ID),
            "responsavel_nome": "Gerente Comercial",
            "decidido_em": "2026-11-09T14:30:00Z",
        }
    ]

    resposta = http.get(BASE, headers=TOKEN)

    assert resposta.status_code == 200
    assert cliente.consultas == ["decisao_aprovacao_historico"]
    [linha] = resposta.json()
    assert (linha["cenario_versao"], linha["responsavel_nome"], linha["comentario"]) == (
        3,
        "Gerente Comercial",
        "Rever o frete.",
    )


def test_historico_exige_precificacao_ler(ambiente):
    http, _cliente, usuario = ambiente
    usuario["permissoes"] = ["cadastro.ler"]

    assert http.get(BASE, headers=TOKEN).status_code == 403
