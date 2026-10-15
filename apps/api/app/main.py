from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.calculate import router as calculate_router
from app.routers.health import router as health_router

app = FastAPI(
    title="NeoPrice API",
    version="0.1.0",
    description=(
        "API do NeoPrice. O endpoint /calculate está publicado como MOCK "
        "nesta fase (Sprint 1) — ver docs/contrato-calculate.md."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(calculate_router)
