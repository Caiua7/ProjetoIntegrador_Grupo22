"""Rentabilidade absoluta do cenário a partir do volume negociado (US32, RF08).

O motor devolve preço e margem por unidade. Sem volume, o analista só
enxerga margem percentual e não sabe quanto a operação gera em reais. Com o
volume negociado do cenário:

    ROB      = PBsIPI × Volume
    ROL      = ROL unitária × Volume
    Deduções = ROB − ROL                  (PIS, COFINS e ICMS)
    MaCo     = MaCo$ unitária × Volume
    MB       = (ROL unitária − CustoTotal) × Volume

DECISÕES EM ABERTO — confirmar com o PO junto da homologação dos 30 casos
(ver tests/conformidade/README.md). Não mudam a forma do resultado, só a
fórmula:
    1. ROB sobre ``PBsIPI``, e não sobre ``PB``: IPI e ICMS-ST são tributos
       cobrados do comprador por conta do Fisco e ficam fora da receita
       bruta (Lei 12.973/2014, art. 12, § 4º). Assim ROB − deduções fecha
       exatamente na ROL que o motor calcula a partir do ``PBsIPI``.
    2. MB como ROL − custo do produto (``CustoTotal``: MP, embalagem, perda,
       MOD e GGF). Comissão, frete e encargo financeiro são despesas
       comerciais e financeiras e ficam fora da margem bruta; já entram na
       MaCo.

Nenhum valor é arredondado aqui, pelo mesmo motivo do encargo: o
arredondamento para centavos é de quem apresenta o resultado.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from pricing_core.numeros import PRECISAO, Numero, para_decimal


@dataclass(frozen=True)
class Rentabilidade:
    """Valores em reais do cenário inteiro, para o volume negociado."""

    volume: Decimal
    receita_operacional_bruta: Decimal
    deducoes: Decimal
    receita_operacional_liquida: Decimal
    margem_contribuicao: Decimal
    margem_bruta: Decimal


def derivar_rentabilidade(
    volume: Numero,
    *,
    preco_bruto_sem_ipi: Numero,
    receita_operacional_liquida: Numero,
    margem_contribuicao_valor: Numero,
    custo_total: Numero,
) -> Rentabilidade:
    """Multiplica os valores unitários do cálculo pelo volume negociado.

    Os argumentos nomeados são os campos de mesmo nome de
    ``CalculateResponse``, por unidade de produto.

    >>> r = derivar_rentabilidade(
    ...     10000,
    ...     preco_bruto_sem_ipi="12.50",
    ...     receita_operacional_liquida="9.30",
    ...     margem_contribuicao_valor="2.10",
    ...     custo_total="6.00",
    ... )
    >>> r.receita_operacional_bruta, r.margem_contribuicao, r.margem_bruta
    (Decimal('125000.00'), Decimal('21000.00'), Decimal('33000.00'))
    """
    volume = para_decimal(volume, "volume")
    pbsipi = para_decimal(preco_bruto_sem_ipi, "preco_bruto_sem_ipi")
    rol = para_decimal(receita_operacional_liquida, "receita_operacional_liquida")
    maco = para_decimal(margem_contribuicao_valor, "margem_contribuicao_valor")
    custo = para_decimal(custo_total, "custo_total")

    if volume < 0:
        raise ValueError(f"volume não pode ser negativo: {volume}")
    if pbsipi < 0:
        raise ValueError(f"preco_bruto_sem_ipi não pode ser negativo: {pbsipi}")
    if custo < 0:
        raise ValueError(f"custo_total não pode ser negativo: {custo}")
    # ROL, MaCo e MB podem ser negativas: é o cenário que dá prejuízo, e o
    # painel precisa mostrar isso, não esconder.

    with localcontext() as ctx:
        ctx.prec = PRECISAO
        rob = pbsipi * volume
        rol_total = rol * volume
        return Rentabilidade(
            volume=volume,
            receita_operacional_bruta=rob,
            deducoes=rob - rol_total,
            receita_operacional_liquida=rol_total,
            margem_contribuicao=maco * volume,
            margem_bruta=(rol - custo) * volume,
        )
