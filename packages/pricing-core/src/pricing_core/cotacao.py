"""Cotação vigente de matéria-prima (US25, RF12).

O custo de MP depende da cotação certa: fornecedor, moeda e preço mudam com a
validade e com a faixa de volume negociada. Este módulo tem o modelo da
cotação, a seleção das cotações vigentes numa data e a resolução da cotação
aplicável a uma quantidade.

Convenções:
    - A faixa é definida só pelo ``volume_minimo`` (inclusive). A faixa de uma
      cotação vai do seu mínimo até o mínimo da próxima; a última é aberta.
    - ``validade_fim`` é o último dia de validade (inclusive); ``None`` = sem fim.
    - Preço e volume são ``Decimal``; nenhum valor é arredondado aqui.

Resolução (``resolver_cotacao``), nesta ordem:
    1. só entram cotações da MP vigentes na data (e do fornecedor, se informado);
    2. vence a faixa de maior ``volume_minimo`` que não passa da quantidade;
    3. na mesma faixa, desempata o início de validade mais recente;
    4. se ainda empatar (ex.: dois fornecedores), é ambiguidade e o chamador
       decide informando o fornecedor. Comparar preço exigiria câmbio (US13).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pricing_core.numeros import Numero, para_decimal


class CotacaoError(Exception):
    """Base dos erros de domínio da resolução de cotação."""


class CotacaoNaoEncontrada(CotacaoError, LookupError):
    """Não há cotação vigente aplicável à MP, data e quantidade informadas."""


class CotacaoAmbigua(CotacaoError):
    """Mais de uma cotação empata em faixa e validade; é preciso informar o fornecedor."""


@dataclass(frozen=True)
class Cotacao:
    """Cotação de uma matéria-prima por um fornecedor, para uma faixa de volume."""

    id: str
    materia_prima_id: str
    fornecedor_id: str
    moeda: str
    preco: Decimal
    volume_minimo: Decimal
    validade_inicio: date
    validade_fim: date | None = None
    prazo_entrega_dias: int = 0

    def __post_init__(self) -> None:
        # float é recusado de propósito: o critério de aceite do motor é divergência máxima de R$ 0,01.
        if not isinstance(self.preco, Decimal) or not isinstance(self.volume_minimo, Decimal):
            raise TypeError("preco e volume_minimo devem ser Decimal")
        if not (self.preco.is_finite() and self.volume_minimo.is_finite()):
            raise ValueError("preco e volume_minimo devem ser finitos")
        if self.preco < 0:
            raise ValueError(f"preco não pode ser negativo: {self.preco}")
        if self.volume_minimo < 0:
            raise ValueError(f"volume_minimo não pode ser negativo: {self.volume_minimo}")
        if len(self.moeda) != 3 or not self.moeda.isalpha() or not self.moeda.isupper():
            raise ValueError(f"moeda deve ser um código ISO de 3 letras maiúsculas: {self.moeda!r}")
        if self.prazo_entrega_dias < 0:
            raise ValueError(f"prazo_entrega_dias não pode ser negativo: {self.prazo_entrega_dias}")
        if self.validade_fim is not None and self.validade_fim < self.validade_inicio:
            raise ValueError("validade_fim não pode ser anterior a validade_inicio")


def esta_vigente(cotacao: Cotacao, data_referencia: date) -> bool:
    """Diz se a cotação vale na data. Início e fim são inclusivos."""
    if data_referencia < cotacao.validade_inicio:
        return False
    return cotacao.validade_fim is None or data_referencia <= cotacao.validade_fim


def cotacoes_vigentes(cotacoes: Iterable[Cotacao], materia_prima_id: str, data_referencia: date) -> list[Cotacao]:
    """Cotações da MP vigentes na data, da menor para a maior faixa.

    Dentro da mesma faixa, a de início de validade mais recente vem primeiro.
    A ordem espelha a função ``cotacoes_vigentes`` do banco.
    """
    candidatas = [
        cotacao
        for cotacao in cotacoes
        if cotacao.materia_prima_id == materia_prima_id and esta_vigente(cotacao, data_referencia)
    ]
    return sorted(candidatas, key=lambda c: (c.volume_minimo, -c.validade_inicio.toordinal(), c.id))


def resolver_cotacao(
    cotacoes: Iterable[Cotacao],
    materia_prima_id: str,
    quantidade: Numero,
    data_referencia: date,
    fornecedor_id: str | None = None,
) -> Cotacao:
    """Escolhe a cotação vigente que vale para a quantidade negociada.

    Levanta ``CotacaoNaoEncontrada`` quando nada vigente alcança a quantidade e
    ``CotacaoAmbigua`` quando duas ou mais empatam em faixa e validade.
    """
    qtd = para_decimal(quantidade, "quantidade")
    if qtd <= 0:
        raise ValueError(f"quantidade deve ser positiva: {qtd}")

    vigentes = cotacoes_vigentes(cotacoes, materia_prima_id, data_referencia)
    if fornecedor_id is not None:
        vigentes = [c for c in vigentes if c.fornecedor_id == fornecedor_id]
    if not vigentes:
        de_quem = " do fornecedor informado" if fornecedor_id is not None else ""
        raise CotacaoNaoEncontrada(
            f"Não há cotação vigente{de_quem} para a matéria-prima em {data_referencia:%d/%m/%Y}."
        )

    elegiveis = [c for c in vigentes if c.volume_minimo <= qtd]
    if not elegiveis:
        menor = min(c.volume_minimo for c in vigentes)
        raise CotacaoNaoEncontrada(f"A quantidade {qtd} está abaixo do volume mínimo da menor faixa vigente ({menor}).")

    faixa = max(c.volume_minimo for c in elegiveis)
    da_faixa = [c for c in elegiveis if c.volume_minimo == faixa]
    inicio = max(c.validade_inicio for c in da_faixa)
    finalistas = [c for c in da_faixa if c.validade_inicio == inicio]
    if len(finalistas) > 1:
        fornecedores = ", ".join(sorted(c.fornecedor_id for c in finalistas))
        raise CotacaoAmbigua(
            f"Há {len(finalistas)} cotações vigentes empatadas na faixa a partir de {faixa} e no início de "
            f"validade ({inicio:%d/%m/%Y}): fornecedores {fornecedores}. Informe o fornecedor."
        )
    return finalistas[0]
