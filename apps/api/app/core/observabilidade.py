"""Observabilidade da API (issue #65): logs em JSON, id de correlação e Sentry.

Cada requisição ganha um id de correlação. Se o front mandar `X-Request-ID`,
ele é reaproveitado; senão a API gera um. O id volta no cabeçalho da resposta,
entra em toda linha de log da requisição e vira tag no Sentry, então dá para
achar o mesmo problema no navegador, no log do Render e no Sentry.
"""

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

CABECALHO_CORRELACAO = "X-Request-ID"
_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

_id_correlacao: ContextVar[str | None] = ContextVar("id_correlacao", default=None)

logger = logging.getLogger("neoprice")


def id_correlacao_atual() -> str | None:
    return _id_correlacao.get()


def _normalizar_id(recebido: str | None) -> str:
    """Aceita o id do cliente só se for curto e sem caracteres estranhos (evita injeção no log)."""
    if recebido and _ID_VALIDO.match(recebido):
        return recebido
    return uuid.uuid4().hex


class FormatoJson(logging.Formatter):
    """Uma linha JSON por evento, pronta para busca no painel de logs."""

    def format(self, record: logging.LogRecord) -> str:
        evento = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        correlacao = id_correlacao_atual()
        if correlacao:
            evento["request_id"] = correlacao
        extras = getattr(record, "dados", None)
        if isinstance(extras, dict):
            evento.update(extras)
        if record.exc_info:
            evento["erro"] = self.formatException(record.exc_info)
        return json.dumps(evento, ensure_ascii=False, default=str)


def configurar_logs(nivel: str = "INFO") -> None:
    manipulador = logging.StreamHandler()
    manipulador.setFormatter(FormatoJson())
    raiz = logging.getLogger()
    raiz.handlers = [manipulador]
    raiz.setLevel(nivel.upper())
    # o access log do uvicorn fica redundante com o log de requisição abaixo
    logging.getLogger("uvicorn.access").disabled = True


def configurar_sentry(dsn: str, ambiente: str, versao: str | None) -> bool:
    """Liga o Sentry só quando há DSN. Sem DSN (local e testes) não faz nada."""
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=ambiente,
        release=versao or None,
        traces_sample_rate=0.2,
        send_default_pii=False,
    )
    return True


def instalar_correlacao(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlacao(request: Request, call_next) -> Response:
        correlacao_id = _normalizar_id(request.headers.get(CABECALHO_CORRELACAO))
        token = _id_correlacao.set(correlacao_id)
        try:
            import sentry_sdk

            sentry_sdk.get_isolation_scope().set_tag("request_id", correlacao_id)
        except ImportError:
            pass

        inicio = time.perf_counter()
        status_code = 500
        try:
            resposta = await call_next(request)
            status_code = resposta.status_code
            resposta.headers[CABECALHO_CORRELACAO] = correlacao_id
            return resposta
        except Exception as erro:
            logger.exception("erro não tratado")
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(erro)
            except ImportError:
                pass
            return JSONResponse(
                {"detail": "Erro interno no NeoPrice. Informe o código ao suporte.", "request_id": correlacao_id},
                status_code=500,
                headers={CABECALHO_CORRELACAO: correlacao_id},
            )
        finally:
            logger.info(
                "requisição",
                extra={
                    "dados": {
                        "metodo": request.method,
                        "rota": request.url.path,
                        "status": status_code,
                        "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1),
                    }
                },
            )
            _id_correlacao.reset(token)
