"""Planilha da homologação dos 30 casos com o PO.

    python tests/conformidade/planilha.py exportar homologacao-30-casos.xlsx
    python tests/conformidade/planilha.py importar homologacao-30-casos.xlsx

`exportar` gera a planilha a partir de casos/caso_NNN.json: a aba "Resultados" tem um caso por
linha com as colunas de saída vazias para o PO preencher, e a aba "Insumos" lista os itens de cada
caso. `importar` lê a aba "Resultados" e grava os valores em `saida_esperada` (como string, com
ponto decimal). Célula vazia continua PREENCHER_COM_PO. Requer `pip install openpyxl`.
"""

import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CASOS_DIR = Path(__file__).parent / "casos"
PENDENTE = "PREENCHER_COM_PO"
SAIDAS = {
    "preco_bruto_sem_ipi_sem_encargo": "Preço s/ IPI s/ encargo (R$)",
    "preco_bruto_sem_ipi": "Preço s/ IPI (R$)",
    "preco_bruto": "Preço bruto (R$)",
    "receita_operacional_liquida": "ROL (R$)",
    "margem_contribuicao_valor": "MaCo (R$)",
    "custo_total": "Custo total (R$)",
    "impostos_destacados.icms_st_valor": "ICMS-ST (R$)",
    "preco_indicado": "Preço indicado (R$)",
}
ENTRADAS = [
    ("Destino", lambda e: e["cliente_uf"]),
    ("Modalidade", lambda e: e["modalidade_comercial"]),
    ("Regime", lambda e: e["regime_tributario"]),
    ("Material do cliente (global)", lambda e: "sim" if e["material_fornecido_pelo_cliente"] else "não"),
    ("Valor global do cliente (R$)", lambda e: e["valor_material_cliente"]),
    ("Perda", lambda e: e["perda_percentual"]),
    ("MOD (R$/h)", lambda e: e["producao"]["taxa_mod"]),
    ("GGF (R$/h)", lambda e: e["producao"]["taxa_ggf"]),
    ("Produtividade (un/h)", lambda e: e["producao"]["produtividade"]),
    ("Funcionários", lambda e: e["producao"]["numero_funcionarios"]),
    ("PIS", lambda e: e["impostos"]["pis_percentual"]),
    ("COFINS", lambda e: e["impostos"]["cofins_percentual"]),
    ("ICMS", lambda e: e["impostos"]["icms_percentual"]),
    ("IPI", lambda e: e["impostos"]["ipi_percentual"]),
    ("ICMS interno", lambda e: e["impostos"]["icms_interno_percentual"]),
    ("FCP", lambda e: e["impostos"]["fcp_percentual"]),
    ("MVA", lambda e: e["impostos"]["mva_percentual"]),
    ("Margem desejada", lambda e: e["comercial"]["margem_desejada_percentual"]),
    ("Comissão", lambda e: e["comercial"]["comissao_percentual"]),
    ("Frete", lambda e: e["comercial"]["frete_percentual"]),
    ("Prazo médio (dias)", lambda e: e["comercial"]["prazo_medio_dias"]),
    ("Taxa financeira mensal", lambda e: e["comercial"]["taxa_financeira_mensal_percentual"]),
]
CABECALHO = Font(bold=True, color="FFFFFF")
FUNDO_ENTRADA = PatternFill("solid", fgColor="1F3A68")
FUNDO_SAIDA = PatternFill("solid", fgColor="2F6B3A")
PREENCHER = PatternFill("solid", fgColor="FFF4CC")


def _casos():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CASOS_DIR.glob("caso_[0-9][0-9][0-9].json"))]


def exportar(destino: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"
    titulos = ["Caso", "Descrição", *[t for t, _ in ENTRADAS], *SAIDAS.values(), "Observações do PO"]
    ws.append(titulos)
    n_entradas = 2 + len(ENTRADAS)
    for col, _ in enumerate(titulos, 1):
        celula = ws.cell(row=1, column=col)
        celula.font = CABECALHO
        celula.fill = FUNDO_SAIDA if col > n_entradas else FUNDO_ENTRADA
        celula.alignment = Alignment(wrap_text=True, vertical="center")
    for caso in _casos():
        e = caso["entrada"]
        if caso.get("erro_esperado"):
            saidas = [f"erro esperado: {caso['erro_esperado']}"] + [""] * (len(SAIDAS) - 1)
        else:
            saidas = [
                "" if caso["saida_esperada"].get(c, PENDENTE) == PENDENTE else caso["saida_esperada"][c] for c in SAIDAS
            ]
        ws.append([caso["id"], caso["descricao"], *[f(e) for _, f in ENTRADAS], *saidas, caso.get("observacoes", "")])
        if not caso.get("erro_esperado"):
            for col in range(n_entradas + 1, n_entradas + len(SAIDAS) + 1):
                ws.cell(row=ws.max_row, column=col).fill = PREENCHER
    ws.freeze_panes = "C2"
    ws.row_dimensions[1].height = 45
    for col in range(1, len(titulos) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 60 if col == 2 else 16

    wi = wb.create_sheet("Insumos")
    wi.append(
        [
            "Caso",
            "Tipo",
            "Código",
            "Descrição",
            "Origem",
            "Quantidade",
            "Preço negociado",
            "Moeda",
            "Câmbio",
            "Margem de segurança",
            "Descarte",
        ]
    )
    for celula in wi[1]:
        celula.font, celula.fill = CABECALHO, FUNDO_ENTRADA
    for caso in _casos():
        for tipo, chave in (("Matéria-prima", "materiais_primas"), ("Embalagem", "embalagens")):
            for item in caso["entrada"][chave]:
                wi.append(
                    [
                        caso["id"],
                        tipo,
                        item["codigo"],
                        item.get("descricao", ""),
                        item.get("origem_material") or "—",
                        item["quantidade"],
                        item["preco_negociado"],
                        item.get("moeda", "BRL"),
                        item.get("cambio", "1"),
                        item.get("margem_seguranca_percentual", "0"),
                        item.get("percentual_descarte", "0"),
                    ]
                )
    for col, largura in enumerate([10, 14, 11, 40, 11, 12, 15, 8, 10, 18, 10], 1):
        wi.column_dimensions[get_column_letter(col)].width = largura

    wl = wb.create_sheet("Leia-me")
    for linha in [
        "Homologação dos 30 casos de referência do motor (RNF08).",
        "Percentuais estão em fração: 0.18 = 18%.",
        "Na aba Resultados, preencha as células amarelas com o valor da planilha da área de Pricing, em reais.",
        "Deixe em branco o que não tiver; o caso fica pendente e não reprova.",
        "A aba Insumos traz as matérias-primas e embalagens de cada caso.",
        "Divergência aceita entre o sistema e a planilha: até R$ 0,01 por campo.",
    ]:
        wl.append([linha])
    wl.column_dimensions["A"].width = 110
    wb.move_sheet("Leia-me", offset=-2)
    wb.save(destino)
    print(f"planilha gerada: {destino}")


def _decimal(valor) -> str:
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return str(Decimal(texto))
    except InvalidOperation:
        raise SystemExit(f"valor inválido na planilha: {valor!r}") from None


def importar(origem: Path) -> None:
    ws = load_workbook(origem, data_only=True)["Resultados"]
    titulos = [c.value for c in ws[1]]
    coluna = {campo: titulos.index(rotulo) for campo, rotulo in SAIDAS.items()}
    obs = titulos.index("Observações do PO")
    atualizados = 0
    for linha in ws.iter_rows(min_row=2, values_only=True):
        if not linha[0]:
            continue
        caminho = CASOS_DIR / f"{linha[0]}.json"
        caso = json.loads(caminho.read_text(encoding="utf-8"))
        if caso.get("erro_esperado"):
            continue
        for campo, idx in coluna.items():
            valor = linha[idx]
            caso["saida_esperada"][campo] = PENDENTE if valor in (None, "") else _decimal(valor)
        if linha[obs]:
            caso["observacoes"] = str(linha[obs])
        caminho.write_text(json.dumps(caso, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        atualizados += 1
    print(f"{atualizados} casos atualizados a partir de {origem}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("exportar", "importar"):
        raise SystemExit(__doc__)
    (exportar if sys.argv[1] == "exportar" else importar)(Path(sys.argv[2]))
