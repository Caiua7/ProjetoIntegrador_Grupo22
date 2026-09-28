"""App FastAPI mínimo desta tarefa: só existe para publicar o contrato de
`/calculate` (schema OpenAPI em /docs e /openapi.json) e servir o mock
para o Squad B. Login, RLS e demais rotas entram por outras stories
(US01–US04)."""

from fastapi import FastAPI

from app.routers.calculate import router as calculate_router

app = FastAPI(
    title="NeoPrice API",
    version="0.1.0",
    description=(
        "API do NeoPrice. O endpoint /calculate está publicado como MOCK "
        "nesta fase (Sprint 1) — ver docs/contrato-calculate.md."
    ),
)

app.include_router(calculate_router)
