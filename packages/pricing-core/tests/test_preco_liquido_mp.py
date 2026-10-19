from decimal import ROUND_HALF_UP, Decimal

import pytest

from pricing_core.preco_liquido_mp import preco_liquido_mp

CENTAVO = Decimal("0.01")
ICMS, PIS, COFINS = Decimal("0.18"), Decimal("0.0165"), Decimal("0.076")


def _centavos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


class TestDesoneracao:
    def test_exemplo_do_criterio_de_aceite_base_liquida_de_icms(self):
        # ICMS 1,80; PIS+COFINS (10 − 1,80) × 0,0925 = 0,7585; líquido 7,4415
        assert preco_liquido_mp("10.00", ICMS, PIS, COFINS) == Decimal("7.4415")

    def test_base_cheia_quando_homologacao_exigir(self):
        # 10 × (1 − 0,18 − 0,0165 − 0,076) = 7,275
        resultado = preco_liquido_mp("10.00", ICMS, PIS, COFINS, pis_cofins_sobre_base_sem_icms=False)
        assert resultado == Decimal("7.275")

    def test_nao_arredonda_antes_da_hora(self):
        resultado = preco_liquido_mp("12.345", ICMS, PIS, COFINS)
        assert resultado != _centavos(resultado)

    def test_preco_zero_devolve_zero(self):
        assert preco_liquido_mp("0", ICMS, PIS, COFINS) == 0

    def test_aliquotas_zero_nao_alteram_o_preco(self):
        assert preco_liquido_mp("10.00", 0, 0, 0) == Decimal("10.00")


class TestCreditoNaoRecuperavel:
    def test_sem_credito_nenhum_mantem_o_preco_bruto(self):
        resultado = preco_liquido_mp("10.00", ICMS, PIS, COFINS, recupera_icms=False, recupera_pis_cofins=False)
        assert resultado == Decimal("10.00")

    def test_so_pis_cofins_recuperavel_usa_base_cheia(self):
        # sem ICMS recuperado, a base é o próprio bruto: 10 × (1 − 0,0925)
        resultado = preco_liquido_mp("10.00", ICMS, PIS, COFINS, recupera_icms=False)
        assert resultado == Decimal("9.075")

    def test_so_icms_recuperavel(self):
        resultado = preco_liquido_mp("10.00", ICMS, PIS, COFINS, recupera_pis_cofins=False)
        assert resultado == Decimal("8.20")

    def test_liquido_nunca_supera_o_bruto(self):
        bruto = Decimal("37.50")
        assert preco_liquido_mp(bruto, ICMS, PIS, COFINS) < bruto


class TestEntradasInvalidas:
    def test_recusa_preco_negativo(self):
        with pytest.raises(ValueError, match="negativ"):
            preco_liquido_mp("-1", ICMS, PIS, COFINS)

    @pytest.mark.parametrize("aliquota", ["-0.01", "1", "1.5"])
    def test_recusa_aliquota_fora_de_zero_a_um(self, aliquota):
        with pytest.raises(ValueError, match="icms"):
            preco_liquido_mp("10", aliquota, PIS, COFINS)

    def test_recusa_creditos_que_superam_o_preco(self):
        with pytest.raises(ValueError, match="supera"):
            preco_liquido_mp("10", "0.9", "0.5", "0.5", pis_cofins_sobre_base_sem_icms=False)

    @pytest.mark.parametrize("valor", [10.0, True, None])
    def test_recusa_tipos_imprecisos(self, valor):
        with pytest.raises(TypeError):
            preco_liquido_mp(valor, ICMS, PIS, COFINS)

    @pytest.mark.parametrize("valor", ["abc", "NaN", "Infinity"])
    def test_recusa_texto_que_nao_e_numero_finito(self, valor):
        with pytest.raises(ValueError):
            preco_liquido_mp(valor, ICMS, PIS, COFINS)
