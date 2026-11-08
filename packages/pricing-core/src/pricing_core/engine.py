"""Motor puro de precificação do NeoPrice (US16/US19).

Este módulo depende apenas dos contratos e das regras de domínio do
``pricing-core``. Não acessa banco, rede, arquivos nem frameworks web.

ATENÇÃO — três premissas abaixo são provisórias e DEVEM ser confirmadas
com o Product Owner antes da homologação comercial:
1. ``Base = CustoTotal`` na parcela ``m × Base``.
2. ``Comissao$ = Comissao × PB``.
3. ``MaterialCliente = CustoEnviadoCliente = valor_material_cliente``.
As premissas foram mantidas para viabilizar a implementação e os testes,
não representam confirmação de regra fiscal/comercial pelo PO.
"""

from decimal import ROUND_HALF_UP, Decimal, localcontext

from pricing_core.contracts import (
    ENGINE_CONTRACT_VERSION,
    CalculateMetadata,
    CalculateRequest,
    CalculateResponse,
    DomainErrorCodigo,
    ImpostosDestacados,
    IsencaoMaoDeObraInfo,
)
from pricing_core.custos import (
    calcular_custo_embalagem,
    calcular_custo_mp,
    calcular_custo_perda,
    calcular_custo_total,
)
from pricing_core.encargo import taxa_encargo
from pricing_core.numeros import PRECISAO

CENTAVO = Decimal("0.01")
ZERO = Decimal("0")
UM = Decimal("1")


class ErroDominioPricing(Exception):
    """Erro de domínio esperado pelo motor e traduzido pela camada da API.

    O atributo ``codigo`` é consumido pela suíte de conformidade.
    """

    def __init__(
        self,
        codigo: DomainErrorCodigo,
        mensagem: str,
        detalhes: dict[str, str] | None = None,
    ) -> None:
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes or {}
        super().__init__(mensagem)


def _arredondar_monetario(valor: Decimal) -> Decimal:
    """Arredonda somente os campos monetários apresentados, em centavos."""

    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _validar_denominador(valor: Decimal, *, etapa: str, termo_impostos: Decimal) -> None:
    if valor <= ZERO:
        raise ErroDominioPricing(
            codigo=DomainErrorCodigo.DENOMINADOR_INVALIDO,
            mensagem=f"Denominador inválido na etapa {etapa}: o valor deve ser maior que zero.",
            detalhes={
                "etapa": etapa,
                "denominador": str(valor),
                "termo_impostos": str(termo_impostos),
            },
        )


def calcular(entrada: CalculateRequest) -> CalculateResponse:
    """Calcula a estrutura completa de preço sem alterar a entrada.

    Todos os cálculos intermediários são executados com ``Decimal`` e
    precisão explícita. O arredondamento monetário ocorre apenas ao montar
    a resposta.

    >>> from pricing_core.contracts import CalculateRequest
    >>> entrada = CalculateRequest.model_validate({
    ...     "cliente_uf": "SP",
    ...     "modalidade_comercial": "full_service_nacional",
    ...     "regime_tributario": "Lucro Real",
    ...     "materiais_primas": [{"codigo": "MP-1", "preco_negociado": "10",
    ...         "quantidade": "1"}],
    ...     "producao": {"taxa_mod": "0", "taxa_ggf": "0",
    ...         "produtividade": "1", "numero_funcionarios": "0"},
    ...     "impostos": {"pis_percentual": "0", "cofins_percentual": "0",
    ...         "icms_percentual": "0"},
    ...     "comercial": {"margem_desejada_percentual": "0"}
    ... })
    >>> calcular(entrada).preco_bruto
    Decimal('10.00')
    """
    if not isinstance(entrada, CalculateRequest):
        raise TypeError("entrada deve ser uma instância de CalculateRequest")

    # A entrada Pydantic é lida, nunca modificada. Os cálculos são isolados
    # em um contexto Decimal para não depender da precisão global do processo.
    with localcontext() as contexto:
        contexto.prec = PRECISAO

        custo_mp = calcular_custo_mp(entrada.materiais_primas)
        custo_embalagem = calcular_custo_embalagem(entrada.embalagens)
        custo_perda = calcular_custo_perda(
            custo_mp,
            custo_embalagem,
            entrada.valor_material_cliente,
            entrada.perda_percentual,
        )

        producao = entrada.producao
        custo_mod = (producao.taxa_mod / producao.produtividade) * producao.numero_funcionarios
        custo_ggf = producao.taxa_ggf / producao.produtividade
        custo_total = calcular_custo_total(
            custo_mp,
            custo_embalagem,
            custo_perda,
            custo_mod,
            custo_ggf,
        )

        impostos = entrada.impostos
        comercial = entrada.comercial
        pis = impostos.pis_percentual
        cofins = impostos.cofins_percentual
        icms = impostos.icms_percentual
        margem = comercial.margem_desejada_percentual
        comissao = comercial.comissao_percentual
        frete = comercial.frete_percentual

        termo_impostos = pis * (UM - icms) + cofins * (UM - icms) + icms
        denominador = UM - (comissao + frete + margem * (UM - termo_impostos) + termo_impostos)
        _validar_denominador(
            denominador,
            etapa="D",
            termo_impostos=termo_impostos,
        )

        encargo_percentual = taxa_encargo(
            comercial.taxa_financeira_mensal_percentual,
            comercial.prazo_medio_dias,
        )

        isencao_valor = custo_mod if entrada.material_fornecido_pelo_cliente and entrada.cliente_uf == "SP" else ZERO

        # TODO(PO): confirmar se CustoEnviadoCliente deve usar o mesmo
        # valor informado para MaterialCliente em CustoPerda.
        custo_enviado_cliente = entrada.valor_material_cliente

        # TODO(PO): confirmar se a base da margem desejada é CustoTotal.
        base_margem = custo_total

        preco_bruto_sem_ipi_sem_encargo = custo_total / denominador - custo_enviado_cliente - isencao_valor
        # A especificação define Encargo$ = Encargo × PBsIPIsEncargo.
        # Não arredondar a base nem o resultado intermediário.
        encargo_valor = encargo_percentual * preco_bruto_sem_ipi_sem_encargo

        denominador_preco_sem_ipi = UM - (termo_impostos + comissao + frete)
        _validar_denominador(
            denominador_preco_sem_ipi,
            etapa="PBsIPI",
            termo_impostos=termo_impostos,
        )

        preco_bruto_sem_ipi = (
            (margem * base_margem + custo_total + encargo_valor) / denominador_preco_sem_ipi
            - custo_enviado_cliente
            - isencao_valor
        )

        preco_bruto_com_ipi = preco_bruto_sem_ipi * (UM + impostos.ipi_percentual)

        if (
            impostos.icms_interno_percentual == ZERO
            and impostos.fcp_percentual == ZERO
            and impostos.mva_percentual == ZERO
        ):
            preco_bruto = preco_bruto_com_ipi
        else:
            preco_bruto = preco_bruto_com_ipi + (
                (preco_bruto_com_ipi * (UM + impostos.mva_percentual))
                * (impostos.icms_interno_percentual + impostos.fcp_percentual)
                - preco_bruto_sem_ipi * icms
            )

        receita_operacional_liquida = preco_bruto_sem_ipi - (
            (preco_bruto_sem_ipi - preco_bruto_sem_ipi * icms) * (pis + cofins) + preco_bruto_sem_ipi * icms
        )

        # TODO(PO): confirmar se Comissao$ incide sobre PB (incluindo IPI
        # e eventual ICMS-ST), conforme a premissa adotada nesta versão.
        comissao_valor = comissao * preco_bruto

        margem_contribuicao_valor = receita_operacional_liquida - (
            custo_mp + custo_embalagem + encargo_valor + custo_perda + comissao_valor
        )
        margem_contribuicao_percentual = margem_contribuicao_valor / preco_bruto if preco_bruto != ZERO else ZERO

        return CalculateResponse(
            custo_mp=_arredondar_monetario(custo_mp),
            custo_embalagem=_arredondar_monetario(custo_embalagem),
            custo_perda=_arredondar_monetario(custo_perda),
            custo_mod=_arredondar_monetario(custo_mod),
            custo_ggf=_arredondar_monetario(custo_ggf),
            custo_total=_arredondar_monetario(custo_total),
            denominador=denominador,
            encargo_financeiro_percentual=encargo_percentual,
            encargo_financeiro_valor=_arredondar_monetario(encargo_valor),
            preco_bruto_sem_ipi_sem_encargo=_arredondar_monetario(preco_bruto_sem_ipi_sem_encargo),
            preco_bruto_sem_ipi=_arredondar_monetario(preco_bruto_sem_ipi),
            preco_bruto_com_ipi=_arredondar_monetario(preco_bruto_com_ipi),
            preco_bruto=_arredondar_monetario(preco_bruto),
            preco_indicado=_arredondar_monetario(preco_bruto),
            receita_operacional_liquida=_arredondar_monetario(receita_operacional_liquida),
            margem_contribuicao_valor=_arredondar_monetario(margem_contribuicao_valor),
            margem_contribuicao_percentual=margem_contribuicao_percentual,
            isencao_mao_de_obra=IsencaoMaoDeObraInfo(
                aplicada=isencao_valor > ZERO,
                valor=_arredondar_monetario(isencao_valor),
            ),
            impostos_destacados=ImpostosDestacados(
                # TODO(PO): confirmar as bases de destaque. PIS/COFINS e
                # ICMS usam aqui as mesmas bases de PBsIPI da fórmula da ROL;
                # IPI usa PBsIPI e ICMS-ST corresponde ao acréscimo entre PB
                # e PBcIPI no ramo com MVA/FCP/ICMS interno.
                pis_valor=_arredondar_monetario((preco_bruto_sem_ipi - preco_bruto_sem_ipi * icms) * pis),
                cofins_valor=_arredondar_monetario((preco_bruto_sem_ipi - preco_bruto_sem_ipi * icms) * cofins),
                icms_valor=_arredondar_monetario(preco_bruto_sem_ipi * icms),
                ipi_valor=_arredondar_monetario(preco_bruto_sem_ipi * impostos.ipi_percentual),
                icms_st_valor=_arredondar_monetario(preco_bruto - preco_bruto_com_ipi),
            ),
            metadata=CalculateMetadata(
                versao_motor=ENGINE_CONTRACT_VERSION,
                is_mock=False,
            ),
        )
