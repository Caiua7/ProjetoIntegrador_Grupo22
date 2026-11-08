"""Persistencia do cabecalho da precificacao (US57)."""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario, supabase_servico

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
    # vazios nas precificações anteriores à migration 20261103000001
    uf_destino: str | None = None
    frete: Frete | None = None
    regime_tributario: Regime | None = None
    status: str
    homologacao_pendente: bool = False
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


class VerificacaoSubmissao(BaseModel):
    pode_submeter: bool
    modo_politica: Literal["demonstracao", "homologada"]
    homologacao_pendente: bool
    campos_obrigatorios: list[str]
    motivos_bloqueio: list[str]
    status: str | None = None


class HistoricoStatusResposta(BaseModel):
    id: UUID
    precificacao_id: UUID
    status_anterior: str
    status_novo: str
    modo: Literal["demonstracao", "homologada"]
    responsavel_id: UUID
    ocorrido_em: datetime


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
        mensagem = getattr(erro, "message", None) or str(erro)
        if codigo == "P0002":
            raise HTTPException(404, "Precificação não encontrada ou fora da sua carteira.") from erro
        if codigo == "42501":
            raise HTTPException(403, "Seu perfil não pode executar esta ação.") from erro
        if codigo == "55000":
            raise HTTPException(409, mensagem) from erro
        if codigo in {"23503", "23514", "22P02"}:
            raise HTTPException(422, mensagem) from erro
        raise HTTPException(503, "Nao foi possivel acessar as precificacoes.") from erro


@router.get("/opcoes", response_model=OpcoesResposta)
def listar_opcoes(usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar"))):
    if not usuario.tem_permissao("cliente.ler") or not usuario.tem_permissao("cadastro.ler"):
        raise HTTPException(403, "Seu perfil nao pode consultar clientes e produtos.")
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
        .select("*,cliente(razao_social),produto(descricao,ncm_codigo)")
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
    resposta = _executar(lambda: _cliente(usuario).table("precificacao").insert(dados).execute())
    if not resposta.data:
        raise HTTPException(503, "A precificacao nao foi retornada apos a gravacao.")
    return resposta.data[0]


def _rpc_submissao(nome: str, usuario: UsuarioAutenticado, precificacao_id: UUID) -> dict:
    resposta = _executar(
        lambda: (
            supabase_servico()
            .rpc(
                nome,
                {
                    "p_usuario_id": str(usuario.id),
                    "p_precificacao_id": str(precificacao_id),
                },
            )
            .execute()
        )
    )
    dado = resposta.data[0] if isinstance(resposta.data, list) else resposta.data
    if not dado:
        raise HTTPException(503, "A API não recebeu o resultado da verificação de submissão.")
    return dado


@router.get("/{precificacao_id}/submissao", response_model=VerificacaoSubmissao)
def verificar_submissao(
    precificacao_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar")),
) -> dict:
    return _rpc_submissao("avaliar_submissao_precificacao", usuario, precificacao_id)


@router.post("/{precificacao_id}/submissao", response_model=VerificacaoSubmissao)
def submeter_precificacao(
    precificacao_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar")),
) -> dict:
    return _rpc_submissao("submeter_precificacao", usuario, precificacao_id)


@router.get("/{precificacao_id}/historico-status", response_model=list[HistoricoStatusResposta])
def historico_status(
    precificacao_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler")),
) -> list[dict]:
    resposta = _executar(
        lambda: (
            _cliente(usuario)
            .table("historico_status_precificacao")
            .select("*")
            .eq("precificacao_id", str(precificacao_id))
            .order("ocorrido_em", desc=True)
            .execute()
        )
    )
    return resposta.data or []
