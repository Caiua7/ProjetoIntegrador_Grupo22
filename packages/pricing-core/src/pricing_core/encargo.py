"""Encargo financeiro pelo prazo médio de pagamento (US18, RF06).

Vender a prazo tem custo: o dinheiro só entra depois de ``PrazoMedio`` dias.
A especificação homologada com o PO converte a taxa mensal em taxa do período
por capitalização composta:

    Encargo  = (1 + Taxa) ^ (PrazoMedio / 30) − 1
    Encargo$ = Encargo × PBsIPIsEncargo

Taxas são frações (1,2% a.m. = ``Decimal("0.012")``), nunca percentuais.
Nenhum valor é arredondado aqui: o arredondamento para centavos é
responsabilidade de quem apresenta o resultado, para não acumular erro ao
longo da cadeia de preço.
"""

from decimal import Decimal, localcontext

from pricing_core.numeros import PRECISAO, Numero, para_decimal

DIAS_POR_MES = Decimal(30)


def taxa_encargo(taxa_mensal: Numero, prazo_medio_dias: Numero) -> Decimal:
    """Retorna a taxa de encargo do período, como fração.

    >>> taxa_encargo("0.012", 30)
    Decimal('0.012')
    """
    taxa = para_decimal(taxa_mensal, "taxa_mensal")
    prazo = para_decimal(prazo_medio_dias, "prazo_medio_dias")
    if taxa < 0:
        raise ValueError(f"taxa_mensal não pode ser negativa: {taxa}")
    if prazo < 0:
        raise ValueError(f"prazo_medio_dias não pode ser negativo: {prazo}")

    # Pagamento à vista ou dinheiro sem custo: não há encargo.
    if taxa == 0 or prazo == 0:
        return Decimal(0)

    with localcontext() as ctx:
        ctx.prec = PRECISAO
        return (1 + taxa) ** (prazo / DIAS_POR_MES) - 1


def valor_encargo(taxa: Numero, base_preco: Numero) -> Decimal:
    """Retorna o encargo em reais (``Encargo$``) sobre a base de preço.

    A base é o ``PBsIPIsEncargo``: preço bruto sem IPI e ainda sem encargo.
    Aplicar a taxa sobre o preço já com IPI ou com encargo cobraria juros
    sobre imposto ou juros sobre juros.
    """
    taxa = para_decimal(taxa, "taxa")
    base = para_decimal(base_preco, "base_preco")
    if taxa < 0:
        raise ValueError(f"taxa não pode ser negativa: {taxa}")
    if base < 0:
        raise ValueError(f"base_preco não pode ser negativa: {base}")

    with localcontext() as ctx:
        ctx.prec = PRECISAO
        return taxa * base
