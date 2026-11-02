from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import tax_rates

TOKEN = {"Authorization": "Bearer token-valido"}

# Linha como o banco devolve com select("*"): inclui colunas que a API não expõe
LINHA = {
    "id": str(uuid4()),
    "uf_destino": "SP",
    "ncm_codigo": None,
    "regime_tributario": "lucro_real",
    "vigencia_inicio": "2026-01-01",
    "pis_percentual": "0.0165",
    "cofins_percentual": "0.076",
    "icms_percentual": "0.18",
    "ipi_percentual": "0",
    "icms_interno_percentual": "0.18",
    "fcp_percentual": "0",
    "mva_percentual": "0",
    "created_by": None,
    "updated_by": None,
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:00:00+00:00",
}


class ConsultaFalsa:
    def __getattr__(self, _nome):
        return lambda *args, **kwargs: self

    def execute(self):
        return SimpleNamespace(data=[dict(LINHA)], count=1)


@pytest.fixture
def cliente(monkeypatch):
    usuario = auth.UsuarioAutenticado(
        id=uuid4(),
        nome="Ana",
        email="ana@empresa.com",
        perfil_codigo="analista_pricing",
        perfil_nome="Analista de Pricing",
        permissoes=frozenset({"parametro_fiscal.ler"}),
        access_token="token-valido",
    )
    app.dependency_overrides[auth.usuario_atual] = lambda: usuario
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr(tax_rates, "_consulta_base", lambda _usuario: ConsultaFalsa())
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_lista_ignora_colunas_internas_do_banco(cliente):
    resposta = cliente.get("/parametros-fiscais/aliquotas", headers=TOKEN)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo[0]["uf_destino"] == "SP"
    assert "created_by" not in corpo[0]


def test_resolver_ignora_colunas_internas_do_banco(cliente):
    resposta = cliente.get(
        "/parametros-fiscais/aliquotas/resolver",
        params={"uf_destino": "SP", "ncm_codigo": "21069030", "regime_tributario": "lucro_real"},
        headers=TOKEN,
    )
    assert resposta.status_code == 200
    assert "updated_by" not in resposta.json()
