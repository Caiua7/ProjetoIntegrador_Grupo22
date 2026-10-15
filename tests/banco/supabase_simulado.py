"""O que só existe pronto no Supabase e as migrations usam: os papéis do
PostgREST, `auth.uid()` e a tabela `auth.users`. Sem isso o schema não sobe
num PostgreSQL puro. Compartilhado pelas fixtures de banco (conftest.py e
test_auditoria.py).
"""

PAPEIS_SUPABASE = ["anon", "authenticated", "service_role"]

# Mesmo comportamento do auth.uid() do Supabase: o id do usuário é o `sub`
# do JWT, que o PostgREST publica em request.jwt.claims. De auth.users, só as
# colunas que as migrations usam.
AUTH_SIMULADO = """
CREATE SCHEMA auth;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
    SELECT (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')::uuid
$$;
CREATE TABLE auth.users (
    id                  uuid PRIMARY KEY,
    email               text,
    raw_user_meta_data  jsonb NOT NULL DEFAULT '{}'
);
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
"""
