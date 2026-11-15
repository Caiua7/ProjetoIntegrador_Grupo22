"""Conferência dos 30 casos pela metodologia documentada (PI6), em fórmulas de Excel.

Uso: pip install openpyxl formulas && python tests/conformidade/conferencia_metodologia.py tests/conformidade/casos tests/conformidade/conferencia-metodologia.xlsx

Gera conferencia-metodologia.xlsx com fórmulas visíveis (nada vem do motor), avalia as fórmulas com a
biblioteca `formulas` e compara com pricing_core.engine.calcular.
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

import formulas
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CASOS = Path(sys.argv[1])
SAIDA = Path(sys.argv[2])
casos = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CASOS.glob("caso_[0-9][0-9][0-9].json"))]

wb = Workbook()
leia = wb.active
leia.title = "Leia-me"
for linha in [
    "Conferência dos 30 casos pela metodologia documentada (PI6-planejamento-produto.md, seção do motor).",
    "Todas as contas estão em fórmulas visíveis na aba Cálculo; os itens ficam na aba Insumos. Nada aqui vem do motor do sistema.",
    "Percentuais em fração: 0,18 = 18%.",
    "Premissas ainda abertas com o PO (as mesmas do motor):",
    "  1. Base da margem = CustoTotal (m × Base).",
    "  2. Comissão$ = Comissão × PB.",
    "  3. MaterialCliente = CustoEnviadoCliente = soma dos itens de origem cliente (ou o valor global, em entrada antiga).",
    "  4. Embalagem entra no custo pelo descarte: preço × quantidade × % de descarte.",
    "Se o PO decidir diferente, basta mudar a fórmula da coluna correspondente.",
]:
    leia.append([linha])
leia.column_dimensions["A"].width = 120

ins = wb.create_sheet("Insumos")
ins.append(
    [
        "Caso",
        "Tipo",
        "Código",
        "Descrição",
        "Origem",
        "Quantidade",
        "Preço negociado",
        "Câmbio",
        "Margem seg.",
        "Descarte",
        "Custo do item",
    ]
)
r = 1
for c in casos:
    for tipo, chave in (("Matéria-prima", "materiais_primas"), ("Embalagem", "embalagens")):
        for it in c["entrada"][chave]:
            r += 1
            ins.append(
                [
                    c["id"],
                    tipo,
                    it["codigo"],
                    it.get("descricao", ""),
                    it.get("origem_material") or "",
                    float(it["quantidade"]),
                    float(it["preco_negociado"]),
                    float(it.get("cambio", "1")),
                    float(it.get("margem_seguranca_percentual", "0")),
                    float(it.get("percentual_descarte", "0")),
                    f'=G{r}*H{r}*(1+I{r})*F{r}*IF(B{r}="Embalagem",J{r},1)',
                ]
            )
ULT = r

COLS = [
    # (título, chave ou fórmula com {r})
    ("Caso", lambda c, e: c["id"]),
    ("Descrição", lambda c, e: c["descricao"]),
    ("UF", lambda c, e: e["cliente_uf"]),
    ("Material do cliente (global)", lambda c, e: 1 if e["material_fornecido_pelo_cliente"] else 0),
    ("Valor global do cliente", lambda c, e: float(e["valor_material_cliente"])),
    (
        "Origem por item?",
        lambda c, e: 1 if any(i.get("origem_material") for i in e["materiais_primas"] + e["embalagens"]) else 0,
    ),
    ("Perda", lambda c, e: float(e["perda_percentual"])),
    ("Taxa MOD", lambda c, e: float(e["producao"]["taxa_mod"])),
    ("Taxa GGF", lambda c, e: float(e["producao"]["taxa_ggf"])),
    ("Produtividade", lambda c, e: float(e["producao"]["produtividade"])),
    ("Funcionários", lambda c, e: float(e["producao"]["numero_funcionarios"])),
    ("PIS", lambda c, e: float(e["impostos"]["pis_percentual"])),
    ("COFINS", lambda c, e: float(e["impostos"]["cofins_percentual"])),
    ("ICMS", lambda c, e: float(e["impostos"]["icms_percentual"])),
    ("IPI", lambda c, e: float(e["impostos"]["ipi_percentual"])),
    ("ICMS interno", lambda c, e: float(e["impostos"]["icms_interno_percentual"])),
    ("FCP", lambda c, e: float(e["impostos"]["fcp_percentual"])),
    ("MVA", lambda c, e: float(e["impostos"]["mva_percentual"])),
    ("Margem (m)", lambda c, e: float(e["comercial"]["margem_desejada_percentual"])),
    ("Comissão", lambda c, e: float(e["comercial"]["comissao_percentual"])),
    ("Frete", lambda c, e: float(e["comercial"]["frete_percentual"])),
    ("Prazo médio (dias)", lambda c, e: float(e["comercial"]["prazo_medio_dias"])),
    ("Taxa financeira mensal", lambda c, e: float(e["comercial"]["taxa_financeira_mensal_percentual"])),
]
N_ENT = len(COLS)
L = {t: get_column_letter(i + 1) for i, (t, _) in enumerate(COLS)}
A, UF, FLAG, VGLOB, ORIG, PERDA, TMOD, TGGF, PROD, FUNC, PIS, COF, ICMS, IPI, ICMSI, FCP, MVA, M, COM, FRT, PRZ, TX = (
    L[t] for t, _ in COLS[:1] + COLS[2:]
)
CASO_INS = f"Insumos!$A$2:$A${ULT}"
TIPO = f"Insumos!$B$2:$B${ULT}"
ORIGEM = f"Insumos!$E$2:$E${ULT}"
CUSTO = f"Insumos!$K$2:$K${ULT}"

CALC = [
    ("CustoMP", 'SUMIFS({CUSTO},{I},{A}{r},{TIPO},"Matéria-prima")'),
    ("CustoEmb", 'SUMIFS({CUSTO},{I},{A}{r},{TIPO},"Embalagem")'),
    ("MaterialCliente", 'IF({ORIG}{r}=1,SUMIFS({CUSTO},{I},{A}{r},{ORIGEM},"cliente"),{VGLOB}{r})'),
    ("CustoPerda", "({CustoMP}+{CustoEmb}-{MaterialCliente})*{PERDA}{r}"),
    ("CustoMOD", "{TMOD}{r}/{PROD}{r}*{FUNC}{r}"),
    ("CustoGGF", "{TGGF}{r}/{PROD}{r}"),
    ("CustoTotal", "{CustoMP}+{CustoEmb}+{CustoPerda}+{CustoMOD}+{CustoGGF}"),
    ("Termo impostos", "{PIS}{r}*(1-{ICMS}{r})+{COF}{r}*(1-{ICMS}{r})+{ICMS}{r}"),
    ("D", "1-({COM}{r}+{FRT}{r}+{M}{r}*(1-{Termo impostos})+{Termo impostos})"),
    ("Encargo %", "(1+{TX}{r})^({PRZ}{r}/30)-1"),
    ("Isenção MDO", 'IF(AND({FLAG}{r}=1,{UF}{r}="SP"),{CustoMOD},0)'),
    ("PBsIPIsEncargo", 'IF({D}<=0,"ERRO D<=0",{CustoTotal}/{D}-{MaterialCliente}-{Isenção MDO})'),
    ("Encargo $", 'IF({D}<=0,"",{Encargo %}*{PBsIPIsEncargo})'),
    (
        "PBsIPI",
        'IF({D}<=0,"",({M}{r}*{CustoTotal}+{CustoTotal}+{Encargo $})/(1-({Termo impostos}+{COM}{r}+{FRT}{r}))-{MaterialCliente}-{Isenção MDO})',
    ),
    ("PBcIPI", 'IF({D}<=0,"",{PBsIPI}*(1+{IPI}{r}))'),
    (
        "PB",
        'IF({D}<=0,"",IF(AND({ICMSI}{r}=0,{FCP}{r}=0,{MVA}{r}=0),{PBcIPI},{PBcIPI}+({PBcIPI}*(1+{MVA}{r}))*({ICMSI}{r}+{FCP}{r})-{PBsIPI}*{ICMS}{r}))',
    ),
    ("ICMS-ST", 'IF({D}<=0,"",{PB}-{PBcIPI})'),
    ("ROL", 'IF({D}<=0,"",{PBsIPI}-(({PBsIPI}-{PBsIPI}*{ICMS}{r})*({PIS}{r}+{COF}{r})+{PBsIPI}*{ICMS}{r}))'),
    ("Comissão $", 'IF({D}<=0,"",{COM}{r}*{PB})'),
    ("MaCo $", 'IF({D}<=0,"",{ROL}-({CustoMP}+{CustoEmb}+{Encargo $}+{CustoPerda}+{Comissão $}))'),
]
for k, (t, _) in enumerate(CALC):
    L[t] = get_column_letter(N_ENT + k + 1)

ws = wb.create_sheet("Cálculo")
ws.append([t for t, _ in COLS] + [t for t, _ in CALC])
for r, c in enumerate(casos, 2):
    e = c["entrada"]
    linha = [f(c, e) for _, f in COLS]
    ctx = dict(
        r=r,
        A=A,
        UF=UF,
        FLAG=FLAG,
        VGLOB=VGLOB,
        ORIG=ORIG,
        PERDA=PERDA,
        TMOD=TMOD,
        TGGF=TGGF,
        PROD=PROD,
        FUNC=FUNC,
        PIS=PIS,
        COF=COF,
        ICMS=ICMS,
        IPI=IPI,
        ICMSI=ICMSI,
        FCP=FCP,
        MVA=MVA,
        M=M,
        COM=COM,
        FRT=FRT,
        PRZ=PRZ,
        TX=TX,
        I=CASO_INS,
        TIPO=TIPO,
        ORIGEM=ORIGEM,
        CUSTO=CUSTO,
    )
    for t, _ in CALC:
        ctx[t] = f"{L[t]}{r}"
    for _t, f in CALC:
        expr = f
        for chave in sorted(ctx, key=len, reverse=True):
            expr = expr.replace("{" + chave + "}", str(ctx[chave]))
        linha.append("=" + expr)
    ws.append(linha)
azul, verde = PatternFill("solid", fgColor="1F3A68"), PatternFill("solid", fgColor="2F6B3A")
for col in range(1, len(COLS) + len(CALC) + 1):
    cel = ws.cell(row=1, column=col)
    cel.font = Font(bold=True, color="FFFFFF")
    cel.fill = azul if col <= N_ENT else verde
    cel.alignment = Alignment(wrap_text=True, vertical="center")
    ws.column_dimensions[get_column_letter(col)].width = 50 if col == 2 else 14
ws.row_dimensions[1].height = 40
ws.freeze_panes = "C2"
wb.move_sheet("Cálculo", offset=-1)
wb.save(SAIDA)

# ------------- avalia as fórmulas e compara com o motor
modelo = formulas.ExcelModel().loads(str(SAIDA)).finish()
sol = modelo.calculate()


def valor(col, r):
    for k, v in sol.items():
        if k.upper().endswith(f"[{SAIDA.name.upper()}]CÁLCULO'!{col}{r}"):
            x = v.value[0, 0]
            return x
    raise KeyError(col)


from pricing_core.contracts import CalculateRequest  # noqa: E402
from pricing_core.engine import calcular  # noqa: E402

CAMPOS = {
    "PBsIPIsEncargo": "preco_bruto_sem_ipi_sem_encargo",
    "PBsIPI": "preco_bruto_sem_ipi",
    "PB": "preco_bruto",
    "ROL": "receita_operacional_liquida",
    "MaCo $": "margem_contribuicao_valor",
    "CustoTotal": "custo_total",
    "ICMS-ST": "impostos_destacados.icms_st_valor",
}
resumo, planilha_vals = [], {}
for r, c in enumerate(casos, 2):
    try:
        res = calcular(CalculateRequest.model_validate(c["entrada"]))
    except Exception as erro:
        xl = valor(L["PBsIPIsEncargo"], r)
        resumo.append(
            (
                c["id"],
                "erro nos dois" if isinstance(xl, str) and "ERRO" in xl else f"motor deu erro, Excel não ({erro})",
                0,
            )
        )
        continue
    maior = Decimal(0)
    vals = {}
    for t, campo in CAMPOS.items():
        xl = Decimal(str(valor(L[t], r))).quantize(Decimal("0.01"))
        obj = res
        for parte in campo.split("."):
            obj = getattr(obj, parte)
        vals[campo] = str(xl)
        maior = max(maior, abs(xl - obj))
    vals["preco_indicado"] = vals["preco_bruto"]
    planilha_vals[c["id"]] = vals
    resumo.append((c["id"], "confere" if maior <= Decimal("0.01") else "DIVERGE", maior))
for linha in resumo:
    print(*linha)
SAIDA.with_suffix(".json").write_text(json.dumps(planilha_vals, indent=1), encoding="utf-8")
