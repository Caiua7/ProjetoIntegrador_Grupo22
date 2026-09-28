"""Endpoint mock de `/calculate` (Sprint 1).

Implementa as fórmulas da seção 2.3 usando as três suposições documentadas
no topo de `pricing_core.contracts` (Base, Comissao$, MaterialCliente ==
CustoEnviadoCliente). Isso é deliberado: dá ao Squad B números de magnitude
realista para desenhar telas (formatação de moeda, gráficos, etc.) e dá ao
Squad A uma referência já executável para revisar assim que os 30 casos
forem homologados com o PO — mas os valores retornados NÃO são
certificados e não devem ser usados em decisão comercial nem em demo para
a banca. `CalculateMetadata.is_mock` é sempre `True` aqui de propósito.

A implementação definitiva (US16/US19, Sprint 3) deve:
    - resolver as 3 suposições em aberto com o PO;
    - substituir o cálculo de `encargo_financeiro_percentual` abaixo, que
      usa `float` para a potenciação fracionária — aceitável num mock,
      mas contraria a decisão de arquitetura "Decimal em vez de ponto
      flutuante para todo valor monetário e percentual" e deve virar
      Decimal com contexto de precisão explícito;
    - implementar o ramo de ICMS-ST (MVA/FCP) com a suíte de conformidade
      de 30 casos, não apenas a checagem estrutural feita aqui.
"""

from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, HTTPException, status

from pricing_core.contracts import (
    CalculateMetadata,
    CalculateRequest,
    CalculateResponse,
    DomainErrorCodigo,
    DomainErrorResponse,
    ENGINE_CONTRACT_VERSION,
    ImpostosDestacados,
    IsencaoMaoDeObraInfo,
)

router = APIRouter(prefix="/calculate", tags=["calculate"])

CENTAVO = Decimal("0.01")


def _arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _erro_denominador(mensagem: str, detalhes: dict) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=DomainErrorResponse(
            codigo=DomainErrorCodigo.DENOMINADOR_INVALIDO,
            mensagem=mensagem,
            detalhes=detalhes,
        ).model_dump(mode="json"),
    )


@router.post(
    "",
    response_model=CalculateResponse,
    responses={
        422: {
            "model": DomainErrorResponse,
            "description": "Entrada matematicamente inválida (ex.: denominador <= 0) — RNF08",
        }
    },
    summary="Calcula um cenário de precificação (MOCK — Sprint 1)",
    description=(
        "Publicado na Sprint 1 antes de US16/US19 (motor real, Sprint 3). "
        "Implementa a seção 2.3 com suposições ainda não homologadas com o "
        "PO (ver docstring do contrato). Use para desenvolver telas, nunca "
        "para decisão comercial."
    ),
)
def calculate(payload: CalculateRequest) -> CalculateResponse:
    custo_mp = sum(
        (i.preco_negociado * i.cambio * (1 + i.margem_seguranca_percentual) * i.quantidade for i in payload.materiais_primas),
        Decimal("0"),
    )
    custo_embalagem = sum(
        (
            i.preco_negociado * i.cambio * (1 + i.margem_seguranca_percentual) * i.quantidade * i.percentual_descarte
            for i in payload.embalagens
        ),
        Decimal("0"),
    )
    custo_perda = (custo_mp + custo_embalagem - payload.valor_material_cliente) * payload.perda_percentual

    prod = payload.producao
    custo_mod = (prod.taxa_mod / prod.produtividade) * prod.numero_funcionarios
    custo_ggf = prod.taxa_ggf / prod.produtividade
    custo_total = custo_mp + custo_embalagem + custo_perda + custo_mod + custo_ggf

    imp = payload.impostos
    com = payload.comercial

    pis, cofins, icms = imp.pis_percentual, imp.cofins_percentual, imp.icms_percentual
    m = com.margem_desejada_percentual
    comissao, frete = com.comissao_percentual, com.frete_percentual

    termo_impostos = pis * (1 - icms) + cofins * (1 - icms) + icms
    denominador = 1 - (comissao + frete + m * (1 - termo_impostos) + termo_impostos)
    if denominador <= 0:
        _erro_denominador(
            "Denominador D <= 0 — combinação de margem, comissão, frete e impostos torna o preço indeterminado.",
            {"denominador": str(denominador), "termo_impostos": str(termo_impostos)},
        )

    # Encargo financeiro — potenciação fracionária em float (ver nota no
    # topo do arquivo); prazo em dias, referência de 30 dias por mês.
    taxa = float(com.taxa_financeira_mensal_percentual)
    prazo_em_meses = float(com.prazo_medio_dias) / 30
    encargo_percentual = Decimal(str((1 + taxa) ** prazo_em_meses - 1))

    isencao_valor = custo_mod if (payload.material_fornecido_pelo_cliente and payload.cliente_uf == "SP") else Decimal("0")
    custo_enviado_cliente = payload.valor_material_cliente  # suposição (3), ver contracts.py

    base = custo_total  # suposição (1), ver contracts.py
    pb_sem_ipi_sem_encargo = custo_total / denominador - custo_enviado_cliente - isencao_valor
    encargo_valor = encargo_percentual * pb_sem_ipi_sem_encargo

    denominador2 = 1 - (termo_impostos + comissao + frete)
    if denominador2 <= 0:
        _erro_denominador(
            "Segundo denominador (PBsIPI) <= 0 — mesma causa raiz do denominador principal.",
            {"denominador2": str(denominador2)},
        )

    pb_sem_ipi = (m * base + custo_total + encargo_valor) / denominador2 - custo_enviado_cliente - isencao_valor
    pb_com_ipi = pb_sem_ipi * (1 + imp.ipi_percentual)

    if imp.icms_interno_percentual == 0 and imp.fcp_percentual == 0 and imp.mva_percentual == 0:
        preco_bruto = pb_com_ipi
    else:
        preco_bruto = pb_com_ipi + (
            (pb_com_ipi * (1 + imp.mva_percentual)) * (imp.icms_interno_percentual + imp.fcp_percentual)
            - pb_sem_ipi * icms
        )

    rol = pb_sem_ipi - ((pb_sem_ipi - pb_sem_ipi * icms) * (pis + cofins) + pb_sem_ipi * icms)
    comissao_valor = comissao * preco_bruto  # suposição (2), ver contracts.py
    maco_valor = rol - (custo_mp + custo_embalagem + encargo_valor + custo_perda + comissao_valor)
    maco_percentual = (maco_valor / preco_bruto) if preco_bruto else Decimal("0")

    return CalculateResponse(
        custo_mp=_arredondar(custo_mp),
        custo_embalagem=_arredondar(custo_embalagem),
        custo_perda=_arredondar(custo_perda),
        custo_mod=_arredondar(custo_mod),
        custo_ggf=_arredondar(custo_ggf),
        custo_total=_arredondar(custo_total),
        denominador=denominador,
        encargo_financeiro_percentual=encargo_percentual,
        encargo_financeiro_valor=_arredondar(encargo_valor),
        preco_bruto_sem_ipi_sem_encargo=_arredondar(pb_sem_ipi_sem_encargo),
        preco_bruto_sem_ipi=_arredondar(pb_sem_ipi),
        preco_bruto_com_ipi=_arredondar(pb_com_ipi),
        preco_bruto=_arredondar(preco_bruto),
        preco_indicado=_arredondar(preco_bruto),
        receita_operacional_liquida=_arredondar(rol),
        margem_contribuicao_valor=_arredondar(maco_valor),
        margem_contribuicao_percentual=maco_percentual,
        isencao_mao_de_obra=IsencaoMaoDeObraInfo(aplicada=isencao_valor > 0, valor=_arredondar(isencao_valor)),
        impostos_destacados=ImpostosDestacados(
            pis_valor=_arredondar(pis * preco_bruto),
            cofins_valor=_arredondar(cofins * preco_bruto),
            icms_valor=_arredondar(icms * preco_bruto),
            ipi_valor=_arredondar(pb_sem_ipi * imp.ipi_percentual),
            icms_st_valor=_arredondar(preco_bruto - pb_com_ipi),
        ),
        metadata=CalculateMetadata(versao_motor=ENGINE_CONTRACT_VERSION, is_mock=True),
    )
