"""Fila de aprovação do gerente (issue #67, US36).

O gerente olha exceção, não rotina: a fila traz as precificações em
aprovação da carteira dele, ordenadas pela data de submissão, com a margem
da versão vigente do cenário comparada à política de margem mínima (o
parâmetro global ``margem_minima_contribuicao_percentual``, #49). Filtra por
cliente e por margem. A comparação com a versão anterior usa
``/precificacoes/{id}/cenarios/comparacao`` (#63).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario

router = APIRouter(prefix="/aprovacoes", tags=["aprovação"])

CODIGO_POLITICA = "margem_minima_contribuicao_percentual"

DecimalComoString = Annotated[
    Decimal,
    PlainSerializer(lambda valor: format(valor, "f"), return_type=str, when_used="json"),
]
SituacaoMargem = Literal["abaixo_da_politica", "dentro_da_politica"]
Ordem = Literal["mais_antigas", "mais_recentes"]


class PoliticaMargem(BaseModel):
    margem_minima: DecimalComoString
    vigencia_inicio: date


class ItemFila(BaseModel):
    model_config = ConfigDict(extra="ignore")

    precificacao_id: UUID
    codigo: str
    cliente_id: UUID
    cliente_nome: str
    produto_id: UUID
    produto_descricao: str
    modalidade_comercial: str
    uf_destino: str | None = None
    homologacao_pendente: bool = False
    submetido_em: datetime
    submetido_por_nome: str | None = None
    cenario_versao: int | None = None
    versao_anterior: int | None = None
    volume: DecimalComoString | None = None
    preco_bruto: DecimalComoString | None = None
    margem_contribuicao_valor: DecimalComoString | None = None
    margem_contribuicao_percentual: DecimalComoString | None = None
    abaixo_da_politica: bool | None = None
    distancia_da_politica: DecimalComoString | None = None


class ClienteDaFila(BaseModel):
    id: UUID
    nome: str


class Fila(BaseModel):
    politica: PoliticaMargem | None
    clientes: list[ClienteDaFila]
    total_em_aprovacao: int
    itens: list[ItemFila]


# ------------------------------------------------------------ regra pura


def _decimal(valor) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


def classificar(linha: dict, margem_minima: Decimal | None) -> dict:
    """Marca se a margem da versão vigente está abaixo da política e a
    distância até ela (fração: -0.048 é 4,8 p.p. abaixo). Sem política ou
    sem cenário, os dois ficam nulos."""
    margem = _decimal(linha.get("margem_contribuicao_percentual"))
    if margem is None or margem_minima is None:
        return {**linha, "abaixo_da_politica": None, "distancia_da_politica": None}
    return {**linha, "abaixo_da_politica": margem < margem_minima, "distancia_da_politica": margem - margem_minima}


def montar_fila(
    linhas: list[dict],
    margem_minima: Decimal | None,
    *,
    cliente_id: UUID | None = None,
    situacao: SituacaoMargem | None = None,
    margem_ate: Decimal | None = None,
    ordem: Ordem = "mais_antigas",
) -> list[dict]:
    """Aplica os filtros e ordena pela data de submissão.

    `situacao` compara com a política; `margem_ate` é um teto livre de margem
    (fração). Cenário sem margem não entra em nenhum dos dois filtros. Na
    ordem padrão, o que espera há mais tempo vem primeiro.
    """
    itens = [classificar(linha, margem_minima) for linha in linhas]
    if cliente_id is not None:
        itens = [item for item in itens if str(item["cliente_id"]) == str(cliente_id)]
    if situacao is not None:
        abaixo = situacao == "abaixo_da_politica"
        itens = [item for item in itens if item["abaixo_da_politica"] is abaixo]
    if margem_ate is not None:
        itens = [
            item
            for item in itens
            if (margem := _decimal(item.get("margem_contribuicao_percentual"))) is not None and margem <= margem_ate
        ]
    return sorted(
        itens,
        key=lambda item: (str(item["submetido_em"]), item["codigo"]),
        reverse=ordem == "mais_recentes",
    )


# ------------------------------------------------------------ rota


def _consultar(operacao):
    try:
        return operacao()
    except Exception as erro:
        if str(getattr(erro, "code", "")) == "42501":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Seu perfil não pode consultar a fila de aprovação."
            ) from erro
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Não foi possível carregar a fila de aprovação."
        ) from erro


@router.get("/fila", response_model=Fila)
def fila_de_aprovacao(
    cliente_id: UUID | None = None,
    situacao: SituacaoMargem | None = Query(default=None, description="Compara a margem com a política"),
    margem_ate: Decimal | None = Query(default=None, ge=0, le=1, description="Margem de contribuição máxima (fração)"),
    ordem: Ordem = "mais_antigas",
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.aprovar")),
) -> dict:
    cliente = supabase_do_usuario(usuario.access_token)
    linhas = _consultar(lambda: cliente.table("fila_aprovacao").select("*").execute()).data or []
    politica = (
        _consultar(
            lambda: (
                cliente.table("parametro_global")
                .select("valor,vigencia_inicio")
                .eq("codigo", CODIGO_POLITICA)
                .lte("vigencia_inicio", date.today().isoformat())
                .order("vigencia_inicio", desc=True)
                .limit(1)
                .execute()
            )
        ).data
        or [None]
    )[0]

    margem_minima = _decimal(politica["valor"]) if politica else None
    if situacao is not None and margem_minima is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Não há margem mínima da política vigente. Cadastre-a em Câmbio e parâmetros para filtrar por ela.",
        )

    clientes = {str(linha["cliente_id"]): linha["cliente_nome"] for linha in linhas}
    return {
        "politica": (
            {"margem_minima": margem_minima, "vigencia_inicio": politica["vigencia_inicio"]} if politica else None
        ),
        "clientes": [{"id": id_, "nome": nome} for id_, nome in sorted(clientes.items(), key=lambda par: par[1])],
        "total_em_aprovacao": len(linhas),
        "itens": montar_fila(
            linhas, margem_minima, cliente_id=cliente_id, situacao=situacao, margem_ate=margem_ate, ordem=ordem
        ),
    }
