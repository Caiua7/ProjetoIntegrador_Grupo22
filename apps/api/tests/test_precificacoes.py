from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import precificacoes

USUARIO_ID = uuid4()
CLIENTE_ID = uuid4()
PRODUTO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us57"}


class Resposta:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.dados = None
        self.filtros = []

    def select(self, *_args):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, str(valor)))
        return self

    def insert(self, dados):
        self.acao, self.dados = "insert", dados
        return self

    def execute(self):
        linhas = self.banco.setdefault(self.tabela, [])
        if self.acao == "insert":
            agora = datetime.now(UTC).isoformat()
            registro = {
                "id": str(uuid4()),
                "created_at": agora,
                "updated_at": agora,
                "status": "em_preenchimento",
                **self.dados,
            }
            linhas.append(registro)
            return Resposta([registro])
        return Resposta(
            [linha for linha in linhas if all(str(linha.get(campo)) == valor for campo, valor in self.filtros)]
        )


class ClienteFalso:
    def __init__(self, banco):
        self.banco = banco
        self.chamadas_rpc = []

    def table(self, tabela):
        return Consulta(self.banco, tabela)

    def rpc(self, nome, parametros):
        self.chamadas_rpc.append((nome, parametros))
        cliente = self

        class Chamada:
            def execute(self):
                if nome == "submeter_precificacao":
                    for item in cliente.banco["precificacao"]:
                        if item["id"] == parametros["p_precificacao_id"]:
                            item["status"] = "em_aprovacao"
                            item["homologacao_pendente"] = True
                    return Resposta(
                        [
                            {
                                "pode_submeter": True,
                                "modo_politica": "demonstracao",
                                "homologacao_pendente": True,
                                "campos_obrigatorios": ["uf_destino", "frete", "regime_tributario"],
                                "motivos_bloqueio": [],
                                "status": "em_aprovacao",
                            }
                        ]
                    )
                return Resposta(
                    [
                        {
                            "pode_submeter": True,
                            "modo_politica": "demonstracao",
                            "homologacao_pendente": True,
                            "campos_obrigatorios": ["uf_destino", "frete", "regime_tributario"],
                            "motivos_bloqueio": [],
                        }
                    ]
                )

        return Chamada()


@pytest.fixture
def ambiente(monkeypatch):
    banco = {
        "cliente": [{"id": str(CLIENTE_ID), "codigo": "C-01", "razao_social": "Cliente teste", "ativo": True}],
        "produto": [{"id": str(PRODUTO_ID), "codigo": "P-01", "descricao": "Produto teste", "ativo": True}],
        "precificacao": [],
    }
    dados_usuario = {
        "nome": "Analista",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_pricing",
        "perfil_nome": "Analista de Pricing",
        "permissoes": ["precificacao.ler", "precificacao.editar", "cliente.ler", "cadastro.ler"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda _token: USUARIO_ID)
    monkeypatch.setattr(auth, "carregar_usuario", lambda _db, _id: dados_usuario)
    monkeypatch.setattr(precificacoes, "supabase_do_usuario", lambda _token: ClienteFalso(banco))
    cliente_servico = ClienteFalso(banco)
    monkeypatch.setattr(precificacoes, "supabase_servico", lambda: cliente_servico)
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), banco, dados_usuario, cliente_servico
    app.dependency_overrides.clear()


def test_opcoes_usa_cadastros_persistidos(ambiente):
    cliente, _banco, _usuario, _servico = ambiente
    resposta = cliente.get("/precificacoes/opcoes", headers=TOKEN)
    assert resposta.status_code == 200
    assert resposta.json()["clientes"][0]["id"] == str(CLIENTE_ID)
    assert resposta.json()["produtos"][0]["id"] == str(PRODUTO_ID)


def test_cria_precificacao_completa_em_preenchimento(ambiente):
    cliente, banco, _usuario, _servico = ambiente
    resposta = cliente.post(
        "/precificacoes",
        headers=TOKEN,
        json={
            "cliente_id": str(CLIENTE_ID),
            "produto_id": str(PRODUTO_ID),
            "modalidade_comercial": "full_service_nacional",
            "uf_destino": "SP",
            "frete": "cif",
            "regime_tributario": "lucro_real",
        },
    )
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "em_preenchimento"
    assert resposta.json()["uf_destino"] == "SP"
    assert len(banco["precificacao"]) == 1


def test_rejeita_cabecalho_sem_campo_obrigatorio(ambiente):
    cliente, _banco, _usuario, _servico = ambiente
    resposta = cliente.post(
        "/precificacoes",
        headers=TOKEN,
        json={
            "cliente_id": str(CLIENTE_ID),
            "produto_id": str(PRODUTO_ID),
            "modalidade_comercial": "full_service_nacional",
        },
    )
    assert resposta.status_code == 422


def test_opcoes_exigem_permissao_de_leitura_dos_cadastros(ambiente):
    cliente, _banco, usuario, _servico = ambiente
    usuario["permissoes"] = ["precificacao.editar"]
    resposta = cliente.get("/precificacoes/opcoes", headers=TOKEN)
    assert resposta.status_code == 403


def test_lista_precificacao_legada_sem_cabecalho_completo(ambiente):
    cliente, banco, _usuario, _servico = ambiente
    agora = datetime.now(UTC).isoformat()
    banco["precificacao"] = [
        {
            "id": str(uuid4()),
            "codigo": "PRC-2026-0148",
            "cliente_id": str(CLIENTE_ID),
            "produto_id": str(PRODUTO_ID),
            "modalidade_comercial": "full_service_nacional",
            "uf_destino": None,
            "frete": None,
            "regime_tributario": None,
            "status": "em_aprovacao",
            "created_at": agora,
            "updated_at": agora,
        }
    ]

    resposta = cliente.get("/precificacoes", headers=TOKEN)

    assert resposta.status_code == 200
    assert resposta.json()[0]["uf_destino"] is None
    assert resposta.json()[0]["frete"] is None


def test_verificacao_e_submissao_usam_rpc_privilegiado_com_usuario(ambiente):
    http, banco, _usuario, servico = ambiente
    prc = str(uuid4())
    banco["precificacao"].append(
        {
            "id": prc,
            "codigo": "PRC-TESTE",
            "cliente_id": str(CLIENTE_ID),
            "produto_id": str(PRODUTO_ID),
            "modalidade_comercial": "full_service_nacional",
            "uf_destino": "SP",
            "frete": "cif",
            "regime_tributario": "lucro_real",
            "status": "em_preenchimento",
            "homologacao_pendente": False,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    verificacao = http.get(f"/precificacoes/{prc}/submissao", headers=TOKEN)
    resposta = http.post(f"/precificacoes/{prc}/submissao", headers=TOKEN)
    assert verificacao.status_code == 200 and verificacao.json()["pode_submeter"] is True
    assert resposta.status_code == 200 and resposta.json()["status"] == "em_aprovacao"
    assert resposta.json()["homologacao_pendente"] is True
    assert servico.chamadas_rpc[0] == (
        "avaliar_submissao_precificacao",
        {"p_usuario_id": str(USUARIO_ID), "p_precificacao_id": prc},
    )
    assert servico.chamadas_rpc[1][0] == "submeter_precificacao"


def test_submissao_exige_permissao_de_edicao(ambiente):
    http, _banco, usuario, servico = ambiente
    usuario["permissoes"] = ["precificacao.ler"]
    resposta = http.post(f"/precificacoes/{uuid4()}/submissao", headers=TOKEN)
    assert resposta.status_code == 403
    assert servico.chamadas_rpc == []
