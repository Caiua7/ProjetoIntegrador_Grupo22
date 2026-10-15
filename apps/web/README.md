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

O formulário não restringe domínios porque o domínio corporativo autorizado ainda não foi definido. A proteção desta etapa é aplicada no frontend; validação de JWT na API deverá ser concluída antes de proteger recursos da API, conforme o escopo de integração do backend.
