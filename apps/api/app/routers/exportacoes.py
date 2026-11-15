
"""Exportação de cenários e indicadores para BI (issue #69)."""

import csv
import io
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario
from pricing_core.rentabilidade import derivar_rentabilidade

router = APIRouter(prefix="/exportacoes", tags=["exportações"])

COLUNAS_BASE = [
    ("precificacao_codigo", "Código da precificação"),
    ("precificacao_status", "Status da precificação"),
    ("cliente", "Cliente"),
    ("produto", "Produto"),
    ("cenario_id", "ID do cenário"),
    ("versao", "Versão"),
    ("vigente", "Versão vigente"),
    ("observacao", "Observação"),
    ("volume", "Volume negociado"),
    ("data_calculo", "Data do cálculo"),
    ("versao_motor", "Versão do motor"),
    ("preco_bruto", "Preço bruto"),
    ("preco_bruto_sem_ipi", "Preço bruto sem IPI"),
    ("created_at", "Criado em"),
]

COLUNAS_CUSTO = [
    ("margem_aplicada", "Margem aplicada"),
    ("custo_mp", "Custo de matéria-prima"),
    ("custo_embalagem", "Custo de embalagem"),
    ("custo_perda", "Custo de perda"),
    ("custo_mod", "Custo MOD"),
    ("custo_ggf", "Custo GGF"),
    ("custo_conversao", "Custo de conversão"),
    ("custo_total", "Custo total"),
    ("margem_contribuicao_valor", "MaCo unitária"),
    ("margem_contribuicao_percentual", "Margem de contribuição"),
    ("receita_operacional_bruta", "ROB"),
    ("margem_contribuicao_absoluta", "MaCo absoluta"),
]


def _buscar_todas(consulta, tamanho: int = 1000) -> list[dict]:
    """Percorre as páginas do PostgREST para não limitar a exportação."""
    registros = []
    inicio = 0

    while True:
        resposta = consulta.range(inicio, inicio + tamanho - 1).execute()
        pagina = resposta.data or []
        registros.extend(pagina)

        if len(pagina) < tamanho:
            break

        inicio += tamanho

    return registros


def _decimal(valor) -> Decimal | None:
    if valor is None:
        return None
    return Decimal(str(valor))


def _nome_relacionado(registro: dict, relacao: str, campo: str) -> str:
    relacionado = registro.get(relacao) or {}

    if isinstance(relacionado, list):
        relacionado = relacionado[0] if relacionado else {}

    return relacionado.get(campo, "")


def _montar_linhas(usuario: UsuarioAutenticado):
    cliente_supabase = supabase_do_usuario(usuario.access_token)
    tem_custo = usuario.tem_permissao("custo.ler")

    # A consulta das precificações também passa pelo JWT e pelo RLS.
    precificacoes = _buscar_todas(
        cliente_supabase.table("precificacao")
        .select("id,codigo,status,cliente(razao_social),produto(descricao)")
        .order("codigo")
    )

    precificacoes_por_id = {
        str(item["id"]): item for item in precificacoes
    }

    # Usuários sem custo.ler consultam exclusivamente a view segura.
    if tem_custo:
        consulta = (
            cliente_supabase.table("cenario")
            .select(
                "id,precificacao_id,versao,observacao,volume,data_calculo,"
                "versao_motor,preco_bruto,preco_bruto_sem_ipi,created_at,"
                "entrada,resultado"
            )
        )
    else:
        consulta = (
            cliente_supabase.table("cenario_preco")
            .select(
                "id,precificacao_id,versao,volume,data_calculo,"
                "versao_motor,preco_bruto,preco_bruto_sem_ipi,"
                "created_at,vigente"
            )
        )

    cenarios = _buscar_todas(
        consulta.order("precificacao_id").order("versao")
    )

    maiores_versoes = {}
    for cenario in cenarios:
        chave = str(cenario["precificacao_id"])
        versao = cenario["versao"]
        maiores_versoes[chave] = max(
            versao, maiores_versoes.get(chave, 0)
        )

    linhas = []

    for cenario in cenarios:
        precificacao_id = str(cenario["precificacao_id"])
        precificacao = precificacoes_por_id.get(precificacao_id)

        # Não exporta cenário sem o cabeçalho visível ao usuário.
        if not precificacao:
            continue

        linha = {
            "precificacao_codigo": precificacao.get("codigo"),
            "precificacao_status": precificacao.get("status"),
            "cliente": _nome_relacionado(
                precificacao, "cliente", "razao_social"
            ),
            "produto": _nome_relacionado(
                precificacao, "produto", "descricao"
            ),
            "cenario_id": cenario.get("id"),
            "versao": cenario.get("versao"),
            "vigente": (
                cenario.get("vigente")
                if not tem_custo
                else cenario["versao"] == maiores_versoes[precificacao_id]
            ),
            "observacao": cenario.get("observacao"),
            "volume": cenario.get("volume"),
            "data_calculo": cenario.get("data_calculo"),
            "versao_motor": cenario.get("versao_motor"),
            "preco_bruto": cenario.get("preco_bruto"),
            "preco_bruto_sem_ipi": cenario.get("preco_bruto_sem_ipi"),
            "created_at": cenario.get("created_at"),
        }

        if tem_custo:
            entrada = cenario.get("entrada") or {}
            resultado = cenario.get("resultado") or {}
            comercial = entrada.get("comercial") or {}

            custo_mod = _decimal(resultado.get("custo_mod")) or Decimal("0")
            custo_ggf = _decimal(resultado.get("custo_ggf")) or Decimal("0")

            linha.update({
                "margem_aplicada": comercial.get(
                    "margem_desejada_percentual"
                ),
                "custo_mp": resultado.get("custo_mp"),
                "custo_embalagem": resultado.get("custo_embalagem"),
                "custo_perda": resultado.get("custo_perda"),
                "custo_mod": resultado.get("custo_mod"),
                "custo_ggf": resultado.get("custo_ggf"),
                "custo_conversao": custo_mod + custo_ggf,
                "custo_total": resultado.get("custo_total"),
                "margem_contribuicao_valor": resultado.get(
                    "margem_contribuicao_valor"
                ),
                "margem_contribuicao_percentual": resultado.get(
                    "margem_contribuicao_percentual"
                ),
                "receita_operacional_bruta": None,
                "margem_contribuicao_absoluta": None,
            })

            volume = _decimal(cenario.get("volume"))

            if volume is not None and resultado:
                rentabilidade = derivar_rentabilidade(
                    volume,
                    preco_bruto_sem_ipi=resultado["preco_bruto_sem_ipi"],
                    receita_operacional_liquida=resultado[
                        "receita_operacional_liquida"
                    ],
                    margem_contribuicao_valor=resultado[
                        "margem_contribuicao_valor"
                    ],
                    custo_total=resultado["custo_total"],
                )

                linha["receita_operacional_bruta"] = (
                    rentabilidade.receita_operacional_bruta
                )
                linha["margem_contribuicao_absoluta"] = (
                    rentabilidade.margem_contribuicao
                )

        linhas.append(linha)

    colunas = COLUNAS_BASE + (
        COLUNAS_CUSTO if tem_custo else []
    )

    return linhas, colunas


def _gerar_csv(linhas: list[dict], colunas: list[tuple[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")

    escritor = csv.DictWriter(
        buffer,
        fieldnames=[chave for chave, _ in colunas],
        extrasaction="ignore",
        delimiter=",",
        lineterminator="\r\n",
    )

    escritor.writeheader()
    escritor.writerows(linhas)

    return buffer.getvalue().encode("utf-8-sig")


def _gerar_xlsx(
    linhas: list[dict],
    colunas: list[tuple[str, str]],
) -> bytes:
    workbook = Workbook()
    planilha = workbook.active
    planilha.title = "Cenários"

    planilha.append([rotulo for _, rotulo in colunas])

    for celula in planilha[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor="244062")

    for linha in linhas:
        valores = []

        for chave, _ in colunas:
            valor = linha.get(chave)

            if isinstance(valor, Decimal):
                valor = float(valor)

            valores.append(valor)

        planilha.append(valores)

    planilha.freeze_panes = "A2"
    planilha.auto_filter.ref = planilha.dimensions

    for indice, (_, rotulo) in enumerate(colunas, start=1):
        tamanhos = [len(str(rotulo))]
        tamanhos.extend(
            len(str(planilha.cell(row, indice).value or ""))
            for row in range(2, planilha.max_row + 1)
        )

        planilha.column_dimensions[
            get_column_letter(indice)
        ].width = min(max(max(tamanhos) + 2, 12), 40)

    buffer = io.BytesIO()
    workbook.save(buffer)

    return buffer.getvalue()


@router.get("/cenarios")
def exportar_cenarios(
    formato: Literal["csv", "xlsx"] = Query(default="csv"),
    usuario: UsuarioAutenticado = Depends(
        exigir_permissao("precificacao.ler")
    ),
):
    """Exporta todas as versões visíveis ao usuário para BI."""
    try:
        linhas, colunas = _montar_linhas(usuario)

        if formato == "csv":
            conteudo = _gerar_csv(linhas, colunas)
            media_type = "text/csv; charset=utf-8"
        else:
            conteudo = _gerar_xlsx(linhas, colunas)
            media_type = (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )

    except HTTPException:
        raise
    except Exception as erro:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível gerar a exportação dos cenários.",
        ) from erro

    return StreamingResponse(
        iter([conteudo]),
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="neoprice-cenarios.{formato}"'
            )
        },
    )
