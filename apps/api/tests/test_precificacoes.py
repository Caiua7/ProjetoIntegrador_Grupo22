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

    def table(self, tabela):
        return Consulta(self.banco, tabela)


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
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), banco, dados_usuario
    app.dependency_overrides.clear()


def test_opcoes_usa_cadastros_persistidos(ambiente):
    cliente, _banco, _usuario = ambiente
    resposta = cliente.get("/precificacoes/opcoes", headers=TOKEN)
    assert resposta.status_code == 200
    assert resposta.json()["clientes"][0]["id"] == str(CLIENTE_ID)
    assert resposta.json()["produtos"][0]["id"] == str(PRODUTO_ID)


def test_cria_precificacao_completa_em_preenchimento(ambiente):
    cliente, banco, _usuario = ambiente
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
    cliente, _banco, _usuario = ambiente
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
    cliente, _banco, usuario = ambiente
    usuario["permissoes"] = ["precificacao.editar"]
    resposta = cliente.get("/precificacoes/opcoes", headers=TOKEN)
    assert resposta.status_code == 403
