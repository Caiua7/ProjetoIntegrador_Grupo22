from datetime import date, timedelta
from decimal import Decimal

import pytest

from pricing_core.cotacao import (
    Cotacao,
    CotacaoAmbigua,
    CotacaoNaoEncontrada,
    cotacoes_vigentes,
    esta_vigente,
    resolver_cotacao,
)

HOJE = date(2026, 10, 18)
MP = "mp-1"


def cotacao(**campos) -> Cotacao:
    base = {
        "id": "c1",
        "materia_prima_id": MP,
        "fornecedor_id": "f1",
        "moeda": "BRL",
        "preco": Decimal("10.00"),
        "volume_minimo": Decimal("0"),
        "validade_inicio": date(2026, 10, 1),
        "validade_fim": date(2026, 10, 31),
    }
    return Cotacao(**{**base, **campos})


def faixas_do_criterio() -> list[Cotacao]:
    """Faixas de 0–100 kg e 101–500 kg do critério de aceite da US25."""
    return [
        cotacao(id="faixa-1", volume_minimo=Decimal("0"), preco=Decimal("10.00")),
        cotacao(id="faixa-2", volume_minimo=Decimal("101"), preco=Decimal("8.00")),
    ]


class TestVigencia:
    def test_vigente_no_meio_do_periodo(self):
        assert esta_vigente(cotacao(), HOJE)

    def test_inicio_e_inclusivo(self):
        assert esta_vigente(cotacao(), date(2026, 10, 1))

    def test_fim_e_inclusivo(self):
        assert esta_vigente(cotacao(), date(2026, 10, 31))

    def test_vespera_do_inicio_nao_vale(self):
        assert not esta_vigente(cotacao(), date(2026, 10, 1) - timedelta(days=1))

    def test_dia_seguinte_ao_fim_nao_vale(self):
        assert not esta_vigente(cotacao(), date(2026, 10, 31) + timedelta(days=1))

    def test_sem_fim_vale_para_qualquer_data_futura(self):
        assert esta_vigente(cotacao(validade_fim=None), date(2030, 1, 1))

    def test_validade_de_um_dia_so(self):
        c = cotacao(validade_inicio=HOJE, validade_fim=HOJE)
        assert esta_vigente(c, HOJE)
        assert not esta_vigente(c, HOJE + timedelta(days=1))


class TestCotacoesVigentes:
    def test_filtra_pela_materia_prima(self):
        outras = [cotacao(id="a", materia_prima_id="mp-2"), cotacao(id="b")]
        assert [c.id for c in cotacoes_vigentes(outras, MP, HOJE)] == ["b"]

    def test_descarta_cotacoes_fora_da_validade(self):
        vencida = cotacao(id="vencida", validade_inicio=date(2026, 8, 1), validade_fim=date(2026, 9, 30))
        futura = cotacao(id="futura", validade_inicio=date(2026, 11, 1), validade_fim=None)
        vigente = cotacao(id="vigente")
        assert [c.id for c in cotacoes_vigentes([vencida, futura, vigente], MP, HOJE)] == ["vigente"]

    def test_sem_cotacao_devolve_lista_vazia(self):
        assert cotacoes_vigentes([], MP, HOJE) == []

    def test_ordena_da_menor_para_a_maior_faixa(self):
        faixa_2 = cotacao(id="f2", volume_minimo=Decimal("101"))
        faixa_1 = cotacao(id="f1", volume_minimo=Decimal("0"))
        faixa_3 = cotacao(id="f3", volume_minimo=Decimal("501"))
        assert [c.id for c in cotacoes_vigentes([faixa_3, faixa_1, faixa_2], MP, HOJE)] == ["f1", "f2", "f3"]

    def test_na_mesma_faixa_a_validade_mais_recente_vem_primeiro(self):
        antiga = cotacao(id="antiga", validade_inicio=date(2026, 9, 1))
        recente = cotacao(id="recente", validade_inicio=date(2026, 10, 10))
        assert [c.id for c in cotacoes_vigentes([antiga, recente], MP, HOJE)] == ["recente", "antiga"]

    def test_aceita_qualquer_iteravel(self):
        assert len(cotacoes_vigentes(iter([cotacao()]), MP, HOJE)) == 1


class TestResolverCotacao:
    def test_criterio_de_aceite_250_kg_devolve_a_segunda_faixa(self):
        assert resolver_cotacao(faixas_do_criterio(), MP, 250, HOJE).id == "faixa-2"

    @pytest.mark.parametrize(
        ("quantidade", "esperada"),
        [
            ("1", "faixa-1"),
            ("100", "faixa-1"),  # último kg da primeira faixa
            ("100.5", "faixa-1"),  # ainda abaixo do mínimo de 101
            ("101", "faixa-2"),  # o mínimo é inclusivo
            ("250", "faixa-2"),
            ("500", "faixa-2"),
            ("100000", "faixa-2"),  # a última faixa é aberta
        ],
    )
    def test_bordas_de_faixa(self, quantidade, esperada):
        assert resolver_cotacao(faixas_do_criterio(), MP, quantidade, HOJE).id == esperada

    def test_aceita_decimal_e_inteiro(self):
        assert resolver_cotacao(faixas_do_criterio(), MP, Decimal("250"), HOJE).id == "faixa-2"
        assert resolver_cotacao(faixas_do_criterio(), MP, 250, HOJE).id == "faixa-2"

    def test_a_ordem_da_lista_nao_importa(self):
        invertidas = list(reversed(faixas_do_criterio()))
        assert resolver_cotacao(invertidas, MP, 250, HOJE).id == "faixa-2"

    def test_sem_nenhuma_cotacao_levanta_nao_encontrada(self):
        with pytest.raises(CotacaoNaoEncontrada, match="vigente"):
            resolver_cotacao([], MP, 250, HOJE)

    def test_so_cotacao_vencida_ou_futura_levanta_nao_encontrada(self):
        vencida = cotacao(id="vencida", validade_inicio=date(2026, 8, 1), validade_fim=date(2026, 9, 30))
        futura = cotacao(id="futura", validade_inicio=date(2026, 11, 1), validade_fim=None)
        with pytest.raises(CotacaoNaoEncontrada, match="vigente"):
            resolver_cotacao([vencida, futura], MP, 250, HOJE)

    def test_cotacao_de_outra_materia_prima_nao_serve(self):
        with pytest.raises(CotacaoNaoEncontrada, match="vigente"):
            resolver_cotacao([cotacao(materia_prima_id="mp-2")], MP, 250, HOJE)

    def test_quantidade_abaixo_do_menor_minimo_levanta_nao_encontrada(self):
        so_a_partir_de_50 = [cotacao(volume_minimo=Decimal("50"))]
        with pytest.raises(CotacaoNaoEncontrada, match="volume mínimo"):
            resolver_cotacao(so_a_partir_de_50, MP, 30, HOJE)

    def test_resolve_pela_data_de_referencia(self):
        antiga = cotacao(id="antiga", validade_inicio=date(2026, 9, 1), validade_fim=date(2026, 9, 30))
        atual = cotacao(id="atual", validade_inicio=date(2026, 10, 1), validade_fim=None)
        assert resolver_cotacao([antiga, atual], MP, 10, date(2026, 9, 15)).id == "antiga"
        assert resolver_cotacao([antiga, atual], MP, 10, HOJE).id == "atual"

    def test_desempate_na_mesma_faixa_fica_com_a_validade_mais_recente(self):
        antiga = cotacao(id="antiga", validade_inicio=date(2026, 9, 1), validade_fim=None)
        recente = cotacao(id="recente", fornecedor_id="f2", validade_inicio=date(2026, 10, 10), validade_fim=None)
        assert resolver_cotacao([antiga, recente], MP, 10, HOJE).id == "recente"

    def test_a_faixa_vale_mais_que_a_validade(self):
        faixa_alta_antiga = cotacao(
            id="alta", volume_minimo=Decimal("101"), validade_inicio=date(2026, 9, 1), validade_fim=None
        )
        faixa_baixa_recente = cotacao(
            id="baixa", volume_minimo=Decimal("0"), validade_inicio=date(2026, 10, 15), validade_fim=None
        )
        assert resolver_cotacao([faixa_baixa_recente, faixa_alta_antiga], MP, 250, HOJE).id == "alta"

    def test_empate_entre_fornecedores_levanta_ambiguidade(self):
        a = cotacao(id="a", fornecedor_id="f1")
        b = cotacao(id="b", fornecedor_id="f2")
        with pytest.raises(CotacaoAmbigua, match="empatadas") as erro:
            resolver_cotacao([a, b], MP, 10, HOJE)
        assert "f1" in str(erro.value)
        assert "f2" in str(erro.value)

    def test_informar_o_fornecedor_resolve_a_ambiguidade(self):
        a = cotacao(id="a", fornecedor_id="f1")
        b = cotacao(id="b", fornecedor_id="f2")
        assert resolver_cotacao([a, b], MP, 10, HOJE, fornecedor_id="f2").id == "b"

    def test_fornecedor_sem_cotacao_vigente_levanta_nao_encontrada(self):
        with pytest.raises(CotacaoNaoEncontrada, match="fornecedor informado"):
            resolver_cotacao([cotacao()], MP, 10, HOJE, fornecedor_id="f9")

    @pytest.mark.parametrize("quantidade", ["0", "-1", -5])
    def test_recusa_quantidade_nao_positiva(self, quantidade):
        with pytest.raises(ValueError, match="positiva"):
            resolver_cotacao(faixas_do_criterio(), MP, quantidade, HOJE)

    def test_recusa_float(self):
        with pytest.raises(TypeError):
            resolver_cotacao(faixas_do_criterio(), MP, 250.5, HOJE)

    def test_recusa_texto_que_nao_e_numero(self):
        with pytest.raises(ValueError):
            resolver_cotacao(faixas_do_criterio(), MP, "abc", HOJE)


class TestValidacaoDoModelo:
    def test_recusa_preco_negativo(self):
        with pytest.raises(ValueError, match="preco"):
            cotacao(preco=Decimal("-1"))

    def test_recusa_volume_minimo_negativo(self):
        with pytest.raises(ValueError, match="volume_minimo"):
            cotacao(volume_minimo=Decimal("-1"))

    def test_recusa_fim_anterior_ao_inicio(self):
        with pytest.raises(ValueError, match="validade_fim"):
            cotacao(validade_inicio=date(2026, 10, 10), validade_fim=date(2026, 10, 9))

    @pytest.mark.parametrize("moeda", ["brl", "BR", "REAIS", "B1L"])
    def test_recusa_moeda_fora_do_padrao_iso(self, moeda):
        with pytest.raises(ValueError, match="moeda"):
            cotacao(moeda=moeda)

    def test_recusa_prazo_negativo(self):
        with pytest.raises(ValueError, match="prazo"):
            cotacao(prazo_entrega_dias=-1)

    @pytest.mark.parametrize("campo", ["preco", "volume_minimo"])
    def test_recusa_float(self, campo):
        with pytest.raises(TypeError):
            cotacao(**{campo: 1.5})

    def test_recusa_valor_nao_finito(self):
        with pytest.raises(ValueError, match="finitos"):
            cotacao(preco=Decimal("NaN"))
