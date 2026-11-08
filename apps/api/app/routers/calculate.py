"""HTTP adapter for the pure pricing engine."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import UsuarioAutenticado, exigir_permissao
from pricing_core.contracts import (
    CalculateRequest,
    CalculateResponse,
    CalculateResponseSemCustos,
    DomainErrorResponse,
)
from pricing_core.engine import ErroDominioPricing
from pricing_core.engine import calcular as calcular_motor

router = APIRouter(prefix="/calculate", tags=["calculate"])


def calculate(payload: CalculateRequest) -> CalculateResponse:
    """Execute the engine for internal API use and translate domain errors."""
    try:
        return calcular_motor(payload)
    except ErroDominioPricing as erro:
        corpo = DomainErrorResponse(codigo=erro.codigo, mensagem=erro.mensagem, detalhes=erro.detalhes)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=corpo.model_dump(mode="json"),
        ) from erro


@router.post(
    "",
    response_model=CalculateResponse | CalculateResponseSemCustos,
    responses={
        422: {
            "model": DomainErrorResponse,
            "description": "Invalid mathematical input, such as a non-positive denominator.",
        }
    },
    summary="Calculate a pricing scenario",
    description="Runs pricing-core and filters cost fields according to the authenticated user's permission.",
)
def calculate_endpoint(
    payload: CalculateRequest,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler")),
) -> CalculateResponse | CalculateResponseSemCustos:
    resultado = calculate(payload)
    if usuario.tem_permissao("custo.ler"):
        return resultado
    return CalculateResponseSemCustos.model_validate(
        resultado.model_dump(
            include={
                "preco_bruto_sem_ipi_sem_encargo",
                "preco_bruto_sem_ipi",
                "preco_bruto_com_ipi",
                "preco_bruto",
                "preco_indicado",
                "receita_operacional_liquida",
                "impostos_destacados",
                "metadata",
            }
        )
    )
