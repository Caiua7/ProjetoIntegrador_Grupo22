from copy import deepcopy
from decimal import Decimal

import pytest

from pricing_core.contracts import (
    CalculateRequest,
    DomainErrorCodigo,
)
from pricing_core.engine import ErroDominioPricing, calcular


def _entrada(**alteracoes):
    dados = {
        "cliente_uf": "SP",
        "modalidade_comercial": "full_service_nacional",
        "regime_tributario": "Lucro Real",
        "materiais_primas": [
            {
                "codigo": "MP-001",
                "preco_negociado": "100",
                "quantidade": "2",
                "cambio": "1",
                "margem_seguranca_percentual": "0.10",
            }
        ],
        "embalagens": [
            {
                "codigo": "EMB-001",
                "preco_negociado": "5",
                "quantidade": "2",
                "percentual_descarte": "0.10",
            }
        ],
        "perda_percentual": "0.05",
        "material_fornecido_pelo_cliente": False,
        "valor_material_cliente": "10",
        "producao": {
            "taxa_mod": "20",
            "taxa_ggf": "10",
            "produtividade": "2",
            "numero_funcionarios": "2",
        },
        "impostos": {
            "pis_percentual": "0.0165",
            "cofins_percentual": "0.076",
            "icms_percentual": "0.18",
            "ipi_percentual": "0.05",
            "icms_interno_percentual": "0",
            "fcp_percentual": "0",
            "mva_percentual": "0",
        },
        "comercial": {
            "margem_desejada_percentual": "0.20",
            "comissao_percentual": "0.03",
            "frete_percentual": "0.02",
            "prazo_medio_dias": "45",
            "taxa_financeira_mensal_percentual": "0.012",
        },
    }
    dados.update(alteracoes)
    return CalculateRequest.model_validate(dados)


def test_calcula_estrutura_completa_e_marca_motor_como_real():
    resultado = calcular(_entrada())

    assert resultado.custo_mp == Decimal("220.00")
    assert resultado.custo_embalagem == Decimal("1.00")
    assert resultado.custo_perda == Decimal("10.55")
    assert resultado.custo_mod == Decimal("20.00")
    assert resultado.custo_ggf == Decimal("5.00")
    assert resultado.custo_total == Decimal("256.55")
    assert resultado.denominador > 0
    assert resultado.preco_bruto_sem_ipi_sem_encargo > 0
    assert resultado.preco_bruto_sem_ipi > 0
    assert resultado.preco_bruto_com_ipi > resultado.preco_bruto_sem_ipi
    assert resultado.preco_bruto == resultado.preco_bruto_com_ipi
    assert resultado.preco_indicado == resultado.preco_bruto
    assert resultado.metadata.is_mock is False
    assert resultado.metadata.versao_motor


def test_entrada_nao_e_mutada_pelo_motor():
    entrada = _entrada()
    antes = deepcopy(entrada.model_dump(mode="python"))

    calcular(entrada)

    assert entrada.model_dump(mode="python") == antes


def test_d_igual_a_zero_gera_erro_de_dominio():
    entrada = _entrada(
        comercial={
            "margem_desejada_percentual": "0",
            "comissao_percentual": "1",
            "frete_percentual": "0",
        }
    )

    with pytest.raises(ErroDominioPricing) as captura:
        calcular(entrada)

    assert captura.value.codigo is DomainErrorCodigo.DENOMINADOR_INVALIDO
    assert captura.value.detalhes["etapa"] == "D"


def test_d_negativo_gera_erro_de_dominio():
    entrada = _entrada(
        comercial={
            "margem_desejada_percentual": "0.5",
            "comissao_percentual": "0.8",
            "frete_percentual": "0",
        }
    )

    with pytest.raises(ErroDominioPricing) as captura:
        calcular(entrada)

    assert captura.value.codigo is DomainErrorCodigo.DENOMINADOR_INVALIDO
    assert Decimal(captura.value.detalhes["denominador"]) < 0


def test_segundo_denominador_invalido_tambem_gera_erro_de_dominio():
    # D continua positivo, mas o denominador usado em PBsIPI chega a zero.
    entrada = _entrada(
        impostos={
            "pis_percentual": "0",
            "cofins_percentual": "0",
            "icms_percentual": "0.2",
        },
        comercial={
            "margem_desejada_percentual": "-1",
            "comissao_percentual": "0.8",
            "frete_percentual": "0",
        },
    )

    with pytest.raises(ErroDominioPricing) as captura:
        calcular(entrada)

    assert captura.value.codigo is DomainErrorCodigo.DENOMINADOR_INVALIDO
    assert captura.value.detalhes["etapa"] == "PBsIPI"


def test_isencao_de_mod_so_ocorre_com_material_do_cliente_em_sp():
    entrada = _entrada(
        material_fornecido_pelo_cliente=True,
        cliente_uf="SP",
    )

    resultado = calcular(entrada)

    assert resultado.isencao_mao_de_obra.aplicada is True
    assert resultado.isencao_mao_de_obra.valor == Decimal("20.00")


def test_nao_aplica_isencao_fora_de_sp():
    entrada = _entrada(
        material_fornecido_pelo_cliente=True,
        cliente_uf="RJ",
    )

    resultado = calcular(entrada)

    assert resultado.isencao_mao_de_obra.aplicada is False
    assert resultado.isencao_mao_de_obra.valor == Decimal("0.00")


def test_icms_st_e_calculado_quando_mva_ou_fcp_estao_preenchidos():
    entrada = _entrada(
        impostos={
            "pis_percentual": "0.0165",
            "cofins_percentual": "0.076",
            "icms_percentual": "0.18",
            "ipi_percentual": "0.05",
            "icms_interno_percentual": "0.18",
            "fcp_percentual": "0.02",
            "mva_percentual": "0.40",
        }
    )

    resultado = calcular(entrada)

    assert resultado.preco_bruto != resultado.preco_bruto_com_ipi
    assert resultado.impostos_destacados.icms_st_valor != Decimal("0.00")
