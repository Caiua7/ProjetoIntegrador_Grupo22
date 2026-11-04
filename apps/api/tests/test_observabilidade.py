import json
import logging

from fastapi.testclient import TestClient

from app.core.observabilidade import FormatoJson, _normalizar_id
from app.main import app


def test_resposta_traz_id_de_correlacao_gerado():
    resposta = TestClient(app).get("/health")
    assert resposta.status_code == 200
    assert len(resposta.headers["X-Request-ID"]) == 32


def test_reaproveita_id_enviado_pelo_front():
    resposta = TestClient(app).get("/health", headers={"X-Request-ID": "front-abc123"})
    assert resposta.headers["X-Request-ID"] == "front-abc123"


def test_descarta_id_malicioso():
    assert _normalizar_id("abc\nlinha falsa") != "abc\nlinha falsa"
    assert _normalizar_id("x" * 200) != "x" * 200


def test_log_sai_em_json_com_dados_extras():
    registro = logging.LogRecord("neoprice", logging.INFO, __file__, 1, "requisição", None, None)
    registro.dados = {"status": 200}
    evento = json.loads(FormatoJson().format(registro))
    assert evento["msg"] == "requisição"
    assert evento["status"] == 200
    assert evento["nivel"] == "INFO"


def test_erro_nao_tratado_vira_500_com_cors_e_id():
    from fastapi import APIRouter

    rota = APIRouter()

    @rota.get("/_teste/explode")
    def explode():
        raise RuntimeError("falha de teste")

    app.include_router(rota)
    origem = "http://localhost:5173"
    resposta = TestClient(app, raise_server_exceptions=False).get(
        "/_teste/explode", headers={"Origin": origem, "X-Request-ID": "abc-123"}
    )

    assert resposta.status_code == 500
    assert resposta.headers["access-control-allow-origin"] == origem
    assert resposta.headers["x-request-id"] == "abc-123"
    assert resposta.json()["request_id"] == "abc-123"
