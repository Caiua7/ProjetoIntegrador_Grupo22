# Roteiro de validação no staging (PO)

Para o PO aceitar de uma vez o que está pronto. Cada bloco diz o que fazer e o que deve acontecer; marque o que passou e anote o que não passou no próprio item da issue.

- **Endereço:** https://neoprice.vercel.app (API em `https://neoprice-api-staging.onrender.com`)
- **Acessos:** a equipe entrega dois usuários de homologação, um **Analista de Pricing** e um **Gerente Comercial**. As senhas não ficam neste repositório.
- **Primeiro acesso do dia:** a API está no plano gratuito e desliga sem uso; o primeiro carregamento pode levar alguns segundos.
- **Dados:** o staging tem 7 produtos com formulação, cotações vigentes de novembro e dezembro de 2026, câmbio de USD e EUR, parâmetros globais e alíquotas por UF.

## 1. Cadastros e parâmetros (#48, #49, #50, #47)

Com o Analista de Pricing:

- [ ] **Matérias-primas e embalagens:** a lista abre, o filtro por tipo funciona e "Visualizar" mostra o detalhe na hora.
- [ ] **Cotações:** as cotações vigentes aparecem por matéria-prima, com fornecedor, moeda, preço e validade.
- [ ] **Câmbio e parâmetros:** USD e EUR aparecem como **Vigente**; perda, taxa financeira e prazo médio têm valor vigente.
- [ ] **Tributos:** as alíquotas aparecem em porcentagem legível (ex.: 7,6% de COFINS), por UF, NCM e regime.

## 2. Formulação (#62)

- [ ] Em **Formulações**, escolher um produto (ex.: BCAA 2:1:1 — 250 g): a composição aparece com quantidades, unidade e origem do material.
- [ ] Adicionar e remover um item e salvar: aparece "Formulação salva." e o painel de rentabilidade é atualizado.

## 3. Cálculo com o motor real (#59, #60, #61)

Em **Precificações**, botão **Cenários** de uma precificação em preenchimento ou reprovada (ex.: PRC-2026-0145):

- [ ] Informar o volume (ex.: 1000) e clicar em **Calcular cenário**. O sistema reúne formulação, cotações, câmbio, parâmetros e alíquota em poucos segundos e lista só o que falta digitar.
- [ ] Preencher **Dados do cenário** (MOD, GGF, produtividade, funcionários, margem, comissão, frete e preço/descarte das embalagens) e calcular de novo: aparece o resultado com preço bruto, preço sem IPI, ROL, custos, margem de contribuição e impostos destacados.
- [ ] **Conferir o resultado com a planilha da área** para o mesmo caso. Divergência aceita: até R$ 0,01 (RNF08).
- [ ] **Isenção de mão de obra (#60):** com material fornecido pelo cliente e destino SP, o resultado mostra a isenção aplicada e o preço cai exatamente o custo de MOD; com destino fora de SP, ou material do fabricante, não há isenção.
- [ ] **ICMS-ST (#61):** com MVA ou FCP preenchidos para o destino, o ICMS-ST aparece entre os impostos destacados.

## 4. Versões do cenário (#63, #64)

- [ ] **Salvar como nova versão:** a versão aparece em "Versões salvas" como **Vigente**, com volume, preços e custo total.
- [ ] **Detalhes** mostra a entrada usada e o resultado; **Duplicar** cria uma versão nova a partir dela.
- [ ] Com duas versões, a comparação mostra o que subiu, desceu ou ficou igual.
- [ ] Receita bruta, margem de contribuição absoluta e margem bruta acompanham o volume negociado.

## 5. Submissão e aprovação (#66, #68)

- [ ] **Submeter** (Analista): o sistema confere os campos obrigatórios e se há um cenário calculado salvo; ao confirmar, o status vira **Em aprovação**.
- [ ] **Decidir** (Gerente Comercial): aprovar sem comentário e reprovar com comentário obrigatório; o status muda e a decisão aparece no **Histórico**.
- [ ] O analista não consegue editar uma precificação em aprovação.

> Enquanto a política de aprovação estiver marcada como demonstrativa, as submissões ficam com **homologação pendente** e só podem ser reprovadas. A troca para a política homologada depende do aceite deste roteiro.

## 6. Acesso por perfil (#45)

- [ ] O Gerente Comercial vê custos e margens; a Executiva de Contas (se houver usuário) vê preços, mas não custos.
- [ ] Um usuário só enxerga as precificações da própria carteira.

## Pendências conhecidas, fora deste aceite

- **Suíte de conformidade com os 30 casos homologados (#56):** depende da sessão de homologação com o PO; a estrutura e os testes já rodam no pipeline.
- **Fila de aprovação do gerente (#67) e exportação para BI (#69):** em desenvolvimento na S5.
- **Embalagem no custo:** o motor considera da embalagem só o descarte (preço × % de descarte). Confirmar com o PO se é a regra esperada.
