# web

SPA do NeoPrice: React 18, TypeScript e Vite. Consome a API e os tipos gerados a partir do contrato OpenAPI de `/calculate`.

## Autenticação local

O frontend usa Supabase Auth para login por e-mail e senha, restauração da sessão, renovação automática de token e recuperação de senha. Para executar localmente, copie `.env.example` para `.env.local` e preencha somente os valores públicos do projeto:

```powershell
Copy-Item .env.example .env.local
```

- `VITE_NEOPRICE_SUPABASE_URL`: URL pública do projeto Supabase.
- `VITE_NEOPRICE_SUPABASE_ANON_KEY`: chave pública `anon` ou `publishable`.

Nunca coloque `SUPABASE_SERVICE_KEY`, uma chave `service_role` ou a senha do banco nessas variáveis ou em qualquer arquivo do frontend. O Vite valida e recusa chaves privilegiadas nessa variável.

No painel Supabase, o administrador do projeto precisa confirmar que o provedor Email está habilitado e configurar a URL do site e as URLs de redirecionamento para os ambientes usados (incluindo `http://localhost:5173` no desenvolvimento). A recuperação de senha envia o link pelo fluxo de e-mail do Supabase e depende dessa configuração. O acesso administrativo e a autenticação real ainda precisam ser verificados; os testes locais não autenticam contra um projeto remoto.

- `VITE_NEOPRICE_API_URL`: endereço da API (padrão `http://localhost:8000`).

Depois do login, o front chama `GET /auth/me` e guarda perfil e permissões. O menu mostra só o que o perfil alcança e uma tela sem permissão cai no painel (`src/app/navigation.ts`). Toda chamada à API passa por `apiFetch` (`src/services/apiClient.ts`), que envia o token, renova a sessão uma vez se a API responder 401 e desloga se ainda falhar.

O formulário não restringe domínios porque o domínio corporativo autorizado ainda não foi definido.

## Organização

| Pasta | Conteúdo |
| :--- | :--- |
| `src/app` | Configuração do app: menu, telas e permissões |
| `src/components/icons` | Ícones próprios com micro-animações (`Icon`, desenhos por grupo, `icons.css`) |
| `src/components/layout` | Barra lateral, topo, marca e avatar |
| `src/features/<área>` | Telas e regras de cada área (auth, dashboard, pricing) |
| `src/services` | Clientes da API e do Supabase |

Tipografia: Bricolage Grotesque nos títulos, Instrument Sans no texto e JetBrains Mono nos números (`--f-titulo`, `--f-texto`, `--f-numero` em `index.css`).
