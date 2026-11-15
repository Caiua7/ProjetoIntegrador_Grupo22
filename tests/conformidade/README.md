# Homologação dos 30 casos (Sprint 1, semana 2)

> **Situação em 15/11/2026:** os 30 casos (`casos/caso_001.json` a `caso_030.json`) estão montados
> com dados reais do staging (formulações, cotações, câmbio, alíquotas e parâmetros) e a suíte passa
> **30 de 30** no CI. Como a área de Pricing não tem planilha de referência, a `saida_esperada` dos 28
> casos de cálculo vem da conferência pela metodologia documentada (`conferencia-metodologia.xlsx`,
> fórmulas de Excel escritas a partir do PI6, sem usar o motor); os 2 casos de erro esperam
> `DENOMINADOR_INVALIDO`. Ver `conferencia-metodologia.md`.
>
> **Falta o PO:** validar por amostra (casos 001, 008, 013, 015, 017, 020 e 022) e decidir os 5 pontos
> de `conferencia-metodologia.md`. Se ele mudar alguma premissa, ajuste a fórmula da coluna em
> `conferencia_metodologia.py` e o motor, e regrave os valores:
>
> ```bash
> pip install openpyxl formulas
> python tests/conformidade/conferencia_metodologia.py tests/conformidade/casos tests/conformidade/conferencia-metodologia.xlsx --gravar
> pytest tests/conformidade --relatorio-conformidade=relatorio-conformidade.md
> ```
>
> Se o PO trouxer valores próprios, preencha `homologacao-30-casos.xlsx` (aba *Resultados*, já com os
> valores atuais) e rode `python tests/conformidade/planilha.py importar homologacao-30-casos.xlsx`.
> Mudou algum caso? Gere a planilha de novo com `python tests/conformidade/planilha.py exportar homologacao-30-casos.xlsx`.
> Produção (MOD, GGF, produtividade, funcionários) e preço de embalagem ainda não têm cadastro e usam
> valores fixos plausíveis; o PO pode trocá-los na própria planilha, anotando em *Observações*.

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

- [x] Caso simples, Full Service Nacional, sem ICMS-ST (`ICMSInt = FCP = MVA = 0`)
- [x] Caso com ICMS-ST (`MVA` e `FCP` diferentes de zero)
- [x] Caso com material fornecido pelo cliente e UF de destino = SP (isenção de MDO)
- [x] Caso com material fornecido pelo cliente e UF ≠ SP (isenção **não** se aplica)
- [x] Caso com `PrazoMedio > 0` (encargo financeiro relevante no preço)
- [x] Caso de exportação (Full Service Exportação)
- [x] Caso de Industrialização por Encomenda
- [x] Ao menos um caso desenhado para **falhar de propósito** (margem e
      impostos que zerem ou neguem o denominador `D`), para validar que a
      API responde com `DomainErrorResponse` (422) e não uma exceção crua

## Formato do caso

- `id`: igual ao nome do arquivo (`caso_007`).
- `entrada`: payload de `CalculateRequest`, validado contra o contrato.
- `saida_esperada`: campos de `CalculateResponse` com o valor do PO, sempre
  como **string** (`"1749.93"`, nunca `1749.93`: número no JSON vira float e
  perde precisão). Campo aninhado vai com ponto:
  `"impostos_destacados.icms_st_valor"`. Enquanto o PO não der o valor,
  deixe `"PREENCHER_COM_PO"`: o caso fica como pendente e não falha.
- `erro_esperado` (só no caso desenhado para falhar): o código de
  `DomainErrorCodigo`, por exemplo `"DENOMINADOR_INVALIDO"`, e
  `saida_esperada` vazio. A suíte espera que `calcular` levante uma exceção
  com atributo `codigo` igual a ele.

Tolerância: R$ 0,01 nos campos monetários e 0,000001 nas frações
(`denominador`, `encargo_financeiro_percentual`,
`margem_contribuicao_percentual`). Ver `conferencia.py`.

## Rodando

```bash
pip install -e "packages/pricing-core[dev]"
pytest tests/conformidade --relatorio-conformidade=relatorio-conformidade.md
```

- `test_caso_bem_formado` valida todo JSON contra o contrato desde já: um
  caso mal preenchido falha agora, e não só quando o motor chegar.
- `test_caso_homologado` compara de verdade assim que
  `pricing_core.engine.calcular(entrada: CalculateRequest) -> CalculateResponse`
  existir (US16/US19). Até lá fica com skip.
- O relatório traz a situação de cada caso (conforme, divergente, erro,
  pendente com o PO) e a tabela de divergências por campo.

## No CI

O workflow `.github/workflows/conformidade.yml` roda os testes do
`pricing-core` e esta suíte em todo PR que mexe no motor ou nos casos, e
publica o relatório no resumo do job e como artefato
(`relatorio-conformidade`). A S3 só fecha com os 30 casos conformes.
