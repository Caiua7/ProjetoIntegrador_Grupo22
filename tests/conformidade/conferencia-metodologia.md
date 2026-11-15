# Conferência pela metodologia documentada (15/11/2026)

Não existe planilha de referência da área de Pricing. Para conferir o motor por um caminho independente, os 30 casos foram recalculados em **fórmulas de Excel** escritas a partir da cadeia documentada em `docs/PI6-planejamento-produto.md` (seção do motor), sem usar o código do motor:

- `conferencia-metodologia.xlsx`: aba *Cálculo* com uma linha por caso e cada etapa em uma coluna com fórmula visível (CustoMP, CustoEmb, MaterialCliente, CustoPerda, MOD, GGF, CustoTotal, D, encargo, isenção, PBsIPIsEncargo, PBsIPI, PBcIPI, PB, ICMS-ST, ROL, Comissão$, MaCo$); aba *Insumos* com o custo de cada item.
- `conferencia_metodologia.py`: gera a planilha, avalia as fórmulas com a biblioteca `formulas` (motor de cálculo de Excel em Python) e compara com `pricing_core.engine.calcular`.

## Resultado

| Situação | Casos |
| --- | --- |
| Confere (diferença ≤ R$ 0,01 em PBsIPIsEncargo, PBsIPI, PB, ROL, MaCo, custo total e ICMS-ST) | 28 (001–028), todos com diferença de R$ 0,00 |
| Erro de domínio nos dois (denominador ≤ 0) | 2 (029 e 030) |
| Divergente | 0 |

**Conclusão:** o motor implementa fielmente a metodologia documentada. Isto é uma **conferência interna**, não a homologação do PO: ela prova que o código segue as fórmulas acordadas, não que as fórmulas e as premissas abertas estão certas para o negócio.

## Para fechar com o PO (validação por amostra)

Mostrar a aba *Cálculo* nos casos 001, 008, 013, 015, 017, 020 e 022 e decidir:

1. **Material do cliente:** pela metodologia, a MaCo$ desconta o custo total de MP, inclusive a do cliente, enquanto o preço já exclui esse material. Resultado: margem negativa nos casos 013–018 e 022–024 (ex.: caso 013, MaCo$ = −R$ 18,96). Provável ajuste: descontar `MaterialCliente` também na MaCo$.
2. **Base da margem** (`m × Base`): hoje `Base = CustoTotal`.
3. **Comissão$:** hoje `Comissão × PB`.
4. **Embalagem:** entra no custo só pelo descarte (`preço × quantidade × % descarte`).
5. **PBsIPIsEncargo maior que PBsIPI:** como as duas fórmulas usam denominadores diferentes, o preço "antes do encargo" sai maior que o preço com encargo (ex.: caso 001, R$ 77,66 contra R$ 71,19). Confirmar se é o esperado.

Com o ok do PO (no termo de aceite ou em comentário no #56), os valores da aba *Cálculo* viram a `saida_esperada` dos casos e a suíte passa a 30 de 30.
