from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core import auth
from app.infrastructure.database import get_db
from app.main import app

USUARIO_ID = uuid4()
DADOS = {
    "nome": "Rafael Costa",
    "email": "rafael@empresa.com",
    "ativo": True,
    "perfil_codigo": "analista_pricing",
    "perfil_nome": "Analista de Pricing",
    "permissoes": ["cadastro.ler", "precificacao.ler"],
}


class _AuthFalso:
    def get_user(self, token):
        if token != "token-valido":
            raise Exception("invalid JWT")
        return SimpleNamespace(user=SimpleNamespace(id=str(USUARIO_ID)))


@pytest.fixture
def dados(monkeypatch):
    dados = dict(DADOS)
    monkeypatch.setattr(auth, "supabase_servico", lambda: SimpleNamespace(auth=_AuthFalso()))
    monkeypatch.setattr(auth, "carregar_usuario", lambda db, uid: dados if uid == USUARIO_ID else None)
    app.dependency_overrides[get_db] = lambda: None
    yield dados
    app.dependency_overrides.clear()


TOKEN_VALIDO = {"Authorization": "Bearer token-valido"}


def test_me_sem_token_devolve_401(dados):
    assert TestClient(app).get("/auth/me").status_code == 401


def test_me_com_token_invalido_devolve_401(dados):
    resposta = TestClient(app).get("/auth/me", headers={"Authorization": "Bearer expirado"})
    assert resposta.status_code == 401


def test_me_devolve_perfil_e_permissoes(dados):
    resposta = TestClient(app).get("/auth/me", headers=TOKEN_VALIDO)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == str(USUARIO_ID)
    assert corpo["perfil_codigo"] == "analista_pricing"
    assert corpo["permissoes"] == ["cadastro.ler", "precificacao.ler"]


def test_usuario_inativo_devolve_403(dados):
    dados["ativo"] = False
    assert TestClient(app).get("/auth/me", headers=TOKEN_VALIDO).status_code == 403


def test_exigir_permissao_barra_quem_nao_tem(dados):
    app_teste = FastAPI()
    app_teste.dependency_overrides[get_db] = lambda: None

    @app_teste.get("/aprovar")
    def aprovar(usuario=Depends(auth.exigir_permissao("precificacao.aprovar"))):
        return {"ok": True}

    @app_teste.get("/ler")
    def ler(usuario=Depends(auth.exigir_permissao("precificacao.ler"))):
        return {"ok": True}

    http = TestClient(app_teste)
    assert http.get("/aprovar", headers=TOKEN_VALIDO).status_code == 403
    assert http.get("/ler", headers=TOKEN_VALIDO).status_code == 200
