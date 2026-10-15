"""Conversão e precisão numérica comuns às regras do motor.

Todo valor monetário e percentual do motor é ``Decimal``: o critério de
aceite é divergência máxima de R$ 0,01 (RNF08).
"""

from decimal import Decimal

# Dígitos significativos no cálculo. Folga ampla sobre a tolerância de
# R$ 0,01 da suíte de conformidade, mesmo com expoente fracionário.
PRECISAO = 34

Numero = Decimal | int | str


def para_decimal(valor: Numero, nome: str) -> Decimal:
    """Converte para ``Decimal`` finito, recusando ``float`` e ``bool``.

    >>> para_decimal("10000", "volume")
    Decimal('10000')
    """
    # float é recusado de propósito: 0.012 em binário já chega impreciso, e o
    # critério de aceite do motor é divergência máxima de R$ 0,01.
    if isinstance(valor, bool) or not isinstance(valor, Decimal | int | str):
        raise TypeError(
            f"{nome} deve ser Decimal, int ou str, não {type(valor).__name__}"
        )
    try:
        numero = Decimal(valor)
    except ArithmeticError:
        raise ValueError(f"{nome} não é um número válido: {valor!r}") from None
    if not numero.is_finite():
        raise ValueError(f"{nome} deve ser finito: {valor!r}")
    return numero
