from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.auth import UsuarioAutenticado
from app.routers.entrada_calculo import montar_entrada

HOJE = date(2026, 11, 11)
PREC_ID = uuid4()
MP_USD, MP_BRL, EMB = str(uuid4()), str(uuid4()), str(uuid4())
TODAS = frozenset(
    {"precificacao.ler", "cadastro.ler", "custo.ler", "cambio.ler", "parametro_global.ler", "parametro_fiscal.ler"}
)


class _Consulta:
    def __init__(self, dados):
        self._dados = dados

    def __getattr__(self, _nome):
        return lambda *_a, **_k: self

    def execute(self):
        return SimpleNamespace(data=self._dados)


class _ClienteFalso:
    """Imita o cliente do Supabase: devolve linhas fixas por tabela e por RPC."""

    def __init__(self, tabelas, cotacoes):
        self.tabelas, self.cotacoes, self.rpcs = tabelas, cotacoes, []

    def table(self, nome):
        return _Consulta(self.tabelas.get(nome, []))

    def rpc(self, nome, parametros):
        self.rpcs.append((nome, parametros["p_materia_prima_id"]))
        return _Consulta(self.cotacoes.get(parametros["p_materia_prima_id"], []))


def _cotacao(mp, moeda, preco):
    return {
        "id": str(uuid4()),
        "materia_prima_id": mp,
        "fornecedor_id": str(uuid4()),
        "moeda": moeda,
        "preco": preco,
        "volume_minimo": 0,
        "validade_inicio": "2026-11-01",
        "validade_fim": "2026-12-31",
        "prazo_entrega_dias": 15,
    }


def _cliente(**trocas):
    tabelas = {
        "precificacao": [
            {
                "id": str(PREC_ID),
                "produto_id": str(uuid4()),
                "uf_destino": "SP",
                "modalidade_comercial": "full_service_nacional",
                "regime_tributario": "lucro_real",
                "produto": {"ncm_codigo": "21069030"},
            }
        ],
        "formulacao": [
            {
                "id": str(uuid4()),
                "formulacao_item": [
                    {
                        "tipo_insumo": "embalagem",
                        "materia_prima_id": None,
                        "embalagem_id": EMB,
                        "quantidade": 1.0,
                        "unidade_medida": "un",
                        "origem_material": "fabricante",
                        "ordem": 2,
                        "materia_prima": None,
                        "embalagem": {"codigo": "EMB-1", "descricao": "Pote", "unidade_medida": "un"},
                    },
                    {
                        "tipo_insumo": "materia_prima",
                        "materia_prima_id": MP_USD,
                        "embalagem_id": None,
                        "quantidade": 0.5,
                        "unidade_medida": "kg",
                        "origem_material": "fabricante",
                        "ordem": 0,
                        "materia_prima": {"codigo": "MP-1", "descricao": "Whey", "unidade_medida": "kg"},
                        "embalagem": None,
                    },
                    {
                        "tipo_insumo": "materia_prima",
                        "materia_prima_id": MP_BRL,
                        "embalagem_id": None,
                        "quantidade": 0.01,
                        "unidade_medida": "kg",
                        "origem_material": "fabricante",
                        "ordem": 1,
                        "materia_prima": {"codigo": "MP-2", "descricao": "Aroma", "unidade_medida": "kg"},
                        "embalagem": None,
                    },
                ],
            }
        ],
        "parametro_global": [
            {"codigo": "perda_percentual", "valor": 0.02, "vigencia_inicio": "2026-01-01"},
            {"codigo": "taxa_financeira_mensal_percentual", "valor": 0.012, "vigencia_inicio": "2026-01-01"},
            {"codigo": "prazo_medio_padrao_dias", "valor": 30, "vigencia_inicio": "2026-01-01"},
            {"codigo": "desvio_maximo_cotacao_percentual", "valor": 0.1, "vigencia_inicio": "2026-01-01"},
        ],
        "aliquota_fiscal": [
            {
                "ncm_codigo": None,
                "vigencia_inicio": "2026-01-01",
                "pis_percentual": 0.0165,
                "cofins_percentual": 0.076,
                "icms_percentual": 0.12,
                "ipi_percentual": 0,
                "icms_interno_percentual": 0.18,
                "fcp_percentual": 0.02,
                "mva_percentual": 0.4,
            }
        ],
        "cambio": [{"moeda": "USD", "data_referencia": "2026-11-10", "taxa": 5.0, "margem_seguranca_percentual": 0.02}],
    }
    tabelas.update(trocas)
    cotacoes = {MP_USD: [_cotacao(MP_USD, "USD", 11.8)], MP_BRL: [_cotacao(MP_BRL, "BRL", 72)]}
    return _ClienteFalso(tabelas, cotacoes)


def _usuario(permissoes=TODAS):
    return UsuarioAutenticado(
        id=uuid4(),
        nome="Ana",
        email="ana@x.com",
        perfil_codigo="analista_pricing",
        perfil_nome="Analista",
        permissoes=permissoes,
    )


def test_monta_a_entrada_completa_em_uma_chamada():
    cliente = _cliente()
    resultado = montar_entrada(cliente, _usuario(), PREC_ID, Decimal("1000"), HOJE)
    entrada = resultado["entrada"]

    assert resultado["pendencias"] == []
    assert entrada["cliente_uf"] == "SP" and entrada["regime_tributario"] == "lucro_real"
    assert [m["codigo"] for m in entrada["materiais_primas"]] == ["MP-1", "MP-2"]  # segue a ordem da formulação
    whey, aroma = entrada["materiais_primas"]
    assert (whey["preco_negociado"], whey["moeda"], whey["cambio"]) == ("11.8", "USD", "5.100")  # taxa × (1 + margem)
    assert (aroma["moeda"], aroma["cambio"]) == ("BRL", "1")
    assert entrada["embalagens"][0]["codigo"] == "EMB-1" and entrada["embalagens"][0]["preco_negociado"] == ""
    assert entrada["material_fornecido_pelo_cliente"] is False and entrada["valor_material_cliente"] == "0"
    assert entrada["perda_percentual"] == "0.02"
    assert entrada["comercial"] == {"taxa_financeira_mensal_percentual": "0.012", "prazo_medio_dias": "30"}
    assert entrada["impostos"]["icms_percentual"] == "0.12"
    assert sorted(mp for _, mp in cliente.rpcs) == sorted([MP_USD, MP_BRL])


def test_sem_volume_nao_cota_e_pede_o_volume():
    cliente = _cliente()
    resultado = montar_entrada(cliente, _usuario(), PREC_ID, None, HOJE)
    assert cliente.rpcs == []
    assert "Informe o volume negociado para escolher a faixa de cotação dos insumos." in resultado["pendencias"]


def test_respeita_as_permissoes_do_perfil():
    cliente = _cliente()
    resultado = montar_entrada(
        cliente, _usuario(frozenset({"precificacao.ler", "cadastro.ler"})), PREC_ID, Decimal("10"), HOJE
    )
    assert cliente.rpcs == []  # sem custo.ler, nenhuma cotação é lida
    texto = " ".join(resultado["pendencias"])
    assert "não pode ver custos" in texto
    assert "parâmetros globais" in texto
    assert "tributos" in texto
    assert all(valor == "" for valor in resultado["entrada"]["impostos"].values())


def test_cabecalho_incompleto_e_sem_formulacao():
    cliente = _cliente(
        precificacao=[
            {
                "id": str(PREC_ID),
                "produto_id": str(uuid4()),
                "uf_destino": None,
                "modalidade_comercial": "full_service_nacional",
                "regime_tributario": None,
                "produto": {"ncm_codigo": None},
            }
        ],
        formulacao=[],
    )
    pendencias = montar_entrada(cliente, _usuario(), PREC_ID, Decimal("10"), HOJE)["pendencias"]
    assert "Preencha a UF de destino no cabeçalho da precificação." in pendencias
    assert "Preencha o regime tributário do cliente no cabeçalho." in pendencias
    assert "O produto ainda não tem formulação. Monte a composição em Formulações." in pendencias


def test_sem_cotacao_vigente_vira_pendencia():
    cliente = _cliente()
    cliente.cotacoes = {}
    pendencias = montar_entrada(cliente, _usuario(), PREC_ID, Decimal("1000"), HOJE)["pendencias"]
    assert "Sem cotação vigente de Whey para esse volume. Cadastre ou atualize em Cotações." in pendencias


def test_precificacao_fora_da_carteira_devolve_404():
    with pytest.raises(HTTPException) as erro:
        montar_entrada(_cliente(precificacao=[]), _usuario(), PREC_ID, Decimal("1"), HOJE)
    assert erro.value.status_code == 404
