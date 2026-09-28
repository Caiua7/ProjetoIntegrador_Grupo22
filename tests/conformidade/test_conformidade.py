"""Suíte de conformidade do motor de precificação (RNF08 / US22).

Compara a saída de `pricing_core.engine.calcular` contra os 30 casos
homologados com o PO. Critério de aceite (RNF08): divergência máxima de
R$ 0,01 por campo monetário.

Publicada na Sprint 1 sem casos reais, para já existir onde registrar o
resultado da homologação (Sprint 1/2). Fica com skip automático até:
  1. existir ao menos um caso além do template em ./casos/;
  2. `pricing_core.engine` existir (US16/US19 — Sprint 3). Até lá, o
     endpoint mock em apps/api/app/routers/calculate.py NÃO é o alvo
     desta suíte — ele existe só para o Squad B, e usa suposições ainda
     não homologadas.
"""

from decimal import Decimal
import json
from pathlib import Path

import pytest

CASOS_DIR = Path(__file__).parent / "casos"
TOLERANCIA = Decimal("0.01")


def _carregar_casos() -> list[dict]:
    casos = []
    for arquivo in sorted(CASOS_DIR.glob("caso_*.json")):
        if arquivo.stem.endswith("_template"):
            continue
        casos.append(json.loads(arquivo.read_text(encoding="utf-8")))
    return casos


CASOS = _carregar_casos()

try:
    from pricing_core.engine import calcular  # type: ignore

    MOTOR_DISPONIVEL = True
except ImportError:
    MOTOR_DISPONIVEL = False


pytestmark = pytest.mark.skipif(
    not CASOS,
    reason="nenhum caso homologado em tests/conformidade/casos/ ainda — copie caso_000_template.json",
)


@pytest.mark.skipif(
    not MOTOR_DISPONIVEL,
    reason="pricing_core.engine ainda não implementado (US16/US19 — Sprint 3)",
)
@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.get("id", "sem-id"))
def test_caso_homologado(caso: dict) -> None:
    from pricing_core.contracts import CalculateRequest

    entrada = CalculateRequest.model_validate(caso["entrada"])
    resultado = calcular(entrada)

    for campo, esperado in caso["saida_esperada"].items():
        obtido = getattr(resultado, campo)
        diferenca = abs(Decimal(str(obtido)) - Decimal(str(esperado)))
        assert diferenca <= TOLERANCIA, (
            f"caso {caso.get('id')}: campo '{campo}' esperado={esperado} "
            f"obtido={obtido} diferença={diferenca} > {TOLERANCIA}"
        )
