# api

API REST do NeoPrice: FastAPI, Pydantic v2 e SQLAlchemy 2.0. Orquestra os casos de uso, faz a autorização e chama o `pricing-core` para calcular. Não contém regra de preço.

## Configurar o ambiente

1. Copie o modelo e preencha com os dados do projeto Supabase:

   ```bash
   cp apps/api/.env.example apps/api/.env
   ```

   | Variável | Onde pegar no painel do Supabase | Segredo? |
   | :--- | :--- | :---: |
   | `SUPABASE_URL` | Project Settings → API → Project URL | não |
   | `SUPABASE_ANON_KEY` | Project Settings → API → `anon` `public` | não |
   | `SUPABASE_SERVICE_KEY` | Project Settings → API → `service_role` | **sim** |
   | `DATABASE_URL` | Project Settings → Database → Connection string (URI) | **sim** |
   | `CORS_ORIGINS` | Endereço do front; o padrão serve para o Vite local | não |

   Para o banco local (`supabase start`), use `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres`.

   O `.env` está no `.gitignore` e nunca vai para o repositório. A `service_role` e a senha do banco ignoram o RLS: quem tem essas duas lê e altera qualquer dado.

2. Instale as dependências, a partir da raiz do repositório:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows (no Linux/macOS: source .venv/bin/activate)
   pip install -r apps/api/requirements.txt
   ```

3. Suba a API:

   ```bash
   cd apps/api
   uvicorn app.main:app --reload
   ```

4. Confira em <http://localhost:8000/health/banco>. Com o `.env` certo e o schema aplicado, a resposta traz `"status": "ok"` e `"produtos": 7`. Se algo estiver errado, o `motivo` diz o quê (variável faltando, senha errada, banco inacessível).

A documentação interativa fica em <http://localhost:8000/docs>.

## Acesso ao banco

| Módulo | Quando usar | RLS |
| :--- | :--- | :--- |
| `supabase_do_usuario(token)` | Qualquer consulta feita em nome do usuário logado, repassando o JWT dele | Vale |
| `supabase_servico()` | Tarefas de sistema (cargas, jobs) | **Ignorado** |
| `get_db()` / `get_engine()` | SQL direto pelo SQLAlchemy, também só para tarefas de sistema | **Ignorado** |

Detalhes da regra de acesso em [docs/controle-de-acesso.md](../../docs/controle-de-acesso.md).

## Autenticação

O front manda o access token do Supabase Auth em `Authorization: Bearer <token>`. A API confere o token no próprio Supabase e carrega perfil e permissões da tabela `usuario` (`app/core/auth.py`).

| Dependência | O que faz |
| :--- | :--- |
| `usuario_atual` | 401 sem token ou com token inválido/expirado; 403 para usuário inativo ou sem linha em `usuario` |
| `exigir_permissao("precificacao.ler")` | Além do acima, 403 se o perfil não tem a permissão nomeada |

```python
@router.get("/precificacoes")
def listar(usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler"))): ...
```

`GET /auth/me` devolve nome, perfil e permissões de quem está logado; o front usa para montar o menu e a guarda de rota.

Quem se cadastra no Supabase Auth ganha a linha em `usuario` sozinho (migration `20261016000001_criar_usuario_ao_cadastrar.sql`), mas **inativa**: o administrador ativa e escolhe o perfil.

## Cadastros de matérias-primas e embalagens (US06)

As rotas usam `supabase_do_usuario(token)`, exigem JWT e respeitam `cadastro.ler` para consulta e `cadastro.editar` para gravação. O PostgREST aplica as políticas RLS existentes e os gatilhos de auditoria registram o usuário autenticado.

| Método e rota | Operação |
| :--- | :--- |
| `GET /cadastros/materias-primas` / `GET /cadastros/embalagens` | Lista registros com busca, filtros e paginação no servidor |
| `GET /cadastros/{tipo}/{id}` | Consulta um registro |
| `POST /cadastros/{tipo}` | Cria matéria-prima ou embalagem |
| `PATCH /cadastros/{tipo}/{id}` | Atualiza campos informados; `ativo` permite reativar um cadastro |
| `DELETE /cadastros/{tipo}/{id}` | Inativa o registro, sem apagar histórico ou quebrar referências |
| `GET /cadastros/ncm?termo=...` | Busca até 20 resultados por descrição ou prefixo de código NCM |

`tipo` é `materias-primas` ou `embalagens`. Os campos vêm das tabelas existentes: `codigo`, `descricao`, `unidade_medida`, `ncm_codigo` e `ativo`. Código, descrição, unidade permitida e NCM de oito dígitos seguem limites e restrições já declarados no schema; as unidades padrão são `kg` para matéria-prima e `un` para embalagem. Não foi necessária nova tabela ou migration. A exclusão é lógica porque a convenção do projeto é inativar cadastros; a foreign key existente mantém a validação do NCM.

Na listagem, `busca` (opcional, até 100 caracteres) pesquisa código, descrição e NCM; `ativo` e `unidade_medida` são filtros opcionais combináveis. A paginação usa `pagina` (padrão `1`) e `tamanho_pagina` (padrão `20`, máximo `100`). A resposta contém `registros`, `total`, `pagina`, `tamanho_pagina` e `total_paginas`; os registros são ordenados por descrição e, como desempate estável, por ID. Contagem, filtros e intervalo são executados pelo PostgREST em nome do usuário, então RLS continua aplicado.

Testes: `cd apps/api && python -m pytest tests`.
