# Controle de acesso: perfis, permissões e carteiras

Resultado do spike de RLS e da implementação da US04 (issue #45). Descreve como o banco decide o que cada usuário enxerga e o que o restante do time precisa fazer para as regras valerem.

A regra central: **a interface esconde, mas quem barra é o banco**. Custo e margem de uma carteira não chegam a quem não tem acesso a ela, mesmo que a consulta saia de uma tela ou de um endpoint mal filtrado.

## Abordagem

- **Identidade pelo Supabase Auth.** `usuario.id` é o mesmo UUID de `auth.users`. As políticas descobrem quem está consultando por `auth.uid()`, que o Supabase extrai do token do usuário.
- **Perfil dá permissões nomeadas.** Cada usuário tem um perfil; cada perfil tem um conjunto de permissões no formato `recurso.acao` (por exemplo `precificacao.ler`). As políticas perguntam pela permissão, nunca pelo nome do perfil, então criar ou ajustar um perfil é só dado, sem migration.
- **Carteira limita o alcance.** Cada cliente pertence a uma carteira e cada usuário é vinculado às carteiras que atende. Cliente e precificação só aparecem para quem tem a permissão **e** alcança a carteira. A carteira de uma precificação é a do seu cliente.
- **Três papéis do Postgres.** `authenticated` (usuário logado) passa pelas políticas; `service_role` (chave de serviço do backend) tem acesso total; `anon` não tem acesso a nenhuma tabela.

As três funções que as políticas usam estão na migration `20261012000003_criar_perfis_carteiras_rls.sql`: `usuario_tem_permissao(permissao)`, `usuario_acessa_carteira(carteira_id)` e `usuario_acessa_cliente(cliente_id)`. A API pode chamá-las para a segunda camada de autorização.

## O que a API e o front precisam respeitar

O RLS só funciona se a consulta chegar ao banco **em nome do usuário**:

- o front consulta o Supabase com a sessão do usuário logado; ou
- a API cria o cliente Supabase com a chave pública e repassa o token do usuário no cabeçalho `Authorization`.

Consulta feita com a chave `service_role` ou por conexão direta como dono do banco **ignora todas as políticas**. Esses caminhos ficam restritos a seed, migrations e tarefas de sistema, e nesse caso o filtro por carteira é responsabilidade do código.

## Matriz de acesso

Proposta inicial do time, carregada por `supabase/seed/referencia/06_perfil_permissao.sql`. **Falta a revisão com o PO** (RNF09).

| Permissão | Analista de Pricing | Executiva de Contas | Gerente Comercial | Analista de Suprimentos | Administrador |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `cadastro.ler` | ✔ | ✔ | ✔ | ✔ | ✔ |
| `cadastro.editar` | | | | ✔ | ✔ |
| `custo.ler` | ✔ | | ✔ | ✔ | ✔ |
| `custo.editar` | | | | ✔ | ✔ |
| `parametro_fiscal.ler` | ✔ | | ✔ | | ✔ |
| `parametro_fiscal.editar` | ✔ | | | | ✔ |
| `cliente.ler` | ✔ | ✔ | ✔ | | ✔ |
| `cliente.editar` | | | | | ✔ |
| `precificacao.ler` | ✔ | ✔ | ✔ | | ✔ |
| `precificacao.editar` | ✔ | | | | |
| `precificacao.aprovar` | | | ✔ | | |
| `carteira.todas` | | | | | ✔ |
| `acesso.administrar` | | | | | ✔ |

O que cada permissão libera no banco:

| Permissão | Tabelas |
| :--- | :--- |
| `cadastro.*` | `uf`, `municipio`, `cep`, `ncm`, `fornecedor`, `materia_prima`, `embalagem`, `produto` |
| `custo.*` | `linha_producao`, `produtividade` |
| `parametro_fiscal.*` | `aliquota_fiscal` |
| `cliente.*` | `cliente`, só nas carteiras do usuário |
| `precificacao.*` | `precificacao`, só nas carteiras do usuário |
| `carteira.todas` | Remove o recorte por carteira, inclusive para clientes sem carteira |
| `acesso.administrar` | `usuario`, `perfil`, `permissao`, `perfil_permissao`, `carteira`, `usuario_carteira` |

Regras que valem para todos:

- Usuário inativo, ou autenticado mas sem linha em `usuario`, não enxerga nada.
- Ninguém apaga cadastro nem precificação pelo papel `authenticated`: cadastro é inativado e o histórico de precificação não se apaga (RF09).
- Cada usuário lê o próprio cadastro e as próprias carteiras; só `acesso.administrar` altera perfil, permissão ou carteira de alguém, o que impede o usuário de se promover.
- Quem tem `precificacao.aprovar` altera a precificação para mudar o status. A regra de quais transições de status são válidas é do workflow de aprovação, não do RLS.

## Como dar acesso a um usuário

1. Crie o usuário no Supabase Auth (painel ou tela de login).
2. Insira a linha em `usuario` com o mesmo id e o perfil desejado.
3. Vincule as carteiras em `usuario_carteira`.

```sql
INSERT INTO usuario (id, nome, email, perfil_id)
SELECT '<id em auth.users>', 'Rafael Costa', 'rafael@empresa.com', id
FROM perfil WHERE codigo = 'analista_pricing';

INSERT INTO usuario_carteira (usuario_id, carteira_id)
SELECT '<id em auth.users>', id FROM carteira WHERE codigo = 'CART-SUDESTE';
```

A carga de desenvolvimento cria três carteiras (`CART-SUDESTE`, `CART-SUL`, `CART-EXPORTACAO`) e distribui entre elas os clientes e as precificações do protótipo, mas não cria usuários.

## Pendências

- **Login (US03).** A criação automática da linha em `usuario` quando alguém se cadastra no Supabase Auth fica com a story de login.
- **Tabela `precificacao`.** Hoje tem só o cabeçalho mínimo que a regra de acesso precisa. Cenários e demais tabelas filhas (US29 em diante) devem herdar o recorte com `usuario_acessa_cliente(...)` a partir da precificação.
- **Custo dentro da precificação.** A executiva de contas lê precificações, mas não tem `custo.ler`. Quando os cenários guardarem custo e margem, esses campos precisam ficar em tabela ou visão protegida por `custo.ler`.
- **Staging.** As políticas foram testadas em um PostgreSQL com `auth.uid()` simulado; falta validar em um projeto Supabase real.
