from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import cadastros

USUARIO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us06"}


class ErroPersistencia(Exception):
    def __init__(self, code: str):
        self.code = code
        self.status_code = 400 if code in {"23503", "23514"} else 409 if code == "23505" else 403


class Resposta:
    def __init__(self, data):
        self.data = data


class ConsultaFalsa:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.dados = None
        self.filtros = []
        self.busca = None
        self.limite = None
        self.ordem = None

    def select(self, _campos="*"):
        return self

    def insert(self, dados):
        self.acao, self.dados = "insert", dados
        return self

    def update(self, dados):
        self.acao, self.dados = "update", dados
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def ilike(self, campo, valor):
        self.busca = (campo, valor.strip("% ").casefold())
        return self

    def order(self, campo):
        self.ordem = campo
        return self

    def limit(self, quantidade):
        self.limite = quantidade
        return self

    def execute(self):
        linhas = self.banco.setdefault(self.tabela, [])
        if self.acao == "insert":
            entrada = deepcopy(self.dados)
            if any(linha["codigo"] == entrada["codigo"] for linha in linhas):
                raise ErroPersistencia("23505")
            if not any(ncm["codigo"] == entrada["ncm_codigo"] for ncm in self.banco["ncm"]):
                raise ErroPersistencia("23503")
            agora = datetime.now(UTC).isoformat()
            entrada.update({"id": str(uuid4()), "ativo": True, "created_at": agora, "updated_at": agora})
            linhas.append(entrada)
            return Resposta([deepcopy(entrada)])

        correspondentes = [
            linha for linha in linhas if all(str(linha.get(campo)) == str(valor) for campo, valor in self.filtros)
        ]
        if self.busca:
            campo, termo = self.busca
            correspondentes = [linha for linha in correspondentes if termo in linha[campo].casefold()]
        if self.acao == "update":
            for linha in correspondentes:
                if "codigo" in self.dados and any(
                    outra is not linha and outra["codigo"] == self.dados["codigo"] for outra in linhas
                ):
                    raise ErroPersistencia("23505")
                if "ncm_codigo" in self.dados and not any(
                    ncm["codigo"] == self.dados["ncm_codigo"] for ncm in self.banco["ncm"]
                ):
                    raise ErroPersistencia("23503")
                linha.update(self.dados)
                linha["updated_at"] = datetime.now(UTC).isoformat()
            return Resposta(deepcopy(correspondentes[: self.limite]))
        if self.ordem:
            correspondentes.sort(key=lambda linha: linha[self.ordem])
        return Resposta(deepcopy(correspondentes[: self.limite]))


class ClienteFalso:
    def __init__(self, banco):
        self.banco = banco

    def table(self, tabela):
        return ConsultaFalsa(self.banco, tabela)


@pytest.fixture
def ambiente(monkeypatch):
    banco = {
        "ncm": [
            {"codigo": "10000000", "descricao": "Animais vivos"},
            {"codigo": "02011000", "descricao": "Carne bovina"},
        ],
        "materia_prima": [],
        "embalagem": [],
    }
    dados_usuario = {
        "nome": "Analista de suprimentos",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_suprimentos",
        "perfil_nome": "Analista de Suprimentos",
        "permissoes": ["cadastro.ler", "cadastro.editar"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: USUARIO_ID if token == "token-us06" else UUID(int=0))
    monkeypatch.setattr(
        auth, "carregar_usuario", lambda _db, usuario_id: dados_usuario if usuario_id == USUARIO_ID else None
    )
    monkeypatch.setattr(
        cadastros, "supabase_do_usuario", lambda token: ClienteFalso(banco) if token == "token-us06" else None
    )
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), banco, dados_usuario
    app.dependency_overrides.clear()


def payload(**sobrescritos):
    return {
        "codigo": "MP-001",
        "descricao": "Farinha de trigo",
        "unidade_medida": "kg",
        "ncm_codigo": "10000000",
        **sobrescritos,
    }


def test_cria_lista_consulta_edita_e_inativa_materia_prima(ambiente):
    http, banco, _usuario = ambiente
    criada = http.post("/cadastros/materias-primas", headers=TOKEN, json=payload())
    assert criada.status_code == 201
    registro = criada.json()
    assert registro["unidade_medida"] == "kg"
    assert registro["created_at"]
    assert banco["materia_prima"][0]["created_by"] == str(USUARIO_ID)

    lista = http.get("/cadastros/materias-primas", headers=TOKEN)
    assert lista.status_code == 200
    assert [item["id"] for item in lista.json()] == [registro["id"]]

    detalhe = http.get(f"/cadastros/materias-primas/{registro['id']}", headers=TOKEN)
    assert detalhe.status_code == 200
    assert detalhe.json()["descricao"] == "Farinha de trigo"

    atualizada = http.patch(
        f"/cadastros/materias-primas/{registro['id']}", headers=TOKEN, json={"descricao": "Farinha integral"}
    )
    assert atualizada.status_code == 200
    assert atualizada.json()["descricao"] == "Farinha integral"

    inativada = http.delete(f"/cadastros/materias-primas/{registro['id']}", headers=TOKEN)
    assert inativada.status_code == 200
    assert inativada.json()["ativo"] is False
    assert len(banco["materia_prima"]) == 1

    reativada = http.patch(f"/cadastros/materias-primas/{registro['id']}", headers=TOKEN, json={"ativo": True})
    assert reativada.status_code == 200
    assert reativada.json()["ativo"] is True


def test_embalagem_usa_unidade_padrao_do_schema(ambiente):
    http, _banco, _usuario = ambiente
    resposta = http.post(
        "/cadastros/embalagens",
        headers=TOKEN,
        json={"codigo": "EMB-001", "descricao": "Caixa de papelão", "ncm_codigo": "10000000"},
    )
    assert resposta.status_code == 201
    assert resposta.json()["unidade_medida"] == "un"


def test_valida_campos_codigos_unidade_e_ncm(ambiente):
    http, _banco, _usuario = ambiente
    assert http.post("/cadastros/materias-primas", headers=TOKEN, json=payload(codigo=" ")).status_code == 422
    assert http.post("/cadastros/materias-primas", headers=TOKEN, json=payload(unidade_medida="cx")).status_code == 422
    assert http.post("/cadastros/materias-primas", headers=TOKEN, json=payload(unidade_medida=None)).status_code == 422
    assert http.post("/cadastros/materias-primas", headers=TOKEN, json=payload(ncm_codigo="123")).status_code == 422
    assert http.post("/cadastros/materias-primas", headers=TOKEN, json=payload(codigo="X" * 31)).status_code == 422


def test_codigos_duplicados_e_ncm_inexistente_sao_tratados(ambiente):
    http, _banco, _usuario = ambiente
    assert http.post("/cadastros/materias-primas", headers=TOKEN, json=payload()).status_code == 201
    duplicado = http.post("/cadastros/materias-primas", headers=TOKEN, json=payload(descricao="Outra descrição"))
    assert duplicado.status_code == 409
    ncm_inexistente = http.post(
        "/cadastros/materias-primas", headers=TOKEN, json=payload(codigo="MP-002", ncm_codigo="99999999")
    )
    assert ncm_inexistente.status_code == 422


def test_registro_inexistente_e_corpo_vazio(ambiente):
    http, _banco, _usuario = ambiente
    registro_id = uuid4()
    assert http.get(f"/cadastros/embalagens/{registro_id}", headers=TOKEN).status_code == 404
    assert http.patch(f"/cadastros/embalagens/{registro_id}", headers=TOKEN, json={}).status_code == 422
    criada = http.post("/cadastros/embalagens", headers=TOKEN, json=payload()).json()
    assert http.patch(f"/cadastros/embalagens/{criada['id']}", headers=TOKEN, json={"ativo": None}).status_code == 422
    assert http.delete(f"/cadastros/embalagens/{registro_id}", headers=TOKEN).status_code == 404


def test_busca_ncm_por_descricao_e_codigo(ambiente):
    http, _banco, _usuario = ambiente
    por_descricao = http.get("/cadastros/ncm", headers=TOKEN, params={"termo": "carne"})
    assert por_descricao.status_code == 200
    assert por_descricao.json()[0]["codigo"] == "02011000"
    por_codigo = http.get("/cadastros/ncm", headers=TOKEN, params={"termo": "10000000"})
    assert por_codigo.status_code == 200
    assert any(item["codigo"] == "10000000" for item in por_codigo.json())
    por_prefixo = http.get("/cadastros/ncm", headers=TOKEN, params={"termo": "100"})
    assert por_prefixo.status_code == 200
    assert any(item["codigo"] == "10000000" for item in por_prefixo.json())


def test_rotas_exigem_sessao_e_permissao_de_edicao(ambiente):
    http, _banco, dados_usuario = ambiente
    assert http.get("/cadastros/materias-primas").status_code == 401
    dados_usuario["permissoes"] = ["cadastro.ler"]
    assert http.post("/cadastros/materias-primas", headers=TOKEN, json=payload()).status_code == 403
