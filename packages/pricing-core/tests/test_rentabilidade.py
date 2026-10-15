from decimal import Decimal

import pytest

from pricing_core.contracts import CalculateResponse
from pricing_core.rentabilidade import Rentabilidade, derivar_rentabilidade

# Valores unitários de um cenário com PIS 1,65%, COFINS 7,6% e ICMS 18%
# sobre PBsIPI de R$ 12,50:
#   ICMS       = 12,50 × 0,18                    = 2,25
#   PIS+COFINS = (12,50 − 2,25) × 0,0925         = 0,948125
#   ROL        = 12,50 − 2,25 − 0,948125         = 9,301875
UNITARIO = {
    "preco_bruto_sem_ipi": Decimal("12.50"),
    "receita_operacional_liquida": Decimal("9.301875"),
    "margem_contribuicao_valor": Decimal("2.104321"),
    "custo_total": Decimal("6.20"),
}


def test_criterio_de_aceite_volume_de_10_mil_unidades_em_reais():
    r = derivar_rentabilidade(10000, **UNITARIO)

    assert r == Rentabilidade(
        volume=Decimal("10000"),
        receita_operacional_bruta=Decimal("125000.00"),
        deducoes=Decimal("31981.25"),
        receita_operacional_liquida=Decimal("93018.75"),
        margem_contribuicao=Decimal("21043.21"),
        margem_bruta=Decimal("31018.75"),
    )


def test_rob_menos_deducoes_fecha_na_rol():
    r = derivar_rentabilidade("3517", **UNITARIO)

    assert r.receita_operacional_bruta - r.deducoes == r.receita_operacional_liquida


def test_nao_arredonda_para_nao_acumular_erro():
    r = derivar_rentabilidade(3, **UNITARIO)

    assert r.receita_operacional_liquida == Decimal("27.905625")


def test_volume_fracionado_para_produto_vendido_a_granel():
    r = derivar_rentabilidade("2.5", **UNITARIO)

    assert r.receita_operacional_bruta == Decimal("31.250")


def test_volume_zero_zera_tudo():
    r = derivar_rentabilidade(0, **UNITARIO)

    assert r.receita_operacional_bruta == r.margem_contribuicao == r.margem_bruta == 0


def test_cenario_com_prejuizo_mostra_margens_negativas():
    r = derivar_rentabilidade(
        1000,
        preco_bruto_sem_ipi="5.00",
        receita_operacional_liquida="3.72",
        margem_contribuicao_valor="-1.80",
        custo_total="6.20",
    )

    assert r.margem_contribuicao == Decimal("-1800.00")
    assert r.margem_bruta == Decimal("-2480.00")


def test_aceita_os_campos_do_contrato_do_motor():
    resposta = CalculateResponse.model_construct(**UNITARIO)

    r = derivar_rentabilidade(
        10000,
        preco_bruto_sem_ipi=resposta.preco_bruto_sem_ipi,
        receita_operacional_liquida=resposta.receita_operacional_liquida,
        margem_contribuicao_valor=resposta.margem_contribuicao_valor,
        custo_total=resposta.custo_total,
    )

    assert r.receita_operacional_bruta == Decimal("125000.00")


@pytest.mark.parametrize(
    "campo, valor",
    [
        pytest.param("volume", -1, id="volume_negativo"),
        pytest.param("preco_bruto_sem_ipi", "-0.01", id="preco_negativo"),
        pytest.param("custo_total", "-6.20", id="custo_negativo"),
    ],
)
def test_recusa_valores_negativos_sem_sentido(campo, valor):
    argumentos = {"volume": 10000, **UNITARIO, campo: valor}

    with pytest.raises(ValueError, match=campo):
        derivar_rentabilidade(**argumentos)


@pytest.mark.parametrize("volume", [10000.0, True, None, "dez mil", "NaN"])
def test_recusa_volume_que_nao_e_decimal_exato(volume):
    with pytest.raises((TypeError, ValueError)):
        derivar_rentabilidade(volume, **UNITARIO)
