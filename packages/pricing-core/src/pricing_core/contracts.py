"""Contrato do motor de precificação (NeoPrice) — endpoint `/calculate`.

Publicado na Sprint 1 (14/09–25/09) para que o Squad B desenvolva as telas
de simulação contra um formato de dados fechado, sem esperar a
implementação real do motor (US16/US19, prevista para a Sprint 3).

Referências:
    - README.md, seção "Arquitetura" — motor como biblioteca pura; Decimal
      para todo valor monetário e percentual; versão do motor registrada
      por cenário.
    - docs/PI6-planejamento-produto.md, seção 2.3 — especificação do
      modelo de cálculo homologada com a área de Pricing.

Convenções:
    - Todo campo percentual é uma fração decimal (0.18 representa 18%),
      nunca um valor de 0 a 100.
    - Todo campo monetário/percentual usa `DecimalComoString`: internamente
      é `decimal.Decimal` (mesma precisão do motor), mas é serializado como
      string em JSON — evita perda de precisão de ponto flutuante no
      front-end. O front-end deve tratar esses campos com uma lib decimal
      (ex.: decimal.js), não com `Number()` direto.
    - `ENGINE_CONTRACT_VERSION` deve ser incrementada a cada mudança de
      forma do contrato ou de fórmula; o valor fica registrado em
      `CalculateMetadata.versao_motor` e, futuramente, no cenário
      persistido (RF09 — versionamento).

DECISÕES EM ABERTO — confirmar na homologação dos 30 casos com o PO
(ver tests/conformidade/README.md). Nenhuma delas muda a FORMA do
contrato abaixo, apenas a fórmula usada por trás dele:
    1. "Base" em `m × Base` (seção 2.3) — assumido aqui como `CustoTotal`.
    2. `Comissao$` — assumido aqui como `Comissao × PB`, por analogia a
       `Encargo$ = Encargo × PBsIPIsEncargo`, que é a única definição
       explícita na especificação.
    3. `MaterialCliente` (usado em CustoPerda) e `CustoEnviadoCliente`
       (usado em PBsIPIsEncargo) — assumidos aqui como o mesmo valor,
       informado uma única vez em `valor_material_cliente`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

ENGINE_CONTRACT_VERSION = "0.1.0-mock"

DecimalComoString = Annotated[
    Decimal,
    PlainSerializer(lambda v: format(v, "f"), return_type=str, when_used="json"),
]


class ModalidadeComercial(str, Enum):
    """Modalidades comerciais atendidas nesta fase do produto (PI VI, seção
    "Contexto de domínio")."""

    FULL_SERVICE_NACIONAL = "full_service_nacional"
    FULL_SERVICE_EXPORTACAO = "full_service_exportacao"
    INDUSTRIALIZACAO_POR_ENCOMENDA = "industrializacao_por_encomenda"


class ItemInsumo(BaseModel):
    """Um insumo (matéria-prima ou material de embalagem) da formulação
    (RF05). `percentual_descarte` só entra na fórmula de custo para itens
    de embalagem (seção 2.3); para matéria-prima o campo é aceito por
    completude do cadastro, mas hoje não é usado no cálculo.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo: str = Field(..., min_length=1, description="Código do insumo no cadastro mestre (RF03)")
    descricao: Optional[str] = None
    preco_negociado: DecimalComoString = Field(..., ge=0, description="PrecoNeg — preço cotado, na moeda de origem")
    moeda: str = Field("BRL", min_length=3, max_length=3, description="Código ISO da moeda da cotação")
    cambio: DecimalComoString = Field(Decimal("1"), gt=0, description="Câmbio da moeda de origem para BRL")
    margem_seguranca_percentual: DecimalComoString = Field(Decimal("0"), ge=0, description="MgSeg")
    quantidade: DecimalComoString = Field(..., gt=0, description="Qtd — por unidade de produto")
    percentual_descarte: DecimalComoString = Field(Decimal("0"), ge=0, le=1, description="Descarte (fração 0–1)")


class ParametrosProducao(BaseModel):
    """Parâmetros de mão de obra e GGF (RF03 — produtividade, MOD e GGF por
    linha de produção)."""

    taxa_mod: DecimalComoString = Field(..., ge=0, description="TaxaMOD")
    taxa_ggf: DecimalComoString = Field(..., ge=0, description="TaxaGGF")
    produtividade: DecimalComoString = Field(..., gt=0, description="Produtividade — usada em CustoMOD e CustoGGF")
    numero_funcionarios: DecimalComoString = Field(..., ge=0, description="NumFunc")


class ParametrosImpostos(BaseModel):
    """Alíquotas aplicadas ao cenário (RF12/US12). Frações decimais."""

    pis_percentual: DecimalComoString = Field(..., ge=0)
    cofins_percentual: DecimalComoString = Field(..., ge=0)
    icms_percentual: DecimalComoString = Field(..., ge=0)
    ipi_percentual: DecimalComoString = Field(Decimal("0"), ge=0)
    icms_interno_percentual: DecimalComoString = Field(Decimal("0"), ge=0, description="ICMSInt — ICMS-ST (US21)")
    fcp_percentual: DecimalComoString = Field(Decimal("0"), ge=0)
    mva_percentual: DecimalComoString = Field(Decimal("0"), ge=0)


class ParametrosComerciais(BaseModel):
    """Margem, comissão, frete e prazo do cenário (RF04)."""

    margem_desejada_percentual: DecimalComoString = Field(..., description="m")
    comissao_percentual: DecimalComoString = Field(Decimal("0"), ge=0)
    frete_percentual: DecimalComoString = Field(Decimal("0"), ge=0)
    prazo_medio_dias: DecimalComoString = Field(Decimal("0"), ge=0, description="PrazoMedio")
    taxa_financeira_mensal_percentual: DecimalComoString = Field(Decimal("0"), ge=0, description="Taxa")


class CalculateRequest(BaseModel):
    """Payload de entrada de `POST /calculate` (RF04–RF07, RF13, RF15)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    cenario_id: Optional[UUID] = Field(None, description="Cenário já existente sendo recalculado (RF09)")
    cliente_uf: str = Field(..., pattern=r"^[A-Z]{2}$", description="UF de destino — usada na isenção de MDO e no ICMS-ST")
    modalidade_comercial: ModalidadeComercial
    regime_tributario: str = Field(..., min_length=1, description="Ex.: Lucro Real, Lucro Presumido, Simples Nacional")

    materiais_primas: list[ItemInsumo] = Field(default_factory=list)
    embalagens: list[ItemInsumo] = Field(default_factory=list)
    perda_percentual: DecimalComoString = Field(Decimal("0"), ge=0, le=1, description="Perda")

    material_fornecido_pelo_cliente: bool = Field(False, description="Origem do material (RF05)")
    valor_material_cliente: DecimalComoString = Field(
        Decimal("0"), ge=0, description="MaterialCliente / CustoEnviadoCliente — ver decisão em aberto (3) no topo do módulo"
    )

    producao: ParametrosProducao
    impostos: ParametrosImpostos
    comercial: ParametrosComerciais

    @model_validator(mode="after")
    def _exige_ao_menos_um_insumo(self) -> "CalculateRequest":
        if not self.materiais_primas and not self.embalagens:
            raise ValueError("informe ao menos um item em materiais_primas ou embalagens")
        return self


class ImpostosDestacados(BaseModel):
    pis_valor: DecimalComoString
    cofins_valor: DecimalComoString
    icms_valor: DecimalComoString
    ipi_valor: DecimalComoString
    icms_st_valor: DecimalComoString = Decimal("0")


class IsencaoMaoDeObraInfo(BaseModel):
    aplicada: bool
    valor: DecimalComoString = Decimal("0")


class CalculateMetadata(BaseModel):
    versao_motor: str = ENGINE_CONTRACT_VERSION
    calculado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_mock: bool = Field(..., description="True enquanto o motor real (US16/US19, Sprint 3) não estiver integrado")


class CalculateResponse(BaseModel):
    """Saída de `POST /calculate` (RF06–RF08, RF13; campos-chave citados no
    critério de aceite de US19: PBsIPIsEncargo, PBsIPI, PB, ROL, MaCo$ e
    PrecoInd)."""

    custo_mp: DecimalComoString
    custo_embalagem: DecimalComoString
    custo_perda: DecimalComoString
    custo_mod: DecimalComoString
    custo_ggf: DecimalComoString
    custo_total: DecimalComoString

    denominador: DecimalComoString = Field(..., description="D — se <= 0, a API responde 422 com DomainErrorResponse")

    encargo_financeiro_percentual: DecimalComoString
    encargo_financeiro_valor: DecimalComoString

    preco_bruto_sem_ipi_sem_encargo: DecimalComoString = Field(..., description="PBsIPIsEncargo")
    preco_bruto_sem_ipi: DecimalComoString = Field(..., description="PBsIPI")
    preco_bruto_com_ipi: DecimalComoString = Field(..., description="PBcIPI")
    preco_bruto: DecimalComoString = Field(..., description="PB")
    preco_indicado: DecimalComoString = Field(..., description="PrecoInd")

    receita_operacional_liquida: DecimalComoString = Field(..., description="ROL")
    margem_contribuicao_valor: DecimalComoString = Field(..., description="MaCo$")
    margem_contribuicao_percentual: DecimalComoString

    isencao_mao_de_obra: IsencaoMaoDeObraInfo
    impostos_destacados: ImpostosDestacados

    metadata: CalculateMetadata


class DomainErrorCodigo(str, Enum):
    DENOMINADOR_INVALIDO = "DENOMINADOR_INVALIDO"
    ENTRADA_INVALIDA = "ENTRADA_INVALIDA"


class DomainErrorResponse(BaseModel):
    """Corpo de erro para entradas matematicamente inválidas (RNF08:
    "denominador D ≤ 0 retorna erro de domínio tratado e não exceção
    genérica")."""

    codigo: DomainErrorCodigo
    mensagem: str
    detalhes: dict = Field(default_factory=dict)
