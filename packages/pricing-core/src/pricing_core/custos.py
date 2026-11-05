
"""Cálculos de custos do produto conforme a seção 2.3 do planejamento."""

from collections.abc import Iterable
from decimal import Decimal, localcontext

from pricing_core.contracts import ItemInsumo
from pricing_core.numeros import PRECISAO, Numero, para_decimal


def _validar_nao_negativo(valor: Numero, nome: str) -> Decimal:
    """Converte um valor para Decimal e garante que não seja negativo."""

    resultado = para_decimal(valor, nome)

    if resultado < 0:
        raise ValueError(f"{nome} deve ser maior ou igual a zero.")

    return resultado


def _validar_positivo(valor: Numero, nome: str) -> Decimal:
    """Converte um valor para Decimal e garante que seja maior que zero."""

    resultado = para_decimal(valor, nome)

    if resultado <= 0:
        raise ValueError(f"{nome} deve ser maior que zero.")

    return resultado


def calcular_custo_mp(materias_primas: Iterable[ItemInsumo]) -> Decimal:
    """Calcula o custo total das matérias-primas da formulação."""

    with localcontext() as contexto:
        contexto.prec = PRECISAO

        custo_total = sum(
            (
                item.preco_negociado
                * item.cambio
                * (Decimal("1") + item.margem_seguranca_percentual)
                * item.quantidade
                for item in materias_primas
            ),
            Decimal("0"),
        )

    return custo_total


def calcular_custo_embalagem(embalagens: Iterable[ItemInsumo]) -> Decimal:
    """Calcula o custo total das embalagens da formulação."""

    with localcontext() as contexto:
        contexto.prec = PRECISAO

        custo_total = sum(
            (
                item.preco_negociado
                * item.cambio
                * (Decimal("1") + item.margem_seguranca_percentual)
                * item.quantidade
                * item.percentual_descarte
                for item in embalagens
            ),
            Decimal("0"),
        )

    return custo_total


def calcular_custo_perda(
    custo_mp: Numero,
    custo_embalagem: Numero,
    valor_material_cliente: Numero,
    perda_percentual: Numero,
) -> Decimal:
    """Calcula o custo de perda descontando o material fornecido pelo cliente."""

    custo_mp_decimal = _validar_nao_negativo(custo_mp, "custo_mp")
    custo_embalagem_decimal = _validar_nao_negativo(
        custo_embalagem,
        "custo_embalagem",
    )
    material_cliente_decimal = _validar_nao_negativo(
        valor_material_cliente,
        "valor_material_cliente",
    )
    perda_decimal = _validar_nao_negativo(
        perda_percentual,
        "perda_percentual",
    )

    with localcontext() as contexto:
        contexto.prec = PRECISAO

        custo_base = (
            custo_mp_decimal
            + custo_embalagem_decimal
            - material_cliente_decimal
        )
        custo_total = custo_base * perda_decimal

    return custo_total


def calcular_custo_mod(
    taxa_mod: Numero,
    produtividade: Numero,
    numero_funcionarios: int,
) -> Decimal:
    """Calcula o custo de mão de obra direta."""

    taxa_mod_decimal = _validar_nao_negativo(taxa_mod, "taxa_mod")
    produtividade_decimal = _validar_positivo(
        produtividade,
        "produtividade",
    )

    if (
        isinstance(numero_funcionarios, bool)
        or not isinstance(numero_funcionarios, int)
    ):
        raise TypeError("numero_funcionarios deve ser um número inteiro.")

    if numero_funcionarios < 0:
        raise ValueError("numero_funcionarios deve ser maior ou igual a zero.")

    with localcontext() as contexto:
        contexto.prec = PRECISAO

        custo_total = (
            taxa_mod_decimal / produtividade_decimal
        ) * numero_funcionarios

    return custo_total


def calcular_custo_ggf(
    taxa_ggf: Numero,
    produtividade: Numero,
) -> Decimal:
    """Calcula o custo dos gastos gerais de fabricação."""

    taxa_ggf_decimal = _validar_nao_negativo(taxa_ggf, "taxa_ggf")
    produtividade_decimal = _validar_positivo(
        produtividade,
        "produtividade",
    )

    with localcontext() as contexto:
        contexto.prec = PRECISAO

        custo_total = taxa_ggf_decimal / produtividade_decimal

    return custo_total


def calcular_custo_total(
    custo_mp: Numero,
    custo_embalagem: Numero,
    custo_perda: Numero,
    custo_mod: Numero,
    custo_ggf: Numero,
) -> Decimal:
    """Soma as cinco parcelas para obter o custo total do produto."""

    custo_mp_decimal = para_decimal(custo_mp, "custo_mp")
    custo_embalagem_decimal = para_decimal(
        custo_embalagem,
        "custo_embalagem",
    )
    custo_perda_decimal = para_decimal(custo_perda, "custo_perda")
    custo_mod_decimal = para_decimal(custo_mod, "custo_mod")
    custo_ggf_decimal = para_decimal(custo_ggf, "custo_ggf")

    with localcontext() as contexto:
        contexto.prec = PRECISAO

        custo_total = (
            custo_mp_decimal
            + custo_embalagem_decimal
            + custo_perda_decimal
            + custo_mod_decimal
            + custo_ggf_decimal
        )

    return custo_total
