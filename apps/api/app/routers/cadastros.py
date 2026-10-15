"""CRUD de matérias-primas e embalagens (US06)."""

from collections.abc import Callable
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario

router = APIRouter(prefix="/cadastros", tags=["cadastros"])

TipoInsumo = Literal["materias-primas", "embalagens"]
UnidadeMedida = Literal["kg", "g", "l", "ml", "un"]


class InsumoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=30)
    descricao: str = Field(min_length=1, max_length=200)
    unidade_medida: UnidadeMedida | None = None
    ncm_codigo: str = Field(pattern=r"^[0-9]{8}$")

    @model_validator(mode="after")
    def rejeitar_unidade_nula_explicita(self) -> "InsumoEntrada":
        if "unidade_medida" in self.model_fields_set and self.unidade_medida is None:
            raise ValueError("A unidade de medida não pode ser nula.")
        return self


class InsumoAtualizacao(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    descricao: str | None = Field(default=None, min_length=1, max_length=200)
    unidade_medida: UnidadeMedida | None = None
    ncm_codigo: str | None = Field(default=None, pattern=r"^[0-9]{8}$")
    ativo: bool | None = None

    @model_validator(mode="after")
    def rejeitar_nulos_explicitos(self) -> "InsumoAtualizacao":
        if any(getattr(self, campo) is None for campo in self.model_fields_set):
            raise ValueError("Os campos enviados não podem ser nulos.")
        return self


class InsumoResposta(BaseModel):
    id: UUID
    codigo: str
    descricao: str
    unidade_medida: UnidadeMedida
    ncm_codigo: str
    ativo: bool
    created_at: datetime
    updated_at: datetime


class PaginaInsumosResposta(BaseModel):
    registros: list[InsumoResposta]
    total: int
    pagina: int
    tamanho_pagina: int
    total_paginas: int


class NcmResposta(BaseModel):
    codigo: str
    descricao: str


def _tabela(tipo: TipoInsumo) -> str:
    return "materia_prima" if tipo == "materias-primas" else "embalagem"


def _erro_persistencia(erro: Exception) -> HTTPException:
    codigo = str(getattr(erro, "code", ""))
    try:
        codigo_http = int(getattr(erro, "status_code", 0) or 0)
    except (TypeError, ValueError):
        codigo_http = 0

    if codigo == "23505":
        return HTTPException(status.HTTP_409_CONFLICT, "Já existe um cadastro com este código.")
    if codigo == "23503":
        return HTTPException(422, "O NCM informado não existe na base de referência.")
    if codigo in {"23514", "22001", "22003", "22P02"} or codigo_http == 400:
        return HTTPException(422, "Os dados informados não são válidos para este cadastro.")
    if codigo == "42501" or codigo_http == 403:
        return HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode acessar ou alterar este cadastro.")
    if codigo_http == 401:
        return HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.")
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível acessar a base de cadastros. Tente novamente."
    )


def _executar[Resultado](operacao: Callable[[], Resultado]) -> Resultado:
    try:
        return operacao()
    except Exception as erro:
        raise _erro_persistencia(erro) from erro


def _buscar_por_id(tipo: TipoInsumo, registro_id: UUID, usuario: UsuarioAutenticado) -> dict:
    resposta = _executar(
        lambda: (
            supabase_do_usuario(usuario.access_token)
            .table(_tabela(tipo))
            .select("*")
            .eq("id", str(registro_id))
            .limit(1)
            .execute()
        )
    )
    registros = resposta.data or []
    if not registros:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cadastro não encontrado.")
    return registros[0]


def _padrao_busca_postgrest(termo: str) -> str:
    """Escapa a busca como valor do filtro PostgREST, sem abrir sua gramática."""
    escapado = termo.replace("\\", "\\\\").replace('"', '\\"').replace("%", "\\%").replace("_", "\\_")
    return f'"%{escapado}%"'


@router.get("/ncm", response_model=list[NcmResposta])
def buscar_ncm(
    termo: str = Query(min_length=1, max_length=80),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cadastro.ler")),
) -> list[dict]:
    cliente = _executar(lambda: supabase_do_usuario(usuario.access_token))
    termo = termo.strip()
    if not termo:
        raise HTTPException(422, "Informe um termo de busca para o NCM.")
    por_descricao = _executar(
        lambda: (
            cliente.table("ncm")
            .select("codigo,descricao")
            .ilike("descricao", f"%{termo}%")
            .order("descricao")
            .limit(20)
            .execute()
        )
    )
    encontrados = {item["codigo"]: item for item in (por_descricao.data or [])}

    if termo.isdigit():
        por_codigo = _executar(
            lambda: (
                cliente.table("ncm")
                .select("codigo,descricao")
                .ilike("codigo", f"{termo}%")
                .order("codigo")
                .limit(20)
                .execute()
            )
        )
        encontrados.update({item["codigo"]: item for item in (por_codigo.data or [])})

    ordenados = sorted(encontrados.values(), key=lambda item: item["descricao"].casefold())
    return ordenados[:20]


@router.get("/{tipo}", response_model=PaginaInsumosResposta)
def listar_insumos(
    tipo: TipoInsumo,
    busca: str | None = Query(default=None, max_length=100),
    ativo: bool | None = None,
    unidade_medida: UnidadeMedida | None = None,
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=20, ge=1, le=100),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cadastro.ler")),
) -> dict:
    termo = busca.strip() if busca else ""
    inicio = (pagina - 1) * tamanho_pagina

    def consultar():
        consulta = supabase_do_usuario(usuario.access_token).table(_tabela(tipo)).select("*", count="exact")
        if termo:
            padrao = _padrao_busca_postgrest(termo)
            consulta = consulta.or_(f"codigo.ilike.{padrao},descricao.ilike.{padrao},ncm_codigo.ilike.{padrao}")
        if ativo is not None:
            consulta = consulta.eq("ativo", ativo)
        if unidade_medida is not None:
            consulta = consulta.eq("unidade_medida", unidade_medida)
        return consulta.order("descricao").order("id").range(inicio, inicio + tamanho_pagina - 1).execute()

    resposta = _executar(consultar)
    total = resposta.count or 0
    return {
        "registros": resposta.data or [],
        "total": total,
        "pagina": pagina,
        "tamanho_pagina": tamanho_pagina,
        "total_paginas": (total + tamanho_pagina - 1) // tamanho_pagina,
    }


@router.get("/{tipo}/{registro_id}", response_model=InsumoResposta)
def obter_insumo(
    tipo: TipoInsumo,
    registro_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cadastro.ler")),
) -> dict:
    return _buscar_por_id(tipo, registro_id, usuario)


@router.post("/{tipo}", response_model=InsumoResposta, status_code=status.HTTP_201_CREATED)
def criar_insumo(
    tipo: TipoInsumo,
    entrada: InsumoEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cadastro.editar")),
) -> dict:
    dados = entrada.model_dump(exclude={"unidade_medida"})
    dados["unidade_medida"] = entrada.unidade_medida or ("kg" if tipo == "materias-primas" else "un")
    dados["created_by"] = str(usuario.id)
    dados["updated_by"] = str(usuario.id)
    resposta = _executar(
        lambda: supabase_do_usuario(usuario.access_token).table(_tabela(tipo)).insert(dados).select("*").execute()
    )
    if not resposta.data:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "O cadastro não foi retornado após a gravação.")
    return resposta.data[0]


@router.patch("/{tipo}/{registro_id}", response_model=InsumoResposta)
def atualizar_insumo(
    tipo: TipoInsumo,
    registro_id: UUID,
    entrada: InsumoAtualizacao,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cadastro.editar")),
) -> dict:
    dados = entrada.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(422, "Informe ao menos um campo para atualizar.")
    dados["updated_by"] = str(usuario.id)
    resposta = _executar(
        lambda: (
            supabase_do_usuario(usuario.access_token)
            .table(_tabela(tipo))
            .update(dados)
            .eq("id", str(registro_id))
            .select("*")
            .execute()
        )
    )
    if not resposta.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cadastro não encontrado.")
    return resposta.data[0]


@router.delete("/{tipo}/{registro_id}", response_model=InsumoResposta)
def inativar_insumo(
    tipo: TipoInsumo,
    registro_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cadastro.editar")),
) -> dict:
    atual = _buscar_por_id(tipo, registro_id, usuario)
    if not atual["ativo"]:
        return atual
    resposta = _executar(
        lambda: (
            supabase_do_usuario(usuario.access_token)
            .table(_tabela(tipo))
            .update({"ativo": False, "updated_by": str(usuario.id)})
            .eq("id", str(registro_id))
            .select("*")
            .execute()
        )
    )
    if not resposta.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cadastro não encontrado.")
    return resposta.data[0]
