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
