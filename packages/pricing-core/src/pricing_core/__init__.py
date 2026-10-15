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
from pricing_core.encargo import taxa_encargo, valor_encargo
from pricing_core.rentabilidade import Rentabilidade, derivar_rentabilidade

__all__ = [
    "CalculateMetadata",
    "CalculateRequest",
    "CalculateResponse",
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
    "derivar_rentabilidade",
    "taxa_encargo",
    "valor_encargo",
]
