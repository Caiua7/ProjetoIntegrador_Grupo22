# Homologação dos 30 casos (Sprint 1, semana 2)

Esta pasta é o oráculo do motor (RNF08, US22): cada `caso_NNN.json`
representa um cenário real que o PO confere à mão (ou já tem em planilha)
e cujo resultado o motor precisa reproduzir com divergência máxima de
R$ 0,01.

**Importante**: os números da sessão saem do PO, não deste repositório.
Este README e o template servem só para a sessão ser rápida e o resultado
já nascer em formato consumível pelo `test_conformidade.py`.

## Como rodar a sessão

1. Para cada caso, copie `casos/caso_000_template.json` para
   `casos/caso_NNN.json` (`001`, `002`, ...).
2. Preencha `entrada` com os dados do cenário real (produto, insumos,
   alíquotas, margem etc.).
3. Peça ao PO o resultado esperado para os campos em `saida_esperada`
   (todos hoje com o placeholder `"PREENCHER_COM_PO"`).
4. Registre em `observacoes` qualquer decisão que o caso ajudou a fechar
   — em especial as três suposições abertas em `contracts.py`:
   - o que é `Base` em `m × Base`;
   - como `Comissao$` é calculado;
   - se `MaterialCliente` e `CustoEnviadoCliente` são sempre o mesmo valor.

## Cobertura mínima sugerida para os 30 casos

Para os 30 casos realmente funcionarem como oráculo (e não só repetirem o
caso feliz), cubra pelo menos:

- [ ] Caso simples, Full Service Nacional, sem ICMS-ST (`ICMSInt = FCP = MVA = 0`)
- [ ] Caso com ICMS-ST (`MVA` e `FCP` diferentes de zero)
- [ ] Caso com material fornecido pelo cliente e UF de destino = SP (isenção de MDO)
- [ ] Caso com material fornecido pelo cliente e UF ≠ SP (isenção **não** se aplica)
- [ ] Caso com `PrazoMedio > 0` (encargo financeiro relevante no preço)
- [ ] Caso de exportação (Full Service Exportação)
- [ ] Caso de Industrialização por Encomenda
- [ ] Ao menos um caso desenhado para **falhar de propósito** (margem e
      impostos que zerem ou neguem o denominador `D`), para validar que a
      API responde com `DomainErrorResponse` (422) e não uma exceção crua

## Depois da sessão

- Rode `pytest tests/conformidade/` — os testes ficam com skip até
  `pricing_core.engine` existir (Sprint 3), mas já validam que os JSONs
  estão bem formados.
- Assim que `pricing_core.engine.calcular` existir, a suíte passa a
  comparar de verdade — nenhuma mudança neste arquivo é esperada.
