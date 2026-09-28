"""Regenera apps/web/src/types/calculate.generated.ts a partir de
packages/pricing-core/pricing_core/contracts.py.

Dependências (não incluídas no monorepo ainda — instalar ao rodar):
    pip install pydantic-to-typescript
    npm install -g json-schema-to-typescript

Uso:
    python scripts/generate_ts_types.py

Rode este script sempre que contracts.py mudar. O arquivo .ts gerado tem
um header "NÃO EDITAR À MÃO" — se você editar o .ts direto, a próxima
rodada do script sobrescreve sem aviso.
"""

from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "packages" / "pricing-core"))


def main() -> None:
    from pydantic2ts import generate_typescript_defs  # type: ignore

    saida = RAIZ / "apps" / "web" / "src" / "types" / "calculate.generated.ts"
    saida.parent.mkdir(parents=True, exist_ok=True)
    generate_typescript_defs("pricing_core.contracts", str(saida))
    print(f"Tipos TypeScript gerados em {saida}")


if __name__ == "__main__":
    main()
