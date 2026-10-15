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
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class ConsultaFalsa:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.dados = None
        self.filtros = []
        self.busca = None
        self.limite = None
        self.intervalo = None
        self.ordens = []
        self.contagem_exata = False

    def select(self, _campos="*", count=None):
        self.contagem_exata = count == "exact"
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

    def or_(self, filtros):
        prefixo = 'codigo.ilike."%'
        separador = '%",descricao.ilike."%'
        inicio = filtros.find(prefixo)
        fim = filtros.find(separador, inicio + len(prefixo))
        self.busca = filtros[inicio + len(prefixo) : fim].replace(r"\%", "%").replace(r"\_", "_").casefold()
        return self

    def order(self, campo):
        self.ordens.append(campo)
        return self

    def limit(self, quantidade):
        self.limite = quantidade
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
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
            if isinstance(self.busca, tuple):
                campo, termo = self.busca
                correspondentes = [linha for linha in correspondentes if termo in linha[campo].casefold()]
            else:
                termo = self.busca
                correspondentes = [
                    linha
                    for linha in correspondentes
                    if (
                        termo in linha["codigo"].casefold()
                        or termo in linha["descricao"].casefold()
                        or termo in linha["ncm_codigo"].casefold()
                    )
                ]
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
        for campo in reversed(self.ordens):
            correspondentes.sort(key=lambda linha: linha[campo])
        total = len(correspondentes)
        if self.intervalo is not None:
            inicio, fim = self.intervalo
            correspondentes = correspondentes[inicio : fim + 1]
        elif self.limite is not None:
            correspondentes = correspondentes[: self.limite]
        return Resposta(deepcopy(correspondentes), total if self.contagem_exata else None)


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
    assert [item["id"] for item in lista.json()["registros"]] == [registro["id"]]
    assert lista.json()["total"] == 1

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


def _registro(codigo, descricao, unidade="kg", ativo=True, identificador=None, ncm="10000000"):
    agora = datetime.now(UTC).isoformat()
    return {
        "id": str(identificador or uuid4()),
        "codigo": codigo,
        "descricao": descricao,
        "unidade_medida": unidade,
        "ncm_codigo": ncm,
        "ativo": ativo,
        "created_at": agora,
        "updated_at": agora,
    }


def test_lista_paginada_retorna_metadados_padrao(ambiente):
    http, banco, _usuario = ambiente
    banco["materia_prima"] = [_registro("MP-001", "Farinha")]

    resposta = http.get("/cadastros/materias-primas", headers=TOKEN)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [item["id"] for item in corpo["registros"]] == [banco["materia_prima"][0]["id"]]
    assert {chave: corpo[chave] for chave in ("total", "pagina", "tamanho_pagina", "total_paginas")} == {
        "total": 1,
        "pagina": 1,
        "tamanho_pagina": 20,
        "total_paginas": 1,
    }


def test_busca_filtros_combinados_e_paginacao_sao_aplicados_no_servidor(ambiente):
    http, banco, _usuario = ambiente
    banco["materia_prima"] = [
        _registro("MP-001", "Farinha de trigo", ativo=True),
        _registro("MP-002", "Farinha de milho", unidade="g", ativo=False),
        _registro("MP-003", "Farinha integral", ativo=False),
        _registro("MP-004", "Açúcar", ativo=False),
    ]

    resposta = http.get(
        "/cadastros/materias-primas",
        headers=TOKEN,
        params={"busca": "farinha", "ativo": "false", "unidade_medida": "kg", "pagina": 1, "tamanho_pagina": 1},
    )

    assert resposta.status_code == 200
    assert [item["codigo"] for item in resposta.json()["registros"]] == ["MP-003"]
    assert resposta.json()["total"] == 1
    assert resposta.json()["total_paginas"] == 1


def test_busca_e_filtros_individuais(ambiente):
    http, banco, _usuario = ambiente
    banco["materia_prima"] = [
        _registro("MP-001", "Farinha de trigo", unidade="kg", ativo=True),
        _registro("MP-002", "Amido", unidade="g", ativo=False, ncm="02011000"),
    ]

    por_codigo = http.get("/cadastros/materias-primas", headers=TOKEN, params={"busca": "MP-002"}).json()
    por_ncm = http.get("/cadastros/materias-primas", headers=TOKEN, params={"busca": "02011000"}).json()
    por_unidade = http.get("/cadastros/materias-primas", headers=TOKEN, params={"unidade_medida": "g"}).json()
    por_situacao = http.get("/cadastros/materias-primas", headers=TOKEN, params={"ativo": "true"}).json()

    assert [item["codigo"] for item in por_codigo["registros"]] == ["MP-002"]
    assert [item["codigo"] for item in por_ncm["registros"]] == ["MP-002"]
    assert [item["codigo"] for item in por_unidade["registros"]] == ["MP-002"]
    assert [item["codigo"] for item in por_situacao["registros"]] == ["MP-001"]


def test_paginas_ordenadas_estavelmente_e_pagina_vazia(ambiente):
    http, banco, _usuario = ambiente
    banco["embalagem"] = [
        _registro("EMB-003", "Caixa", identificador=UUID(int=3)),
        _registro("EMB-001", "Caixa", identificador=UUID(int=1)),
        _registro("EMB-002", "Caixa", identificador=UUID(int=2)),
    ]

    primeira = http.get("/cadastros/embalagens", headers=TOKEN, params={"pagina": 1, "tamanho_pagina": 2}).json()
    segunda = http.get("/cadastros/embalagens", headers=TOKEN, params={"pagina": 2, "tamanho_pagina": 2}).json()
    vazia = http.get("/cadastros/embalagens", headers=TOKEN, params={"pagina": 3, "tamanho_pagina": 2}).json()

    assert [item["codigo"] for item in primeira["registros"]] == ["EMB-001", "EMB-002"]
    assert [item["codigo"] for item in segunda["registros"]] == ["EMB-003"]
    assert vazia["registros"] == []
    assert vazia["total"] == 3
    assert vazia["pagina"] == 3
    assert vazia["total_paginas"] == 2


@pytest.mark.parametrize(
    "parametros",
    [
        {"pagina": 0},
        {"tamanho_pagina": 0},
        {"tamanho_pagina": 101},
        {"busca": "x" * 101},
        {"unidade_medida": "cx"},
        {"ativo": "talvez"},
    ],
)
def test_parametros_de_listagem_invalidos_sao_rejeitados(ambiente, parametros):
    http, _banco, _usuario = ambiente

    assert http.get("/cadastros/materias-primas", headers=TOKEN, params=parametros).status_code == 422


def test_limite_maximo_de_pagina_e_busca_vazia(ambiente):
    http, banco, _usuario = ambiente
    banco["materia_prima"] = [_registro("MP-001", "Farinha")]

    resposta = http.get("/cadastros/materias-primas", headers=TOKEN, params={"busca": "   ", "tamanho_pagina": 100})

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1
    assert resposta.json()["tamanho_pagina"] == 100


def test_valor_de_busca_escapa_gramatica_do_postgrest():
    assert cadastros._padrao_busca_postgrest('a,b"c\\d%_') == '"%a,b\\"c\\\\d\\%\\_%"'


def test_consulta_da_listagem_repassa_o_token_do_usuario_para_o_postgrest(ambiente, monkeypatch):
    http, banco, _usuario = ambiente
    tokens = []
    monkeypatch.setattr(cadastros, "supabase_do_usuario", lambda token: tokens.append(token) or ClienteFalso(banco))

    resposta = http.get("/cadastros/materias-primas", headers=TOKEN)

    assert resposta.status_code == 200
    assert tokens == ["token-us06"]
