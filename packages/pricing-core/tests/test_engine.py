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


def _assert_centavos_iguais(valor, esperado):
    assert abs(valor - esperado) <= Decimal("0.01")


def test_preco_sem_st_respeita_relacao_pbsipi_pbcipi_e_pb():
    entrada = _entrada()
    resultado = calcular(entrada)

    esperado_pbcipi = resultado.preco_bruto_sem_ipi * (Decimal("1") + entrada.impostos.ipi_percentual)
    _assert_centavos_iguais(resultado.preco_bruto_com_ipi, esperado_pbcipi)
    _assert_centavos_iguais(resultado.preco_bruto, esperado_pbcipi)


def test_preco_com_st_aplica_icms_interno_fcp_e_mva():
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
    impostos = entrada.impostos

    esperado_pbcipi = resultado.preco_bruto_sem_ipi * (Decimal("1") + impostos.ipi_percentual)
    esperado_pb = esperado_pbcipi + (
        esperado_pbcipi
        * (Decimal("1") + impostos.mva_percentual)
        * (impostos.icms_interno_percentual + impostos.fcp_percentual)
        - resultado.preco_bruto_sem_ipi * impostos.icms_percentual
    )

    _assert_centavos_iguais(resultado.preco_bruto_com_ipi, esperado_pbcipi)
    _assert_centavos_iguais(resultado.preco_bruto, esperado_pb)
    _assert_centavos_iguais(
        resultado.impostos_destacados.icms_st_valor,
        esperado_pb - esperado_pbcipi,
    )


def test_rol_e_composta_com_as_bases_de_pis_cofins_e_icms_especificadas():
    entrada = _entrada()
    resultado = calcular(entrada)
    pbsipi = resultado.preco_bruto_sem_ipi
    icms = entrada.impostos.icms_percentual
    pis = entrada.impostos.pis_percentual
    cofins = entrada.impostos.cofins_percentual

    esperado = pbsipi - ((pbsipi - pbsipi * icms) * (pis + cofins) + pbsipi * icms)
    _assert_centavos_iguais(resultado.receita_operacional_liquida, esperado)


def test_maco_deduz_custos_encargo_perda_e_comissao():
    entrada = _entrada()
    resultado = calcular(entrada)
    # TODO(PO): a base Comissao$ = Comissao × PB é uma premissa provisória.
    comissao_valor = entrada.comercial.comissao_percentual * resultado.preco_bruto
    esperado = resultado.receita_operacional_liquida - (
        resultado.custo_mp
        + resultado.custo_embalagem
        + resultado.encargo_financeiro_valor
        + resultado.custo_perda
        + comissao_valor
    )
    _assert_centavos_iguais(resultado.margem_contribuicao_valor, esperado)


def test_impostos_destacados_usam_as_bases_da_formula_da_rol():
    entrada = _entrada()
    resultado = calcular(entrada)
    pbsipi = resultado.preco_bruto_sem_ipi
    icms = entrada.impostos.icms_percentual
    base_pis_cofins = pbsipi - pbsipi * icms

    _assert_centavos_iguais(
        resultado.impostos_destacados.pis_valor,
        base_pis_cofins * entrada.impostos.pis_percentual,
    )
    _assert_centavos_iguais(
        resultado.impostos_destacados.cofins_valor,
        base_pis_cofins * entrada.impostos.cofins_percentual,
    )
    _assert_centavos_iguais(
        resultado.impostos_destacados.icms_valor,
        pbsipi * icms,
    )
    _assert_centavos_iguais(
        resultado.impostos_destacados.ipi_valor,
        pbsipi * entrada.impostos.ipi_percentual,
    )
