import pytest

from app.core import auth


@pytest.fixture(autouse=True)
def _cache_de_perfil_limpo():
    """Cada teste monta o próprio usuário; o cache de perfil não pode vazar entre eles."""
    auth.limpar_cache_usuarios()
    yield
    auth.limpar_cache_usuarios()
