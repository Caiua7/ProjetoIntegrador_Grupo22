"""Entrada do cálculo montada no servidor (uma chamada no lugar de ~20).

O modal de cenários precisava buscar, item a item, a formulação, cada insumo,
cada cotação, cada câmbio, os parâmetros e a alíquota. Aqui as leituras saem
em lote e em paralelo, com o token de quem chama (o RLS continua valendo), e
reaproveitam as mesmas regras dos endpoints de cotação, câmbio, parâmetros e
alíquota. Campos sem cadastro no sistema (embalagem, produção, margem...) vêm
em branco: o front completa com o que o analista digita.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import UsuarioAutenticado, exigir_permissao
from app.infrastructure.supabase_client import supabase_do_usuario
from app.routers.parametros_globais import CODIGOS_PARAMETRO, escolher_vigente, parametros_vigentes, taxa_com_margem
from app.routers.tax_rates import escolher_aliquota_aplicavel
from pricing_core.cotacao import CotacaoAmbigua, CotacaoNaoEncontrada, resolver_cotacao

router = APIRouter(prefix="/precificacoes", tags=["precificações"])

REGIMES = {"lucro_real": "Lucro Real", "lucro_presumido": "Lucro Presumido", "simples_nacional": "Simples Nacional"}
NOME_PARAMETRO = {
    "perda_percentual": "perda padrão",
    "taxa_financeira_mensal_percentual": "taxa financeira mensal",
    "prazo_medio_padrao_dias": "prazo médio",
}
CAMPOS_IMPOSTO = (
    "pis_percentual",
    "cofins_percentual",
    "icms_percentual",
    "ipi_percentual",
    "icms_interno_percentual",
    "fcp_percentual",
    "mva_percentual",
)


class EntradaCalculoResposta(BaseModel):
    entrada: dict
    pendencias: list[str]


def _texto(valor) -> str:
    """Número do PostgREST → texto decimal exato ('' quando não há)."""
    return "" if valor is None else format(Decimal(str(valor)), "f")


def _para_cotacao(linha: dict):
    # import local: evita ciclo com o router de cotações na importação do app
    from app.routers.cotacoes import _para_cotacao as converter

    return converter(linha)


def montar_entrada(cliente, usuario: UsuarioAutenticado, precificacao_id: UUID, volume: Decimal | None, hoje: date):
    pendencias: list[str] = []
    linhas = (
        cliente.table("precificacao")
        .select("id,produto_id,uf_destino,modalidade_comercial,regime_tributario,produto(ncm_codigo)")
        .eq("id", str(precificacao_id))
        .limit(1)
        .execute()
        .data
    )
    if not linhas:
        raise HTTPException(404, "Precificação não encontrada ou fora da sua carteira.")
    prec = linhas[0]
    entrada: dict = {
        "cliente_uf": prec.get("uf_destino") or "",
        "modalidade_comercial": prec.get("modalidade_comercial") or "",
        "regime_tributario": prec.get("regime_tributario") or "",
    }
    if not prec.get("uf_destino"):
        pendencias.append("Preencha a UF de destino no cabeçalho da precificação.")
    if not prec.get("modalidade_comercial"):
        pendencias.append("Preencha a modalidade comercial no cabeçalho.")
    if not prec.get("regime_tributario"):
        pendencias.append("Preencha o regime tributário do cliente no cabeçalho.")
    ncm = (prec.get("produto") or {}).get("ncm_codigo")
    pode_ler = usuario.tem_permissao

    def ler_formulacao():
        if not prec.get("produto_id"):
            return None
        resposta = (
            cliente.table("formulacao")
            .select(
                "id,formulacao_item(tipo_insumo,materia_prima_id,embalagem_id,quantidade,unidade_medida,origem_material,ordem,"
                "materia_prima(codigo,descricao,unidade_medida),embalagem(codigo,descricao,unidade_medida))"
            )
            .eq("produto_id", prec["produto_id"])
            .limit(1)
            .execute()
        )
        return resposta.data[0] if resposta.data else False

    def ler_parametros():
        if not pode_ler("parametro_global.ler"):
            return None
        resposta = cliente.table("parametro_global").select("*").lte("vigencia_inicio", hoje.isoformat()).execute()
        return parametros_vigentes(resposta.data or [], hoje)

    def ler_aliquota():
        if not (pode_ler("parametro_fiscal.ler") and prec.get("uf_destino") and prec.get("regime_tributario") and ncm):
            return None
        resposta = (
            cliente.table("aliquota_fiscal")
            .select("*")
            .eq("uf_destino", prec["uf_destino"])
            .eq("regime_tributario", prec["regime_tributario"])
            .or_(f"ncm_codigo.eq.{ncm},ncm_codigo.is.null")
            .lte("vigencia_inicio", hoje.isoformat())
            .order("vigencia_inicio", desc=True)
            .execute()
        )
        return escolher_aliquota_aplicavel(resposta.data or [], ncm, hoje) or False

    with ThreadPoolExecutor(max_workers=8) as pool:
        f_form, f_param, f_aliq = pool.submit(ler_formulacao), pool.submit(ler_parametros), pool.submit(ler_aliquota)
        formulacao, vigentes, aliquota = f_form.result(), f_param.result(), f_aliq.result()

        # ---------------- itens da formulação, com cotação e câmbio resolvidos em lote
        materiais: list[dict] = []
        embalagens: list[dict] = []
        if formulacao is None:
            pendencias.append("A precificação não tem produto associado.")
        elif formulacao is False:
            pendencias.append("O produto ainda não tem formulação. Monte a composição em Formulações.")
        else:
            itens = sorted(formulacao.get("formulacao_item") or [], key=lambda item: item.get("ordem") or 0)
            pode_cotar = pode_ler("custo.ler") and volume is not None
            cotar = {}
            for item in itens:
                insumo = item.get("materia_prima")
                if (
                    item["tipo_insumo"] == "materia_prima"
                    and insumo
                    and pode_cotar
                    and item["unidade_medida"] == "kg"
                    and insumo["unidade_medida"] == "kg"
                ):
                    quantidade = Decimal(str(item["quantidade"])) * volume
                    cotar[item["materia_prima_id"]] = pool.submit(
                        lambda mp=item["materia_prima_id"], q=quantidade: _resolver_cotacao(cliente, mp, q, hoje)
                    )
            cotacoes = {mp: futuro.result() for mp, futuro in cotar.items()}
            moedas = {c.moeda for c in cotacoes.values() if c is not None and c.moeda != "BRL"}
            cambios = {}
            if pode_ler("cambio.ler"):
                futuros = {moeda: pool.submit(_cambio_vigente, cliente, moeda, hoje) for moeda in moedas}
                cambios = {moeda: futuro.result() for moeda, futuro in futuros.items()}

            for item in itens:
                eh_materia = item["tipo_insumo"] == "materia_prima"
                insumo = item.get("materia_prima") if eh_materia else item.get("embalagem")
                if not insumo:
                    pendencias.append(
                        "Há um item da formulação sem insumo vinculado."
                        if pode_ler("cadastro.ler")
                        else "Seu perfil não pode consultar os insumos da formulação."
                    )
                    continue
                linha = {
                    "codigo": insumo["codigo"],
                    "descricao": insumo["descricao"],
                    "quantidade": _texto(item["quantidade"]),
                    "origem_material": item.get("origem_material"),
                    "preco_negociado": "",
                    "moeda": "",
                    "cambio": "",
                    "margem_seguranca_percentual": "",
                }
                if not eh_materia:
                    linha["percentual_descarte"] = ""
                    embalagens.append(linha)
                    continue
                if not pode_ler("custo.ler"):
                    pendencias.append(
                        "Seu perfil não pode ver custos, então o preço de compra dos insumos não entra no cálculo."
                    )
                elif item["unidade_medida"] != "kg" or insumo["unidade_medida"] != "kg":
                    pendencias.append(f"{insumo['descricao']}: a cotação é por kg, então use kg na formulação.")
                elif volume is None:
                    pendencias.append("Informe o volume negociado para escolher a faixa de cotação dos insumos.")
                elif cotacoes.get(item["materia_prima_id"]) is None:
                    pendencias.append(
                        f"Sem cotação vigente de {insumo['descricao']} para esse volume. Cadastre ou atualize em Cotações."
                    )
                else:
                    cotacao = cotacoes[item["materia_prima_id"]]
                    linha["preco_negociado"] = _texto(cotacao.preco)
                    linha["moeda"] = cotacao.moeda
                    if cotacao.moeda == "BRL":
                        linha["cambio"] = "1"
                    elif not pode_ler("cambio.ler"):
                        pendencias.append(
                            f"Seu perfil não pode consultar o câmbio de {cotacao.moeda}, usado em {insumo['descricao']}."
                        )
                    elif cambios.get(cotacao.moeda) is None:
                        pendencias.append(
                            f"Não há câmbio de {cotacao.moeda} cadastrado. Cadastre em Câmbio e parâmetros."
                        )
                    else:
                        linha["cambio"] = _texto(cambios[cotacao.moeda])
                materiais.append(linha)

            entrada["materiais_primas"] = materiais
            entrada["embalagens"] = embalagens
            origens = {item.get("origem_material") for item in itens}
            if origens == {"fabricante"}:
                entrada["material_fornecido_pelo_cliente"] = False
                entrada["valor_material_cliente"] = "0"
            elif origens == {"cliente"}:
                entrada["material_fornecido_pelo_cliente"] = True
            elif itens:
                pendencias.append("Todos os itens da formulação precisam ter a mesma origem (fabricante ou cliente).")

    # ---------------- parâmetros globais e impostos
    comercial: dict = {}
    if vigentes is None:
        pendencias.append("Seu perfil não pode consultar os parâmetros globais (perda, taxa financeira e prazo).")
    else:
        if "perda_percentual" in vigentes:
            entrada["perda_percentual"] = _texto(vigentes["perda_percentual"]["valor"])
        if "taxa_financeira_mensal_percentual" in vigentes:
            comercial["taxa_financeira_mensal_percentual"] = _texto(
                vigentes["taxa_financeira_mensal_percentual"]["valor"]
            )
        if "prazo_medio_padrao_dias" in vigentes:
            comercial["prazo_medio_dias"] = _texto(vigentes["prazo_medio_padrao_dias"]["valor"])
        for codigo in CODIGOS_PARAMETRO:
            if codigo in NOME_PARAMETRO and codigo not in vigentes:
                pendencias.append(f"Falta um valor vigente de {NOME_PARAMETRO[codigo]} em Câmbio e parâmetros.")
    entrada["comercial"] = comercial

    impostos = {campo: "" for campo in CAMPOS_IMPOSTO}
    if not pode_ler("parametro_fiscal.ler"):
        pendencias.append("Seu perfil não pode consultar os tributos, então os impostos não são preenchidos.")
    elif not ncm:
        pendencias.append("O produto não tem NCM cadastrado, então os impostos não são preenchidos.")
    elif aliquota is False:
        regime = REGIMES.get(prec["regime_tributario"], prec["regime_tributario"])
        pendencias.append(
            f"Não há alíquota cadastrada para {prec['uf_destino']}, NCM {ncm} e {regime}. Cadastre em Tributos."
        )
    elif aliquota:
        impostos = {campo: _texto(aliquota.get(campo)) for campo in CAMPOS_IMPOSTO}
    entrada["impostos"] = impostos

    return {"entrada": entrada, "pendencias": list(dict.fromkeys(pendencias))}


def _resolver_cotacao(cliente, materia_prima_id: str, quantidade: Decimal, hoje: date):
    resposta = cliente.rpc(
        "cotacoes_vigentes", {"p_materia_prima_id": materia_prima_id, "p_data": hoje.isoformat()}
    ).execute()
    try:
        return resolver_cotacao(
            [_para_cotacao(linha) for linha in resposta.data or []], materia_prima_id, quantidade, hoje, None
        )
    except (CotacaoNaoEncontrada, CotacaoAmbigua):
        return None


def _cambio_vigente(cliente, moeda: str, hoje: date) -> Decimal | None:
    resposta = (
        cliente.table("cambio")
        .select("*")
        .eq("moeda", moeda)
        .lte("data_referencia", hoje.isoformat())
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )
    vigente = escolher_vigente(resposta.data or [], "data_referencia", hoje)
    return taxa_com_margem(vigente) if vigente else None


@router.get("/{precificacao_id}/entrada-calculo", response_model=EntradaCalculoResposta)
def entrada_calculo(
    precificacao_id: UUID,
    volume: Decimal | None = Query(default=None, gt=0, allow_inf_nan=False),
    usuario: UsuarioAutenticado = Depends(exigir_permissao("precificacao.ler")),
) -> dict:
    try:
        cliente = supabase_do_usuario(usuario.access_token)
        return montar_entrada(cliente, usuario, precificacao_id, volume, date.today())
    except HTTPException:
        raise
    except Exception as erro:
        raise HTTPException(503, "Não foi possível reunir os dados do cálculo. Tente novamente.") from erro
