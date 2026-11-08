"""Versões de cenário de uma precificação (issue #63, US31).

Cada gravação cria uma nova versão; a anterior fica consultável e igual (o
banco recusa alterar ou excluir versão salva). O resultado é sempre
calculado aqui, pelo motor, a partir da entrada: o cliente não manda
números de preço. A vigente é a versão de maior número.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario
from app.routers.calculate import calculate
from app.services.comparacao_cenarios import comparar_cenarios
from pricing_core.contracts import CalculateRequest
from pricing_core.rentabilidade import derivar_rentabilidade

router = APIRouter(prefix="/precificacoes/{precificacao_id}/cenarios", tags=["cenários"])

DecimalComoString = Annotated[
    Decimal,
    PlainSerializer(lambda valor: format(valor, "f"), return_type=str, when_used="json"),
]
Versao = Annotated[int, Path(ge=1)]
COLUNAS_RESUMO = (
    "id,precificacao_id,versao,cenario_origem_id,observacao,volume,data_calculo,versao_motor,"
    "preco_bruto,preco_bruto_sem_ipi,custo_total,margem_contribuicao_valor,margem_contribuicao_percentual,"
    "created_by,created_at"
)


# ------------------------------------------------------------ modelos


class CenarioEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrada: CalculateRequest
    volume: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3, allow_inf_nan=False)
    observacao: str | None = Field(default=None, max_length=500)


class DuplicacaoEntrada(BaseModel):
    """Nova versão a partir de outra: mesma entrada, recalculada pelo motor
    atual. O volume pode ser trocado; sem ele, vale o da origem."""

    model_config = ConfigDict(extra="forbid")

    volume: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3, allow_inf_nan=False)
    observacao: str | None = Field(default=None, max_length=500)


class CenarioResumo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    precificacao_id: UUID
    versao: int
    vigente: bool = False
    cenario_origem_id: UUID | None = None
    observacao: str | None = None
    volume: DecimalComoString | None = None
    data_calculo: date
    versao_motor: str
    preco_bruto: DecimalComoString
    preco_bruto_sem_ipi: DecimalComoString
    custo_total: DecimalComoString
    margem_contribuicao_valor: DecimalComoString
    margem_contribuicao_percentual: DecimalComoString
    created_by: UUID | None = None
    created_at: datetime


class Rentabilidade(BaseModel):
    """Valores em reais do cenário inteiro, para o volume negociado (#64)."""

    volume: DecimalComoString
    receita_operacional_bruta: DecimalComoString
    deducoes: DecimalComoString
    receita_operacional_liquida: DecimalComoString
    margem_contribuicao: DecimalComoString
    margem_bruta: DecimalComoString


class CenarioDetalhe(CenarioResumo):
    entrada: dict
    resultado: dict
    rentabilidade: Rentabilidade | None = None


class CenarioSalvoSemCustos(BaseModel):
    """ConfirmaÃ§Ã£o de gravaÃ§Ã£o que preserva preÃ§os sem devolver custo/margem."""

    id: UUID
    precificacao_id: UUID
    versao: int
    vigente: bool
    volume: DecimalComoString | None = None
    data_calculo: date
    versao_motor: str
    preco_bruto: DecimalComoString
    preco_bruto_sem_ipi: DecimalComoString
    created_at: datetime


class PrecoDaVersao(BaseModel):
    model_config = ConfigDict(extra="ignore")

    versao: int
    vigente: bool
    volume: DecimalComoString | None = None
    data_calculo: date
    preco_bruto: DecimalComoString
    preco_bruto_sem_ipi: DecimalComoString
    created_at: datetime


class IndicadorComparado(BaseModel):
    codigo: str
    rotulo: str
    unidade: Literal["un", "brl", "percentual"]
    valor_de: DecimalComoString | None
    valor_para: DecimalComoString | None
    variacao: DecimalComoString | None
    variacao_percentual: DecimalComoString | None
    sentido: Literal["subiu", "desceu", "igual", "sem_base"]


class Comparacao(BaseModel):
    versao_de: int
    versao_para: int
    indicadores: list[IndicadorComparado]


# ------------------------------------------------------------ acesso ao banco


def _erro(erro: Exception) -> HTTPException:
    codigo = str(getattr(erro, "code", ""))
    mensagem = getattr(erro, "message", None) or str(erro)
    if codigo == "P0002":
        return HTTPException(status.HTTP_404_NOT_FOUND, "Precificação não encontrada.")
    if codigo in {"22023", "23503", "23514", "22P02", "22003"}:
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, mensagem)
    if codigo == "23505":
        return HTTPException(status.HTTP_409_CONFLICT, "Outra versão foi salva ao mesmo tempo; tente de novo.")
    if codigo == "23001":
        return HTTPException(status.HTTP_409_CONFLICT, mensagem)
    if codigo == "42501":
        return HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode acessar ou alterar esta precificação.")
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível acessar os cenários.")


def _executar(operacao):
    try:
        return operacao()
    except HTTPException:
        raise
    except Exception as erro:
        raise _erro(erro) from erro


def _cliente(usuario: UsuarioAutenticado):
    return supabase_do_usuario(usuario.access_token)


def _versoes(usuario: UsuarioAutenticado, precificacao_id: UUID, colunas: str) -> list[dict]:
    resposta = _executar(
        lambda: (
            _cliente(usuario)
            .table("cenario")
            .select(colunas)
            .eq("precificacao_id", str(precificacao_id))
            .order("versao", desc=True)
            .execute()
        )
    )
    return resposta.data or []


def _versao(usuario: UsuarioAutenticado, precificacao_id: UUID, versao: int) -> dict:
    resposta = _executar(
        lambda: (
            _cliente(usuario)
            .table("cenario")
            .select("*")
            .eq("precificacao_id", str(precificacao_id))
            .eq("versao", versao)
            .execute()
        )
    )
    if not resposta.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"A versão {versao} não existe nesta precificação.")
    return resposta.data[0]


def _com_rentabilidade(cenario: dict) -> dict:
    """Acrescenta ROB, deduções, ROL, MaCo e MB em reais quando a versão tem
    volume. Sem volume não há valor absoluto: só a margem unitária."""
    volume = _volume(cenario)
    if volume is None:
        return {**cenario, "rentabilidade": None}
    resultado = cenario["resultado"]
    rentabilidade = derivar_rentabilidade(
        volume,
        preco_bruto_sem_ipi=resultado["preco_bruto_sem_ipi"],
        receita_operacional_liquida=resultado["receita_operacional_liquida"],
        margem_contribuicao_valor=resultado["margem_contribuicao_valor"],
        custo_total=resultado["custo_total"],
    )
    return {**cenario, "rentabilidade": vars(rentabilidade)}


def _marcar_vigente(linhas: list[dict]) -> list[dict]:
    maior = max((linha["versao"] for linha in linhas), default=None)
    return [{**linha, "vigente": linha["versao"] == maior} for linha in linhas]


def _salvar(
    usuario: UsuarioAutenticado,
    precificacao_id: UUID,
    entrada: CalculateRequest,
    volume: Decimal | None,
    observacao: str | None,
    origem_id: str | None = None,
) -> dict:
    resultado = calculate(entrada)
    if resultado.metadata.is_mock:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Resultados produzidos por uma versÃ£o mock nÃ£o podem ser salvos como cenÃ¡rios reais.",
        )
    parametros = {
        "p_precificacao_id": str(precificacao_id),
        "p_entrada": entrada.model_dump(mode="json"),
        "p_resultado": resultado.model_dump(mode="json"),
        "p_versao_motor": resultado.metadata.versao_motor,
        "p_volume": None if volume is None else format(volume, "f"),
        "p_observacao": observacao,
        "p_cenario_origem_id": origem_id,
    }
    resposta = _executar(lambda: _cliente(usuario).rpc("salvar_cenario", parametros).execute())
    salvo = resposta.data[0] if isinstance(resposta.data, list) else resposta.data
    if not salvo:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "A versão não foi retornada após a gravação.")
    return _com_rentabilidade({**salvo, "vigente": True})


# ------------------------------------------------------------ rotas


@router.get("", response_model=list[CenarioResumo])
def listar_versoes(
    precificacao_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("custo.ler")),
) -> list[dict]:
    return _marcar_vigente(_versoes(usuario, precificacao_id, COLUNAS_RESUMO))


@router.get("/precos", response_model=list[PrecoDaVersao])
def listar_precos(
    precificacao_id: UUID,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler")),
) -> list[dict]:
    """Preço de cada versão, sem custo nem margem, para quem negocia."""
    resposta = _executar(
        lambda: (
            _cliente(usuario)
            .table("cenario_preco")
            .select("*")
            .eq("precificacao_id", str(precificacao_id))
            .order("versao", desc=True)
            .execute()
        )
    )
    return resposta.data or []


@router.get("/comparacao", response_model=Comparacao)
def comparar_versoes(
    precificacao_id: UUID,
    de: int = Query(ge=1),
    para: int = Query(ge=1),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("custo.ler")),
) -> dict:
    if de == para:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Escolha duas versões diferentes para comparar.")
    indicadores = comparar_cenarios(
        _versao(usuario, precificacao_id, de),
        _versao(usuario, precificacao_id, para),
    )
    return {"versao_de": de, "versao_para": para, "indicadores": [vars(item) for item in indicadores]}


@router.get("/{versao}", response_model=CenarioDetalhe)
def consultar_versao(
    precificacao_id: UUID,
    versao: Versao,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("custo.ler")),
) -> dict:
    detalhe = _versao(usuario, precificacao_id, versao)
    maior = max(linha["versao"] for linha in _versoes(usuario, precificacao_id, "versao"))
    return _com_rentabilidade({**detalhe, "vigente": detalhe["versao"] == maior})


@router.post("", response_model=CenarioDetalhe | CenarioSalvoSemCustos, status_code=status.HTTP_201_CREATED)
def salvar_nova_versao(
    precificacao_id: UUID,
    corpo: CenarioEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar")),
) -> dict:
    salvo = _salvar(usuario, precificacao_id, corpo.entrada, corpo.volume, corpo.observacao)
    if usuario.tem_permissao("custo.ler"):
        return salvo
    campos_preco = {
        "id", "precificacao_id", "versao", "vigente", "volume", "data_calculo", "versao_motor",
        "preco_bruto", "preco_bruto_sem_ipi", "created_at",
    }
    return CenarioSalvoSemCustos.model_validate({campo: salvo[campo] for campo in campos_preco})


@router.post("/{versao}/duplicar", response_model=CenarioDetalhe, status_code=status.HTTP_201_CREATED)
def duplicar_versao(
    precificacao_id: UUID,
    versao: Versao,
    corpo: DuplicacaoEntrada,
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.editar")),
) -> dict:
    origem = _versao(usuario, precificacao_id, versao)
    volume = corpo.volume if corpo.volume is not None else _volume(origem)
    observacao = corpo.observacao or f"Duplicada da versão {versao}"
    entrada = CalculateRequest.model_validate(origem["entrada"])
    return _salvar(usuario, precificacao_id, entrada, volume, observacao, origem_id=origem["id"])


def _volume(cenario: dict) -> Decimal | None:
    return None if cenario.get("volume") is None else Decimal(str(cenario["volume"]))
