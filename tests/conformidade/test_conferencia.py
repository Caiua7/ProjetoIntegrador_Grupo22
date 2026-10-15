"""Testes da regra de comparação da suíte, sem depender do motor."""

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from conferencia import PENDENTE, Caso, Relatorio, Situacao, conferir


def _caso(saida_esperada: dict) -> Caso:
    return Caso(id="caso_999", arquivo=Path("caso_999.json"), entrada={}, saida_esperada=saida_esperada)


@pytest.mark.parametrize(
    "obtido, ok",
    [
        pytest.param("100.00", True, id="igual"),
        pytest.param("100.01", True, id="um_centavo_acima"),
        pytest.param("99.99", True, id="um_centavo_abaixo"),
        pytest.param("100.0100001", False, id="acima_da_tolerancia"),
        pytest.param("99.989", False, id="abaixo_da_tolerancia"),
    ],
)
def test_tolerancia_de_um_centavo_no_campo_monetario(obtido, ok):
    [c] = conferir(_caso({"preco_bruto": "100.00"}), SimpleNamespace(preco_bruto=Decimal(obtido)))

    assert c.ok is ok


def test_fracao_tem_tolerancia_propria():
    resultado = SimpleNamespace(margem_contribuicao_percentual=Decimal("0.2001"))

    [c] = conferir(_caso({"margem_contribuicao_percentual": "0.2000"}), resultado)

    # 0,0001 seria aceito como centavo, mas numa fração é 0,01 ponto percentual
    assert not c.ok


def test_campo_aninhado_por_caminho_com_ponto():
    resultado = SimpleNamespace(impostos_destacados=SimpleNamespace(icms_st_valor=Decimal("3.20")))

    [c] = conferir(_caso({"impostos_destacados.icms_st_valor": "3.2"}), resultado)

    assert c.ok


def test_numero_no_json_e_recusado_para_nao_perder_precisao():
    with pytest.raises(TypeError, match="string"):
        conferir(_caso({"preco_bruto": 100.1}), SimpleNamespace(preco_bruto=Decimal("100.1")))


def test_caso_com_placeholder_fica_pendente():
    caso = _caso({"preco_bruto": PENDENTE, "receita_operacional_liquida": "80.00"})

    assert caso.campos_pendentes == ["preco_bruto"]


def test_relatorio_lista_situacao_e_divergencias():
    relatorio = Relatorio(versao_motor="1.0.0")
    conforme = _caso({"preco_bruto": "10.00"})
    divergente = Caso(id="caso_002", arquivo=Path("caso_002.json"), entrada={}, saida_esperada={"preco_bruto": "10.00"})
    relatorio.registrar(conforme, Situacao.CONFORME, conferir(conforme, SimpleNamespace(preco_bruto=Decimal("10.00"))))
    relatorio.registrar(
        divergente, Situacao.DIVERGENTE, conferir(divergente, SimpleNamespace(preco_bruto=Decimal("10.05")))
    )

    texto = relatorio.markdown()

    assert "**2 de 30**" in texto
    assert "Conformes: **1**" in texto
    assert "| caso_002 | `preco_bruto` | 10.00 | 10.05 | 0.05 | 0.01 |" in texto
