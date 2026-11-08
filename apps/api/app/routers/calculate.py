"""Adaptador HTTP do motor puro de precificação.

O cálculo de domínio fica em ``pricing_core.engine``. Esta camada limita-se
a converter erros de domínio para a resposta HTTP prevista no contrato.
"""

from fastapi import APIRouter, HTTPException, status

from pricing_core.contracts import (
    CalculateRequest,
    CalculateResponse,
    DomainErrorResponse,
)
from pricing_core.engine import ErroDominioPricing
from pricing_core.engine import calcular as calcular_motor

router = APIRouter(prefix="/calculate", tags=["calculate"])


@router.post(
    "",
    response_model=CalculateResponse,
    responses={
        422: {
            "model": DomainErrorResponse,
            "description": "Entrada matematicamente inválida (ex.: denominador <= 0) — RNF08",
        }
    },
    summary="Calcula um cenário de precificação",
    description=(
        "Executa o motor puro pricing-core. As três premissas marcadas com "
        "TODO(PO) ainda precisam de confirmação pelo Product Owner."
    ),
)
def calculate(payload: CalculateRequest) -> CalculateResponse:
    """Mantém a função pública usada também pelo fluxo de cenários."""

    try:
        return calcular_motor(payload)
    except ErroDominioPricing as erro:
        corpo = DomainErrorResponse(
            codigo=erro.codigo,
            mensagem=erro.mensagem,
            detalhes=erro.detalhes,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=corpo.model_dump(mode="json"),
        ) from erro
