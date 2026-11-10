from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError, AuthRetryableError

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
            raise AuthApiError("invalid JWT", 403, None)
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


class _ConsultaUsuario:
    def __init__(self, linhas):
        self.linhas = linhas

    def __getattr__(self, _nome):
        return lambda *args, **kwargs: self

    def execute(self):
        return SimpleNamespace(data=self.linhas)


def test_carregar_usuario_monta_perfil_e_permissoes(monkeypatch):
    linha = {
        "nome": "Rafael Costa",
        "email": "rafael@empresa.com",
        "ativo": True,
        "perfil": {
            "codigo": "analista_pricing",
            "nome": "Analista de Pricing",
            "perfil_permissao": [{"permissao_codigo": "precificacao.ler"}, {"permissao_codigo": "cadastro.ler"}],
        },
    }
    servico = SimpleNamespace(table=lambda _nome: _ConsultaUsuario([linha]))
    monkeypatch.setattr(auth, "supabase_servico", lambda: servico)
    dados = auth.carregar_usuario(None, USUARIO_ID)
    assert dados["perfil_codigo"] == "analista_pricing"
    assert dados["permissoes"] == ["cadastro.ler", "precificacao.ler"]


def test_carregar_usuario_sem_cadastro_devolve_none(monkeypatch):
    servico = SimpleNamespace(table=lambda _nome: _ConsultaUsuario([]))
    monkeypatch.setattr(auth, "supabase_servico", lambda: servico)
    assert auth.carregar_usuario(None, USUARIO_ID) is None


class _AuthInstavel:
    """Falha `falhas` vezes por erro passageiro do Supabase e depois responde."""

    def __init__(self, falhas):
        self.falhas = falhas
        self.chamadas = 0

    def get_user(self, token):
        self.chamadas += 1
        if self.chamadas <= self.falhas:
            raise AuthRetryableError("timeout", 504)
        return SimpleNamespace(user=SimpleNamespace(id=str(USUARIO_ID)))


def test_falha_passageira_do_supabase_tenta_de_novo(monkeypatch):
    instavel = _AuthInstavel(falhas=1)
    monkeypatch.setattr(auth, "supabase_servico", lambda: SimpleNamespace(auth=instavel))

    assert auth.validar_token("qualquer") == USUARIO_ID
    assert instavel.chamadas == 2


def test_supabase_fora_do_ar_devolve_503_e_nao_desloga(monkeypatch):
    instavel = _AuthInstavel(falhas=2)
    monkeypatch.setattr(auth, "supabase_servico", lambda: SimpleNamespace(auth=instavel))

    with pytest.raises(auth.HTTPException) as erro:
        auth.validar_token("qualquer")

    assert erro.value.status_code == 503


def test_token_recusado_nao_tenta_de_novo(monkeypatch):
    falso = _AuthFalso()
    chamadas = []
    monkeypatch.setattr(
        auth,
        "supabase_servico",
        lambda: SimpleNamespace(auth=SimpleNamespace(get_user=lambda t: chamadas.append(t) or falso.get_user(t))),
    )

    with pytest.raises(auth.HTTPException) as erro:
        auth.validar_token("expirado")

    assert erro.value.status_code == 401
    assert len(chamadas) == 1
