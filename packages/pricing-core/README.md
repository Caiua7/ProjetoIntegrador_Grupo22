# pricing-core

Regras puras do motor de preço do NeoPrice. Não depende de banco, rede nem framework web. Recebe valores, devolve valores. Todo valor monetário e percentual é `Decimal`, porque o critério de aceite do motor é divergência máxima de R$ 0,01.

## Rodando os testes

```bash
cd packages/pricing-core
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -e ".[dev]"
pytest
```

## Módulos

| Módulo | O que faz | Issue |
| :--- | :--- | :--- |
| `encargo` | Encargo financeiro pelo prazo médio: `(1 + Taxa)^(PrazoMedio/30) − 1` | #52 |
