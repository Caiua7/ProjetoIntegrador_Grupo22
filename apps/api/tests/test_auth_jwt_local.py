"""Validação local do access token pela chave pública do projeto (issue #70).

Sob carga, ir ao Supabase a cada requisição custava ~250 ms e falhava em
2–5% das chamadas com 5–8 simultâneas. A chave aqui é gerada no teste; em
produção vem do JWKS do projeto.
"""

import time
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import auth

URL = "https://projeto.supabase.co"
USUARIO_ID = uuid4()
CHAVE = ec.generate_private_key(ec.SECP256R1())
OUTRA_CHAVE = ec.generate_private_key(ec.SECP256R1())


def token(chave=CHAVE, algoritmo="ES256", **campos):
    agora = int(time.time())
    dados = {
        "sub": str(USUARIO_ID),
        "aud": "authenticated",
        "iss": f"{URL}/auth/v1",
        "iat": agora,
        "exp": agora + 3600,
        "role": "authenticated",
        **campos,
    }
    return jwt.encode(dados, chave, algorithm=algoritmo, headers={"kid": "chave-teste"})


class _JwksFalso:
    def __init__(self, falha=None):
        self.falha = falha
        self.buscas = 0

    def get_signing_key_from_jwt(self, _token):
        self.buscas += 1
        if self.falha:
            raise self.falha
        return SimpleNamespace(key=CHAVE.public_key())


class _SupabaseQueNaoDeveSerChamado:
    def get_user(self, _token):
        raise AssertionError("a validação local não deveria ir ao Supabase")


@pytest.fixture
def jwks(monkeypatch):
    falso = _JwksFalso()
    monkeypatch.setattr(auth.settings, "SUPABASE_URL", URL)
    monkeypatch.setattr(auth, "_cliente_jwks", lambda: falso)
    monkeypatch.setattr(auth, "supabase_servico", lambda: SimpleNamespace(auth=_SupabaseQueNaoDeveSerChamado()))
    return falso


def _status(access_token):
    with pytest.raises(auth.HTTPException) as erro:
        auth.validar_token(access_token)
    return erro.value.status_code


def test_token_assinado_pelo_projeto_vale_sem_ir_ao_supabase(jwks):
    assert auth.validar_token(token()) == USUARIO_ID


@pytest.mark.parametrize(
    "access_token",
    [
        pytest.param(lambda: token(exp=int(time.time()) - 120), id="expirado"),
        pytest.param(lambda: token(chave=OUTRA_CHAVE), id="assinado_por_outra_chave"),
        pytest.param(lambda: token(aud="anon"), id="publico_errado"),
        pytest.param(lambda: token(iss="https://outro.supabase.co/auth/v1"), id="emissor_errado"),
        pytest.param(lambda: token(sub="nao-e-uuid"), id="sub_invalido"),
    ],
)
def test_token_recusado_localmente_devolve_401(jwks, access_token):
    assert _status(access_token()) == 401


def test_sem_sub_devolve_401(jwks):
    agora = int(time.time())
    sem_sub = jwt.encode(
        {"aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": agora + 60},
        CHAVE,
        algorithm="ES256",
        headers={"kid": "chave-teste"},
    )
    assert _status(sem_sub) == 401


def test_token_com_alg_none_nao_passa(jwks, monkeypatch):
    sem_assinatura = jwt.encode({"sub": str(USUARIO_ID)}, None, algorithm="none")
    chamadas = []
    monkeypatch.setattr(
        auth,
        "supabase_servico",
        lambda: SimpleNamespace(
            auth=SimpleNamespace(
                get_user=lambda t: chamadas.append(t) or (_ for _ in ()).throw(auth.AuthApiError("bad", 403, None))
            )
        ),
    )
    assert _status(sem_assinatura) == 401
    assert chamadas == [sem_assinatura]  # foi confirmado no Supabase, que recusou


def test_chave_indisponivel_volta_para_o_supabase(jwks, monkeypatch):
    jwks.falha = jwt.PyJWKClientConnectionError("sem rede")
    monkeypatch.setattr(
        auth,
        "supabase_servico",
        lambda: SimpleNamespace(
            auth=SimpleNamespace(get_user=lambda _t: SimpleNamespace(user=SimpleNamespace(id=str(USUARIO_ID))))
        ),
    )
    assert auth.validar_token(token()) == USUARIO_ID


def test_token_simetrico_legado_volta_para_o_supabase(jwks, monkeypatch):
    legado = jwt.encode({"sub": str(USUARIO_ID)}, "segredo-com-tamanho-suficiente-para-hs256", algorithm="HS256")
    monkeypatch.setattr(
        auth,
        "supabase_servico",
        lambda: SimpleNamespace(
            auth=SimpleNamespace(get_user=lambda _t: SimpleNamespace(user=SimpleNamespace(id=str(USUARIO_ID))))
        ),
    )
    assert auth.validar_token(legado) == USUARIO_ID
    assert jwks.buscas == 0
