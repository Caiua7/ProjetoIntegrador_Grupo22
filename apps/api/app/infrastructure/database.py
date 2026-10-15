from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _url_sqlalchemy(url: str) -> str:
    for prefixo in ("postgresql://", "postgres://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo) :]
    return url


@lru_cache
def get_engine() -> Engine:
    if not settings.DATABASE_URL:
        raise RuntimeError("Banco não configurado: defina DATABASE_URL em apps/api/.env (modelo em .env.example).")
    return create_engine(
        _url_sqlalchemy(settings.DATABASE_URL),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


@lru_cache
def _fabrica_de_sessao() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False)


def get_db() -> Iterator[Session]:
    sessao = _fabrica_de_sessao()()
    try:
        yield sessao
    finally:
        sessao.close()
