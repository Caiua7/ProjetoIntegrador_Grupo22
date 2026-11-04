"""Gravações passando pelo construtor de consultas real do postgrest.

Os outros testes usam clientes falsos que aceitam qualquer método; por isso
`.insert(...).select("*")`, que não existe no supabase-py 2.x, passou no CI e
só quebrou no staging (503 ao criar precificação, cadastro e alíquota).
Aqui o HTTP é simulado, mas a cadeia de métodos é a da biblioteca.
"""

import json
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from postgrest import SyncPostgrestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app
from app.routers import precificacoes, tax_rates

USUARIO_ID = uuid4()
TOKEN = {"Authorization": "Bearer token-postgrest"}


def _devolve_o_que_foi_gravado(request: httpx.Request) -> httpx.Response:
    corpo = json.loads(request.content or b"{}")
    linha = {
        "id": str(uuid4()),
        "status": "em_preenchimento",
        "created_at": "2026-11-03T00:00:00Z",
        "updated_at": "2026-11-03T00:00:00Z",
        **(corpo if isinstance(corpo, dict) else {}),
    }
    return httpx.Response(201 if request.method == "POST" else 200, json=[linha])


class _ClienteReal:
    def __init__(self):
        self.postgrest = SyncPostgrestClient(
            "http://postgrest.teste",
            http_client=httpx.Client(
                base_url="http://postgrest.teste", transport=httpx.MockTransport(_devolve_o_que_foi_gravado)
            ),
        )

    def table(self, nome):
        return self.postgrest.from_(nome)


@pytest.fixture
def http(monkeypatch):
    dados = {
        "nome": "Analista",
        "email": "analista@example.com",
        "ativo": True,
        "perfil_codigo": "analista_pricing",
        "perfil_nome": "Analista de Pricing",
        "permissoes": ["precificacao.editar", "parametro_fiscal.editar"],
    }
    monkeypatch.setattr(auth, "validar_token", lambda token: USUARIO_ID if token == "token-postgrest" else UUID(int=0))
    monkeypatch.setattr(auth, "carregar_usuario", lambda _db, uid: dados if uid == USUARIO_ID else None)
    for modulo in (precificacoes, tax_rates):
        monkeypatch.setattr(modulo, "supabase_do_usuario", lambda _token: _ClienteReal())
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_cria_precificacao(http):
    entrada = {
        "cliente_id": str(uuid4()),
        "produto_id": str(uuid4()),
        "modalidade_comercial": "full_service_nacional",
        "uf_destino": "MG",
        "frete": "cif",
        "regime_tributario": "lucro_presumido",
    }
    resposta = http.post("/precificacoes", headers=TOKEN, json=entrada)
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["uf_destino"] == "MG"


def test_cria_aliquota(http):
    entrada = {
        "uf_destino": "MG",
        "ncm_codigo": None,
        "regime_tributario": "lucro_presumido",
        "vigencia_inicio": "2026-01-01",
        "pis_percentual": "0.0165",
        "cofins_percentual": "0.076",
        "icms_percentual": "0.12",
        "ipi_percentual": "0",
        "icms_interno_percentual": "0.18",
        "fcp_percentual": "0",
        "mva_percentual": "0",
    }
    resposta = http.post("/parametros-fiscais/aliquotas", headers=TOKEN, json=entrada)
    assert resposta.status_code == 201, resposta.text
