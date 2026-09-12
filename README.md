# Pricing Intelligence

> Plataforma web multissetorial de formação de preço, com recomendação de markup assistida por Inteligência Artificial e geração automática de proposta comercial.

**Projeto Integrador VI** — Engenharia de Software · PUC-Campinas · 2º semestre de 2026
Disciplina 12563 · Grupo 22 · Professora orientadora: Sílvia C. de Matos Soares

---

## Sobre o projeto

O preço é a variável de maior alavancagem sobre o resultado de uma organização e, ainda assim, na maior parte das empresas de médio porte ele é definido em planilhas isoladas: sem trabalho colaborativo, sem controle de versão, sem trilha de auditoria e com a margem herdada de convenção histórica, sem relação verificável com o que o mercado pratica.

O Pricing Intelligence ataca três lacunas ao mesmo tempo:

1. **Governança** — o cálculo vira um motor determinístico, versionado e auditável, e não uma fórmula de célula.
2. **Inteligência de mercado** — preço público coletado, estruturado e casado com o portfólio, ancorando a decisão de margem em evidência.
3. **Formalização** — o cenário aprovado vira proposta comercial em PDF, numerada e rastreável, sem digitação manual.

### A decisão de arquitetura central

O que varia entre setores é apenas a **composição do custo**; as camadas seguintes — despesas variáveis, encargo financeiro do prazo, tributação e formação de margem — são estruturalmente idênticas. Isolando a composição em modos intercambiáveis, um único motor atende a modelos de negócio distintos sem duplicar regra:

| Modo | Composição do custo | Atende |
| :--- | :--- | :--- |
| MC1 | Formulação (lista técnica de insumos e embalagens) | Manufatura |
| MC2 | Aquisição (custo de compra) | Distribuição e varejo |
| MC3 | Recursos e horas | Serviços |
| MC4 | Custo direto informado | Casos gerais |

O tratamento tributário contempla o regime brasileiro de incidência indireta: cálculo por dentro do ICMS, encadeamento do IPI, substituição tributária por MVA com FCP e a alternativa do ISS para operações de serviço.

---

## Escopo

### O que o software faz

- Autenticação e controle de acesso por perfil, com permissões nomeadas e restrição de visibilidade por carteira de clientes.
- Cadastros mestres e paramétricos via **CRUD dirigido por metadados** — novas entidades entram por configuração, não por código de tela.
- Cotação de insumos em múltiplas moedas, com validade, prazo de entrega, pedido mínimo, faixas de volume e detecção de desvio contra o preço médio histórico.
- Ciclo completo de formação de preço: estudo por cliente, versionamento de cenários, composição de custo, despesas variáveis, gross-up tributário e preço bruto e líquido.
- Problemas inversos: margem resultante de um preço-alvo e custo máximo admissível de insumos para um preço desejado.
- Volume negociado por cenário, derivando ROB, ROL e margem bruta absoluta, com agregação por cliente, produto, categoria e período.
- Recomendação de faixa de markup por modelo supervisionado, com explicabilidade por atributo.
- Proposta comercial em PDF multiproduto, com identidade visual configurável, numeração sequencial e controle de validade.

### O que o software não faz

- Não substitui o ERP: consome cadastros exportados e não escreve de volta.
- Não emite documento fiscal nem apura tributo para escrituração — alíquotas são parâmetros de simulação.
- Não faz gestão de pedido, estoque, produção, faturamento ou contas a receber.
- Não compra nem negocia com fornecedor de forma automatizada.
- Não publica preço em canal externo nem integra marketplace.
- O módulo de IA **não decide preço**: produz recomendação, faixa e explicação; a decisão é do analista, com registro de aceite ou rejeição.

---

## Módulos

| Módulo | Descrição | Telas | RFs |
| :--- | :--- | :---: | :--- |
| M1 | Autenticação e controle de acesso | 6 | RF01–RF09 |
| M2 | Cadastros mestres e parâmetros | 24 | RF10–RF22 |
| M3 | Cotação e custo de insumos | 4 | RF23–RF29 |
| M4 | Formação de preço e simulação de cenários | 14 | RF30–RF48 |
| M5 | Relatórios e análises | 6 | RF49–RF56 |
| M6 | Markup assistido por IA | 5 | RF57–RF66 |
| M7 | Proposta comercial em PDF | 4 | RF67–RF73 |
| M8 | Administração da plataforma | 8 | RF74–RF82 |

M1–M5 formam o núcleo transacional, M6 e M7 são as capacidades diferenciadoras e M8 a administração.

---

## Arquitetura

Camadas com núcleo de domínio isolado. O princípio orientador é que o motor de cálculo não dependa de banco, de rede nem de framework web — condição para ser testável e verificável de forma independente.

| Plano | Responsabilidade | Componentes |
| :--- | :--- | :--- |
| Apresentação | Interface, sessão, validação de entrada e apresentação de resultado | SPA React, CRUD genérico, editor de cenário, painéis |
| Aplicação | Orquestração de casos de uso, autorização, transações, contratos | API REST FastAPI, camada de serviços, esquemas Pydantic |
| Domínio | Regras puras: composição, gross-up, margem, inversões | Pacote `pricing-core`, sem dependência de infraestrutura |
| Integração | Processamento assíncrono | Fila de tarefas, coletores, extrator LLM, treinador, gerador de PDF |
| Persistência | Armazenamento, integridade, autorização de dados, busca vetorial | PostgreSQL/Supabase, RLS, pgvector, Storage |

Decisões relevantes:

- **Motor como biblioteca pura** — entrada imutável, saída completa, sem estado. A versão do motor fica registrada em cada cenário, o que permite evoluir a regra fiscal sem invalidar o histórico.
- **`Decimal` em vez de ponto flutuante** para todo valor monetário e percentual, com contexto de precisão explícito — o critério de aceite é divergência máxima de R$ 0,01.
- **Composição e regimes de incidência como estratégias** — um novo modo de negócio ou um novo regime é uma entrada em tabela, não uma alteração no motor.
- **Método de Brent** para as resoluções inversas, sobre intervalo com mudança de sinal garantida.
- **Autorização em duas camadas** — dependências declarativas na aplicação e RLS no banco. A interface reflete as duas, mas nunca é a única barreira.
- **Pipeline de IA assíncrono** — coleta, extração, embeddings, treinamento e PDF rodam fora do ciclo de requisição; só a recomendação é síncrona.

---

## Stack

| Camada | Tecnologias |
| :--- | :--- |
| Front-end | React 18, TypeScript, Vite, TanStack Query/Table, React Hook Form + Zod, Tailwind + shadcn/ui, Recharts |
| Back-end | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 + asyncpg |
| Domínio | `pricing-core` (pacote próprio), SciPy (`optimize.brentq`) |
| Dados | PostgreSQL 15 (Supabase), pgvector, Supabase Auth e Storage |
| Assíncrono | Celery + Redis |
| IA | Playwright + httpx + selectolax (coleta), LLM com saída estruturada, embeddings multilíngues, LightGBM + scikit-learn, SHAP, MLflow |
| PDF | Jinja2 + WeasyPrint |
| Testes | pytest, Hypothesis, Vitest, Playwright |
| Infra | GitHub Actions, Vercel (front), Fly.io (API), Supabase, Sentry |

---

## Cronograma

Cinco sprints de duas semanas, de 14/09 a 20/11. A quinzena de 01/09 a 11/09 foi de descoberta e especificação.

| Sprint | Período | Entrega |
| :--- | :--- | :--- |
| S1 | 14/09 – 25/09 | Fundação: monorepo, CI, login, perfis e RLS, schema e seed, contrato do motor |
| S2 | 28/09 – 09/10 | Custo e parâmetros fiscais: alíquotas, câmbio, CRUD de MP, custo total, encargo |
| S3 | 12/10 – 23/10 | Preço: `pricing_engine`, PB, ROL, MaCo, suíte de conformidade, tela de simulação |
| S4 | 26/10 – 06/11 | Ponta a ponta: formulação, versionamento, ICMS-ST, ROB e margem absoluta |
| S5 | 09/11 – 20/11 | Governança de aprovação, exportação, testes finais e entrega |

Sprints, épicos e andamento das tarefas no [quadro do projeto](https://github.com/users/felipecorsopretoni/projects/2).

**Status atual**: especificação concluída, S1 em andamento. Ainda sem código de aplicação no repositório.

---

## Documentos

| Arquivo | Conteúdo |
| :--- | :--- |
| `Time_X.docx` | Documentação de projeto completa: requisitos, regras de negócio, modelo de dados, arquitetura, IA, testes e gestão |
| `PI6-planejamento-produto.md` | Planejamento de produto e backlog (versão anterior do escopo, sob revisão) |

---

## Equipe

| RA | Integrante |
| :--- | :--- |
| 24018174 | Felipe Corso Pretoni |
| 24004548 | Marcelo Oliveira |
| 24006976 | Caiuã Vieira |
| 24006720 | Gustavo Zorzo |
| 24012785 | Mateus Mergulhão |
| 24007872 | Victor De Palma |
