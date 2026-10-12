# Testes de banco

Verificam o critério de aceite da issue #43: dado um banco vazio, migrations e
seed sobem o schema populado e o seed pode rodar de novo sem duplicar. Também
cobrem as restrições de integridade, o RLS ativo e o gatilho de `updated_at`.

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
