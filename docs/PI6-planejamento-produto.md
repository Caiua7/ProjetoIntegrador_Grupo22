# NeoPrice \- Planejamento de Produto (PI VI)

Documento base para `Documentação\Time X.docx`.

**Visão de produto**

> Plataforma web multiusuário de precificação industrial B2B, que integra cotação de insumos, motor de cálculo fiscal, versionamento de cenários e governança de aprovação, permitindo formar preço com rentabilidade absoluta visível por volume negociado.

**Contexto de domínio**: indústria de bens de consumo de transformação (alimentos, suplementos, cosméticos e químico leve), operando em três modalidades comerciais (Full Service Nacional, Full Service Exportação e Industrialização por Encomenda), com incidência de PIS, COFINS, ICMS, IPI e substituição tributária.

**Beachhead de validação**: o MVP é validado no segmento de suplementos e nutrição esportiva, por acesso a dados reais e disponibilidade de PO para homologação. O modelo de custo e o motor fiscal não contêm nenhuma regra específica de setor: alíquota, MVA e NCM são dados de configuração, não código.

**Proposta de valor**: o mercado de precificação industrial opera hoje majoritariamente em planilhas isoladas, sem trilha de auditoria, sem histórico de cenário e sem visão de margem absoluta. O NeoPrice ataca os três pontos ao mesmo tempo.

**Stack alvo**: React \+ TypeScript (Vite) · FastAPI (Python 3.12) · Supabase (Postgres \+ Auth \+ RLS \+ Storage) · Vercel (front) \+ Render (API) · Pytest \+ Vitest · GitHub Actions.

---

## 1\. Personas

### Resumo

| \# | Persona | Papel | Frequência de uso | Necessidade central |
| :---- | :---- | :---- | :---- | :---- |
| P1 | Rafael Costa | Analista de Pricing | Diária (usuário core) | Formar preço com margem garantida |
| P2 | Juliana Marques | Executiva de Contas | Semanal | Negociar com preço válido e formalizar proposta |
| P3 | Marcos Tavares | Gerente Comercial | Semanal | Aprovar exceções e proteger a margem |
| P4 | Camila Reis | Analista de Suprimentos | Diária | Manter custo de insumo confiável |
| P5 | Diego Almeida | Administrador / TI | Eventual | Governar acessos e integridade dos dados |

---

### P1 \- Rafael Costa, Analista de Pricing (persona primária)

- **Perfil**: 29 anos, Engenharia de Produção, 4 anos na indústria de nutrição esportiva. Excel avançado, SQL básico, nenhuma programação.  
- **Objetivos**: simular o preço de um SKU em minutos, comparar as três modalidades comerciais, garantir margem mínima e responder o time comercial no mesmo dia.  
- **Dores**:  
  - Cálculo disperso em arquivos locais, cada analista com a própria versão da fórmula.  
  - Cenários da mesma negociação não ficam registrados, então é impossível reconstruir a decisão depois.  
  - Sem volume associado ao preço, enxerga apenas margem percentual e não sabe quanto a operação gera em reais.  
- **Cenário de uso**: recebe pedido de preço para WPC pote 600 g, cliente de grande porte, frete CIF, destino SP. Cria a simulação, o sistema resolve a cotação pela faixa de volume, ele ajusta a margem e submete o cenário.  
- **Origina**: RF04, RF05, RF06, RF07, RF13, RF16.

### P2 \- Juliana Marques, Executiva de Contas

- **Perfil**: 34 anos, novos negócios B2B, trabalha em campo, usa tablet e celular.  
- **Objetivos**: obter preço válido para negociar, conhecer o piso de desconto e enviar proposta formal ao cliente.  
- **Dores**: não sabe se o preço em mãos ainda está vigente; a proposta sai como arquivo solto, sem numeração nem validade, e vira problema quando o cliente reabre a negociação meses depois.  
- **Cenário de uso**: acompanha o status da precificação, solicita revisão com justificativa comercial e baixa a proposta em PDF com número e data de validade.  
- **Origina**: RF08, RF17, RF18, RNF03.

### P3 \- Marcos Tavares, Gerente Comercial

- **Perfil**: 41 anos, responde por margem e receita da unidade. Olha exceção, não rotina.  
- **Objetivos**: aprovar ou reprovar preços fora da política, enxergar impacto em reais e não só em percentual, auditar quem alterou o quê.  
- **Dores**: aprovação informal por mensagem e e-mail, sem trilha; a política de margem é uma tabela fixa, sem ancoragem em volume ou em histórico do cliente.  
- **Cenário de uso**: abre a fila de aprovação, compara o cenário proposto com o anterior e com o histórico do cliente, aprova com comentário registrado.  
- **Origina**: RF10, RF11, RF19, RF20, RNF05.

### P4 \- Camila Reis, Analista de Suprimentos

- **Perfil**: 26 anos, mantém a base de matéria-prima, câmbio e fornecedores.  
- **Objetivos**: manter cotações atualizadas por faixa de volume e garantir que o pricing consuma o custo correto.  
- **Dores**: atualização manual sem validação de desvio; um erro de digitação vira preço errado sem nenhum alerta no caminho.  
- **Cenário de uso**: importa a planilha de cotações do período, o sistema sinaliza itens com desvio acima do parâmetro configurado e ela valida antes de publicar.  
- **Origina**: RF03, RF12, RF14, RF21.

### P5 \- Diego Almeida, Administrador / TI

- **Perfil**: 38 anos, analista de sistemas, responsável por acessos e integridade dos dados.  
- **Objetivos**: administrar usuários, perfis e cadastros sem depender de desenvolvimento.  
- **Dores**: regras de acesso embutidas em código, mudança de campo exigindo intervenção técnica, nenhuma visibilidade de quem acessa qual cliente.  
- **Cenário de uso**: cria um perfil novo, concede acesso restrito a uma carteira de clientes e ajusta metadados de um cadastro pela própria interface.  
- **Origina**: RF02, RF22, RF23, RNF02, RNF06.

---

## 2\. Requisitos

### 2.1 Requisitos Funcionais

| ID | Requisito | Persona | Prioridade |
| :---- | :---- | :---- | :---- |
| RF01 | Autenticar usuário via e-mail corporativo com sessão e refresh token | Todas | Must |
| RF02 | Controlar acesso por funcionalidade e por carteira de clientes | P5 | Must |
| RF03 | Manter cadastros base: MP, embalagem, produto, cliente, fornecedor, NCM, CEP/IBGE, produtividade | P4, P5 | Must |
| RF04 | Criar precificação informando cliente, produto, modalidade comercial, UF, frete e regime tributário | P1 | Must |
| RF05 | Compor formulação com MPs, quantidades, percentual de descarte e origem do material (cliente ou fabricante) | P1 | Must |
| RF06 | Calcular custo total (MP, embalagem, perda, MOD, GGF) e encargo financeiro pelo prazo médio de pagamento | P1 | Must |
| RF07 | Calcular preço bruto, preço sem IPI, ROL, MaCo e impostos destacados conforme o modelo fiscal especificado | P1 | Must |
| RF08 | Persistir o volume negociado e derivar ROB, MaCo absoluta e MB por cenário | P2, P3 | Must |
| RF09 | Versionar a precificação mantendo histórico imutável de cada cenário | P1, P3 | Must |
| RF10 | Controlar o ciclo de status: Em Preenchimento → Em Aprovação → Aprovado / Reprovado | P3 | Must |
| RF11 | Registrar a aprovação com responsável, data e comentário | P3 | Must |
| RF12 | Resolver automaticamente a cotação vigente de cada MP respeitando a faixa de volume mínimo | P1, P4 | Must |
| RF13 | Calcular o preço líquido de MP descontando os impostos recuperáveis na aquisição (ICMS, PIS e COFINS) | P1 | Must |
| RF14 | Importar cotações e câmbio por planilha com validação de desvio percentual configurável | P4 | Should |
| RF15 | Aplicar isenção de mão de obra quando houver material fornecido pelo cliente e a UF de destino for SP | P1 | Must |
| RF16 | Modo inverso: informar preço-alvo e obter a margem resultante, ou informar meta de custo de MP e obter o preço | P1 | Should |
| RF17 | Gerar proposta comercial em PDF com numeração sequencial, data de emissão e validade | P2 | Must |
| RF18 | Consultar status e histórico de precificações por cliente | P2 | Should |
| RF19 | Comparar cenários de uma mesma precificação com destaque de variação | P3 | Should |
| RF20 | Analisar break-even: volume mínimo e tolerância de variação de preço | P3 | Could |
| RF21 | Simular sensibilidade da margem a variações de câmbio e de custo de MP | P4 | Could |
| RF22 | Administrar usuários, perfis e funcionalidades pela interface | P5 | Should |
| RF23 | Configurar metadados de cadastro (campos, tipos e validações) sem necessidade de deploy | P5 | Could |
| RF24 | Exportar dados de precificação em CSV e XLSX para consumo em ferramentas de BI | P1, P3 | Should |

### 2.2 Requisitos Não Funcionais

| ID | Categoria | Requisito | Métrica de aceite |
| :---- | :---- | :---- | :---- |
| RNF01 | Performance | Cálculo completo de um cenário | p95 abaixo de 800 ms |
| RNF02 | Segurança | RLS no Postgres por perfil e carteira de clientes; toda query parametrizada | Zero query montada por concatenação; teste de injeção no pipeline |
| RNF03 | Usabilidade | Interface responsiva em desktop e tablet | Fluxo de consulta navegável em viewport de 768 px |
| RNF04 | Confiabilidade | Motor de cálculo implementado como serviço puro, sem dependência de planilha ou estado externo | Cobertura de testes do módulo `pricing_engine` igual ou superior a 90% |
| RNF05 | Auditabilidade | Log imutável de toda criação, alteração e exclusão, com usuário, timestamp e diff | 100% das mutações registradas |
| RNF06 | Manutenibilidade | Schema versionado por migrations; código tipado com TypeScript strict e Pydantic | Pipeline bloqueia merge sem type check |
| RNF07 | Portabilidade | Deploy automatizado a cada merge na branch principal | Pipeline verde em menos de 6 min |
| RNF08 | Corretude fiscal | Resultado do motor conforme a especificação homologada com o PO | 30 casos de teste com divergência máxima de R$ 0,01 |
| RNF09 | LGPD | Dados de cliente e de custo restritos por perfil, sem coleta de PII desnecessária | Matriz de acesso revisada e documentada |

### 2.3 Modelo de cálculo (especificação de domínio)

O motor implementa a seguinte cadeia, homologada com a área de Pricing:

Denominador  
D \= 1 − \[Comissao \+ Frete \+ m×(1−\[PIS(1−ICMS)+COFINS(1−ICMS)+ICMS\])  
         \+ PIS(1−ICMS) \+ COFINS(1−ICMS) \+ ICMS\]

Composição de custo  
CustoMP    \= Σ (PrecoNeg × Cambio × (1+MgSeg)) × Qtd  
CustoEmb   \= Σ (PrecoNeg × Cambio × (1+MgSeg)) × Qtd × Descarte  
CustoPerda \= (CustoMP \+ CustoEmb − MaterialCliente) × Perda  
CustoMOD   \= (TaxaMOD / Produtividade) × NumFunc  
CustoGGF   \= TaxaGGF / Produtividade  
Encargo    \= (1 \+ Taxa)^(PrazoMedio/30) − 1

Formação de preço  
PBsIPIsEncargo \= CustoTotal/D − CustoEnviadoCliente − IsencaoMDO  
PBsIPI  \= (m×Base \+ CustoTotal \+ Encargo×PBsIPIsEncargo)  
          / (1 − \[PIS(1−ICMS)+COFINS(1−ICMS)+ICMS+Comissao+Frete\])  
          − CustoEnviadoCliente − IsencaoMDO  
PBcIPI  \= PBsIPI × (1+IPI)  
PB      \= PBcIPI, se ICMSInt \= 0 e FCP \= 0 e MVA \= 0  
          senão PBcIPI \+ \[(PBcIPI×(1+MVA))×(ICMSInt+FCP) − PBsIPI×ICMS\]  
ROL     \= PBsIPI − \[(PBsIPI − PBsIPI×ICMS)×(PIS+COFINS) \+ PBsIPI×ICMS\]  
MaCo$   \= ROL − (CustoMP \+ CustoEmb \+ Encargo$ \+ CustoPerda \+ Comissao$)  
Regra de isenção de mão de obra: aplicada apenas quando houver material fornecido pelo cliente e a UF de destino for SP.

### 2.4 Restrições e premissas

- O modelo de cálculo é especificação de domínio validada com o PO; qualquer alteração de regra exige nova homologação.  
- Prazo do semestre letivo, time de 6 integrantes, dedicação parcial, com disponibilidade de fim de semana como reserva.  
- **Formulação de nível único**: o produto é composto diretamente por MPs e embalagens, sem semiacabados. BOM multinível com rollup recursivo de custo é fronteira consciente, registrada como expansão futura.  
- A carga inicial de dados de referência (NCM, CEP/IBGE, alíquotas por UF) é feita por seed idempotente.

---

## 3\. Product Backlog

Escala: Fibonacci (1, 2, 3, 5, 8, 13). Prioridade: MoSCoW.

### EP01 \- Fundação técnica

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US01 | Como time, quero um monorepo com front, API e migrations para padronizar o desenvolvimento | 3 | Must |
| US02 | Como time, quero pipeline de CI com lint, type check e testes para impedir merge quebrado | 3 | Must |
| US03 | Como usuário, quero fazer login com e-mail corporativo para acessar o sistema | 5 | Must |
| US04 | Como administrador, quero que cada perfil enxergue apenas os dados permitidos | 8 | Must |
| US05 | Como time, quero o schema modelado e populado com dados de referência para desenvolver sobre dados realistas | 8 | Must |

### EP02 \- Cadastros base

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US06 | Como analista, quero CRUD de matéria-prima e embalagem para manter a base de insumos | 5 | Must |
| US07 | Como analista, quero CRUD de produto e tipo de produto com NCM vinculado | 5 | Must |
| US08 | Como analista, quero CRUD de cliente com UF, regime tributário e CEP | 5 | Must |
| US09 | Como analista, quero CRUD de fornecedor e da relação fornecedor x MP | 3 | Should |
| US10 | Como analista, quero manter produtividade, MOD e GGF por linha de produção | 5 | Must |
| US11 | Como usuário, quero busca, filtro e paginação server-side nos cadastros | 5 | Should |

### EP03 \- Parâmetros fiscais e financeiros

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US12 | Como analista, quero manter alíquotas por UF, NCM e regime (PIS, COFINS, ICMS, IPI, ICMS interno, FCP, MVA) | 8 | Must |
| US13 | Como analista, quero manter câmbio por moeda com margem de segurança | 3 | Must |
| US14 | Como analista, quero manter parâmetros globais (perda, taxa financeira, prazo padrão, desvio de cotação) | 3 | Must |
| US15 | Como analista, quero manter tabela de frete por região e modal | 3 | Should |

### EP04 \- Motor de cálculo

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US16 | Como sistema, quero um serviço puro `pricing_engine` que receba os insumos e devolva a estrutura de preço | 13 | Must |
| US17 | Como analista, quero o cálculo de custo total (MP, embalagem, perda, MOD, GGF) | 8 | Must |
| US18 | Como analista, quero o cálculo de encargo financeiro pelo prazo médio | 3 | Must |
| US19 | Como analista, quero o cálculo de PB, PB sem IPI, ROL, MaCo e impostos destacados | 13 | Must |
| US20 | Como analista, quero a regra de isenção de mão de obra para material do cliente em SP | 5 | Must |
| US21 | Como analista, quero o cálculo de ICMS-ST com MVA e FCP quando aplicável | 8 | Must |
| US22 | Como time, quero uma suíte de conformidade com 30 casos homologados pelo PO | 8 | Must |
| US23 | Como analista, quero o modo inverso, informando preço-alvo e obtendo a margem | 8 | Should |
| US24 | Como analista, quero o modo meta de custo de MP para chegar ao preço correspondente | 5 | Could |

**Critérios de aceite de US19 (referência)**

- Dado custo, margem e alíquotas válidos, o retorno traz `PBsIPIsEncargo`, `PBsIPI`, `PB`, `ROL`, `MaCo$` e `PrecoInd`.  
- Com `ICMSInt = 0`, `FCP = 0` e `MVA = 0`, `PB` é igual a `PBsIPI × (1+IPI)`.  
- Divergência máxima de R$ 0,01 contra o caso homologado correspondente.  
- Entrada inválida, com denominador `D ≤ 0`, retorna erro de domínio tratado e não exceção genérica.

### EP05 \- Cotação de insumos

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US25 | Como analista, quero que o sistema resolva a cotação vigente pela faixa de volume | 8 | Must |
| US26 | Como analista, quero o preço líquido de MP calculado com desoneração de ICMS, PIS e COFINS | 5 | Must |
| US27 | Como suprimentos, quero importar cotações por planilha com preview e validação de desvio | 8 | Should |
| US28 | Como suprimentos, quero consultar o histórico de cotação por MP e fornecedor | 3 | Should |

### EP06 \- Simulação e versionamento

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US29 | Como analista, quero criar uma precificação com cabeçalho comercial e fiscal | 8 | Must |
| US30 | Como analista, quero montar a formulação com MPs, quantidades, descarte e origem do material | 8 | Must |
| US31 | Como analista, quero criar cenários versionados preservando o histórico | 8 | Must |
| US32 | Como analista, quero informar o volume negociado e ver ROB, MaCo absoluta e MB | 5 | Must |
| US33 | Como analista, quero duplicar um cenário existente como ponto de partida | 3 | Should |
| US34 | Como analista, quero ver o resumo de rentabilidade em painel lateral durante a edição | 5 | Should |

### EP07 \- Workflow de aprovação

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US35 | Como analista, quero submeter um cenário para aprovação | 5 | Must |
| US36 | Como gerente, quero uma fila de aprovação com filtros por cliente e por margem | 5 | Must |
| US37 | Como gerente, quero aprovar ou reprovar com comentário obrigatório na reprovação | 5 | Must |
| US38 | Como gerente, quero alerta automático quando a margem ficar abaixo da política | 5 | Should |
| US39 | Como usuário, quero notificação por e-mail nas transições de status | 3 | Could |

### EP08 \- Proposta comercial

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US40 | Como comercial, quero gerar proposta em PDF a partir de um cenário aprovado | 8 | Must |
| US41 | Como comercial, quero numeração sequencial, data de emissão e validade na proposta | 3 | Must |
| US42 | Como comercial, quero que a proposta siga a identidade visual definida | 3 | Should |
| US43 | Como comercial, quero o histórico de propostas emitidas por cliente | 3 | Should |

### EP09 \- Relatórios e análises

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US44 | Como gerente, quero comparar cenários lado a lado com destaque de variação | 8 | Should |
| US45 | Como gerente, quero relatório de meta de custo de MP por produto | 5 | Should |
| US46 | Como gerente, quero análise de break-even com volume mínimo e tolerância de preço | 8 | Could |
| US47 | Como analista, quero simulação de sensibilidade a câmbio e custo de MP | 8 | Could |
| US48 | Como analista, quero exportar dados para consumo em BI | 3 | Should |

### EP10 \- Administração e auditoria

| ID | User Story | Pts | Prio |
| :---- | :---- | :---- | :---- |
| US49 | Como administrador, quero gerenciar usuários, perfis e funcionalidades | 8 | Should |
| US50 | Como administrador, quero conceder acesso restrito por carteira de clientes | 5 | Should |
| US51 | Como auditor, quero log imutável de todas as mutações com diff | 5 | Must |
| US52 | Como administrador, quero configurar metadados de cadastro sem deploy | 13 | Could |

**Total estimado**: \~296 pts. Escopo Must: \~190 pts.

---

## 4\. Planejamento de Sprints

**Janela real**: 15/09/2026 (terça) a 06/11/2026 (sexta) \= 53 dias corridos, 7,6 semanas. **Cadência**: 4 sprints de 2 semanas, a última com 11 dias. **Time**: 6 integrantes, organizados em 2 squads com trilhas paralelas. **Capacidade**: 29 pts por sprint em dias úteis. Fim de semana não entra na linha de base, entra como reserva (ver 4.7). **Capacidade total**: \~115 pts de linha de base mais \~18 pts de reserva, contra 190 pts de escopo Must.

### 4.1 Estrutura de squads

Seis pessoas no mesmo módulo se atrapalham. A capacidade só vira entrega se houver duas trilhas independentes.

| Squad | Pessoas | Responsabilidade | Artefato de fronteira |
| :---- | :---- | :---- | :---- |
| A \- Domínio | 3 | Modelagem, cotação, motor de cálculo, regras fiscais | Contrato OpenAPI de `/calculate`, fechado na S1 |
| B \- Produto | 3 | Autenticação, cadastros, telas de simulação, export | Consome o contrato com mock até a S3 |

**Regra de integração**: o contrato de `/calculate` é definido e versionado na Sprint 1, antes de qualquer implementação. O Squad B trabalha contra mock e só troca pelo serviço real na S3. Sem isso, o Squad B fica quatro semanas bloqueado esperando o motor.

### 4.2 Calendário

| Sprint | Início | Fim | Dias úteis | Pts | Tema |
| :---- | :---- | :---- | :---- | :---- | :---- |
| S1 | 15/09 ter | 28/09 seg | 10 | 27 | Fundação, dados e contrato |
| S2 | 29/09 ter | 12/10 seg | 9 (feriado 12/10) | 30 | Custo e parâmetros fiscais |
| S3 | 13/10 ter | 26/10 seg | 10 | 31 | Preço (sprint crítica) |
| S4 | 27/10 ter | 06/11 sex | 8 (feriado 02/11) | 27 | Ponta a ponta e entrega |

Feriados na janela: 12/10 e 02/11, ambos em segunda-feira. Antecipar a review da S2 para 09/10 (sexta). Congelamento de código: 04/11. Dias 05 e 06/11 reservados para documentação final e ensaio da apresentação.

### 4.3 Sprint 1 \- Fundação, dados e contrato (15/09 a 28/09, 27 pts)

- **Meta**: aplicação autenticada sobre um schema populado, com o contrato do motor fechado.  
- Squad A: US05 Modelagem do schema e seed de dados de referência (8) · US25 Resolução de cotação por faixa de volume (8)  
- Squad B: US01 Monorepo e ambiente (3) · US02 Pipeline de CI (3) · US03 Login (5)  
- Fora da contagem: contrato OpenAPI de `/calculate`, spike de RLS com timebox de 4 h, homologação dos 30 casos de teste com o PO.  
- **Demo**: login com dois perfis distintos, listagem de MPs e produtos, cotação resolvida por volume.

### 4.4 Sprint 2 \- Custo e parâmetros fiscais (29/09 a 12/10, 30 pts)

- **Meta**: composição de custo de um SKU real, com parâmetros mantidos pela interface.  
- Squad A: US26 Preço líquido de MP com desoneração (5) · US17 Custo total, MP, embalagem, perda, MOD e GGF (8) · US18 Encargo financeiro por prazo médio (3)  
- Squad B: US12 Alíquotas por UF, NCM e regime (8) · US13 Câmbio com margem de segurança (3) · US14 Parâmetros globais (3)  
- **Demo**: formulação e volume entram, CustoMP, CustoEmb, CustoPerda, CustoMOD, CustoGGF e CustoTotal saem conferidos contra os casos homologados.

### 4.5 Sprint 3 \- Preço (13/10 a 26/10, 31 pts) \- sprint crítica

- **Meta**: motor fiscal completo e em conformidade com a especificação.  
- Squad A: US16 e US19 fundidas, serviço puro `pricing_engine` com PB, PB sem IPI, ROL, MaCo e impostos destacados (18)  
- Squad B: US29 Tela de simulação com cabeçalho comercial e fiscal (8) · US06 CRUD de MP e embalagem (5)  
- US22 deixa de ser story e vira critério de DoD: a sprint só fecha com os 30 casos homologados passando, divergência máxima de R$ 0,01.  
- **Marco de integração**: 20/10, o Squad B troca o mock pelo motor real. Se escorregar, aciona o plano B (4.9).  
- **Demo**: execução dos casos homologados ao vivo, com 5 cenários escolhidos pela banca.

### 4.6 Sprint 4 \- Ponta a ponta e entrega (27/10 a 06/11, 27 pts)

- **Meta**: analista executa o fluxo completo na aplicação, com ROB e histórico de cenário.  
- Squad A: US20 Isenção de mão de obra (5) · US21 ICMS-ST com MVA e FCP (8)  
- Squad B: US30 Formulação com quantidades, descarte e origem do material (8) · US31 Versionamento com histórico preservado (8) · US32 Volume negociado gerando ROB, MaCo absoluta e MB (5)  
- Total nominal de 34 pts contra 27 de capacidade. US21 é o primeiro item a sair se a S3 atrasar.  
- **Demo final**: precificação criada do zero, custo a partir de cotação, preço com impostos, novo cenário versionado e ROB por volume.

### 4.7 Reserva de fim de semana

O time declarou disponibilidade de fim de semana. A decisão de planejamento é **não contabilizar isso na linha de base**, por dois motivos: oito fins de semana seguidos não se sustentam na prática, e se o sábado já está no plano não sobra mecanismo de recuperação quando a S3 escorregar.

Modelo adotado:

- Linha de base: dias úteis, 29 pts por sprint.  
- Reserva: até 2 sábados por sprint, cerca de 18 pts no semestre inteiro. Domingo livre por padrão.  
- A reserva é acionada por decisão na review, nunca por default.

**A reserva compra exatamente um épico.** Escolha a fazer com o PO na review da S2:

| Opção | Stories | Pts | Argumento |
| :---- | :---- | :---- | :---- |
| A \- Governança de aprovação | US35, US36, US37 | 15 | Fecha a pergunta "quem aprovou este preço", que planilha nenhuma responde. Baixo risco técnico |
| B \- Proposta comercial em PDF | US40, US41 | 11 | Entrega visível para P2, mas é trabalho de layout e não de domínio |
| C \- Não acionar | \- | 0 | Reserva vira colchão para a S3 e para a documentação final |

Recomendação: opção A. Governança é o diferencial estrutural do produto e custa pouco em risco. A proposta em PDF é o item mais fácil de fazer depois sem retrabalho.

### 4.8 Escopo fora do MVP

Mesmo com 6 pessoas, 115 pts de linha de base não cobrem os 190 pts de Must. Fica de fora:

| Item | Stories | Por que sai |
| :---- | :---- | :---- |
| Proposta comercial em PDF | US40 a US43 | Candidata da reserva, opção B |
| Workflow de aprovação | US35 a US39 | Candidata da reserva, opção A |
| CRUD de cliente, fornecedor e produtividade | US07 a US10 | Entram por seed. Só MP e embalagem ganham interface |
| Import de cotação por planilha | US27, US28 | Manutenção manual cobre o semestre |
| Relatórios e administração | EP09, EP10 | Nenhum é pré-requisito do fluxo principal |
| Modo inverso | US23, US24 | Diferencial elegante, mas não bloqueia a demonstração |
| Metadados configuráveis | US52 | 13 pts de abstração sem entrega visível |

**Consequência para as personas**: o MVP atende P1 por completo e P4 de forma indireta. P3 entra se a reserva for para a opção A. P2 e P5 ficam para a etapa seguinte.

### 4.9 Plano B da Sprint 3

Se a conformidade fiscal não fechar até 22/10:

1. Congelar o escopo no cenário simples: `ICMSInt = 0`, `FCP = 0`, `MVA = 0`, sem isenção de mão de obra. Saem US20 e US21 da S4.  
2. Reduzir a suíte de conformidade de 30 para 12 casos, cobrindo apenas Full Service Nacional.  
3. Realocar 1 pessoa do Squad B para o Squad A na segunda semana da S3.  
4. Acionar a reserva de sábado da S3 e da S4.  
5. Registrar as regras não implementadas como backlog técnico, com a fórmula já especificada na seção 2.3.

---

## 5\. Definições de processo

### Definition of Ready

- História com critérios de aceite escritos no formato Dado / Quando / Então.  
- Dependências técnicas mapeadas e dados de teste disponíveis.  
- Estimada pelo time em planning poker.

### Definition of Done

- Código revisado por par e integrado à branch principal.  
- Testes unitários e de integração passando no pipeline.  
- Migration aplicada e documentada.  
- Deploy em staging validado pelo PO.  
- Documentação atualizada no repositório.

### Cerimônias

| Cerimônia | Frequência | Duração |
| :---- | :---- | :---- |
| Planning | Início da sprint | 2 h |
| Daily assíncrona | Diária | 15 min |
| Review com PO | Fim da sprint | 1 h |
| Retrospectiva | Fim da sprint | 45 min |
| Refinement | Meio da sprint | 1 h |

### Riscos principais

| Risco | Impacto | Mitigação |
| :---- | :---- | :---- |
| Regra fiscal mal especificada | Alto | Suíte de conformidade homologada com o PO antes da implementação |
| RLS mal configurada expondo custo entre carteiras | Alto | Spike na S1 e teste automatizado de isolamento |
| Squad B bloqueado esperando o motor | Alto | Contrato OpenAPI fechado na S1 e desenvolvimento contra mock |
| Escopo maior que a capacidade real | Médio | Must reduzido a 115 pts, itens Could fora do semestre |
| Disponibilidade do PO para homologação | Médio | Reviews agendadas no início do semestre |

---

## 6\. Decisões em aberto

1. **Nome do produto**: NeoPrice. Confirmar com o time.  
2. **Velocity**: 29 pts por sprint de 2 semanas com 6 pessoas é estimativa. Recalibrar ao fim da S1 e reajustar o corte da seção 4.8.  
3. **Divisão de squads**: o split 3 \+ 3 assume que pelo menos 2 integrantes conseguem tocar o motor em Python. Se o time for mais forte em front, inverter para 2 no domínio e 4 no produto.  
4. **Camada de API**: mantive FastAPI para o motor. A alternativa enxuta é Edge Function no Supabase, que reduz infraestrutura mas dificulta a suíte de testes em Python.  
5. **Origem dos dados de referência**: definir se alíquotas por UF e tabela NCM entram por seed manual ou por consumo de API pública.

