"""Preço líquido de matéria-prima com desoneração de tributos recuperáveis (US26, RF13).

O preço pago ao fornecedor embute ICMS, PIS e COFINS. Quando a empresa
recupera esses créditos na aquisição, o custo real da MP é o preço sem eles:

    ICMS_rec       = PrecoBruto × ICMS
    PIS/COFINS_rec = (PrecoBruto − ICMS_rec) × (PIS + COFINS)    [base líquida de ICMS]
    PrecoLiquido   = PrecoBruto − ICMS_rec − PIS/COFINS_rec

A base líquida de ICMS segue a convenção do restante do motor (ver ``ROL`` em
``rentabilidade.py``: ``(PBsIPI − PBsIPI×ICMS) × (PIS+COFINS)``). Se a
homologação com o PO indicar base cheia (PIS/COFINS sobre o preço bruto),
use ``pis_cofins_sobre_base_sem_icms=False``.

Se o crédito não é recuperável (fornecedor do Simples Nacional, por exemplo),
passe ``recupera_icms=False`` e/ou ``recupera_pis_cofins=False``: o tributo
permanece no custo. Mapear regime do fornecedor e origem (nacional/importada)
para essas flags é responsabilidade de quem chama, não deste módulo.

Taxas são frações (18% = ``Decimal("0.18")``). Nenhum valor é arredondado aqui.
"""

from decimal import Decimal, localcontext

from pricing_core.numeros import PRECISAO, Numero, para_decimal


def preco_liquido_mp(
    preco_bruto: Numero,
    icms: Numero,
    pis: Numero,
    cofins: Numero,
    *,
    recupera_icms: bool = True,
    recupera_pis_cofins: bool = True,
    pis_cofins_sobre_base_sem_icms: bool = True,
) -> Decimal:
    """Retorna o preço líquido da MP, já desonerado dos créditos recuperáveis.

    >>> preco_liquido_mp("10.00", "0.18", "0.0165", "0.076") == Decimal("7.4415")
    True
    >>> preco_liquido_mp("10.00", "0.18", "0.0165", "0.076", pis_cofins_sobre_base_sem_icms=False) == Decimal("7.275")
    True
    """
    bruto = para_decimal(preco_bruto, "preco_bruto")
    aliq_icms = para_decimal(icms, "icms")
    aliq_pis = para_decimal(pis, "pis")
    aliq_cofins = para_decimal(cofins, "cofins")

    if bruto < 0:
        raise ValueError(f"preco_bruto não pode ser negativo: {bruto}")
    for nome, aliquota in (("icms", aliq_icms), ("pis", aliq_pis), ("cofins", aliq_cofins)):
        if not 0 <= aliquota < 1:
            raise ValueError(f"{nome} deve ser uma fração em [0, 1): {aliquota}")

    with localcontext() as ctx:
        ctx.prec = PRECISAO
        icms_recuperado = bruto * aliq_icms if recupera_icms else Decimal(0)
        base_pis_cofins = bruto - icms_recuperado if pis_cofins_sobre_base_sem_icms else bruto
        pis_cofins_recuperado = base_pis_cofins * (aliq_pis + aliq_cofins) if recupera_pis_cofins else Decimal(0)
        liquido = bruto - icms_recuperado - pis_cofins_recuperado

    if liquido < 0:
        raise ValueError("a soma dos créditos recuperáveis supera o preço bruto")
    return liquido
