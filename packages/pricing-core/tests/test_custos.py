
from decimal import Decimal

import pytest

from pricing_core.contracts import ItemInsumo
from pricing_core.custos import (
    calcular_custo_embalagem,
    calcular_custo_ggf,
    calcular_custo_mod,
    calcular_custo_mp,
    calcular_custo_perda,
    calcular_custo_total,
)


def criar_item(
    preco: str,
    cambio: str,
    margem: str,
    quantidade: str,
    descarte: str = "0",
) -> ItemInsumo:
    return ItemInsumo(
        codigo="MP001",
        descricao="Materia-prima de teste",
        preco_negociado=Decimal(preco),
        moeda="BRL",
        cambio=Decimal(cambio),
        margem_seguranca_percentual=Decimal(margem),
        quantidade=Decimal(quantidade),
        percentual_descarte=Decimal(descarte),
    )


# Testes de custo de matéria-prima


def test_calcular_custo_mp_com_um_item():
    item = criar_item("10", "1", "0.10", "2")

    resultado = calcular_custo_mp([item])

    assert resultado == Decimal("22")


def test_calcular_custo_mp_com_varios_itens():
    item_1 = criar_item("10", "1", "0.10", "2")
    item_2 = criar_item("5", "2", "0.20", "3")

    resultado = calcular_custo_mp([item_1, item_2])

    assert resultado == Decimal("58")


def test_calcular_custo_mp_ignora_descarte():
    item = criar_item("10", "1", "0.10", "2", descarte="0.25")

    resultado = calcular_custo_mp([item])

    assert resultado == Decimal("22")


def test_calcular_custo_mp_sem_itens():
    resultado = calcular_custo_mp([])

    assert resultado == Decimal("0")


# Testes de custo de embalagem


def test_calcular_custo_embalagem_com_um_item():
    item = criar_item("10", "1", "0.10", "2", descarte="0.25")

    resultado = calcular_custo_embalagem([item])

    assert resultado == Decimal("5.50")


def test_calcular_custo_embalagem_sem_itens():
    resultado = calcular_custo_embalagem([])

    assert resultado == Decimal("0")


# Testes de custo de perda


def test_calcular_custo_perda_com_material_cliente():
    resultado = calcular_custo_perda(
        custo_mp=Decimal("100"),
        custo_embalagem=Decimal("20"),
        valor_material_cliente=Decimal("30"),
        perda_percentual=Decimal("0.10"),
    )

    assert resultado == Decimal("9")


def test_calcular_custo_perda_sem_material_cliente():
    resultado = calcular_custo_perda(
        custo_mp=Decimal("100"),
        custo_embalagem=Decimal("20"),
        valor_material_cliente=Decimal("0"),
        perda_percentual=Decimal("0.10"),
    )

    assert resultado == Decimal("12")


def test_calcular_custo_perda_com_custos_zerados():
    resultado = calcular_custo_perda(
        custo_mp=Decimal("0"),
        custo_embalagem=Decimal("0"),
        valor_material_cliente=Decimal("0"),
        perda_percentual=Decimal("0.10"),
    )

    assert resultado == Decimal("0")


@pytest.mark.parametrize(
    "parametro",
    [
        "custo_mp",
        "custo_embalagem",
        "valor_material_cliente",
        "perda_percentual",
    ],
)
def test_calcular_custo_perda_recusa_valores_negativos(parametro):
    valores = {
        "custo_mp": Decimal("100"),
        "custo_embalagem": Decimal("20"),
        "valor_material_cliente": Decimal("10"),
        "perda_percentual": Decimal("0.10"),
    }
    valores[parametro] = Decimal("-1")

    with pytest.raises(ValueError):
        calcular_custo_perda(**valores)


@pytest.mark.parametrize(
    "valor",
    [
        0.1,
        True,
        None,
        "abc",
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_calcular_custo_perda_recusa_valores_invalidos(valor):
    with pytest.raises((TypeError, ValueError)):
        calcular_custo_perda(
            custo_mp=valor,
            custo_embalagem=Decimal("20"),
            valor_material_cliente=Decimal("10"),
            perda_percentual=Decimal("0.10"),
        )


# Testes de custo de mão de obra direta


def test_calcular_custo_mod():
    resultado = calcular_custo_mod(
        taxa_mod=Decimal("120"),
        produtividade=Decimal("10"),
        numero_funcionarios=2,
    )

    assert resultado == Decimal("24")


def test_calcular_custo_mod_sem_funcionarios():
    resultado = calcular_custo_mod(
        taxa_mod=Decimal("120"),
        produtividade=Decimal("10"),
        numero_funcionarios=0,
    )

    assert resultado == Decimal("0")


def test_calcular_custo_mod_recusa_taxa_negativa():
    with pytest.raises(ValueError):
        calcular_custo_mod(
            taxa_mod=Decimal("-120"),
            produtividade=Decimal("10"),
            numero_funcionarios=2,
        )


@pytest.mark.parametrize(
    "produtividade",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_calcular_custo_mod_recusa_produtividade_nao_positiva(produtividade):
    with pytest.raises(ValueError):
        calcular_custo_mod(
            taxa_mod=Decimal("120"),
            produtividade=produtividade,
            numero_funcionarios=2,
        )


@pytest.mark.parametrize(
    "numero_funcionarios",
    [
        1.5,
        True,
        "2",
    ],
)
def test_calcular_custo_mod_recusa_numero_funcionarios_invalido(
    numero_funcionarios,
):
    with pytest.raises(TypeError):
        calcular_custo_mod(
            taxa_mod=Decimal("120"),
            produtividade=Decimal("10"),
            numero_funcionarios=numero_funcionarios,
        )


def test_calcular_custo_mod_recusa_funcionarios_negativos():
    with pytest.raises(ValueError):
        calcular_custo_mod(
            taxa_mod=Decimal("120"),
            produtividade=Decimal("10"),
            numero_funcionarios=-1,
        )


def test_calcular_custo_mod_recusa_taxa_float():
    with pytest.raises((TypeError, ValueError)):
        calcular_custo_mod(
            taxa_mod=120.0,
            produtividade=Decimal("10"),
            numero_funcionarios=2,
        )


# Testes de gastos gerais de fabricação


def test_calcular_custo_ggf():
    resultado = calcular_custo_ggf(
        taxa_ggf=Decimal("120"),
        produtividade=Decimal("10"),
    )

    assert resultado == Decimal("12")


def test_calcular_custo_ggf_com_produtividade_decimal():
    resultado = calcular_custo_ggf(
        taxa_ggf=Decimal("120"),
        produtividade=Decimal("2.5"),
    )

    assert resultado == Decimal("48")


def test_calcular_custo_ggf_recusa_taxa_negativa():
    with pytest.raises(ValueError):
        calcular_custo_ggf(
            taxa_ggf=Decimal("-120"),
            produtividade=Decimal("10"),
        )


@pytest.mark.parametrize(
    "produtividade",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_calcular_custo_ggf_recusa_produtividade_nao_positiva(produtividade):
    with pytest.raises(ValueError):
        calcular_custo_ggf(
            taxa_ggf=Decimal("120"),
            produtividade=produtividade,
        )


def test_calcular_custo_ggf_recusa_taxa_float():
    with pytest.raises((TypeError, ValueError)):
        calcular_custo_ggf(
            taxa_ggf=120.0,
            produtividade=Decimal("10"),
        )


def test_calcular_custo_ggf_recusa_produtividade_float():
    with pytest.raises((TypeError, ValueError)):
        calcular_custo_ggf(
            taxa_ggf=Decimal("120"),
            produtividade=10.0,
        )


# Testes de custo total


def test_calcular_custo_total_soma_as_cinco_parcelas():
    resultado = calcular_custo_total(
        custo_mp=Decimal("58"),
        custo_embalagem=Decimal("5.50"),
        custo_perda=Decimal("9"),
        custo_mod=Decimal("24"),
        custo_ggf=Decimal("12"),
    )

    assert resultado == Decimal("108.50")


def test_calcular_custo_total_com_todas_as_parcelas_zeradas():
    resultado = calcular_custo_total(
        custo_mp=Decimal("0"),
        custo_embalagem=Decimal("0"),
        custo_perda=Decimal("0"),
        custo_mod=Decimal("0"),
        custo_ggf=Decimal("0"),
    )

    assert resultado == Decimal("0")


def test_calcular_custo_total_aceita_perda_negativa():
    resultado = calcular_custo_total(
        custo_mp=Decimal("100"),
        custo_embalagem=Decimal("20"),
        custo_perda=Decimal("-5"),
        custo_mod=Decimal("10"),
        custo_ggf=Decimal("15"),
    )

    assert resultado == Decimal("140")


@pytest.mark.parametrize(
    "parametro",
    [
        "custo_mp",
        "custo_embalagem",
        "custo_perda",
        "custo_mod",
        "custo_ggf",
    ],
)
def test_calcular_custo_total_recusa_valores_invalidos(parametro):
    valores = {
        "custo_mp": Decimal("100"),
        "custo_embalagem": Decimal("20"),
        "custo_perda": Decimal("5"),
        "custo_mod": Decimal("10"),
        "custo_ggf": Decimal("15"),
    }
    valores[parametro] = 10.0

    with pytest.raises((TypeError, ValueError)):
        calcular_custo_total(**valores)
