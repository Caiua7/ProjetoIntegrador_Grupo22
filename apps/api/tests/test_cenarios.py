import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import settings
from app.infrastructure.database import get_db
from app.main import app
from app.routers import cenarios
from app.services.comparacao_cenarios import comparar_cenarios

USUARIO_ID = uuid4()
PRECIFICACAO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us31"}
BASE = f"/precificacoes/{PRECIFICACAO_ID}/cenarios"
RAIZ = Path(__file__).resolve().parents[3]
ENTRADA = json.loads((RAIZ / "tests/conformidade/casos/caso_000_template.json").read_text(encoding="utf-8"))["entrada"]


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class ErroPostgrest(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message)
        self.code, self.message = code, message


class ConsultaFalsa:
    """Filtra por `versao` quando pedido; o resto da cadeia só é aceito."""

    def __init__(self, cliente, tabela):
        self.cliente, self.tabela, self.versao = cliente, tabela, None

    def eq(self, coluna, valor):
        if coluna == "versao":
            self.versao = valor
        return self

    def __getattr__(self, _nome):
        return lambda *_args, **_kwargs: self

    def execute(self):
        linhas = self.cliente.precos if self.tabela == "cenario_preco" else self.cliente.versoes
        if self.versao is not None:
            linhas = [linha for linha in linhas if linha["versao"] == self.versao]
        return RespostaFalsa(deepcopy(linhas))


class RpcFalsa:
    def __init__(self, cliente, nome, parametros):
        self.cliente, self.nome, self.parametros = cliente, nome, parametros

    def execute(self):
        self.cliente.chamadas.append((self.nome, self.parametros))
        if self.cliente.erro:
            raise self.cliente.erro
        proxima = max((linha["versao"] for linha in self.cliente.versoes), default=0) + 1
        return RespostaFalsa(versao_salva(proxima, self.parametros))


class ClienteFalso:
    def __init__(self):
        self.versoes: list[dict] = []
        self.precos: list[dict] = []
        self.chamadas: list[tuple[str, dict]] = []
        self.erro: Exception | None = None

    def table(self, nome):
        return ConsultaFalsa(self, nome)

    def rpc(self, nome, parametros):
        return RpcFalsa(self, nome, parametros)


def versao_salva(numero: int, parametros: dict) -> dict:
    resultado = parametros["p_resultado"]
    return {
        "id": str(uuid4()),
        "precificacao_id": parametros["p_precificacao_id"],
        "versao": numero,
        "cenario_origem_id": parametros["p_cenario_origem_id"],
        "observacao": parametros["p_observacao"],
        "volume": parametros["p_volume"],
        "data_calculo": "2026-11-04",
        "versao_motor": parametros["p_versao_motor"],
        "entrada": parametros["p_entrada"],
        "resultado": resultado,
        "preco_bruto": resultado["preco_bruto"],
        "preco_bruto_sem_ipi": resultado["preco_bruto_sem_ipi"],
        "custo_total": resultado["custo_total"],
        "margem_contribuicao_valor": resultado["margem_contribuicao_valor"],
        "margem_contribuicao_percentual": resultado["margem_contribuicao_percentual"],
        "created_by": str(USUARIO_ID),
        "created_at": "2026-11-04T12:00:00Z",
    }


def resultado(**campos) -> dict:
    base = {
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
    }
    return {**base, **campos}


def cenario(versao: int, volume: str | None, margem: str, **campos_resultado) -> dict:
    entrada = deepcopy(ENTRADA)
    entrada["comercial"]["margem_desejada_percentual"] = margem
    return {"versao": versao, "volume": volume, "entrada": entrada, "resultado": resultado(**campos_resultado)}


@pytest.fixture
def ambiente(monkeypatch):
    cliente = ClienteFalso()
    dados_usuario = {
        "nome": "Analista de pricing",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_pricing",
        "perfil_nome": "Analista de Pricing",
        "permissoes": ["precificacao.ler", "precificacao.editar", "custo.ler"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: USUARIO_ID if token == "token-us31" else UUID(int=0))
    monkeypatch.setattr(
        auth, "carregar_usuario", lambda _db, usuario_id: dados_usuario if usuario_id == USUARIO_ID else None
    )
    monkeypatch.setattr(cenarios, "supabase_do_usuario", lambda _token: cliente)
    monkeypatch.setattr(cenarios, "supabase_servico", lambda: cliente)
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), cliente, dados_usuario
    app.dependency_overrides.clear()


def _salvar(http, cliente, **corpo):
    resposta = http.post(BASE, headers=TOKEN, json={"entrada": ENTRADA, **corpo})
    if resposta.status_code == 201:
        cliente.versoes.append(resposta.json())
    return resposta


# ------------------------------------------------------------ gravação


def test_nova_versao_e_calculada_pelo_motor_e_vira_a_vigente(ambiente):
    http, cliente, _usuario = ambiente

    resposta = _salvar(http, cliente, volume="42000", observacao="Volume revisado")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert (corpo["versao"], corpo["vigente"], corpo["volume"]) == (1, True, "42000")
    [(nome, parametros)] = cliente.chamadas
    assert nome == "salvar_cenario_seguro"
    assert parametros["p_precificacao_id"] == str(PRECIFICACAO_ID)
    assert parametros["p_usuario_id"] == str(USUARIO_ID)
    assert parametros["p_versao_motor"] == parametros["p_resultado"]["metadata"]["versao_motor"]
    assert Decimal(parametros["p_resultado"]["preco_bruto"]) > 0


def test_resultado_vem_do_motor_e_nao_do_cliente(ambiente):
    http, cliente, _usuario = ambiente

    resposta = http.post(BASE, headers=TOKEN, json={"entrada": ENTRADA, "resultado": {"preco_bruto": "1"}})

    assert resposta.status_code == 422
    assert cliente.chamadas == []


def test_calculate_exige_usuario_autenticado(ambiente):
    http, _cliente, _usuario = ambiente
    assert http.post("/calculate", json=ENTRADA).status_code == 401


def test_calculate_sem_custo_ler_devolve_preco_sem_campos_de_custo(ambiente):
    http, _cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.ler"]

    resposta = http.post("/calculate", headers=TOKEN, json=ENTRADA)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["preco_bruto"]
    assert corpo["impostos_destacados"]
    assert (
        not {
            "custo_mp",
            "custo_embalagem",
            "custo_perda",
            "custo_mod",
            "custo_ggf",
            "custo_total",
            "margem_contribuicao_valor",
            "margem_contribuicao_percentual",
            "encargo_financeiro_valor",
            "encargo_financeiro_percentual",
            "isencao_mao_de_obra",
            "denominador",
        }
        & corpo.keys()
    )


def test_calculate_com_custo_ler_preserva_resposta_completa(ambiente):
    http, _cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.ler", "custo.ler"]

    resposta = http.post("/calculate", headers=TOKEN, json=ENTRADA)

    assert resposta.status_code == 200
    assert {"custo_mp", "custo_total", "margem_contribuicao_valor"} <= resposta.json().keys()


def test_modo_demo_desativado_por_padrao_nao_serve_resultados(ambiente, monkeypatch):
    http, _cliente, _usuario = ambiente
    monkeypatch.setattr(settings, "DEMO_CALCULATION_ENABLED", False)
    resposta = http.post("/calculate/demo", headers=TOKEN, json={"dados": {}})
    assert resposta.status_code == 404


def test_calculo_demo_marca_origem_assuncoes_e_nao_e_persistivel(ambiente, monkeypatch):
    http, cliente, _usuario = ambiente
    monkeypatch.setattr(settings, "DEMO_CALCULATION_ENABLED", True)
    resposta = http.post("/calculate/demo", headers=TOKEN, json={"dados": {"cliente_uf": "SP"}})
    assert resposta.status_code == 200
    resultado = resposta.json()
    assert resultado["metadata"]["is_mock"] is True
    assert resultado["metadata"]["origem"] == "demonstracao"
    assert resultado["metadata"]["classificacao"] == "parcialmente_simulado"
    assert resultado["metadata"]["parametros_simulados"]
    assert resultado["metadata"]["dados_recebidos_nao_verificados"] is True
    assert cliente.chamadas == []


def test_calculo_demo_totalmente_mock_usa_defaults_centrais(ambiente, monkeypatch):
    http, _cliente, _usuario = ambiente
    monkeypatch.setattr(settings, "DEMO_CALCULATION_ENABLED", True)
    resposta = http.post("/calculate/demo", headers=TOKEN, json={})
    assert resposta.status_code == 200
    metadata = resposta.json()["metadata"]
    assert metadata["is_mock"] is True
    assert metadata["classificacao"] == "inteiramente_simulado"
    assert metadata["parametros_simulados"]


def test_persistencia_recusa_resultado_mock_produzido_no_backend(ambiente, monkeypatch):
    http, cliente, _usuario = ambiente
    real = cenarios.calculate(cenarios.CalculateRequest.model_validate(ENTRADA))
    simulado = real.model_copy(update={"metadata": real.metadata.model_copy(update={"is_mock": True})})
    monkeypatch.setattr(cenarios, "calculate", lambda _entrada: simulado)

    resposta = _salvar(http, cliente)

    assert resposta.status_code == 409
    assert "mock" in resposta.json()["detail"].lower()
    assert cliente.chamadas == []


def test_persistencia_para_usuario_sem_custo_ler_retira_custos_da_resposta(ambiente):
    http, cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.editar", "precificacao.ler"]

    resposta = _salvar(http, cliente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["preco_bruto"]
    assert not {"resultado", "entrada", "custo_total", "margem_contribuicao_valor", "rentabilidade"} & corpo.keys()


def test_entrada_que_o_motor_recusa_nao_vira_versao(ambiente):
    http, cliente, _usuario = ambiente
    entrada = deepcopy(ENTRADA)
    entrada["comercial"]["margem_desejada_percentual"] = "1.5"

    resposta = http.post(BASE, headers=TOKEN, json={"entrada": entrada})

    assert resposta.status_code == 422
    assert cliente.chamadas == []


def test_duplicar_recalcula_a_entrada_da_origem_e_aponta_para_ela(ambiente):
    http, cliente, _usuario = ambiente
    origem = _salvar(http, cliente, volume="30000").json()
    cliente.chamadas.clear()

    resposta = http.post(f"{BASE}/1/duplicar", headers=TOKEN, json={"volume": "42000"})

    assert resposta.status_code == 201
    assert resposta.json()["versao"] == 2
    [(_nome, parametros)] = cliente.chamadas
    assert parametros["p_cenario_origem_id"] == origem["id"]
    assert parametros["p_entrada"] == origem["entrada"]
    assert parametros["p_volume"] == "42000"
    assert parametros["p_observacao"] == "Duplicada da versão 1"


def test_duplicar_versao_que_nao_existe_devolve_404(ambiente):
    http, cliente, _usuario = ambiente

    assert http.post(f"{BASE}/7/duplicar", headers=TOKEN, json={}).status_code == 404
    assert cliente.chamadas == []


@pytest.mark.parametrize(
    ("codigo", "status_esperado"),
    [("P0002", 404), ("42501", 403), ("23505", 409), ("22023", 422)],
)
def test_erros_do_banco_viram_resposta_tratada(ambiente, codigo, status_esperado):
    http, cliente, _usuario = ambiente
    cliente.erro = ErroPostgrest(codigo, "detalhe do banco")

    assert http.post(BASE, headers=TOKEN, json={"entrada": ENTRADA}).status_code == status_esperado


def test_salvar_exige_permissao_de_edicao(ambiente):
    http, cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.ler", "custo.ler"]

    assert http.post(BASE, headers=TOKEN, json={"entrada": ENTRADA}).status_code == 403
    assert cliente.chamadas == []


# ------------------------------------------------------------ consulta


def test_listagem_marca_so_a_maior_versao_como_vigente(ambiente):
    http, cliente, _usuario = ambiente
    for _ in range(3):
        _salvar(http, cliente)

    resposta = http.get(BASE, headers=TOKEN)

    assert resposta.status_code == 200
    assert {item["versao"]: item["vigente"] for item in resposta.json()} == {1: False, 2: False, 3: True}
    assert "resultado" not in resposta.json()[0]


def test_versao_anterior_continua_consultavel_e_igual(ambiente):
    """Critério de aceite, do lado da API: salvar a versão 2 não muda o que
    se lê da versão 1."""
    http, cliente, _usuario = ambiente
    _salvar(http, cliente, volume="30000")
    antes = http.get(f"{BASE}/1", headers=TOKEN).json()

    entrada = deepcopy(ENTRADA)
    entrada["comercial"]["margem_desejada_percentual"] = "0.30"
    http.post(BASE, headers=TOKEN, json={"entrada": entrada, "volume": "42000"})
    cliente.versoes.append(versao_salva(2, cliente.chamadas[-1][1]))
    depois = http.get(f"{BASE}/1", headers=TOKEN).json()

    assert depois == {**antes, "vigente": False}
    assert antes["vigente"] is True


def test_listar_versoes_exige_custo_ler_mas_o_preco_nao(ambiente):
    http, cliente, usuario = ambiente
    usuario["permissoes"] = ["precificacao.ler"]
    cliente.precos = [
        {
            "versao": 1,
            "vigente": True,
            "volume": "42000",
            "data_calculo": "2026-11-04",
            "preco_bruto": "57.94",
            "preco_bruto_sem_ipi": "52.18",
            "created_at": "2026-11-04T12:00:00Z",
        }
    ]

    assert http.get(BASE, headers=TOKEN).status_code == 403
    precos = http.get(f"{BASE}/precos", headers=TOKEN)
    assert precos.status_code == 200
    assert set(precos.json()[0]) == {
        "versao",
        "vigente",
        "volume",
        "data_calculo",
        "preco_bruto",
        "preco_bruto_sem_ipi",
        "created_at",
    }


# ------------------------------------------------------------ comparação


def test_comparacao_destaca_a_variacao_entre_versoes():
    v2 = cenario(2, "30000", "0.32", preco_bruto="59.80", margem_contribuicao_percentual="0.261", custo_mod="1.94")
    v3 = cenario(3, "42000", "0.30", preco_bruto="57.94", margem_contribuicao_percentual="0.284", custo_mod="1.80")

    indicadores = {item.codigo: item for item in comparar_cenarios(v2, v3)}

    assert indicadores["volume"].variacao == Decimal("12000")
    assert indicadores["volume"].variacao_percentual == Decimal("0.4")
    assert indicadores["preco_bruto"].sentido == "desceu"
    assert indicadores["preco_bruto"].variacao == Decimal("-1.86")
    assert indicadores["custo_conversao"].variacao == Decimal("-0.14")
    margem = indicadores["margem_contribuicao_percentual"]
    assert (margem.variacao, margem.variacao_percentual, margem.sentido) == (Decimal("0.023"), None, "subiu")
    assert indicadores["margem_aplicada"].variacao == Decimal("-0.02")
    assert indicadores["receita_operacional_bruta"].valor_para == Decimal("42000") * Decimal("52.18")


def test_sem_volume_nao_ha_rentabilidade_absoluta_para_comparar():
    indicadores = {item.codigo: item for item in comparar_cenarios(cenario(1, None, "0.2"), cenario(2, "1000", "0.2"))}

    assert indicadores["margem_contribuicao_absoluta"].sentido == "sem_base"
    assert indicadores["margem_contribuicao_absoluta"].variacao is None
    assert indicadores["preco_bruto"].sentido == "igual"


def test_endpoint_de_comparacao(ambiente):
    http, cliente, _usuario = ambiente
    _salvar(http, cliente, volume="30000")
    _salvar(http, cliente, volume="42000")

    resposta = http.get(f"{BASE}/comparacao", headers=TOKEN, params={"de": 1, "para": 2})

    assert resposta.status_code == 200
    volume = next(item for item in resposta.json()["indicadores"] if item["codigo"] == "volume")
    assert (volume["valor_de"], volume["valor_para"], volume["variacao"]) == ("30000", "42000", "12000")


def test_comparar_a_versao_com_ela_mesma_devolve_422(ambiente):
    http, _cliente, _usuario = ambiente

    assert http.get(f"{BASE}/comparacao", headers=TOKEN, params={"de": 1, "para": 1}).status_code == 422


# ------------------------------------------------------------ rentabilidade (#64)


def test_com_volume_de_10_mil_a_versao_traz_rob_maco_e_mb_em_reais(ambiente):
    """Critério de aceite da US32: dado volume de 10 mil unidades, quando o
    cenário é calculado, ROB, MaCo absoluta e MB aparecem em reais."""
    http, cliente, _usuario = ambiente

    salvo = _salvar(http, cliente, volume="10000").json()
    lido = http.get(f"{BASE}/1", headers=TOKEN).json()

    unitario = salvo["resultado"]
    pbsipi = Decimal(unitario["preco_bruto_sem_ipi"])
    rol = Decimal(unitario["receita_operacional_liquida"])
    esperado = {
        "volume": Decimal("10000"),
        "receita_operacional_bruta": pbsipi * 10000,
        "deducoes": (pbsipi - rol) * 10000,
        "receita_operacional_liquida": rol * 10000,
        "margem_contribuicao": Decimal(unitario["margem_contribuicao_valor"]) * 10000,
        "margem_bruta": (rol - Decimal(unitario["custo_total"])) * 10000,
    }
    for corpo in (salvo, lido):
        rentabilidade = corpo["rentabilidade"]
        assert set(rentabilidade) == set(esperado)
        assert all(isinstance(valor, str) for valor in rentabilidade.values()), "dinheiro vai como texto"
        assert {campo: Decimal(valor) for campo, valor in rentabilidade.items()} == esperado


def test_sem_volume_a_versao_nao_tem_rentabilidade_em_reais(ambiente):
    http, cliente, _usuario = ambiente

    salvo = _salvar(http, cliente).json()

    assert salvo["rentabilidade"] is None
    assert http.get(f"{BASE}/1", headers=TOKEN).json()["rentabilidade"] is None


def test_duplicar_com_outro_volume_recalcula_a_rentabilidade(ambiente):
    http, cliente, _usuario = ambiente
    origem = _salvar(http, cliente, volume="10000").json()

    copia = http.post(f"{BASE}/1/duplicar", headers=TOKEN, json={"volume": "20000"}).json()

    rob_origem = Decimal(origem["rentabilidade"]["receita_operacional_bruta"])
    assert Decimal(copia["rentabilidade"]["receita_operacional_bruta"]) == rob_origem * 2
