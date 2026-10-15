"""Conferência dos casos homologados contra a saída do motor (RNF08, US22).

Separado do teste para que a mesma regra de comparação sirva ao pytest e ao
relatório de divergência que o CI publica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
import json
from pathlib import Path
from typing import Any

PENDENTE = "PREENCHER_COM_PO"
TOTAL_DE_CASOS = 30

# Critério de aceite do RNF08: divergência máxima de R$ 0,01 por campo
# monetário. Campos que são fração (taxa, denominador, margem percentual)
# não têm centavo; para eles vale uma casa a mais que a de 0,01%.
TOLERANCIA_MONETARIA = Decimal("0.01")
TOLERANCIA_FRACAO = Decimal("0.000001")
CAMPOS_FRACAO = frozenset(
    {
        "denominador",
        "encargo_financeiro_percentual",
        "margem_contribuicao_percentual",
    }
)


@dataclass(frozen=True)
class Caso:
    id: str
    arquivo: Path
    entrada: dict[str, Any]
    saida_esperada: dict[str, Any]
    erro_esperado: str | None = None
    descricao: str = ""

    @property
    def campos_pendentes(self) -> list[str]:
        return [campo for campo, valor in self.saida_esperada.items() if valor == PENDENTE]


@dataclass(frozen=True)
class Conferencia:
    campo: str
    esperado: Decimal
    obtido: Decimal

    @property
    def tolerancia(self) -> Decimal:
        return TOLERANCIA_FRACAO if self.campo.rsplit(".", 1)[-1] in CAMPOS_FRACAO else TOLERANCIA_MONETARIA

    @property
    def diferenca(self) -> Decimal:
        return abs(self.obtido - self.esperado)

    @property
    def ok(self) -> bool:
        return self.diferenca <= self.tolerancia


def carregar_casos(pasta: Path, incluir_template: bool = False) -> list[Caso]:
    casos = []
    for arquivo in sorted(pasta.glob("caso_*.json")):
        if arquivo.stem.endswith("_template") and not incluir_template:
            continue
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        casos.append(
            Caso(
                id=dados.get("id", arquivo.stem),
                arquivo=arquivo,
                entrada=dados["entrada"],
                saida_esperada=dados.get("saida_esperada", {}),
                erro_esperado=dados.get("erro_esperado"),
                descricao=dados.get("descricao", ""),
            )
        )
    return casos


def valor_do_campo(resultado: Any, campo: str) -> Any:
    """Lê um campo da resposta; aceita caminho com ponto, como
    ``impostos_destacados.icms_st_valor``."""
    valor = resultado
    for parte in campo.split("."):
        valor = getattr(valor, parte)
    return valor


def para_decimal(valor: Any) -> Decimal:
    if isinstance(valor, float):
        raise TypeError("use string no JSON do caso, não número: float perde precisão")
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        raise ValueError(f"não é um número: {valor!r}") from None


def conferir(caso: Caso, resultado: Any) -> list[Conferencia]:
    return [
        Conferencia(campo, para_decimal(esperado), para_decimal(valor_do_campo(resultado, campo)))
        for campo, esperado in caso.saida_esperada.items()
    ]


class Situacao(str, Enum):
    CONFORME = "conforme"
    DIVERGENTE = "divergente"
    ERRO = "erro"
    PENDENTE = "pendente com o PO"
    SEM_MOTOR = "motor indisponível"


@dataclass
class Relatorio:
    """Resultado por caso, para o resumo do CI."""

    versao_motor: str | None = None
    linhas: list[tuple[Caso, Situacao, list[Conferencia], str]] = field(default_factory=list)

    def registrar(self, caso: Caso, situacao: Situacao, conferencias: list[Conferencia] = (), detalhe: str = "") -> None:
        self.linhas.append((caso, situacao, list(conferencias), detalhe))

    def markdown(self) -> str:
        contagem = {s: sum(1 for _, situacao, _, _ in self.linhas if situacao is s) for s in Situacao}
        saida = [
            "# Conformidade do motor (RNF08)",
            "",
            f"Motor: `{self.versao_motor}`" if self.versao_motor else "Motor: `pricing_core.engine` ainda não existe",
            "",
            f"Casos homologados no repositório: **{len(self.linhas)} de {TOTAL_DE_CASOS}**. "
            f"Conformes: **{contagem[Situacao.CONFORME]}**. "
            f"Divergentes: **{contagem[Situacao.DIVERGENTE]}**. "
            f"Com erro: **{contagem[Situacao.ERRO]}**. "
            f"Pendentes com o PO: **{contagem[Situacao.PENDENTE]}**.",
            "",
            f"Tolerância: R$ {TOLERANCIA_MONETARIA} por campo monetário e {TOLERANCIA_FRACAO} nas frações.",
            "",
        ]
        if not self.linhas:
            return "\n".join(saida + ["Nenhum caso em `tests/conformidade/casos/` além do template."]) + "\n"

        saida += ["| Caso | Situação | Campos | Maior diferença | Detalhe |", "| :--- | :--- | ---: | ---: | :--- |"]
        for caso, situacao, conferencias, detalhe in self.linhas:
            maior = max((c.diferenca for c in conferencias), default=None)
            saida.append(
                f"| {caso.id} | {situacao.value} | {len(conferencias)} | "
                f"{'' if maior is None else maior} | {detalhe} |"
            )

        divergencias = [(caso, c) for caso, _, conferencias, _ in self.linhas for c in conferencias if not c.ok]
        if divergencias:
            saida += [
                "",
                "## Divergências",
                "",
                "| Caso | Campo | Esperado | Obtido | Diferença | Tolerância |",
                "| :--- | :--- | ---: | ---: | ---: | ---: |",
            ]
            saida += [
                f"| {caso.id} | `{c.campo}` | {c.esperado} | {c.obtido} | {c.diferenca} | {c.tolerancia} |"
                for caso, c in divergencias
            ]
        return "\n".join(saida) + "\n"
