# supabase

Banco PostgreSQL do NeoPrice (Supabase).

- `migrations/`: schema, índices, políticas de RLS e gatilhos, em ordem de aplicação.
- `seed/referencia/`: carga idempotente dos dados de referência (UF, município IBGE, NCM, CEP, alíquotas por UF, perfis e permissões).
- `seed/dev/`: carga idempotente de desenvolvimento (fornecedores, MPs, embalagens, produtos, produtividade, clientes, carteiras e precificações fictícios). Não aplicar em produção.
- `config.toml`: configuração do Supabase CLI, com a ordem dos seeds.

## Como aplicar

Com o [Supabase CLI](https://supabase.com/docs/guides/cli) instalado, a partir da raiz do repositório:

```bash
# Banco local (Docker): recria do zero, aplica migrations e seeds
supabase start
supabase db reset

# Projeto remoto (staging): aplica as migrations pendentes e os seeds
supabase link --project-ref <ref-do-projeto>
supabase db push --include-seed
```

Os seeds podem rodar quantas vezes for preciso: cada `INSERT` usa `ON CONFLICT` na chave de negócio e só altera a linha quando algum valor mudou.

## Tabelas

| Tabela | Chave de negócio | Conteúdo |
| :--- | :--- | :--- |
| `uf` | `sigla` | 27 unidades da federação, com código IBGE e região |
| `municipio` | `codigo_ibge` | Municípios do IBGE (7 dígitos) |
| `cep` | `cep` | Consulta CEP → município. Não é a base completa dos Correios |
| `ncm` | `codigo` | Itens de 8 dígitos da NCM vigente |
| `aliquota_fiscal` | UF de destino, NCM, regime e início de vigência | PIS, COFINS, ICMS, IPI, ICMS interno, FCP e MVA |
| `fornecedor` | `codigo` | Fornecedores nacionais e estrangeiros |
| `materia_prima` | `codigo` | Matérias-primas, com NCM |
| `embalagem` | `codigo` | Materiais de embalagem, com NCM |
| `produto` | `codigo` | Produtos acabados, com NCM e categoria |
| `linha_producao` | `codigo` | Linhas de produção, com TaxaMOD e TaxaGGF (R$/h) |
| `produtividade` | produto e linha | Unidades por hora e número de funcionários |
| `cliente` | `codigo` | Clientes, com UF, município, CEP, regime tributário e carteira |
| `perfil` | `codigo` | Perfis de usuário, um por persona |
| `permissao` | `codigo` | Permissões nomeadas (`recurso.acao`) |
| `perfil_permissao` | perfil e permissão | Matriz de acesso |
| `usuario` | `id` (o de `auth.users`) | Usuários da aplicação, com perfil |
| `carteira` | `codigo` | Carteiras de clientes |
| `usuario_carteira` | usuário e carteira | Carteiras que cada usuário atende |
| `precificacao` | `codigo` | Cabeçalho mínimo da precificação (completado na US29) |
| `auditoria` | `id` | Trilha imutável de toda inserção, alteração e exclusão, com usuário e diff |
| `cambio` | moeda e data | Taxa em reais por unidade da moeda, com margem de segurança e origem (manual ou PTAX) |
| `parametro_global` | código e início de vigência | Perda, taxa financeira mensal, prazo médio padrão e desvio máximo de cotação |

## Convenções

- Chave primária `UUID` nos cadastros; nas tabelas de referência a chave é o próprio código oficial, só dígitos, sem máscara.
- Todo percentual é fração decimal (`0.18` é 18%), igual ao contrato do motor.
- `created_at` e `updated_at` em todas as tabelas; `updated_at` é mantido pelo gatilho `set_updated_at`.
- Cadastro não é apagado: usa-se a coluna `ativo`.
- RLS ativo em todas as tabelas: o `service_role` (backend) tem acesso total, o `authenticated` passa pelas políticas por perfil e carteira e o `anon` não acessa nada. Ver [docs/controle-de-acesso.md](../docs/controle-de-acesso.md).
- Tabela nova precisa de `ENABLE ROW LEVEL SECURITY`, `GRANT` e políticas na mesma migration; o teste `test_todas_as_tabelas_com_rls_ativo` barra a que ficar sem RLS.
- Toda tabela é auditada: tabela nova precisa de `SELECT habilitar_auditoria('<tabela>');` na mesma migration. Ver [docs/auditoria.md](../docs/auditoria.md).

## Alíquotas

Em `aliquota_fiscal`, a linha com `ncm_codigo` nulo é a regra geral da UF; uma linha com NCM preenchido tem precedência. Para uma data, vale a linha de maior `vigencia_inicio` que não seja posterior a ela.

A importação em massa (`POST /parametros-fiscais/aliquotas/importacao`) lê um CSV com as colunas `uf;ncm;regime;vigencia;pis;cofins;icms;ipi;icms_interno;fcp;mva`, com os percentuais escritos como a área fiscal escreve (`18` ou `18,00` para 18%). A API valida linha a linha e aponta o número da linha com erro; a gravação é da função `importar_aliquotas`, que grava o lote inteiro ou nada, passa pelo RLS (`parametro_fiscal.editar`) e só toca as regras que mudaram. A primeira chamada é sempre uma simulação, que conta o que seria criado ou alterado sem gravar.

Os valores do seed são parâmetros de simulação para desenvolvimento, ainda não homologados com o PO: as premissas estão no cabeçalho de `seed/referencia/05_aliquota_fiscal.sql`.

## Câmbio e parâmetros globais

Os dois são históricos por data: o valor vigente em uma data é o de data mais recente que não seja posterior a ela (`GET /cambios/vigente` e `GET /parametros-globais/vigentes`). O câmbio que entra no custo é `taxa × (1 + margem_seguranca_percentual)`.

Pela aplicação (papel `authenticated`), o passado é imutável: o gatilho `proteger_historico_vigente` recusa criar, alterar ou apagar valor com data anterior a hoje (erro `23001`, que a API devolve como 409). Mudar um parâmetro é cadastrar uma nova vigência; assim um cálculo refeito pela sua data encontra os mesmos valores. Cargas de sistema (seed, migration) não passam por essa trava.

Quem edita: câmbio, `cambio.editar` (suprimentos e administrador); parâmetros, `parametro_global.editar` (pricing e administrador).

## Atualizar os dados de referência

`01_uf.sql` a `04_cep.sql` são gerados a partir das fontes oficiais (IBGE, Portal Único Siscomex e ViaCEP) e não devem ser editados à mão:

```bash
python scripts/gerar_seed_referencia.py
```

Para incluir um CEP, acrescente-o à lista `CEPS` do script e gere de novo.

## Testes

Ver `tests/banco/README.md`.
