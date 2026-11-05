"""Manutenção e resolução de alíquotas fiscais versionadas por vigência."""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario
from app.services.importacao_aliquotas import CABECALHO_MODELO, ler_planilha

router = APIRouter(prefix="/parametros-fiscais/aliquotas", tags=["parâmetros fiscais"])

RegimeTributario = Literal["lucro_real", "lucro_presumido", "simples_nacional"]


class AliquotaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    uf_destino: str = Field(pattern=r"^[A-Z]{2}$")
    ncm_codigo: str | None = Field(default=None, pattern=r"^[0-9]{8}$")
    regime_tributario: RegimeTributario
    vigencia_inicio: date
    pis_percentual: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    cofins_percentual: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    icms_percentual: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    ipi_percentual: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    icms_interno_percentual: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    fcp_percentual: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    mva_percentual: Decimal = Field(ge=0, allow_inf_nan=False)


class AliquotaAtualizacao(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    uf_destino: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    ncm_codigo: str | None = Field(default=None, pattern=r"^[0-9]{8}$")
    regime_tributario: RegimeTributario | None = None
    vigencia_inicio: date | None = None
    pis_percentual: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    cofins_percentual: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    icms_percentual: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    ipi_percentual: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    icms_interno_percentual: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    fcp_percentual: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    mva_percentual: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def rejeitar_atualizacao_vazia_ou_nula(self) -> "AliquotaAtualizacao":
        if not self.model_fields_set or any(
            getattr(self, campo) is None for campo in self.model_fields_set if campo != "ncm_codigo"
        ):
            raise ValueError("Informe campos válidos para atualizar a alíquota.")
        return self


class AliquotaResposta(AliquotaEntrada):
    # A entrada proíbe campos extras; a resposta vem do banco com colunas que
    # não expomos (created_by, updated_by) e só as ignora.
    model_config = ConfigDict(extra="ignore")

    id: UUID
    created_at: datetime
    updated_at: datetime


class ImportacaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conteudo_csv: str = Field(min_length=1, max_length=2_000_000)
    simular: bool = True


class ErroImportacao(BaseModel):
    linha: int
    mensagem: str


class ImportacaoResposta(BaseModel):
    simulacao: bool
    linhas_validas: int
    novas: int = 0
    atualizadas: int = 0
    inalteradas: int = 0
    erros: list[ErroImportacao] = []
    cabecalho_modelo: str = CABECALHO_MODELO


def escolher_aliquota_aplicavel(registros: list[dict], ncm_codigo: str, data_referencia: date) -> dict | None:
    """Regra vigente na data: a específica do NCM tem precedência sobre a
    regra geral da UF; em cada uma, vale a de início de vigência mais recente
    que não seja posterior à data."""

    def mais_recente(candidatas: list[dict]) -> dict | None:
        vigentes = [item for item in candidatas if date.fromisoformat(str(item["vigencia_inicio"])) <= data_referencia]
        return max(vigentes, key=lambda item: str(item["vigencia_inicio"]), default=None)

    especifica = mais_recente([item for item in registros if item["ncm_codigo"] == ncm_codigo])
    return especifica or mais_recente([item for item in registros if item["ncm_codigo"] is None])


def _erro_persistencia(erro: Exception) -> HTTPException:
    codigo = str(getattr(erro, "code", ""))
    try:
        codigo_http = int(getattr(erro, "status_code", 0) or 0)
    except (TypeError, ValueError):
        codigo_http = 0
    if codigo == "23505":
        return HTTPException(status.HTTP_409_CONFLICT, "Já existe uma alíquota para esta UF, NCM, regime e vigência.")
    if codigo in {"23503", "23514", "22001", "22003", "22P02"} or codigo_http == 400:
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Os dados informados não são válidos para esta alíquota.",
        )
    if codigo == "42501" or codigo_http == 403:
        return HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode acessar ou alterar alíquotas.")
    if codigo_http == 401:
        return HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.")
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível acessar as alíquotas fiscais.")


def _executar[Resultado](operacao: Callable[[], Resultado]) -> Resultado:
    try:
        return operacao()
    except Exception as erro:
        raise _erro_persistencia(erro) from erro


def _consulta_base(usuario: UsuarioAutenticado):
    return supabase_do_usuario(usuario.access_token).table("aliquota_fiscal")


@router.get("/resolver", response_model=AliquotaResposta)
def resolver_aliquota(
    uf_destino: str = Query(pattern=r"^[A-Z]{2}$"),
    ncm_codigo: str = Query(pattern=r"^[0-9]{8}$"),
    regime_tributario: RegimeTributario = Query(),
    data_referencia: date = Query(default_factory=date.today),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_fiscal.ler")),
) -> dict:
    resposta = _executar(
        lambda: (
            _consulta_base(usuario)
            .select("*")
            .eq("uf_destino", uf_destino)
            .eq("regime_tributario", regime_tributario)
            .or_(f"ncm_codigo.eq.{ncm_codigo},ncm_codigo.is.null")
            .lte("vigencia_inicio", data_referencia.isoformat())
            .order("vigencia_inicio", desc=True)
            .execute()
        )
    )
    aplicavel = escolher_aliquota_aplicavel(resposta.data or [], ncm_codigo, data_referencia)
    if aplicavel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Não há alíquota vigente para os filtros informados.")
    return aplicavel


@router.get("", response_model=list[AliquotaResposta])
def listar_aliquotas(
    uf_destino: str | None = Query(default=None, pattern=r"^[A-Z]{2}$"),
    ncm_codigo: str | None = Query(default=None, pattern=r"^[0-9]{1,8}$"),
    regime_tributario: RegimeTributario | None = None,
    vigencia_ate: date | None = None,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_fiscal.ler")),
) -> list[dict]:
    def consultar():
        consulta = _consulta_base(usuario).select("*")
        if uf_destino:
            consulta = consulta.eq("uf_destino", uf_destino)
        if ncm_codigo:
            consulta = consulta.ilike("ncm_codigo", f"{ncm_codigo}%")
        if regime_tributario:
            consulta = consulta.eq("regime_tributario", regime_tributario)
        if vigencia_ate:
            consulta = consulta.lte("vigencia_inicio", vigencia_ate.isoformat())
        return (
            consulta.order("uf_destino")
            .order("ncm_codigo")
            .order("regime_tributario")
            .order("vigencia_inicio", desc=True)
            .execute()
        )

    resposta = _executar(consultar)
    return resposta.data or []


@router.post("", response_model=AliquotaResposta, status_code=status.HTTP_201_CREATED)
def criar_aliquota(
    entrada: AliquotaEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_fiscal.editar")),
) -> dict:
    dados = entrada.model_dump(mode="json")
    dados.update(created_by=str(usuario.id), updated_by=str(usuario.id))
    resposta = _executar(lambda: _consulta_base(usuario).insert(dados).execute())
    if not resposta.data:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "A alíquota não foi retornada após a gravação.")
    return resposta.data[0]


@router.patch("/{aliquota_id}", response_model=AliquotaResposta)
def atualizar_aliquota(
    aliquota_id: UUID,
    entrada: AliquotaAtualizacao,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_fiscal.editar")),
) -> dict:
    dados = entrada.model_dump(exclude_unset=True, mode="json")
    dados["updated_by"] = str(usuario.id)
    resposta = _executar(lambda: _consulta_base(usuario).update(dados).eq("id", str(aliquota_id)).execute())
    if not resposta.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alíquota não encontrada.")
    return resposta.data[0]


@router.post("/importacao", response_model=ImportacaoResposta)
def importar_aliquotas(
    entrada: ImportacaoEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("parametro_fiscal.editar")),
) -> ImportacaoResposta:
    """Importa a planilha de alíquotas. Com `simular` (padrão), só valida e
    conta o que seria criado ou alterado; sem ele, grava tudo de uma vez ou
    nada, e só se nenhuma linha tiver erro."""
    leitura = ler_planilha(entrada.conteudo_csv, AliquotaEntrada)
    erros = [ErroImportacao(linha=erro.linha, mensagem=erro.mensagem) for erro in leitura.erros]
    if erros:
        if not entrada.simular:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"A planilha tem {len(erros)} linha(s) com erro; nada foi importado. Valide antes de confirmar.",
            )
        return ImportacaoResposta(simulacao=True, linhas_validas=len(leitura.aliquotas), erros=erros)

    resposta = _executar(
        lambda: (
            supabase_do_usuario(usuario.access_token)
            .rpc("importar_aliquotas", {"p_linhas": leitura.aliquotas, "p_simular": entrada.simular})
            .execute()
        )
    )
    contagem = (resposta.data or [{}])[0]
    return ImportacaoResposta(
        simulacao=entrada.simular,
        linhas_validas=len(leitura.aliquotas),
        novas=contagem.get("novas") or 0,
        atualizadas=contagem.get("atualizadas") or 0,
        inalteradas=contagem.get("inalteradas") or 0,
    )
