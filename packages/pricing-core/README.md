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
| `preco_liquido_mp` | Preço líquido de MP: desconta ICMS, PIS e COFINS recuperáveis do preço de aquisição | #53 |
| `rentabilidade` | ROB, deduções, ROL, MaCo e margem bruta em reais pelo volume negociado do cenário | #64 |
| `numeros` | Conversão para `Decimal` e precisão comuns aos módulos | — |


## Motor de precificação

O ponto de entrada do motor puro é `pricing_core.engine.calcular`:

```python
from pricing_core.engine import calcular
from pricing_core.contracts import CalculateRequest

entrada = CalculateRequest.model_validate(payload)
resultado = calcular(entrada)
```

O motor não acessa banco, rede ou framework web. Recebe um `CalculateRequest`,
não altera a entrada e devolve um `CalculateResponse`. Valores intermediários
são calculados com `Decimal` e precisão explícita; campos monetários da saída
são arredondados para centavos.

Erros matemáticos de domínio são representados por
`ErroDominioPricing`, cujo atributo `codigo` pode ser comparado com
`DomainErrorCodigo`. A API é responsável por traduzir esse erro para HTTP 422.

**Premissas provisórias a confirmar com o PO antes da homologação:**
- `Base = CustoTotal`;
- `Comissao$ = Comissao × PB`;
- `MaterialCliente = CustoEnviadoCliente = valor_material_cliente`.

Essas premissas estão sinalizadas com `TODO(PO)` em `engine.py`. Os resultados
não devem ser considerados homologados até a confirmação do PO e a execução
dos 30 casos oficiais de conformidade.
