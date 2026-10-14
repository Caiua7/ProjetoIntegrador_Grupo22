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
