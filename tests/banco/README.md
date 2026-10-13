# Testes de banco

- `test_migrations_seed.py` (issue #43): dado um banco vazio, migrations e seed
  sobem o schema populado e o seed pode rodar de novo sem duplicar. Também cobre
  as restrições de integridade, o RLS ativo e o gatilho de `updated_at`.
- `test_rls_carteira.py` (issue #45): isolamento entre perfis e carteiras. Um
  analista restrito a uma carteira não enxerga clientes nem precificações de
  outra, cada perfil só alcança o que a matriz de acesso permite e ninguém
  consegue se promover.

## Como rodar

Precisam de um PostgreSQL 15 ou superior. Com o banco local do Supabase
(`supabase start`):

```bash
pip install pytest "psycopg[binary]"
export NEOPRICE_TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
pytest tests/banco
```

Sem `NEOPRICE_TEST_DATABASE_URL` os testes ficam com skip.

A suíte cria um schema temporário (`teste_<hash>`), aplica ali as migrations e
os seeds e o remove ao final: não toca nas tabelas de `public`.

Fora do Supabase, a fixture cria os papéis `anon`, `authenticated` e
`service_role` e um `auth.uid()` simulado, que lê o `sub` de
`request.jwt.claims` como o original. Os papéis ficam no servidor depois do
teste; o schema `auth` simulado é removido.
