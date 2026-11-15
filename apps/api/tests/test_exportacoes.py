
import csv
import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import exportacoes


USUARIO_ID = uuid4()
PRECIFICACAO_ID = str(uuid4())
TOKEN = {"Authorization": "Bearer token-exportacao"}
URL = "/exportacoes/cenarios"


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class ConsultaFalsa:
    def __init__(self, cliente, tabela):
        self.cliente = cliente
        self.tabela = tabela
        self.inicio = 0
        self.fim = None

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, inicio, fim):
        self.inicio = inicio
        self.fim = fim
        return self

    def execute(self):
        dados = self.cliente.tabelas.get(self.tabela, [])
        fim = self.fim + 1 if self.fim is not None else None
        return RespostaFalsa(dados[self.inicio:fim])


class ClienteFalso:
    def __init__(self):
        self.tabelas = {
            "precificacao": [],
            "cenario": [],
            "cenario_preco": [],
        }
        self.tabelas_consultadas = []

    def table(self, nome):
        self.tabelas_consultadas.append(nome)
        return ConsultaFalsa(self, nome)


def criar_precificacao():
    return {
        "id": PRECIFICACAO_ID,
        "codigo": "PREC-001",
        "status": "aprovada",
        "cliente": {"razao_social": "Cliente Teste"},
        "produto": {"descricao": "Produto Teste"},
    }


def criar_cenario(versao, vigente=False):
    return {
        "id": str(uuid4()),
        "precificacao_id": PRECIFICACAO_ID,
        "versao": versao,
        "observacao": f"Observação da versão {versao}",
        "volume": None,
        "data_calculo": "2026-11-04",
        "versao_motor": "1.0.0",
        "preco_bruto": "57.94",
        "preco_bruto_sem_ipi": "52.18",
        "created_at": "2026-11-04T12:00:00Z",
        "entrada": {
            "comercial": {
                "margem_desejada_percentual": "0.30",
            }
        },
        "resultado": {
            "custo_mp": "28.30",
            "custo_embalagem": "0.44",
            "custo_perda": "0.66",
            "custo_mod": "1.94",
            "custo_ggf": "1.12",
            "custo_total": "32.46",
            "preco_bruto": "57.94",
            "preco_bruto_sem_ipi": "52.18",
            "receita_operacional_liquida": "41.02",
            "margem_contribuicao_valor": "11.67",
            "margem_contribuicao_percentual": "0.284",
        },
    }


def criar_cenario_preco(versao, vigente):
    return {
        "id": str(uuid4()),
        "precificacao_id": PRECIFICACAO_ID,
        "versao": versao,
        "volume": None,
        "data_calculo": "2026-11-04",
        "versao_motor": "1.0.0",
        "preco_bruto": "57.94",
        "preco_bruto_sem_ipi": "52.18",
        "created_at": "2026-11-04T12:00:00Z",
        "vigente": vigente,
    }


@pytest.fixture
def ambiente(monkeypatch):
    cliente = ClienteFalso()
    tokens_recebidos = []

    dados_usuario = {
        "nome": "Analista de pricing",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_pricing",
        "perfil_nome": "Analista de Pricing",
        "permissoes": ["precificacao.ler", "custo.ler"],
    }

    def supabase_falso(token):
        tokens_recebidos.append(token)
        return cliente

    monkeypatch.setattr(
        auth,
        "validar_token",
        lambda token: USUARIO_ID
        if token == "token-exportacao"
        else None,
    )

    monkeypatch.setattr(
        auth,
        "carregar_usuario",
        lambda db, usuario_id: dados_usuario
        if usuario_id == USUARIO_ID
        else None,
    )

    monkeypatch.setattr(
        exportacoes,
        "supabase_do_usuario",
        supabase_falso,
    )

    app.dependency_overrides[get_db] = lambda: None

    cliente.tabelas["precificacao"] = [criar_precificacao()]

    yield TestClient(app), cliente, dados_usuario, tokens_recebidos

    app.dependency_overrides.clear()


def test_exportar_cenarios_em_csv_com_todas_as_versoes(ambiente):
    http, cliente, usuario, tokens = ambiente

    cliente.tabelas["cenario"] = [
        criar_cenario(1),
        criar_cenario(2),
    ]

    resposta = http.get(URL, headers=TOKEN, params={"formato": "csv"})

    assert resposta.status_code == 200
    assert "text/csv" in resposta.headers["content-type"]
    assert "attachment;" in resposta.headers["content-disposition"]

    conteudo = resposta.content.decode("utf-8-sig")
    linhas = list(csv.DictReader(io.StringIO(conteudo)))

    assert len(linhas) == 2
    assert [linha["versao"] for linha in linhas] == ["1", "2"]
    assert [linha["vigente"] for linha in linhas] == ["False", "True"]

    assert linhas[0]["cliente"] == "Cliente Teste"
    assert linhas[0]["produto"] == "Produto Teste"
    assert linhas[0]["precificacao_codigo"] == "PREC-001"

    assert tokens == ["token-exportacao"]
    assert "cenario" in cliente.tabelas_consultadas


def test_exportar_cenarios_em_xlsx(ambiente):
    http, cliente, usuario, tokens = ambiente

    cliente.tabelas["cenario"] = [
        criar_cenario(1),
        criar_cenario(2),
    ]

    resposta = http.get(URL, headers=TOKEN, params={"formato": "xlsx"})

    assert resposta.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in resposta.headers["content-type"]
    )

    workbook = load_workbook(io.BytesIO(resposta.content))
    planilha = workbook["Cenários"]

    cabecalho = [celula.value for celula in planilha[1]]

    assert "Código da precificação" in cabecalho
    assert "Versão" in cabecalho
    assert planilha.max_row == 3
    assert planilha.freeze_panes == "A2"
    assert planilha.auto_filter.ref == planilha.dimensions

    indice_versao = cabecalho.index("Versão") + 1

    assert planilha.cell(2, indice_versao).value == 1
    assert planilha.cell(3, indice_versao).value == 2


def test_exportacao_com_custo_ler_inclui_indicadores_de_custo(ambiente):
    http, cliente, usuario, tokens = ambiente

    cliente.tabelas["cenario"] = [criar_cenario(1)]

    resposta = http.get(URL, headers=TOKEN)

    assert resposta.status_code == 200

    conteudo = resposta.content.decode("utf-8-sig")
    linhas = list(csv.DictReader(io.StringIO(conteudo)))

    assert len(linhas) == 1

    linha = linhas[0]

    assert linha["custo_mp"] == "28.30"
    assert linha["custo_total"] == "32.46"
    assert linha["custo_conversao"] == "3.06"
    assert linha["margem_aplicada"] == "0.30"

    assert "custo.ler" in usuario["permissoes"]


def test_exportacao_sem_custo_ler_usa_view_segura_e_omite_indicadores(
    ambiente,
):
    http, cliente, usuario, tokens = ambiente

    usuario["permissoes"] = ["precificacao.ler"]

    cliente.tabelas["cenario_preco"] = [
        criar_cenario_preco(1, False),
        criar_cenario_preco(2, True),
    ]

    resposta = http.get(URL, headers=TOKEN)

    assert resposta.status_code == 200

    conteudo = resposta.content.decode("utf-8-sig")
    leitor = csv.DictReader(io.StringIO(conteudo))
    linhas = list(leitor)

    assert len(linhas) == 2
    assert "custo_total" not in leitor.fieldnames
    assert "custo_mp" not in leitor.fieldnames
    assert "margem_contribuicao_valor" not in leitor.fieldnames

    assert [linha["versao"] for linha in linhas] == ["1", "2"]
    assert [linha["vigente"] for linha in linhas] == ["False", "True"]

    assert "cenario_preco" in cliente.tabelas_consultadas
    assert "cenario" not in cliente.tabelas_consultadas


def test_exportacao_exige_precificacao_ler(ambiente):
    http, cliente, usuario, tokens = ambiente

    usuario["permissoes"] = ["custo.ler"]

    resposta = http.get(URL, headers=TOKEN)

    assert resposta.status_code == 403
    assert cliente.tabelas_consultadas == []


def test_exportacao_exige_autenticacao(ambiente):
    http, cliente, usuario, tokens = ambiente

    resposta = http.get(URL)

    assert resposta.status_code == 401
    assert cliente.tabelas_consultadas == []


def test_exportacao_recusa_formato_invalido(ambiente):
    http, cliente, usuario, tokens = ambiente

    resposta = http.get(URL, headers=TOKEN, params={"formato": "pdf"})

    assert resposta.status_code == 422
    assert cliente.tabelas_consultadas == []


def test_exportacao_sem_cenarios_retorna_arquivo_com_cabecalho(ambiente):
    http, cliente, usuario, tokens = ambiente

    cliente.tabelas["cenario"] = []

    resposta = http.get(URL, headers=TOKEN, params={"formato": "csv"})

    assert resposta.status_code == 200

    conteudo = resposta.content.decode("utf-8-sig")
    linhas = list(csv.reader(io.StringIO(conteudo)))

    assert len(linhas) == 1
    assert "versao" in linhas[0]
    assert "precificacao_codigo" in linhas[0]
    assert "cliente" in linhas[0]
