# Deploy e observabilidade (staging)

Issue #65. O staging existe para o PO validar o NeoPrice sem depender da máquina
de ninguém. Todo merge na `main` atualiza o staging sozinho.

| Peça | Endereço | Conta / dono | Como atualiza |
|---|---|---|---|
| Front (`apps/web`) | https://neoprice.vercel.app | Vercel, time *ProjetoIntegrador_Grupo22* (Caiuã) | push na `main` → build do Vite → publicado |
| API (`apps/api`) | https://neoprice-api-staging.onrender.com | Render, Blueprint `neoprice-staging` (Felipe) | push na `main` → espera os checks do CI → deploy |
| Banco e login | projeto Supabase do desenvolvimento | Supabase | migrations aplicadas pelo `supabase db push` ou pelo SQL Editor |
| Erros | Sentry, projetos `neoprice-web` e `neoprice-api` | Sentry (Felipe) | automático quando há DSN |

Medido na primeira publicação (02/11/2026): API em 1m43s e front em ~1 min depois do merge,
dentro do critério de aceite de 6 min.

## Ambientes

| Ambiente | Front | API | Variável `AMBIENTE` |
|---|---|---|---|
| Local | `http://localhost:5173` | `http://localhost:8000` | `local` |
| Staging | `https://neoprice.vercel.app` | `https://neoprice-api-staging.onrender.com` | `staging` |

Local e testes não mandam nada para o Sentry: sem DSN, ele fica desligado.

## Configuração (uma vez só)

### 1. Sentry
1. Criar conta em sentry.io (login com o GitHub) e uma organização.
2. Criar dois projetos: **neoprice-web** (plataforma React) e **neoprice-api** (plataforma FastAPI).
3. Guardar o DSN de cada um (Settings → Client Keys).

### 2. API no Render
1. Criar conta em render.com com o GitHub e dar acesso ao repositório. O repositório é de conta
   pessoal (Caiua7): só o dono instala o app do Render nele (`github.com/apps/render` →
   Configure → Caiua7 → *Only select repositories*).
2. **New → Blueprint** → escolher o repositório. O Render lê o `render.yaml` da raiz.
3. Preencher as variáveis marcadas como secretas:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`: as mesmas do `apps/api/.env`
   - `SENTRY_DSN`: DSN do projeto **neoprice-api**
   - `CORS_ORIGINS`: URL da Vercel (passo 3), por exemplo `https://neoprice.vercel.app`
4. Conferir `https://<api>.onrender.com/health` → `{"status":"ok"}`.

O plano gratuito "dorme" após ~15 min sem uso; a primeira chamada depois disso leva ~30–50 s.
Antes de apresentar, abra o sistema um minuto antes.

### 3. Front na Vercel
1. Criar conta em vercel.com com o GitHub → **Add New → Project** → importar o repositório.
   A Vercel só importa repositórios das contas em que você entra, então o projeto precisa ser
   criado pelo dono do repositório (hoje, na Vercel do Caiuã).
2. **Root Directory**: `apps/web` (o `vercel.json` dali já define build, saída e rotas).
3. Variáveis de ambiente:
   - `VITE_NEOPRICE_SUPABASE_URL`, `VITE_NEOPRICE_SUPABASE_ANON_KEY`: as mesmas do `apps/web/.env.local`
   - `VITE_NEOPRICE_API_URL`: URL do Render, sem barra no fim
   - `VITE_SENTRY_DSN`: DSN do projeto **neoprice-web**
   - `VITE_AMBIENTE`: `staging`

   Atalho: monte um `apps/web/.env.staging` (ignorado pelo git) com as 5 linhas e use
   **Import .env**. Os valores `VITE_` são públicos (vão no JavaScript do site); a
   `SUPABASE_SERVICE_KEY` e a `DATABASE_URL` nunca vão para a Vercel.
4. Deploy. Depois volte ao Render e ajuste `CORS_ORIGINS` com a URL final.

   **Trocou uma variável `VITE_`? Faça Redeploy** (Deployments → ⋯ → Redeploy). O Vite grava
   as variáveis no build; só salvar não muda o site.

### 4. Supabase
Em **Authentication → URL Configuration**: *Site URL* `https://neoprice.vercel.app`; em
*Redirect URLs*, `https://neoprice.vercel.app/**` e `http://localhost:5173/**`.

## Problemas conhecidos

| Sintoma | Causa | O que fazer |
|---|---|---|
| Login falha com `ERR_NAME_NOT_RESOLVED` em `*.supabase.co` | O Supabase gratuito pausou o projeto (~7 dias sem acesso) | Dono do projeto: dashboard → **Restore project**. O workflow `manter-staging-ativo.yml` faz um acesso a cada 3 dias para evitar a pausa |
| Depois do login, chamada para `localhost:8000` | `VITE_NEOPRICE_API_URL` vazia ou errada na Vercel | Corrigir a variável e fazer **Redeploy** |
| Chamada à API bloqueada por CORS | `CORS_ORIGINS` do Render sem a URL do front | Render → Environment → `CORS_ORIGINS=https://neoprice.vercel.app` |
| Primeira chamada demora ~50 s | API do Render gratuito estava dormindo | Normal; abrir o sistema um minuto antes de apresentar |

## Rastrear um problema (id de correlação)

Toda chamada do front à API leva o cabeçalho `X-Request-ID`. A API devolve o mesmo id
na resposta, grava em toda linha de log e marca o evento no Sentry com a tag `request_id`.

1. No navegador (DevTools → Network), copie o `X-Request-ID` da resposta com erro.
2. No Sentry, busque `request_id:<id>`. Erros 5xx aparecem no projeto do front e no da API.
3. No Render (**Logs**), busque o id: cada requisição gera uma linha JSON como

```json
{"ts": "2026-11-02T14:03:11.204+00:00", "nivel": "INFO", "logger": "neoprice", "msg": "requisição",
 "request_id": "9f1c…", "metodo": "GET", "rota": "/auth/me", "status": 200, "duracao_ms": 182.4}
```

## Critério de aceite (< 6 min)

Depois de um merge na `main`: os checks do CI levam uns 2–3 min, e o build e deploy
do Render mais 1–2 min. A Vercel publica em menos de 1 min. Para medir, compare o horário
do merge com o horário do deploy no painel do Render (**Events**).
