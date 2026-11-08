"""Decisão de aprovação e reprovação da precificação (issue #68, US37).

O gerente aprova ou reprova uma precificação em aprovação. A reprovação
exige comentário; responsável e data vêm da sessão. As regras ficam no
banco (``decidir_aprovacao`` e os gatilhos de ``decisao_aprovacao``); aqui a
mesma exigência do comentário é antecipada para responder 422 sem ir ao
banco, e os erros do banco viram respostas tratadas.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario

router = APIRouter(prefix="/precificacoes/{precificacao_id}/decisoes", tags=["aprovação"])

Decisao = Literal["aprovado", "reprovado"]


class DecisaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisao: Decisao
    comentario: str | None = Field(default=None, max_length=2000)

    @field_validator("comentario")
    @classmethod
    def _limpar(cls, valor: str | None) -> str | None:
        return (valor or "").strip() or None

    @model_validator(mode="after")
    def _reprovar_exige_comentario(self) -> "DecisaoEntrada":
        if self.decisao == "reprovado" and self.comentario is None:
            raise ValueError("A reprovação exige um comentário com a justificativa.")
        return self


class DecisaoRegistrada(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    precificacao_id: UUID
    cenario_id: UUID | None = None
    cenario_versao: int | None = None
    decisao: Decisao
    comentario: str | None = None
    responsavel_id: UUID
    responsavel_nome: str | None = None
    decidido_em: datetime


def _erro(erro: Exception) -> HTTPException:
    codigo = str(getattr(erro, "code", ""))
    mensagem = getattr(erro, "message", None) or str(erro)
    if codigo == "P0002":
        return HTTPException(status.HTTP_404_NOT_FOUND, "Precificação não encontrada.")
    if codigo == "55000":
        return HTTPException(status.HTTP_409_CONFLICT, mensagem)
    if codigo in {"23514", "22023", "22P02"}:
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, mensagem)
    if codigo == "42501":
        return HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode decidir esta precificação.")
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível registrar a decisão.")


def _executar(operacao):
    try:
        return operacao()
    except HTTPException:
        raise
    except Exception as erro:
        raise _erro(erro) from erro


@router.get("", response_model=list[DecisaoRegistrada])
def listar_decisoes(
    precificacao_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler")),
) -> list[dict]:
    """Trilha de decisões da precificação, da mais recente para a mais antiga."""
    resposta = _executar(
        lambda: (
            supabase_do_usuario(usuario.access_token)
            .table("decisao_aprovacao_historico")
            .select("*")
            .eq("precificacao_id", str(precificacao_id))
            .order("decidido_em", desc=True)
            .execute()
        )
    )
    return resposta.data or []


@router.post("", response_model=DecisaoRegistrada, status_code=status.HTTP_201_CREATED)
def registrar_decisao(
    precificacao_id: UUID,
    corpo: DecisaoEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.aprovar")),
) -> dict:
    parametros = {
        "p_precificacao_id": str(precificacao_id),
        "p_decisao": corpo.decisao,
        "p_comentario": corpo.comentario,
    }
    resposta = _executar(
        lambda: supabase_do_usuario(usuario.access_token).rpc("decidir_aprovacao", parametros).execute()
    )
    registrada = resposta.data[0] if isinstance(resposta.data, list) else resposta.data
    if not registrada:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "A decisão não foi retornada após o registro.")
    return {**registrada, "responsavel_nome": usuario.nome}
