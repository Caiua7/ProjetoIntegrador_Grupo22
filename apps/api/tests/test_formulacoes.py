from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import formulacoes
from app.routers.formulacoes import FormulacaoEntrada, ItemEntrada

USUARIO_ID = uuid4()
PRODUTO_ID = uuid4()
MP_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us62"}


class Resposta:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class ConsultaFalsa:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.dados = None
        self.filtros = []
        self.limite = None
        self.campo_ordem = None

    def select(self, _campos="*"):
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, str(valor)))
        return self

    def order(self, campo):
        self.campo_ordem = campo
        return self

    def limit(self, limite):
        self.limite = limite
        return self

    def insert(self, dados):
        self.acao, self.dados = "insert", deepcopy(dados)
        return self

    def update(self, dados):
        self.acao, self.dados = "update", deepcopy(dados)
        return self

    def execute(self):
        linhas = self.banco.setdefault(self.tabela, [])
        if self.acao == "insert":
            agora = datetime.now(UTC).isoformat()
            linha = {"id": str(uuid4()), "created_at": agora, "updated_at": agora, **self.dados}
            linhas.append(linha)
            return Resposta([deepcopy(linha)])
        encontradas = [
            linha
            for linha in linhas
            if all(str(linha.get(campo)) == valor for campo, valor in self.filtros)
            and (self.tabela != "produto" or linha.get("ativo", True))
        ]
        if self.acao == "update":
            for linha in encontradas:
                linha.update(self.dados)
            return Resposta(deepcopy(encontradas[: self.limite]))
        if self.campo_ordem:
            encontradas.sort(key=lambda linha: linha[self.campo_ordem])
        return Resposta(deepcopy(encontradas[: self.limite]))


class ClienteFalso:
    def __init__(self, banco):
        self.banco = banco

    def table(self, tabela):
        return ConsultaFalsa(self.banco, tabela)

    def rpc(self, nome, parametros):
        assert nome == "salvar_formulacao_produto"
        if self.banco.get("falhar_rpc"):
            erro = RuntimeError("Falha ao gravar um item")
            erro.code = "23514"
            raise erro
        produto_id = parametros["p_produto_id"]
        formulacao = next((linha for linha in self.banco["formulacao"] if linha["produto_id"] == produto_id), None)
        formulacao_id = formulacao["id"] if formulacao else str(uuid4())
        novas_linhas = []
        for ordem, item in enumerate(parametros["p_itens"]):
            novas_linhas.append(
                {
                    "id": str(uuid4()),
                    "formulacao_id": formulacao_id,
                    "ordem": ordem,
                    **item,
                }
            )
        if formulacao is None:
            agora = datetime.now(UTC).isoformat()
            self.banco["formulacao"].append(
                {"id": formulacao_id, "produto_id": produto_id, "created_at": agora, "updated_at": agora}
            )
        self.banco["formulacao_item"] = [
            linha for linha in self.banco["formulacao_item"] if linha["formulacao_id"] != formulacao_id
        ] + novas_linhas
        return Resposta(None)


@pytest.fixture
def ambiente(monkeypatch):
    banco = {
        "produto": [
            {
                "id": str(PRODUTO_ID),
                "codigo": "P-01",
                "descricao": "Produto teste",
                "categoria": "Proteína",
                "peso_liquido_g": "500",
                "ativo": True,
            }
        ],
        "materia_prima": [],
        "embalagem": [],
        "formulacao": [],
        "formulacao_item": [],
    }
    dados_usuario = {
        "nome": "Analista",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_pricing",
        "perfil_nome": "Analista de Pricing",
        "permissoes": ["cadastro.ler", "precificacao.ler", "precificacao.editar"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda _token: USUARIO_ID)
    monkeypatch.setattr(auth, "carregar_usuario", lambda _db, _id: dados_usuario)
    monkeypatch.setattr(formulacoes, "supabase_do_usuario", lambda _token: ClienteFalso(banco))
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), banco, dados_usuario
    app.dependency_overrides.clear()


def test_item_de_materia_prima_aceita_unidade_e_perda():
    item = ItemEntrada(
        tipo_insumo="materia_prima",
        materia_prima_id=uuid4(),
        quantidade="1.25",
        unidade_medida="kg",
        perda_percentual="2.5",
        origem_material="fabricante",
    )
    assert item.quantidade == 1.25
    assert item.perda_percentual == 2.5


@pytest.mark.parametrize("quantidade", ["0", "-1"])
def test_rejeita_quantidade_nao_positiva(quantidade):
    with pytest.raises(ValidationError):
        ItemEntrada(tipo_insumo="embalagem", embalagem_id=uuid4(), quantidade=quantidade, unidade_medida="un")


@pytest.mark.parametrize("perda", ["-0.1", "100.1"])
def test_rejeita_perda_fora_da_faixa(perda):
    with pytest.raises(ValidationError):
        ItemEntrada(
            tipo_insumo="embalagem",
            embalagem_id=uuid4(),
            quantidade=1,
            unidade_medida="un",
            perda_percentual=perda,
        )


def test_rejeita_referencias_de_tipo_inconsistente():
    with pytest.raises(ValidationError):
        ItemEntrada(
            tipo_insumo="materia_prima",
            materia_prima_id=uuid4(),
            embalagem_id=uuid4(),
            quantidade=1,
            unidade_medida="kg",
        )


def test_rejeita_lista_acima_do_limite():
    with pytest.raises(ValidationError):
        FormulacaoEntrada(itens=[{}] * 501)


def test_lista_produtos_e_persiste_recupera_edita_e_remove_itens(ambiente):
    http, banco, _usuario = ambiente
    produtos = http.get("/formulacoes/produtos", headers=TOKEN)
    assert produtos.status_code == 200
    assert produtos.json()[0]["id"] == str(PRODUTO_ID)
    assert http.get(f"/formulacoes/{PRODUTO_ID}", headers=TOKEN).status_code == 404

    entrada = {
        "itens": [
            {
                "tipo_insumo": "materia_prima",
                "materia_prima_id": str(MP_ID),
                "embalagem_id": None,
                "quantidade": "1.500000",
                "unidade_medida": "kg",
                "perda_percentual": "2.5000",
                "origem_material": "fabricante",
            }
        ]
    }
    salva = http.put(f"/formulacoes/{PRODUTO_ID}", headers=TOKEN, json=entrada)
    assert salva.status_code == 200
    assert salva.json()["itens"][0]["quantidade"] == "1.500000"
    assert salva.json()["itens"][0]["perda_percentual"] == "2.5000"
    assert len(banco["formulacao_item"]) == 1

    entrada["itens"][0]["quantidade"] = "2.250000"
    entrada["itens"][0]["perda_percentual"] = None
    atualizada = http.put(f"/formulacoes/{PRODUTO_ID}", headers=TOKEN, json=entrada)
    assert atualizada.status_code == 200
    assert atualizada.json()["itens"][0]["quantidade"] == "2.250000"
    assert atualizada.json()["itens"][0]["perda_percentual"] is None

    recuperada = http.get(f"/formulacoes/{PRODUTO_ID}", headers=TOKEN)
    assert recuperada.status_code == 200
    assert recuperada.json()["itens"][0]["quantidade"] == "2.250000"
    removidos = http.put(f"/formulacoes/{PRODUTO_ID}", headers=TOKEN, json={"itens": []})
    assert removidos.status_code == 200
    assert removidos.json()["itens"] == []


def test_formulacao_preserva_precision_decimal_de_api(ambiente):
    http, _banco, _usuario = ambiente
    resposta = http.put(
        f"/formulacoes/{PRODUTO_ID}",
        headers=TOKEN,
        json={
            "itens": [
                {
                    "tipo_insumo": "materia_prima",
                    "materia_prima_id": str(MP_ID),
                    "quantidade": "12345678.123456",
                    "unidade_medida": "kg",
                    "perda_percentual": "99.9999",
                    "origem_material": "cliente",
                }
            ]
        },
    )
    assert resposta.status_code == 200
    assert resposta.json()["itens"][0]["quantidade"] == "12345678.123456"
    assert resposta.json()["itens"][0]["perda_percentual"] == "99.9999"


def test_falha_ao_salvar_item_nao_cria_cabecalho_parcial(ambiente):
    http, banco, _usuario = ambiente
    banco["falhar_rpc"] = True
    resposta = http.put(f"/formulacoes/{PRODUTO_ID}", headers=TOKEN, json={"itens": []})
    assert resposta.status_code == 422
    assert banco["formulacao"] == []
    assert banco["formulacao_item"] == []


def test_formulacao_respeita_permissao_de_edicao(ambiente):
    http, _banco, dados_usuario = ambiente
    dados_usuario["permissoes"] = ["cadastro.ler", "precificacao.ler"]
    resposta = http.put(f"/formulacoes/{PRODUTO_ID}", headers=TOKEN, json={"itens": []})
    assert resposta.status_code == 403


def test_formulacao_rejeita_quantidade_invalida_na_api(ambiente):
    http, _banco, _usuario = ambiente
    resposta = http.put(
        f"/formulacoes/{PRODUTO_ID}",
        headers=TOKEN,
        json={
            "itens": [
                {
                    "tipo_insumo": "materia_prima",
                    "materia_prima_id": str(MP_ID),
                    "quantidade": 0,
                    "unidade_medida": "kg",
                    "origem_material": "fabricante",
                }
            ]
        },
    )
    assert resposta.status_code == 422


@pytest.mark.parametrize(("codigo", "status_code"), [("23503", 422), ("42501", 403), ("XX999", 503)])
def test_mapeia_falhas_de_persistencia(codigo, status_code):
    class ErroBanco(Exception):
        pass

    erro = ErroBanco("Falha de persistência")
    erro.code = codigo
    with pytest.raises(HTTPException) as capturada:
        formulacoes._executar(lambda: (_ for _ in ()).throw(erro))
    assert capturada.value.status_code == status_code
