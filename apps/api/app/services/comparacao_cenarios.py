"""Comparação entre duas versões de um cenário (issue #63, US31).

Mesmos indicadores da tela "Comparar cenários" do protótipo: volume, custo
de matéria-prima, custo de conversão (MOD + GGF), margem aplicada, preço
bruto, MaCo unitária, margem de contribuição e, quando há volume, ROB e MaCo
absoluta. Valor em reais varia em reais e em percentual; percentual varia em
pontos percentuais.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pricing_core.rentabilidade import derivar_rentabilidade

Unidade = Literal["un", "brl", "percentual"]


@dataclass(frozen=True)
class Indicador:
    codigo: str
    rotulo: str
    unidade: Unidade
    valor_de: Decimal | None
    valor_para: Decimal | None
    variacao: Decimal | None
    variacao_percentual: Decimal | None
    sentido: Literal["subiu", "desceu", "igual", "sem_base"]


def _decimal(valor) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


def _valores(cenario: dict) -> dict[str, Decimal | None]:
    resultado = cenario["resultado"]
    entrada = cenario["entrada"]
    volume = _decimal(cenario.get("volume"))
    custo_mod = _decimal(resultado.get("custo_mod")) or Decimal("0")
    custo_ggf = _decimal(resultado.get("custo_ggf")) or Decimal("0")

    valores: dict[str, Decimal | None] = {
        "volume": volume,
        "custo_mp": _decimal(resultado.get("custo_mp")),
        "custo_conversao": custo_mod + custo_ggf,
        "custo_total": _decimal(resultado.get("custo_total")),
        "margem_aplicada": _decimal(entrada.get("comercial", {}).get("margem_desejada_percentual")),
        "preco_bruto": _decimal(resultado.get("preco_bruto")),
        "margem_contribuicao_valor": _decimal(resultado.get("margem_contribuicao_valor")),
        "margem_contribuicao_percentual": _decimal(resultado.get("margem_contribuicao_percentual")),
        "receita_operacional_bruta": None,
        "margem_contribuicao_absoluta": None,
    }
    if volume is not None:
        rentabilidade = derivar_rentabilidade(
            volume,
            preco_bruto_sem_ipi=resultado["preco_bruto_sem_ipi"],
            receita_operacional_liquida=resultado["receita_operacional_liquida"],
            margem_contribuicao_valor=resultado["margem_contribuicao_valor"],
            custo_total=resultado["custo_total"],
        )
        valores["receita_operacional_bruta"] = rentabilidade.receita_operacional_bruta
        valores["margem_contribuicao_absoluta"] = rentabilidade.margem_contribuicao
    return valores


INDICADORES: list[tuple[str, str, Unidade]] = [
    ("volume", "Volume negociado", "un"),
    ("custo_mp", "Custo de matéria-prima", "brl"),
    ("custo_conversao", "Custo de conversão (MOD + GGF)", "brl"),
    ("custo_total", "Custo total", "brl"),
    ("margem_aplicada", "Margem aplicada", "percentual"),
    ("preco_bruto", "Preço bruto", "brl"),
    ("margem_contribuicao_valor", "MaCo unitária", "brl"),
    ("margem_contribuicao_percentual", "Margem de contribuição", "percentual"),
    ("receita_operacional_bruta", "ROB", "brl"),
    ("margem_contribuicao_absoluta", "MaCo absoluta", "brl"),
]


def comparar_cenarios(de: dict, para: dict) -> list[Indicador]:
    """Variação de cada indicador da versão `de` para a versão `para`.

    Percentuais (margens) variam em pontos percentuais, como fração: 0.023
    é +2,3 p.p.; não têm variação percentual. Sem um dos dois valores, ou
    com base zero na variação percentual, o campo fica nulo.
    """
    valores_de, valores_para = _valores(de), _valores(para)
    indicadores = []
    for codigo, rotulo, unidade in INDICADORES:
        antes, depois = valores_de[codigo], valores_para[codigo]
        if antes is None or depois is None:
            indicadores.append(Indicador(codigo, rotulo, unidade, antes, depois, None, None, "sem_base"))
            continue
        variacao = depois - antes
        percentual = None if unidade == "percentual" or antes == 0 else variacao / antes
        sentido = "subiu" if variacao > 0 else "desceu" if variacao < 0 else "igual"
        indicadores.append(Indicador(codigo, rotulo, unidade, antes, depois, variacao, percentual, sentido))
    return indicadores
