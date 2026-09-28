from decimal import ROUND_HALF_UP, Decimal, localcontext

import pytest

from pricing_core.encargo import taxa_encargo, valor_encargo

CENTAVO = Decimal("0.01")


def _centavos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


class TestTaxaEncargo:
    def test_criterio_de_aceite_45_dias_a_1_2_porcento(self):
        # (1,012)^1,5 − 1 conferido por outro caminho: 1,012 × √1,012 − 1
        with localcontext() as ctx:
            ctx.prec = 34
            esperado = Decimal("1.012") * Decimal("1.012").sqrt() - 1

        assert taxa_encargo(Decimal("0.012"), 45) == esperado
        assert esperado.quantize(Decimal("0.000001")) == Decimal("0.018054")

    def test_prazo_de_um_mes_devolve_a_propria_taxa(self):
        assert taxa_encargo(Decimal("0.012"), 30) == Decimal("0.012")

    def test_prazo_de_dois_meses_capitaliza_juros_compostos(self):
        # 1,012² − 1 = 0,024144, maior que os 0,024 de juros simples
        assert taxa_encargo(Decimal("0.012"), 60) == Decimal("0.024144")

    def test_prazo_zero_nao_gera_encargo(self):
        assert taxa_encargo(Decimal("0.012"), 0) == 0

    def test_taxa_nula_nao_gera_encargo(self):
        assert taxa_encargo(Decimal("0"), 45) == 0

    @pytest.mark.parametrize("prazo", ["0.5", "15", "37.5", "44.9"])
    def test_prazo_fracionado_fica_entre_zero_e_a_taxa_capitalizada(self, prazo):
        taxa = taxa_encargo(Decimal("0.012"), Decimal(prazo))
        assert 0 < taxa < taxa_encargo(Decimal("0.012"), 45)

    def test_prazo_de_meio_mes_e_a_raiz_da_taxa_mensal(self):
        with localcontext() as ctx:
            ctx.prec = 34
            esperado = Decimal("1.012").sqrt() - 1
        assert taxa_encargo(Decimal("0.012"), 15) == esperado

    def test_encargo_cresce_com_o_prazo(self):
        prazos = [0, 7, 15, 28, 30, 45, 60, 90, 120]
        taxas = [taxa_encargo(Decimal("0.012"), p) for p in prazos]
        assert taxas == sorted(taxas)
        assert len(set(taxas)) == len(taxas)

    def test_aceita_texto_e_inteiro(self):
        assert taxa_encargo("0.012", "45") == taxa_encargo(Decimal("0.012"), 45)


class TestValorEncargo:
    def test_aplica_a_taxa_sobre_a_base_de_preco(self):
        taxa = taxa_encargo(Decimal("0.012"), 45)
        assert _centavos(valor_encargo(taxa, Decimal("100.00"))) == Decimal("1.81")

    def test_base_zero_nao_gera_encargo(self):
        assert valor_encargo(Decimal("0.018"), Decimal("0")) == 0

    def test_nao_arredonda_antes_da_hora(self):
        taxa = taxa_encargo(Decimal("0.012"), 45)
        valor = valor_encargo(taxa, Decimal("100.00"))
        assert valor != _centavos(valor)


class TestEntradasInvalidas:
    @pytest.mark.parametrize(
        ("taxa", "prazo"),
        [(Decimal("-0.01"), 30), (Decimal("0.012"), -1)],
    )
    def test_recusa_valores_negativos(self, taxa, prazo):
        with pytest.raises(ValueError, match="negativ"):
            taxa_encargo(taxa, prazo)

    def test_recusa_base_negativa(self):
        with pytest.raises(ValueError, match="negativ"):
            valor_encargo(Decimal("0.01"), Decimal("-100"))

    @pytest.mark.parametrize("valor", [0.012, True, None, [0.012]])
    def test_recusa_tipos_imprecisos_ou_invalidos(self, valor):
        with pytest.raises(TypeError):
            taxa_encargo(valor, 30)

    @pytest.mark.parametrize("valor", ["abc", "", "NaN", "Infinity"])
    def test_recusa_texto_que_nao_e_numero_finito(self, valor):
        with pytest.raises(ValueError):
            taxa_encargo(valor, 30)
