"""Câmbio por moeda e parâmetros globais do cálculo (issue #49, US13 e US14).

Os dois são históricos por data: o valor vigente em uma data é o de data
mais recente que não seja posterior a ela. O banco não deixa a aplicação
mexer no passado (migration 20261103130001), então mudar um parâmetro é
cadastrar uma nova vigência e os cálculos antigos continuam reproduzíveis.
"""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario

router_cambio = APIRouter(prefix="/cambios", tags=["câmbio"])
router_parametros = APIRouter(prefix="/parametros-globais", tags=["parâmetros globais"])

Fonte = Literal["manual", "ptax"]
CodigoParametro = Literal[
    "perda_percentual",
    "taxa_financeira_mensal_percentual",
    "prazo_medio_padrao_dias",
    "desvio_maximo_cotacao_percentual",
]
CODIGOS_PARAMETRO: tuple[str, ...] = CodigoParametro.__args__


# ------------------------------------------------------------ modelos


class CambioEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    moeda: str = Field(pattern=r"^[A-Z]{3}$")
    data_referencia: date
    taxa: Decimal = Field(gt=0, max_digits=14, decimal_places=6, allow_inf_nan=False)
    margem_seguranca_percentual: Decimal = Field(
        default=Decimal("0"), ge=0, le=1, max_digits=7, decimal_places=6, allow_inf_nan=False
    )
    fonte: Fonte = "manual"

    @model_validator(mode="after")
    def rejeitar_real(self) -> "CambioEntrada":
        if self.moeda == "BRL":
            raise ValueError("O câmbio é de moeda estrangeira; o real não tem câmbio.")
        return self


class CambioAtualizacao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taxa: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=6, allow_inf_nan=False)
    margem_seguranca_percentual: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=7, decimal_places=6, allow_inf_nan=False
    )
    fonte: Fonte | None = None

    @model_validator(mode="after")
    def rejeitar_atualizacao_vazia_ou_nula(self) -> "CambioAtualizacao":
        if not self.model_fields_set or any(getattr(self, campo) is None for campo in self.model_fields_set):
            raise ValueError("Informe a taxa, a margem ou a fonte para corrigir o câmbio.")
        return self


class CambioResposta(CambioEntrada):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    created_at: datetime
    updated_at: datetime


class CambioVigente(CambioResposta):
    taxa_com_margem: Decimal = Field(description="taxa × (1 + margem): o câmbio que entra no custo")


class ParametroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: CodigoParametro
    valor: Decimal = Field(ge=0, max_digits=14, decimal_places=6, allow_inf_nan=False)
    vigencia_inicio: date

    @model_validator(mode="after")
    def validar_valor_do_codigo(self) -> "ParametroEntrada":
        if self.codigo == "prazo_medio_padrao_dias":
            if self.valor != self.valor.to_integral_value():
                raise ValueError("O prazo médio padrão é em dias inteiros.")
        elif self.valor > 1:
            raise ValueError("Percentuais são frações entre 0 e 1 (0.012 = 1,2%).")
        return self


class ParametroAtualizacao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor: Decimal = Field(ge=0, max_digits=14, decimal_places=6, allow_inf_nan=False)


class ParametroResposta(ParametroEntrada):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    created_at: datetime
    updated_at: datetime


class ParametrosVigentes(BaseModel):
    data_referencia: date
    parametros: dict[str, ParametroResposta]
    faltando: list[str]


# ------------------------------------------------------------ regras puras


def escolher_vigente(registros: list[dict], campo_data: str, data_referencia: date) -> dict | None:
    """O registro de data mais recente que não seja posterior à data."""
    vigentes = [item for item in registros if date.fromisoformat(str(item[campo_data])) <= data_referencia]
    return max(vigentes, key=lambda item: str(item[campo_data]), default=None)


def parametros_vigentes(registros: list[dict], data_referencia: date) -> dict[str, dict]:
    """Um valor por código: a vigência mais recente que já começou na data."""
    por_codigo: dict[str, list[dict]] = {}
    for item in registros:
        por_codigo.setdefault(item["codigo"], []).append(item)
    escolhidos = {
        codigo: escolher_vigente(itens, "vigencia_inicio", data_referencia) for codigo, itens in por_codigo.items()
    }
    return {codigo: item for codigo, item in escolhidos.items() if item is not None}


def taxa_com_margem(cambio: dict) -> Decimal:
    return Decimal(str(cambio["taxa"])) * (1 + Decimal(str(cambio["margem_seguranca_percentual"])))


# ------------------------------------------------------------ acesso ao banco


def _erro_persistencia(erro: Exception, recurso: str) -> HTTPException:
    codigo = str(getattr(erro, "code", ""))
    try:
        codigo_http = int(getattr(erro, "status_code", 0) or 0)
    except (TypeError, ValueError):
        codigo_http = 0
    if codigo == "23001":
        return HTTPException(status.HTTP_409_CONFLICT, getattr(erro, "message", None) or str(erro))
    if codigo == "23505":
        return HTTPException(status.HTTP_409_CONFLICT, f"Já existe {recurso} para esta data.")
    if codigo in {"23503", "23514", "22001", "22003", "22P02"} or codigo_http == 400:
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Os dados informados não são válidos para {recurso}."
        )
    if codigo == "42501" or codigo_http == 403:
        return HTTPException(status.HTTP_403_FORBIDDEN, f"Seu perfil não pode acessar ou alterar {recurso}.")
    if codigo_http == 401:
        return HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.")
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Não foi possível acessar {recurso}.")


def _executar[Resultado](operacao: Callable[[], Resultado], recurso: str) -> Resultado:
    try:
        return operacao()
    except Exception as erro:
        raise _erro_persistencia(erro, recurso) from erro


def _tabela(usuario: UsuarioAutenticado, nome: str):
    return supabase_do_usuario(usuario.access_token).table(nome)


def _primeira_linha(resposta, mensagem_404: str) -> dict:
    if not resposta.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, mensagem_404)
    return resposta.data[0]


# ------------------------------------------------------------ câmbio


@router_cambio.get("/vigente", response_model=CambioVigente)
def cambio_vigente(
    moeda: str = Query(pattern=r"^[A-Z]{3}$"),
    data_referencia: date = Query(default_factory=date.today),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cambio.ler")),
) -> dict:
    resposta = _executar(
        lambda: (
            _tabela(usuario, "cambio")
            .select("*")
            .eq("moeda", moeda)
            .lte("data_referencia", data_referencia.isoformat())
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        ),
        "o câmbio",
    )
    vigente = escolher_vigente(resposta.data or [], "data_referencia", data_referencia)
    if vigente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Não há câmbio de {moeda} cadastrado até {data_referencia}.")
    return {**vigente, "taxa_com_margem": taxa_com_margem(vigente)}


@router_cambio.get("", response_model=list[CambioResposta])
def listar_cambios(
    moeda: str | None = Query(default=None, pattern=r"^[A-Z]{3}$"),
    data_ate: date | None = None,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cambio.ler")),
) -> list[dict]:
    def consultar():
        consulta = _tabela(usuario, "cambio").select("*")
        if moeda:
            consulta = consulta.eq("moeda", moeda)
        if data_ate:
            consulta = consulta.lte("data_referencia", data_ate.isoformat())
        return consulta.order("moeda").order("data_referencia", desc=True).execute()

    return _executar(consultar, "o câmbio").data or []


@router_cambio.post("", response_model=CambioResposta, status_code=status.HTTP_201_CREATED)
def criar_cambio(
    entrada: CambioEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cambio.editar")),
) -> dict:
    dados = {**entrada.model_dump(mode="json"), "created_by": str(usuario.id), "updated_by": str(usuario.id)}
    resposta = _executar(lambda: _tabela(usuario, "cambio").insert(dados).execute(), "o câmbio")
    return _primeira_linha(resposta, "O câmbio não foi retornado após a gravação.")


@router_cambio.patch("/{cambio_id}", response_model=CambioResposta)
def corrigir_cambio(
    cambio_id: UUID,
    entrada: CambioAtualizacao,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("cambio.editar")),
) -> dict:
    dados = {**entrada.model_dump(exclude_unset=True, mode="json"), "updated_by": str(usuario.id)}
    resposta = _executar(
        lambda: _tabela(usuario, "cambio").update(dados).eq("id", str(cambio_id)).execute(), "o câmbio"
    )
    return _primeira_linha(resposta, "Câmbio não encontrado.")


# ------------------------------------------------------------ parâmetros globais


@router_parametros.get("/vigentes", response_model=ParametrosVigentes)
def consultar_parametros_vigentes(
    data_referencia: date = Query(default_factory=date.today),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_global.ler")),
) -> dict:
    resposta = _executar(
        lambda: (
            _tabela(usuario, "parametro_global")
            .select("*")
            .lte("vigencia_inicio", data_referencia.isoformat())
            .execute()
        ),
        "os parâmetros globais",
    )
    vigentes = parametros_vigentes(resposta.data or [], data_referencia)
    return {
        "data_referencia": data_referencia,
        "parametros": vigentes,
        "faltando": [codigo for codigo in CODIGOS_PARAMETRO if codigo not in vigentes],
    }


@router_parametros.get("", response_model=list[ParametroResposta])
def listar_parametros(
    codigo: CodigoParametro | None = None,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_global.ler")),
) -> list[dict]:
    def consultar():
        consulta = _tabela(usuario, "parametro_global").select("*")
        if codigo:
            consulta = consulta.eq("codigo", codigo)
        return consulta.order("codigo").order("vigencia_inicio", desc=True).execute()

    return _executar(consultar, "os parâmetros globais").data or []


@router_parametros.post("", response_model=ParametroResposta, status_code=status.HTTP_201_CREATED)
def criar_vigencia_de_parametro(
    entrada: ParametroEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_global.editar")),
) -> dict:
    dados = {**entrada.model_dump(mode="json"), "created_by": str(usuario.id), "updated_by": str(usuario.id)}
    resposta = _executar(lambda: _tabela(usuario, "parametro_global").insert(dados).execute(), "os parâmetros globais")
    return _primeira_linha(resposta, "O parâmetro não foi retornado após a gravação.")


@router_parametros.patch("/{parametro_id}", response_model=ParametroResposta)
def corrigir_vigencia_de_parametro(
    parametro_id: UUID,
    entrada: ParametroAtualizacao,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_global.editar")),
) -> dict:
    dados = {**entrada.model_dump(mode="json"), "updated_by": str(usuario.id)}
    resposta = _executar(
        lambda: _tabela(usuario, "parametro_global").update(dados).eq("id", str(parametro_id)).execute(),
        "os parâmetros globais",
    )
    return _primeira_linha(resposta, "Parâmetro não encontrado.")
