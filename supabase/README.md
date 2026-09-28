# supabase

Banco PostgreSQL do NeoPrice.

- `migrations/`: schema, índices, políticas de RLS e gatilhos de auditoria, em ordem de aplicação.
- `seed/`: carga idempotente dos dados de referência (NCM, CEP/IBGE, alíquotas por UF). Pode rodar mais de uma vez sem duplicar registros.
