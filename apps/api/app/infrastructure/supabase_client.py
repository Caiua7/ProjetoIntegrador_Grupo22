from functools import lru_cache

from app.core.config import settings
from supabase import Client, ClientOptions, create_client


def _exigir(**variaveis: str) -> None:
    faltando = [nome for nome, valor in variaveis.items() if not valor]
    if faltando:
        raise RuntimeError(
            f"Supabase não configurado: defina {', '.join(faltando)} em apps/api/.env (modelo em .env.example)."
        )


@lru_cache
def supabase_servico() -> Client:
    _exigir(SUPABASE_URL=settings.SUPABASE_URL, SUPABASE_SERVICE_KEY=settings.SUPABASE_SERVICE_KEY)
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def supabase_do_usuario(access_token: str) -> Client:
    _exigir(SUPABASE_URL=settings.SUPABASE_URL, SUPABASE_ANON_KEY=settings.SUPABASE_ANON_KEY)
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        options=ClientOptions(headers={"Authorization": f"Bearer {access_token}"}),
    )
