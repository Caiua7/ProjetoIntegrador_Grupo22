from uuid import uuid4

from app.core import auth

USUARIO_ID = uuid4()
ATIVO = {
    "nome": "Ana",
    "email": "ana@empresa.com",
    "ativo": True,
    "perfil_codigo": "analista_pricing",
    "perfil_nome": "Analista",
    "permissoes": [],
}


def _contar_chamadas(monkeypatch, dados):
    chamadas = []

    def carregar(_db, uid):
        chamadas.append(uid)
        return dados

    monkeypatch.setattr(auth, "carregar_usuario", carregar)
    return chamadas


def test_perfil_ativo_fica_em_cache(monkeypatch):
    chamadas = _contar_chamadas(monkeypatch, ATIVO)
    assert auth._perfil_do_usuario(None, USUARIO_ID) == ATIVO
    assert auth._perfil_do_usuario(None, USUARIO_ID) == ATIVO
    assert len(chamadas) == 1


def test_cache_expira(monkeypatch):
    chamadas = _contar_chamadas(monkeypatch, ATIVO)
    agora = [1000.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: agora[0])
    auth._perfil_do_usuario(None, USUARIO_ID)
    agora[0] += auth.CACHE_PERFIL_SEGUNDOS + 1
    auth._perfil_do_usuario(None, USUARIO_ID)
    assert len(chamadas) == 2


def test_usuario_inativo_ou_sem_cadastro_nao_fica_em_cache(monkeypatch):
    chamadas = _contar_chamadas(monkeypatch, {**ATIVO, "ativo": False})
    auth._perfil_do_usuario(None, USUARIO_ID)
    auth._perfil_do_usuario(None, USUARIO_ID)
    chamadas_sem_cadastro = _contar_chamadas(monkeypatch, None)
    auth._perfil_do_usuario(None, USUARIO_ID)
    auth._perfil_do_usuario(None, USUARIO_ID)
    assert len(chamadas) == 2 and len(chamadas_sem_cadastro) == 2
