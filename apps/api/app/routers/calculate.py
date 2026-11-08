"""HTTP adapter for the pure pricing engine."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.core.config import settings
from app.services.demo_calculator import preparar_entrada_demo
from pricing_core.contracts import (
    CalculateRequest,
    CalculateResponse,
    CalculateResponseSemCustos,
    DomainErrorResponse,
)
from pricing_core.engine import ErroDominioPricing
from pricing_core.engine import calcular as calcular_motor

router = APIRouter(prefix="/calculate", tags=["calculate"])


class CalculateDemoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dados: dict[str, Any] = Field(default_factory=dict)


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


@router.post(
    "/demo",
    response_model=CalculateResponse | CalculateResponseSemCustos,
    responses={422: {"model": DomainErrorResponse}},
    summary="Run an explicitly simulated pricing scenario",
    description="Uses centralized demonstration assumptions, marks every response as mock, and never persists it.",
)
def calculate_demo_endpoint(
    corpo: CalculateDemoInput,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler")),
) -> CalculateResponse | CalculateResponseSemCustos:
    if not settings.DEMO_CALCULATION_ENABLED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "O modo de demonstração está desativado neste ambiente.")
    try:
        entrada, simulados, recebeu_dados = preparar_entrada_demo(corpo.dados)
    except ValidationError as erro:
        erros = erro.errors(include_input=False, include_url=False)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "codigo": "ENTRADA_INVALIDA",
                "mensagem": "Não foi possível montar a entrada de demonstração.",
                "detalhes": {"campos": erros},
            },
        ) from erro
    except ValueError as erro:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(erro)) from erro

    if recebeu_dados and not simulados:
        simulados.append("proveniência dos valores recebidos não verificada pelo modo de demonstração")
    resultado = calculate(entrada)
    metadata = resultado.metadata.model_copy(
        update={
            "is_mock": True,
            "origem": "demonstracao",
            "classificacao": "parcialmente_simulado" if recebeu_dados else "inteiramente_simulado",
            "parametros_simulados": simulados,
            "dados_recebidos_nao_verificados": recebeu_dados,
        }
    )
    resultado = resultado.model_copy(update={"metadata": metadata})
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
