"""Contrato entre o front e a API do motor (issue #59).

`apps/web/src/types/calculate.generated.ts` é mantido à mão (o gerador
`scripts/generate_ts_types.py` depende de ferramentas fora do monorepo).
Este teste lê o .ts e compara com `pricing_core.contracts`: se alguém
muda um campo de um lado só, o CI falha antes do front quebrar em produção.

Regras checadas:
- cada interface tem exatamente os campos do modelo Pydantic;
- na requisição, campo obrigatório na API não pode ser opcional (`?`) no
  front, senão o front pode omitir e receber 422;
- os enums têm os mesmos valores;
- `CalculateResponseSemCustos` (um `Pick` no front) tem os mesmos campos.
"""

import re
from enum import Enum
from pathlib import Path

import pytest
from pydantic import BaseModel

from pricing_core import contracts

ARQUIVO_TS = Path(__file__).resolve().parents[3] / "apps" / "web" / "src" / "types" / "calculate.generated.ts"
TS = ARQUIVO_TS.read_text(encoding="utf-8")

INTERFACES = [
    "ItemInsumo",
    "ParametrosProducao",
    "ParametrosImpostos",
    "ParametrosComerciais",
    "CalculateRequest",
    "ImpostosDestacados",
    "IsencaoMaoDeObraInfo",
    "CalculateMetadata",
    "CalculateResponse",
    "DomainErrorResponse",
]
DA_REQUISICAO = {"ItemInsumo", "ParametrosProducao", "ParametrosImpostos", "ParametrosComerciais", "CalculateRequest"}


def _campos_da_interface(nome: str) -> dict[str, bool]:
    """{campo: opcional} da `export interface <nome> { ... }`."""
    bloco = re.search(rf"export interface {nome} \{{(.*?)^\}}", TS, re.S | re.M)
    assert bloco, f"interface {nome} não encontrada em {ARQUIVO_TS.name}"
    campos = {}
    for linha in bloco.group(1).splitlines():
        achado = re.match(r"\s*(\w+)(\?)?\s*:", linha)
        if achado:
            campos[achado.group(1)] = bool(achado.group(2))
    return campos


def _valores_do_tipo(nome: str) -> set[str]:
    bloco = re.search(rf"export type {nome} =(.*?);", TS, re.S)
    assert bloco, f"type {nome} não encontrado em {ARQUIVO_TS.name}"
    return set(re.findall(r'"([^"]+)"', bloco.group(1)))


def _modelo(nome: str) -> type[BaseModel]:
    return getattr(contracts, nome)


@pytest.mark.parametrize("nome", INTERFACES)
def test_interface_tem_os_campos_do_modelo(nome):
    no_front = set(_campos_da_interface(nome))
    na_api = set(_modelo(nome).model_fields)

    assert no_front - na_api == set(), f"{nome}: campos só no front"
    assert na_api - no_front == set(), f"{nome}: campos só na API"


@pytest.mark.parametrize("nome", sorted(DA_REQUISICAO))
def test_campo_obrigatorio_na_api_nao_e_opcional_no_front(nome):
    opcionais_no_front = {campo for campo, opcional in _campos_da_interface(nome).items() if opcional}
    obrigatorios_na_api = {campo for campo, info in _modelo(nome).model_fields.items() if info.is_required()}

    assert obrigatorios_na_api & opcionais_no_front == set()


@pytest.mark.parametrize("nome", ["ModalidadeComercial", "DomainErrorCodigo"])
def test_enum_tem_os_mesmos_valores(nome):
    enum: type[Enum] = getattr(contracts, nome)
    assert _valores_do_tipo(nome) == {item.value for item in enum}


def test_variante_sem_custos_tem_os_mesmos_campos():
    pick = re.search(r"export type CalculateResponseSemCustos = Pick<CalculateResponse,(.*?)>;", TS, re.S)
    assert pick, "CalculateResponseSemCustos não encontrado"
    assert set(re.findall(r'"(\w+)"', pick.group(1))) == set(contracts.CalculateResponseSemCustos.model_fields)
