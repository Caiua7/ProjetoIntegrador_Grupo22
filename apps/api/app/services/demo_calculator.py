"""Completa entradas somente para a rota de demonstração, nunca para cálculo/salvamento real."""

from __future__ import annotations

import copy
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.config import settings
from pricing_core.contracts import CalculateRequest

# Valores deliberadamente demonstrativos, agrupados num único lugar. Só são
# usados quando DEMO_CALCULATION_ENABLED=true e a chamada escolhe /calculate/demo.
DEFAULT_DEMO_VALUES: dict[str, Any] = {
    "cliente_uf": "SP",
    "modalidade_comercial": "full_service_nacional",
    "regime_tributario": "lucro_real",
    "perda_percentual": "0.02",
    "material_fornecido_pelo_cliente": False,
    "valor_material_cliente": "0",
    "producao": {
        "taxa_mod": "0",
        "taxa_ggf": "0",
        "produtividade": "1",
        "numero_funcionarios": "0",
    },
    "impostos": {
        "pis_percentual": "0",
        "cofins_percentual": "0",
        "icms_percentual": "0",
        "ipi_percentual": "0",
        "icms_interno_percentual": "0",
        "fcp_percentual": "0",
        "mva_percentual": "0",
    },
    "comercial": {
        "margem_desejada_percentual": "0.20",
        "comissao_percentual": "0",
        "frete_percentual": "0",
        "prazo_medio_dias": "0",
        "taxa_financeira_mensal_percentual": "0",
    },
    "item": {
        "preco_negociado": "1",
        "moeda": "BRL",
        "cambio": "1",
        "margem_seguranca_percentual": "0",
        "quantidade": "1",
        "percentual_descarte": "0",
    },
}


def _merge(alvo: dict[str, Any], substituto: dict[str, Any]) -> dict[str, Any]:
    for chave, valor in substituto.items():
        if isinstance(valor, dict) and isinstance(alvo.get(chave), dict):
            _merge(alvo[chave], valor)
        else:
            alvo[chave] = valor
    return alvo


def _valores_demo() -> dict[str, Any]:
    valores = copy.deepcopy(DEFAULT_DEMO_VALUES)
    if settings.DEMO_CALCULATION_DEFAULTS_JSON.strip():
        try:
            substitutos = json.loads(settings.DEMO_CALCULATION_DEFAULTS_JSON)
        except json.JSONDecodeError as erro:
            raise ValueError("DEMO_CALCULATION_DEFAULTS_JSON não contém JSON válido.") from erro
        if not isinstance(substitutos, dict):
            raise ValueError("DEMO_CALCULATION_DEFAULTS_JSON precisa ser um objeto JSON.")
        _merge(valores, substitutos)
    return valores


def _vazio(valor: Any) -> bool:
    return valor is None or valor == ""


def preparar_entrada_demo(payload: dict[str, Any]) -> tuple[CalculateRequest, list[str], bool]:
    """Retorna entrada validada, nomes das assunções aplicadas e se havia dados do chamador."""
    dados = copy.deepcopy(payload)
    valores = _valores_demo()
    simulados: list[str] = []
    recebeu_dados = any(not _vazio(v) for v in dados.values())

    def completar(caminho: str, destino: dict[str, Any], chave: str, padrao: Any) -> None:
        if _vazio(destino.get(chave)):
            destino[chave] = copy.deepcopy(padrao)
            simulados.append(caminho)

    for campo in ("cliente_uf", "modalidade_comercial", "regime_tributario", "perda_percentual"):
        completar(campo, dados, campo, valores[campo])

    for campo in ("material_fornecido_pelo_cliente", "valor_material_cliente"):
        if campo not in dados or dados[campo] is None or dados[campo] == "":
            dados[campo] = copy.deepcopy(valores[campo])
            simulados.append(campo)

    for grupo in ("producao", "impostos", "comercial"):
        dados[grupo] = dados.get(grupo) if isinstance(dados.get(grupo), dict) else {}
        for campo, padrao in valores[grupo].items():
            completar(f"{grupo}.{campo}", dados[grupo], campo, padrao)

    itens_caminhos = ("materiais_primas", "embalagens")
    if not any(dados.get(chave) for chave in itens_caminhos):
        dados["materiais_primas"] = [
            {
                "codigo": "DEMO-MP-001",
                "descricao": "Matéria-prima de demonstração",
                **copy.deepcopy(valores["item"]),
            }
        ]
        simulados.append("materiais_primas[0] (item demonstrativo criado porque a formulação estava vazia)")

    origens: set[str] = set()
    perdas_materias: list[Decimal] = []
    for lista_nome in itens_caminhos:
        lista = dados.get(lista_nome)
        if not isinstance(lista, list):
            dados[lista_nome] = []
            continue
        for indice, linha in enumerate(lista):
            if not isinstance(linha, dict):
                continue
            perda_item = linha.pop("perda_percentual", None)
            if not _vazio(perda_item):
                try:
                    perda_fracao = Decimal(str(perda_item)) / Decimal("100")
                except InvalidOperation as erro:
                    raise ValueError(f"Perda do item {lista_nome}[{indice}] não é decimal válida.") from erro
                if lista_nome == "embalagens" and _vazio(linha.get("percentual_descarte")):
                    linha["percentual_descarte"] = format(perda_fracao, "f")
                    simulados.append(
                        f"{lista_nome}[{indice}].perda_percentual -> percentual_descarte (conversão demonstrativa)"
                    )
                elif lista_nome == "materiais_primas":
                    perdas_materias.append(perda_fracao)
            item = valores["item"]
            for campo, padrao in item.items():
                completar(f"{lista_nome}[{indice}].{campo}", linha, campo, padrao)
            origem = linha.get("origem_material")
            if origem in {"fabricante", "cliente"}:
                origens.add(origem)

    if perdas_materias and ("perda_percentual" not in payload or _vazio(payload.get("perda_percentual"))):
        if len(set(perdas_materias)) == 1:
            dados["perda_percentual"] = format(perdas_materias[0], "f")
            simulados.append("perda_percentual por item -> perda global do motor (conversão demonstrativa)")
        else:
            simulados.append("perdas diferentes por matéria-prima simplificadas para o padrão global demonstrativo")

    # O contrato vigente do motor representa origem como uma flag global.
    # A redução de uma formulação item-a-item para essa flag é demonstrativa.
    if len(origens) > 1:
        dados["material_fornecido_pelo_cliente"] = True
        simulados.append("origem_material por item -> flag global do motor (regra demonstrativa)")
    elif origens == {"cliente"} and not dados["material_fornecido_pelo_cliente"]:
        dados["material_fornecido_pelo_cliente"] = True
        simulados.append("origem_material=cliente -> flag global do motor")
    elif origens == {"fabricante"} and dados["material_fornecido_pelo_cliente"]:
        dados["material_fornecido_pelo_cliente"] = False
        simulados.append("origem_material=fabricante -> flag global do motor")

    if dados["material_fornecido_pelo_cliente"] and "valor_material_cliente" not in payload:
        dados["valor_material_cliente"] = valores["valor_material_cliente"]
        if "valor_material_cliente" not in simulados:
            simulados.append("valor_material_cliente")

    request = CalculateRequest.model_validate(dados)
    return request, simulados, recebeu_dados
