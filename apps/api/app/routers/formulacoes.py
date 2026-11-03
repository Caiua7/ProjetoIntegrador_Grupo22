"""Consulta e edicao da composicao atual dos produtos (US62)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario

router = APIRouter(prefix="/formulacoes", tags=["formulacoes"])
Unidade = Literal["kg", "g", "l", "ml", "un"]
TipoItem = Literal["materia_prima", "embalagem"]


class ProdutoResposta(BaseModel):
    id: UUID
    codigo: str
    descricao: str
    categoria: str
    peso_liquido_g: Decimal | None = None


class ItemEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo_insumo: TipoItem
    materia_prima_id: UUID | None = None
    embalagem_id: UUID | None = None
    quantidade: Decimal = Field(gt=0, max_digits=14, decimal_places=6)
    unidade_medida: Unidade
    perda_percentual: Decimal | None = Field(default=None, ge=0, le=100, max_digits=7, decimal_places=4)

    @model_validator(mode="after")
    def referencia_coerente(self):
        if self.tipo_insumo == "materia_prima" and (self.materia_prima_id is None or self.embalagem_id is not None):
            raise ValueError("Informe somente a matéria-prima selecionada.")
        if self.tipo_insumo == "embalagem" and (self.embalagem_id is None or self.materia_prima_id is not None):
            raise ValueError("Informe somente a embalagem selecionada.")
        return self


class FormulacaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    itens: list[ItemEntrada] = Field(max_length=500)


class FormulacaoResposta(BaseModel):
    id: UUID
    produto_id: UUID
    created_at: datetime
    updated_at: datetime
    itens: list[dict]


def _cliente(usuario: UsuarioAutenticado):
    try:
        return supabase_do_usuario(usuario.access_token)
    except Exception as erro:
        raise HTTPException(503, "Não foi possível acessar a base de formulações.") from erro


def _executar(operacao):
    try:
        return operacao()
    except Exception as erro:
        codigo = str(getattr(erro, "code", ""))
        if codigo == "42501":
            raise HTTPException(403, "Seu perfil não pode alterar esta formulação.") from erro
        if codigo in {"23503", "23514", "22P02", "22023", "22003"}:
            raise HTTPException(422, "Um ou mais itens da formulação são inválidos.") from erro
        raise HTTPException(503, "Não foi possível acessar a base de formulações.") from erro


@router.get("/produtos", response_model=list[ProdutoResposta])
def listar_produtos(usuario: UsuarioAutenticado = Depends(exigir_permissao("cadastro.ler"))):
    resposta = _executar(lambda: _cliente(usuario).table("produto").select(
        "id,codigo,descricao,categoria,peso_liquido_g"
    ).eq("ativo", True).order("descricao").execute())
    return resposta.data or []


def _obter_formulacao(produto_id: UUID, usuario: UsuarioAutenticado):
    cliente = _cliente(usuario)
    resposta = _executar(lambda: cliente.table("formulacao").select("*").eq("produto_id", str(produto_id)).limit(1).execute())
    if not resposta.data:
        raise HTTPException(404, "Este produto ainda não possui formulação.")
    formulacao = resposta.data[0]
    itens = _executar(lambda: cliente.table("formulacao_item").select(
        "id,tipo_insumo,materia_prima_id,embalagem_id,quantidade,unidade_medida,perda_percentual,ordem"
    ).eq("formulacao_id", formulacao["id"]).order("ordem").execute())
    return {**formulacao, "itens": itens.data or []}


@router.get("/{produto_id}", response_model=FormulacaoResposta)
def obter_formulacao(produto_id: UUID, usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler"))):
    return _obter_formulacao(produto_id, usuario)


@router.put("/{produto_id}", response_model=FormulacaoResposta)
def salvar_formulacao(
    produto_id: UUID,
    entrada: FormulacaoEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar")),
):
    cliente = _cliente(usuario)
    produto = _executar(lambda: cliente.table("produto").select("id").eq("id", str(produto_id)).eq("ativo", True).limit(1).execute())
    if not produto.data:
        raise HTTPException(404, "Produto ativo não encontrado.")
    existente = _executar(lambda: cliente.table("formulacao").select("id").eq("produto_id", str(produto_id)).limit(1).execute())
    if existente.data:
        formulacao_id = existente.data[0]["id"]
    else:
        criada = _executar(lambda: cliente.table("formulacao").insert({
            "produto_id": str(produto_id), "created_by": str(usuario.id), "updated_by": str(usuario.id),
        }).select("id").execute())
        if not criada.data:
            raise HTTPException(503, "A formulação não foi retornada após a gravação.")
        formulacao_id = criada.data[0]["id"]

    itens = [item.model_dump(mode="json") for item in entrada.itens]
    _executar(lambda: cliente.rpc("salvar_itens_formulacao", {
        "p_formulacao_id": formulacao_id, "p_itens": itens,
    }).execute())
    return _obter_formulacao(produto_id, usuario)
