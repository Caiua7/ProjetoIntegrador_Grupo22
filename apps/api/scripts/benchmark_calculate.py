"""Microbenchmark do motor puro usando um caso oficial de conformidade.

Executar no ambiente Python já configurado para a API:
    python apps/api/scripts/benchmark_calculate.py --iterations 1000
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "pricing-core" / "src"))

from pricing_core.contracts import CalculateRequest  # noqa: E402
from pricing_core.engine import calcular  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations precisa ser maior que zero")

    case_path = ROOT / "tests" / "conformidade" / "casos" / "caso_000_template.json"
    entrada_json = json.loads(case_path.read_text(encoding="utf-8"))["entrada"]
    entrada = CalculateRequest.model_validate(entrada_json)

    # Aquecimento não entra na distribuição; nenhuma API/rede/banco participa.
    for _ in range(min(100, args.iterations)):
        calcular(entrada)
    duracoes_ms: list[float] = []
    for _ in range(args.iterations):
        inicio = time.perf_counter_ns()
        calcular(entrada)
        duracoes_ms.append((time.perf_counter_ns() - inicio) / 1_000_000)

    ordenadas = sorted(duracoes_ms)

    def percentil(valor: float) -> float:
        indice = round((len(ordenadas) - 1) * valor)
        return ordenadas[indice]

    print(f"case={case_path.relative_to(ROOT)}")
    print(f"iterations={args.iterations} python={platform.python_version()} platform={platform.platform()}")
    print(
        "latency_ms "
        f"min={min(duracoes_ms):.4f} mean={statistics.fmean(duracoes_ms):.4f} "
        f"p50={percentil(0.50):.4f} p95={percentil(0.95):.4f} p99={percentil(0.99):.4f} "
        f"max={max(duracoes_ms):.4f}"
    )


if __name__ == "__main__":
    main()
