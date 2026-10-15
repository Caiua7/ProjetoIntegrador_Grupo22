from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.infrastructure.database import get_engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict:
    return {"status": "ok"}


@router.get("/banco")
def health_banco() -> dict:
    try:
        with get_engine().connect() as conexao:
            versao = conexao.execute(text("SELECT version()")).scalar_one()
            schema_criado = conexao.execute(text("SELECT to_regclass('public.produto') IS NOT NULL")).scalar_one()
            produtos = conexao.execute(text("SELECT count(*) FROM produto")).scalar_one() if schema_criado else 0
    except Exception as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "erro", "motivo": str(erro).splitlines()[0]},
        ) from erro

    return {
        "status": "ok",
        "postgres": versao.split(",")[0],
        "schema_criado": schema_criado,
        "produtos": produtos,
    }
