from copy import deepcopy
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import tax_rates
from app.routers.tax_rates import AliquotaEntrada, escolher_aliquota_aplicavel
from app.services.importacao_aliquotas import ler_planilha

USUARIO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-us12"}
NCM_SUPLEMENTO = "21069030"
RESOLVER = "/parametros-fiscais/aliquotas/resolver"
IMPORTACAO = "/parametros-fiscais/aliquotas/importacao"

CABECALHO = "uf;ncm;regime;vigencia;pis;cofins;icms;ipi;icms_interno;fcp;mva"


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class ConsultaFalsa:
    """Aceita a cadeia de filtros do supabase-py e devolve todas as linhas:
    quem escolhe a regra é `escolher_aliquota_aplicavel`."""

    def __init__(self, cliente):
        self.cliente = cliente

    def __getattr__(self, _nome):
        return lambda *_args, **_kwargs: self

    def execute(self):
        return RespostaFalsa(deepcopy(self.cliente.linhas))


class RpcFalsa:
    def __init__(self, cliente, nome, parametros):
        self.cliente, self.nome, self.parametros = cliente, nome, parametros

    def execute(self):
        self.cliente.chamadas.append((self.nome, self.parametros))
        return RespostaFalsa([self.cliente.contagem])


class ClienteFalso:
    def __init__(self):
        self.linhas: list[dict] = []
        self.chamadas: list[tuple[str, dict]] = []
        self.contagem = {"novas": 0, "atualizadas": 0, "inalteradas": 0}

    def table(self, _nome):
        return ConsultaFalsa(self)

    def rpc(self, nome, parametros):
        return RpcFalsa(self, nome, parametros)


def aliquota(**campos) -> dict:
    base = {
        "id": str(uuid4()),
        "uf_destino": "MG",
        "ncm_codigo": None,
        "regime_tributario": "lucro_presumido",
        "vigencia_inicio": "2026-01-01",
        "pis_percentual": "0.0165",
        "cofins_percentual": "0.076",
        "icms_percentual": "0.12",
        "ipi_percentual": "0",
        "icms_interno_percentual": "0.18",
        "fcp_percentual": "0",
        "mva_percentual": "0",
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": "2026-10-01T00:00:00Z",
    }
    return {**base, **campos}


@pytest.fixture
def ambiente(monkeypatch):
    cliente = ClienteFalso()
    dados_usuario = {
        "nome": "Analista de pricing",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_pricing",
        "perfil_nome": "Analista de Pricing",
        "permissoes": ["parametro_fiscal.ler", "parametro_fiscal.editar"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: USUARIO_ID if token == "token-us12" else UUID(int=0))
    monkeypatch.setattr(
        auth, "carregar_usuario", lambda _db, usuario_id: dados_usuario if usuario_id == USUARIO_ID else None
    )
    monkeypatch.setattr(tax_rates, "supabase_do_usuario", lambda _token: cliente)
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), cliente, dados_usuario
    app.dependency_overrides.clear()


def _resolver(http, **params):
    filtros = {
        "uf_destino": "MG",
        "ncm_codigo": NCM_SUPLEMENTO,
        "regime_tributario": "lucro_presumido",
        "data_referencia": "2026-10-18",
    }
    return http.get(RESOLVER, headers=TOKEN, params={**filtros, **params})


# ------------------------------------------------------------ critério de aceite


def test_venda_para_mg_de_ncm_com_mva_recebe_a_aliquota_vigente(ambiente):
    http, cliente, _usuario = ambiente
    regra_geral = aliquota()
    regra_com_st = aliquota(ncm_codigo=NCM_SUPLEMENTO, vigencia_inicio="2026-09-01", mva_percentual="0.3896")
    cliente.linhas = [regra_geral, regra_com_st]

    resposta = _resolver(http)

    assert resposta.status_code == 200
    assert resposta.json()["id"] == regra_com_st["id"]
    assert Decimal(resposta.json()["mva_percentual"]) == Decimal("0.3896")


# ------------------------------------------------------------ escolha da regra


def test_vigencia_mais_recente_que_ja_comecou_e_a_que_vale():
    antiga = aliquota(ncm_codigo=NCM_SUPLEMENTO, vigencia_inicio="2026-01-01", mva_percentual="0.30")
    nova = aliquota(ncm_codigo=NCM_SUPLEMENTO, vigencia_inicio="2026-09-01", mva_percentual="0.3896")
    futura = aliquota(ncm_codigo=NCM_SUPLEMENTO, vigencia_inicio="2027-01-01", mva_percentual="0.45")
    registros = [nova, futura, antiga]

    assert escolher_aliquota_aplicavel(registros, NCM_SUPLEMENTO, date(2026, 8, 31)) == antiga
    assert escolher_aliquota_aplicavel(registros, NCM_SUPLEMENTO, date(2026, 9, 1)) == nova
    assert escolher_aliquota_aplicavel(registros, NCM_SUPLEMENTO, date(2027, 1, 1)) == futura


def test_sem_regra_do_ncm_vale_a_regra_geral_da_uf(ambiente):
    http, cliente, _usuario = ambiente
    regra_geral = aliquota()
    de_outro_ncm = aliquota(ncm_codigo="04041000", mva_percentual="0.5")
    cliente.linhas = [regra_geral, de_outro_ncm]

    resposta = _resolver(http)

    assert resposta.status_code == 200
    assert resposta.json()["id"] == regra_geral["id"]


def test_regra_do_ncm_ainda_nao_vigente_cai_na_regra_geral(ambiente):
    http, cliente, _usuario = ambiente
    regra_geral = aliquota()
    cliente.linhas = [regra_geral, aliquota(ncm_codigo=NCM_SUPLEMENTO, vigencia_inicio="2026-11-01")]

    resposta = _resolver(http)

    assert resposta.json()["id"] == regra_geral["id"]


def test_sem_nenhuma_regra_vigente_devolve_404(ambiente):
    http, cliente, _usuario = ambiente
    cliente.linhas = [aliquota(vigencia_inicio="2026-11-01")]

    resposta = _resolver(http)

    assert resposta.status_code == 404


def test_resolver_exige_permissao_de_leitura(ambiente):
    http, _cliente, usuario = ambiente
    usuario["permissoes"] = ["cadastro.ler"]

    assert _resolver(http).status_code == 403


# ------------------------------------------------------------ leitura da planilha


def test_planilha_do_excel_vira_fracoes_no_formato_da_api():
    conteudo = (
        "﻿UF;NCM;Regime;Vigência;PIS (%);COFINS (%);ICMS (%);IPI (%);ICMS interno (%);FCP (%);MVA (%)\n"
        "mg;2106.90.30;Lucro Presumido;01/09/2026;1,65;7,6;12;;18;0;38,96\n"
        "SP;;lucro_real;2026-01-01;1,65;7,60;18%;0;18;0;0\n"
    )

    resultado = ler_planilha(conteudo, AliquotaEntrada)

    assert resultado.erros == []
    primeira, segunda = resultado.aliquotas
    assert primeira["uf_destino"] == "MG"
    assert primeira["ncm_codigo"] == NCM_SUPLEMENTO
    assert primeira["regime_tributario"] == "lucro_presumido"
    assert primeira["vigencia_inicio"] == "2026-09-01"
    assert Decimal(primeira["pis_percentual"]) == Decimal("0.0165")
    assert Decimal(primeira["ipi_percentual"]) == 0
    assert Decimal(primeira["mva_percentual"]) == Decimal("0.3896")
    assert segunda["ncm_codigo"] is None
    assert Decimal(segunda["icms_percentual"]) == Decimal("0.18")


def test_separador_virgula_com_ponto_decimal_tambem_funciona():
    conteudo = (
        "uf,ncm,regime,vigencia,pis,cofins,icms,ipi,icms_interno,fcp,mva\nRJ,,simples,2026-01-01,1.65,7.6,12,0,20,2,0\n"
    )

    resultado = ler_planilha(conteudo, AliquotaEntrada)

    assert resultado.erros == []
    assert Decimal(resultado.aliquotas[0]["fcp_percentual"]) == Decimal("0.02")
    assert resultado.aliquotas[0]["regime_tributario"] == "simples_nacional"


@pytest.mark.parametrize(
    ("linha", "trecho_do_erro"),
    [
        pytest.param("XX;;lucro_real;2026-01-01;1;1;1;0;1;0;0", "UF de destino", id="uf_inexistente"),
        pytest.param("SP;2106;lucro_real;2026-01-01;1;1;1;0;1;0;0", "8 dígitos", id="ncm_curto"),
        pytest.param("SP;;lucro_mensal;2026-01-01;1;1;1;0;1;0;0", "regime", id="regime_desconhecido"),
        pytest.param("SP;;lucro_real;31-12-2026;1;1;1;0;1;0;0", "vigência", id="data_invalida"),
        pytest.param("SP;;lucro_real;2026-01-01;abc;1;1;0;1;0;0", "percentual", id="percentual_texto"),
        pytest.param("SP;;lucro_real;2026-01-01;1;1;180;0;1;0;0", "icms_percentual", id="icms_acima_de_100"),
    ],
)
def test_erro_aponta_a_linha_do_arquivo(linha, trecho_do_erro):
    conteudo = f"{CABECALHO}\nSP;;lucro_real;2026-01-01;1,65;7,6;18;0;18;0;0\n{linha}\n"

    resultado = ler_planilha(conteudo, AliquotaEntrada)

    assert len(resultado.aliquotas) == 1
    [erro] = resultado.erros
    assert erro.linha == 3
    assert trecho_do_erro in erro.mensagem


def test_mesma_chave_duas_vezes_no_arquivo_e_erro():
    conteudo = (
        f"{CABECALHO}\n"
        "SP;;lucro_real;2026-01-01;1,65;7,6;18;0;18;0;0\n"
        "\n"
        "SP;;lucro_real;01/01/2026;1,65;7,6;17;0;18;0;0\n"
    )

    resultado = ler_planilha(conteudo, AliquotaEntrada)

    [erro] = resultado.erros
    assert erro.linha == 4
    assert "linha 2" in erro.mensagem


def test_coluna_obrigatoria_faltando_e_erro_do_cabecalho():
    resultado = ler_planilha("uf;regime;vigencia;pis\nSP;lucro_real;2026-01-01;1\n", AliquotaEntrada)

    [erro] = resultado.erros
    assert erro.linha == 1
    assert "cofins_percentual" in erro.mensagem
    assert resultado.aliquotas == []


@pytest.mark.parametrize("conteudo", ["", "   \n", f"{CABECALHO}\n\n"])
def test_planilha_sem_aliquota_e_erro(conteudo):
    assert ler_planilha(conteudo, AliquotaEntrada).erros


# ------------------------------------------------------------ endpoint de importação


PLANILHA_VALIDA = f"{CABECALHO}\nMG;21069030;lucro_presumido;2026-09-01;1,65;7,6;12;0;18;0;38,96\nSP;;lucro_real;2026-01-01;1,65;7,6;18;0;18;0;0\n"


def test_simulacao_conta_o_que_mudaria_sem_gravar(ambiente):
    http, cliente, _usuario = ambiente
    cliente.contagem = {"novas": 1, "atualizadas": 0, "inalteradas": 1}

    resposta = http.post(IMPORTACAO, headers=TOKEN, json={"conteudo_csv": PLANILHA_VALIDA})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["simulacao"] is True
    assert (corpo["linhas_validas"], corpo["novas"], corpo["inalteradas"]) == (2, 1, 1)
    [(nome, parametros)] = cliente.chamadas
    assert nome == "importar_aliquotas"
    assert parametros["p_simular"] is True
    assert parametros["p_linhas"][0]["mva_percentual"] == "0.3896"


def test_confirmacao_grava_o_lote(ambiente):
    http, cliente, _usuario = ambiente
    cliente.contagem = {"novas": 2, "atualizadas": 0, "inalteradas": 0}

    resposta = http.post(IMPORTACAO, headers=TOKEN, json={"conteudo_csv": PLANILHA_VALIDA, "simular": False})

    assert resposta.status_code == 200
    assert resposta.json()["simulacao"] is False
    assert resposta.json()["novas"] == 2
    assert cliente.chamadas[0][1]["p_simular"] is False


def test_simulacao_com_erros_lista_as_linhas_e_nao_chama_o_banco(ambiente):
    http, cliente, _usuario = ambiente
    planilha = f"{PLANILHA_VALIDA}SP;;lucro_real;2026-13-01;1;1;1;0;1;0;0\n"

    resposta = http.post(IMPORTACAO, headers=TOKEN, json={"conteudo_csv": planilha})

    assert resposta.status_code == 200
    assert resposta.json()["linhas_validas"] == 2
    assert [erro["linha"] for erro in resposta.json()["erros"]] == [4]
    assert cliente.chamadas == []


def test_confirmacao_com_erros_e_recusada_sem_gravar_nada(ambiente):
    http, cliente, _usuario = ambiente
    planilha = f"{PLANILHA_VALIDA}SP;;lucro_real;2026-13-01;1;1;1;0;1;0;0\n"

    resposta = http.post(IMPORTACAO, headers=TOKEN, json={"conteudo_csv": planilha, "simular": False})

    assert resposta.status_code == 422
    assert "nada foi importado" in resposta.json()["detail"]
    assert cliente.chamadas == []


def test_importacao_exige_permissao_de_edicao(ambiente):
    http, cliente, usuario = ambiente
    usuario["permissoes"] = ["parametro_fiscal.ler"]

    resposta = http.post(IMPORTACAO, headers=TOKEN, json={"conteudo_csv": PLANILHA_VALIDA})

    assert resposta.status_code == 403
    assert cliente.chamadas == []
