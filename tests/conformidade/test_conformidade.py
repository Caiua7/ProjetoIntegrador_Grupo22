"""Suíte de conformidade do motor de precificação (RNF08 / US22).

Compara a saída de `pricing_core.engine.calcular` contra os 30 casos
homologados com o PO. Critério de aceite (RNF08): divergência máxima de
R$ 0,01 por campo monetário. A regra de comparação está em
`conferencia.py`; o relatório por caso, em `conftest.py`.

Enquanto `pricing_core.engine` não existir (US16/US19), os casos ficam
com skip, mas o formato de cada JSON já é validado contra o contrato: um
caso mal preenchido na homologação falha aqui, e não só quando o motor
chegar. O endpoint mock de apps/api NÃO é o alvo desta suíte.
"""

from pathlib import Path

import pytest

from conferencia import PENDENTE, Situacao, carregar_casos, conferir, para_decimal
from pricing_core.contracts import ENGINE_CONTRACT_VERSION, CalculateRequest, CalculateResponse, DomainErrorCodigo

CASOS_DIR = Path(__file__).parent / "casos"
CASOS = carregar_casos(CASOS_DIR)

try:
    from pricing_core.engine import calcular  # type: ignore[import-not-found]
except ImportError:
    calcular = None


@pytest.fixture(scope="module", autouse=True)
def _versao_do_motor(relatorio):
    if calcular is not None:
        relatorio.versao_motor = ENGINE_CONTRACT_VERSION


@pytest.mark.parametrize("caso", carregar_casos(CASOS_DIR, incluir_template=True), ids=lambda c: c.arquivo.stem)
def test_caso_bem_formado(caso):
    assert caso.id == caso.arquivo.stem, "o id do caso deve ser o nome do arquivo"

    CalculateRequest.model_validate(caso.entrada)

    if caso.erro_esperado is not None:
        assert caso.erro_esperado in {c.value for c in DomainErrorCodigo}
        assert not caso.saida_esperada, "caso de erro não tem saida_esperada"
        return

    assert caso.saida_esperada, "informe ao menos um campo em saida_esperada"
    for campo, valor in caso.saida_esperada.items():
        _exigir_campo_do_contrato(campo)
        if valor != PENDENTE:
            para_decimal(valor)


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.id)
def test_caso_homologado(caso, relatorio):
    if calcular is None:
        relatorio.registrar(caso, Situacao.SEM_MOTOR)
        pytest.skip("pricing_core.engine ainda não implementado (US16/US19 — Sprint 3)")
    if caso.campos_pendentes:
        relatorio.registrar(caso, Situacao.PENDENTE, detalhe=", ".join(caso.campos_pendentes))
        pytest.skip(f"campos ainda sem valor do PO: {', '.join(caso.campos_pendentes)}")

    entrada = CalculateRequest.model_validate(caso.entrada)

    if caso.erro_esperado is not None:
        _conferir_erro(caso, entrada, relatorio)
        return

    try:
        resultado = calcular(entrada)
    except Exception as erro:
        relatorio.registrar(caso, Situacao.ERRO, detalhe=f"{type(erro).__name__}: {erro}")
        raise

    conferencias = conferir(caso, resultado)
    divergentes = [c for c in conferencias if not c.ok]
    relatorio.registrar(caso, Situacao.DIVERGENTE if divergentes else Situacao.CONFORME, conferencias)

    assert not divergentes, "\n".join(
        f"{c.campo}: esperado={c.esperado} obtido={c.obtido} diferença={c.diferenca} > {c.tolerancia}"
        for c in divergentes
    )


def _conferir_erro(caso, entrada, relatorio):
    """O motor sinaliza entrada matematicamente inválida com uma exceção que
    carrega `codigo` (DomainErrorCodigo), e a API a traduz para 422."""
    try:
        calcular(entrada)
    except Exception as erro:
        codigo = getattr(erro, "codigo", None)
        obtido = getattr(codigo, "value", codigo)
        if obtido == caso.erro_esperado:
            relatorio.registrar(caso, Situacao.CONFORME, detalhe=f"recusado com {obtido}")
            return
        relatorio.registrar(caso, Situacao.ERRO, detalhe=f"esperado {caso.erro_esperado}, veio {type(erro).__name__}: {erro}")
        raise
    relatorio.registrar(caso, Situacao.DIVERGENTE, detalhe=f"esperado erro {caso.erro_esperado}, o motor calculou")
    pytest.fail(f"esperado erro de domínio {caso.erro_esperado}, mas o motor calculou")


def _exigir_campo_do_contrato(campo: str) -> None:
    """Aceita caminho com ponto, como `impostos_destacados.icms_st_valor`."""
    modelo = CalculateResponse
    for parte in campo.split("."):
        assert isinstance(modelo, type) and parte in getattr(modelo, "model_fields", {}), (
            f"'{campo}' não é campo de CalculateResponse"
        )
        modelo = modelo.model_fields[parte].annotation
