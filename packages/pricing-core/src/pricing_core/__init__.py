"""pricing-core: regras puras do motor de preço do NeoPrice.

Sem dependência de banco, rede ou framework web. Todo valor monetário e
percentual é ``Decimal``.
"""

from pricing_core.contracts import (
    ENGINE_CONTRACT_VERSION,
    CalculateMetadata,
    CalculateRequest,
    CalculateResponse,
    DomainErrorCodigo,
    DomainErrorResponse,
    ImpostosDestacados,
    IsencaoMaoDeObraInfo,
    ItemInsumo,
    ModalidadeComercial,
    ParametrosComerciais,
    ParametrosImpostos,
    ParametrosProducao,
)
from pricing_core.cotacao import (
    Cotacao,
    CotacaoAmbigua,
    CotacaoError,
    CotacaoNaoEncontrada,
    cotacoes_vigentes,
    esta_vigente,
    resolver_cotacao,
)
from pricing_core.custos import (
    calcular_custo_embalagem,
    calcular_custo_ggf,
    calcular_custo_mod,
    calcular_custo_mp,
    calcular_custo_perda,
    calcular_custo_total,
)
from pricing_core.encargo import taxa_encargo, valor_encargo
from pricing_core.rentabilidade import Rentabilidade, derivar_rentabilidade

__all__ = [
    "CalculateMetadata",
    "CalculateRequest",
    "CalculateResponse",
    "Cotacao",
    "CotacaoAmbigua",
    "CotacaoError",
    "CotacaoNaoEncontrada",
    "DomainErrorCodigo",
    "DomainErrorResponse",
    "ENGINE_CONTRACT_VERSION",
    "ImpostosDestacados",
    "IsencaoMaoDeObraInfo",
    "ItemInsumo",
    "ModalidadeComercial",
    "ParametrosComerciais",
    "ParametrosImpostos",
    "ParametrosProducao",
    "Rentabilidade",
    "calcular_custo_embalagem",
    "calcular_custo_ggf",
    "calcular_custo_mod",
    "calcular_custo_mp",
    "calcular_custo_perda",
    "calcular_custo_total",
    "cotacoes_vigentes",
    "derivar_rentabilidade",
    "esta_vigente",
    "resolver_cotacao",
    "taxa_encargo",
    "valor_encargo",
]
