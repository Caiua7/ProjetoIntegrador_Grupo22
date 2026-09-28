"""Exporta o schema OpenAPI atual para docs/openapi/calculate.json, para
que o PR de qualquer mudança de contrato mostre o diff do schema.

Uso:
    python scripts/export_openapi.py
"""

import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "apps" / "api"))
sys.path.insert(0, str(RAIZ / "packages" / "pricing-core" / "src"))


def main() -> None:
    from app.main import app  # noqa: E402

    saida = RAIZ / "docs" / "openapi" / "calculate.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OpenAPI exportado para {saida}")


if __name__ == "__main__":
    main()
