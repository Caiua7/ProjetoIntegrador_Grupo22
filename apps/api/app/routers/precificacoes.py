"""Persistencia do cabecalho da precificacao (US57)."""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario

router = APIRouter(prefix="/precificacoes", tags=["precificacoes"])
Modalidade = Literal["full_service_nacional", "full_service_exportacao", "industrializacao_por_encomenda"]
Regime = Literal["lucro_real", "lucro_presumido", "simples_nacional"]
Frete = Literal["cif", "fob"]


class PrecificacaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cliente_id: UUID
    produto_id: UUID
    modalidade_comercial: Modalidade
    uf_destino: str = Field(
        pattern=r"^(AC|AL|AM|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO|EX)$"
    )
    frete: Frete
    regime_tributario: Regime


class PrecificacaoResposta(BaseModel):
    id: UUID
    codigo: str
    cliente_id: UUID
    produto_id: UUID
    modalidade_comercial: Modalidade
    uf_destino: str
    frete: Frete
    regime_tributario: Regime
    status: str
    created_at: datetime
    updated_at: datetime
    cliente: dict | None = None
    produto: dict | None = None


class OpcaoResposta(BaseModel):
    id: UUID
    codigo: str
    descricao: str


class OpcoesResposta(BaseModel):
    clientes: list[OpcaoResposta]
    produtos: list[OpcaoResposta]


def _cliente(usuario: UsuarioAutenticado):
    try:
        return supabase_do_usuario(usuario.access_token)
    except Exception as erro:
        raise HTTPException(503, "Nao foi possivel acessar as precificacoes.") from erro


def _executar(operacao):
    try:
        return operacao()
    except Exception as erro:
        codigo = str(getattr(erro, "code", ""))
        if codigo in {"23503", "23514", "22P02"}:
            raise HTTPException(422, "Cliente ou produto invalido para esta precificacao.") from erro
        if codigo == "42501":
            raise HTTPException(403, "Seu perfil nao pode acessar esta precificacao.") from erro
        raise HTTPException(503, "Nao foi possivel acessar as precificacoes.") from erro


@router.get("/opcoes", response_model=OpcoesResposta)
def listar_opcoes(usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar"))):
    cliente = _cliente(usuario)
    clientes = _executar(
        lambda: (
            cliente.table("cliente").select("id,codigo,razao_social").eq("ativo", True).order("razao_social").execute()
        )
    )
    produtos = _executar(
        lambda: cliente.table("produto").select("id,codigo,descricao").eq("ativo", True).order("descricao").execute()
    )
    return {
        "clientes": [
            {"id": item["id"], "codigo": item["codigo"], "descricao": item["razao_social"]}
            for item in clientes.data or []
        ],
        "produtos": produtos.data or [],
    }


@router.get("", response_model=list[PrecificacaoResposta])
def listar_precificacoes(
    status_filtro: Literal["em_preenchimento", "em_aprovacao", "aprovado", "reprovado"] | None = Query(
        default=None, alias="status"
    ),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler")),
):
    consulta = (
        _cliente(usuario)
        .table("precificacao")
        .select("*,cliente:cliente_id(razao_social),produto:produto_id(descricao)")
        .order("updated_at", desc=True)
    )
    if status_filtro:
        consulta = consulta.eq("status", status_filtro)
    return _executar(lambda: consulta.execute()).data or []


@router.post("", response_model=PrecificacaoResposta, status_code=status.HTTP_201_CREATED)
def criar_precificacao(
    entrada: PrecificacaoEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar")),
):
    dados = entrada.model_dump(mode="json")
    codigo = f"PRC-{uuid4().hex[:12].upper()}"
    dados.update({"codigo": codigo, "created_by": str(usuario.id), "updated_by": str(usuario.id)})
    resposta = _executar(lambda: _cliente(usuario).table("precificacao").insert(dados).select("*").execute())
    if not resposta.data:
        raise HTTPException(503, "A precificacao nao foi retornada apos a gravacao.")
    return resposta.data[0]
