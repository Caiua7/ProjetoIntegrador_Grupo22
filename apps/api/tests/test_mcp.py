"""Conector MCP (issue #130).

O conector só confere o token e repassa cada ferramenta para a rota da API com
o token do usuário. Aqui ficam o contrato de autenticação do servidor de
recurso (metadados, 401 sem token), a lista de ferramentas e o repasse: a
ferramenta devolve o que a rota devolve e o 403 da rota vira um erro de
ferramenta com o motivo.
"""

import json
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import mcp_server
from app.core import auth
from app.main import app

USUARIO_ID = uuid4()
TOKEN_VALIDO = "token-mcp-valido"
CABECALHOS = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"}
INICIO = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "teste", "version": "1"}}


def _validar(token: str):
    if token == TOKEN_VALIDO:
        return USUARIO_ID
    raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")


def _usuario(permissoes: set[str]) -> auth.UsuarioAutenticado:
    return auth.UsuarioAutenticado(
        id=USUARIO_ID,
        nome="Gerente Teste",
        email="gerente@neoprice.test",
        perfil_codigo="gerente_comercial",
        perfil_nome="Gerente Comercial",
        permissoes=frozenset(permissoes),
        access_token=TOKEN_VALIDO,
    )


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(mcp_server, "validar_token", _validar)
    app.dependency_overrides[auth.usuario_atual] = lambda: _usuario({"precificacao.ler"})
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _como(permissoes: set[str]):
    app.dependency_overrides[auth.usuario_atual] = lambda: _usuario(permissoes)


def _nomes(cliente) -> set[str]:
    return {f["name"] for f in _rpc(cliente, "tools/list").json()["result"]["tools"]}


def _rpc(cliente, metodo, params=None, token=TOKEN_VALIDO):
    cabecalhos = dict(CABECALHOS)
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    corpo = {"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {}}
    return cliente.post("/mcp", json=corpo, headers=cabecalhos)


def test_metadados_apontam_para_o_supabase_auth(cliente):
    resposta = cliente.get("/.well-known/oauth-protected-resource/mcp")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["resource"].endswith("/mcp")
    assert dados["authorization_servers"][0].endswith("/auth/v1")


def test_sem_token_responde_401_com_o_endereco_dos_metadados(cliente):
    resposta = _rpc(cliente, "initialize", INICIO, token=None)
    assert resposta.status_code == 401
    assert "resource_metadata" in resposta.headers["www-authenticate"]


def test_token_recusado_responde_401(cliente):
    assert _rpc(cliente, "initialize", INICIO, token="token-falso").status_code == 401


def test_cada_perfil_ve_so_as_ferramentas_que_tem_na_tela(cliente):
    assert _rpc(cliente, "initialize", INICIO).status_code == 200
    leitura = _nomes(cliente)
    assert {"quem_sou_eu", "listar_precificacoes", "ver_precificacao"} <= leitura
    assert not {"fila_de_aprovacao", "decidir_aprovacao", "salvar_cenario", "ver_cenario"} & leitura

    _como({"precificacao.ler", "precificacao.aprovar", "custo.ler"})
    gerente = _nomes(cliente)
    assert {"fila_de_aprovacao", "decidir_aprovacao", "ver_cenario"} <= gerente
    assert "salvar_cenario" not in gerente

    _como({"cadastro.ler", "cadastro.editar"})
    cadastro = _nomes(cliente)
    assert {"buscar_insumos", "cadastrar_insumo", "inativar_insumo"} <= cadastro
    assert "listar_precificacoes" not in cadastro


def test_toda_permissao_de_rota_tem_ferramenta():
    """Nenhuma ação da tela fica de fora: toda permissão exigida por rota aparece em alguma ferramenta."""
    usadas = set().union(*mcp_server.PERMISSOES_DA_FERRAMENTA.values())
    exigidas = {
        "precificacao.ler",
        "precificacao.editar",
        "precificacao.aprovar",
        "custo.ler",
        "cadastro.ler",
        "cadastro.editar",
        "cambio.ler",
        "cambio.editar",
        "parametro_global.ler",
        "parametro_global.editar",
        "parametro_fiscal.ler",
        "parametro_fiscal.editar",
    }
    assert exigidas <= usadas


def test_ferramenta_repassa_a_rota_com_o_usuario_do_token(cliente):
    resposta = _rpc(cliente, "tools/call", {"name": "quem_sou_eu", "arguments": {}})
    resultado = resposta.json()["result"]
    assert resultado["isError"] is False
    dados = json.loads(resultado["content"][0]["text"])
    assert dados["id"] == str(USUARIO_ID)
    assert dados["perfil_codigo"] == "gerente_comercial"


def test_ferramenta_fora_do_perfil_e_barrada_com_o_motivo(cliente):
    # o usuário do fixture não tem precificacao.aprovar
    resposta = _rpc(cliente, "tools/call", {"name": "fila_de_aprovacao", "arguments": {}})
    resultado = resposta.json()["result"]
    assert resultado["isError"] is True
    assert "precificacao.aprovar" in resultado["content"][0]["text"]


def test_403_da_rota_vira_erro_de_ferramenta(cliente):
    # o perfil passa no filtro do conector, mas a rota ainda decide (sem carteira, sem dado)
    _como({"precificacao.ler", "precificacao.aprovar"})
    app.dependency_overrides[auth.usuario_atual] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=403, detail="Seu perfil não tem a permissão precificacao.aprovar.")
    )
    resposta = _rpc(cliente, "tools/call", {"name": "quem_sou_eu", "arguments": {}})
    resultado = resposta.json()["result"]
    assert resultado["isError"] is True
    assert "HTTP 403" in resultado["content"][0]["text"]
