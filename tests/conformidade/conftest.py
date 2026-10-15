"""Relatório de divergência por caso da suíte de conformidade.

    pytest tests/conformidade --relatorio-conformidade=relatorio.md

O relatório é escrito ao fim da sessão mesmo quando há caso divergente, que
é justamente quando ele é útil.
"""

from pathlib import Path

import pytest
from conferencia import Relatorio

RELATORIO = pytest.StashKey[Relatorio]()


def pytest_addoption(parser):
    parser.addoption(
        "--relatorio-conformidade",
        metavar="ARQUIVO",
        default=None,
        help="grava em ARQUIVO (Markdown) o resultado de cada caso homologado",
    )


def pytest_configure(config):
    config.stash[RELATORIO] = Relatorio()


def pytest_sessionfinish(session):
    destino = session.config.getoption("--relatorio-conformidade")
    if destino:
        Path(destino).write_text(session.config.stash[RELATORIO].markdown(), encoding="utf-8")


@pytest.fixture(scope="session")
def relatorio(request) -> Relatorio:
    return request.config.stash[RELATORIO]
