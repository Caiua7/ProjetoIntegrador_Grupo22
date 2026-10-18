"""Consulta e resolução da cotação vigente de matéria-prima (US25)."""

from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario
from pricing_core.cotacao import (
    Cotacao,
    CotacaoAmbigua,
    CotacaoNaoEncontrada,
    cotacoes_vigentes,
    resolver_cotacao,
)

router = APIRouter(prefix="/cotacoes", tags=["cotações"])


class CotacaoResposta(BaseModel):
    id: UUID
    materia_prima_id: UUID
    fornecedor_id: UUID
    moeda: str
    preco: Decimal
    volume_minimo: Decimal
    validade_inicio: date
    validade_fim: date | None
    prazo_entrega_dias: int


def _erro_persistencia(erro: Exception) -> HTTPException:
    codigo = str(getattr(erro, "code", ""))
    try:
        codigo_http = int(getattr(erro, "status_code", 0) or 0)
    except (TypeError, ValueError):
        codigo_http = 0
    if codigo == "42501" or codigo_http == 403:
        return HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode consultar cotações.")
    if codigo_http == 401:
        return HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.")
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível acessar as cotações. Tente novamente.")


def _executar[Resultado](operacao: Callable[[], Resultado]) -> Resultado:
    try:
        return operacao()
    except Exception as erro:
        raise _erro_persistencia(erro) from erro


def _para_cotacao(linha: dict) -> Cotacao:
    # O PostgREST devolve numeric como número JSON; Decimal(str(...)) é exato até ~15 dígitos significativos,
    # folga de sobra para preço numeric(18,6) e volume numeric(18,3) em valores reais de cotação.
    return Cotacao(
        id=linha["id"],
        materia_prima_id=linha["materia_prima_id"],
        fornecedor_id=linha["fornecedor_id"],
        moeda=linha["moeda"],
        preco=Decimal(str(linha["preco"])),
        volume_minimo=Decimal(str(linha["volume_minimo"])),
        validade_inicio=date.fromisoformat(linha["validade_inicio"]),
        validade_fim=date.fromisoformat(linha["validade_fim"]) if linha["validade_fim"] else None,
        prazo_entrega_dias=linha["prazo_entrega_dias"],
    )


def _carregar_vigentes(usuario: UsuarioAutenticado, materia_prima_id: UUID, data_referencia: date) -> list[Cotacao]:
    # RPC na função do banco, que roda com o RLS de quem chama (token do usuário).
    resposta = _executar(
        lambda: (
            supabase_do_usuario(usuario.access_token)
            .rpc(
                "cotacoes_vigentes",
                {"p_materia_prima_id": str(materia_prima_id), "p_data": data_referencia.isoformat()},
            )
            .execute()
        )
    )
    return [_para_cotacao(linha) for linha in resposta.data or []]


@router.get("/vigentes", response_model=list[CotacaoResposta])
def listar_vigentes(
    materia_prima_id: UUID,
    data_referencia: date = Query(default_factory=date.today),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("custo.ler")),
) -> list[dict]:
    cotacoes = _carregar_vigentes(usuario, materia_prima_id, data_referencia)
    return [asdict(c) for c in cotacoes_vigentes(cotacoes, str(materia_prima_id), data_referencia)]


@router.get("/resolver", response_model=CotacaoResposta)
def resolver(
    materia_prima_id: UUID,
    quantidade: Decimal = Query(gt=0, allow_inf_nan=False),
    data_referencia: date = Query(default_factory=date.today),
    fornecedor_id: UUID | None = None,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("custo.ler")),
) -> dict:
    cotacoes = _carregar_vigentes(usuario, materia_prima_id, data_referencia)
    try:
        escolhida = resolver_cotacao(
            cotacoes,
            str(materia_prima_id),
            quantidade,
            data_referencia,
            str(fornecedor_id) if fornecedor_id else None,
        )
    except CotacaoNaoEncontrada as erro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(erro)) from erro
    except CotacaoAmbigua as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, str(erro)) from erro
    return asdict(escolhida)
