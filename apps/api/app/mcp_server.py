"""Conector MCP do NeoPrice para o Claude (issue #130, RF20).

O usuário adiciona `<API>/mcp` como conector na conta do Claude. O login é
feito no servidor OAuth do Supabase Auth, que mostra a tela de consentimento
do front (`/oauth/consent`) e devolve ao Claude um access token do próprio
usuário. Este módulo é só o servidor de recurso: confere o token com a mesma
validação da API e cada ferramenta chama uma rota da API em nome do usuário.

Cada ferramenta declara as permissões que a rota exige. A lista de ferramentas
é montada por usuário com essas permissões, então cada cargo enxerga no Claude
exatamente as ações que tem na tela, e a rota ainda aplica a própria checagem
e o RLS por carteira.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, Literal

import httpx
import jwt
from fastapi import HTTPException
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from app.core.auth import validar_token
from app.core.config import settings
from app.routers.cadastros import InsumoAtualizacao, InsumoEntrada, TipoInsumo
from app.routers.formulacoes import FormulacaoEntrada
from app.routers.parametros_globais import CambioAtualizacao, CambioEntrada, ParametroAtualizacao, ParametroEntrada
from app.routers.precificacoes import PrecificacaoEntrada
from app.routers.tax_rates import AliquotaAtualizacao, AliquotaEntrada, ImportacaoEntrada

INSTRUCOES = (
    "Você está conectado ao NeoPrice, plataforma de precificação industrial B2B. "
    "As ferramentas agem com o login do próprio usuário: cada um só vê os dados da sua carteira e só recebe as "
    "ferramentas que o cargo dele tem no sistema. "
    "Quando uma ferramenta responder que o perfil não tem permissão, explique isso ao usuário em vez de tentar outro "
    "caminho. Valores monetários estão em reais e percentuais vêm em fração (0.24 = 24%). "
    "Precificações são identificadas pelo código, como PRC-2026-0145. "
    "Antes de qualquer ferramenta que grava (criar, salvar, submeter, aprovar, cadastrar, alterar, inativar), mostre "
    "ao usuário o que vai ser feito e espere a confirmação dele."
)

LER = "precificacao.ler"
PERMISSOES_DA_FERRAMENTA: dict[str, frozenset[str]] = {}


class VerificadorSupabase:
    """Aceita o access token emitido pelo Supabase Auth, como a API já faz."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            usuario_id = await asyncio.to_thread(validar_token, token)
        except HTTPException:
            return None
        try:
            claims = jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError:
            claims = {}
        return AccessToken(
            token=token,
            client_id=str(claims.get("client_id") or "neoprice"),
            scopes=str(claims.get("scope") or "").split(),
            expires_at=claims.get("exp"),
            subject=str(usuario_id),
        )


def _url_publica() -> str:
    return settings.API_PUBLIC_URL.rstrip("/")


async def _api(metodo: str, caminho: str, params: dict | None = None, corpo: dict | None = None) -> Any:
    """Chama a rota da API em processo, com o token de quem está usando o conector."""
    from app.main import app  # import tardio: main monta este módulo

    acesso = get_access_token()
    if acesso is None:
        raise ToolError("Sessão do conector ausente. Refaça o login no NeoPrice.")
    params = {chave: valor for chave, valor in (params or {}).items() if valor not in (None, "")}
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://neoprice.interno", timeout=60) as cliente:
        resposta = await cliente.request(
            metodo, caminho, params=params, json=corpo, headers={"Authorization": f"Bearer {acesso.token}"}
        )
    if resposta.status_code >= 400:
        try:
            detalhe = resposta.json().get("detail")
        except ValueError:
            detalhe = resposta.text
        if isinstance(detalhe, list):
            detalhe = "; ".join(str(item.get("msg", item)) for item in detalhe)
        raise ToolError(f"{detalhe or 'Erro'} (HTTP {resposta.status_code})")
    if not resposta.content:
        return None
    if "json" not in resposta.headers.get("content-type", ""):
        return resposta.text
    return resposta.json()


class ServidorPorPerfil(MCPServer):
    """Cada usuário só vê e só chama as ferramentas que o perfil dele permite."""

    async def _permissoes(self) -> frozenset[str]:
        return frozenset((await _api("GET", "/auth/me")).get("permissoes") or [])

    async def list_tools(self):
        permissoes = await self._permissoes()
        todas = await super().list_tools()
        return [f for f in todas if PERMISSOES_DA_FERRAMENTA.get(f.name, frozenset()) <= permissoes]

    async def call_tool(self, name, arguments, context=None):
        exigidas = PERMISSOES_DA_FERRAMENTA.get(name)
        if exigidas:
            faltam = exigidas - await self._permissoes()
            if faltam:
                raise ToolError(f"Seu perfil não tem a permissão {', '.join(sorted(faltam))} para usar {name}.")
        return await super().call_tool(name, arguments, context)


mcp = ServidorPorPerfil(
    name="NeoPrice",
    title="NeoPrice — precificação industrial",
    instructions=INSTRUCOES,
    version="1.0.0",
    token_verifier=VerificadorSupabase(),
    auth=AuthSettings(
        issuer_url=f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"
        if settings.SUPABASE_URL
        else "https://example.invalid",
        resource_server_url=f"{_url_publica()}/mcp",
        validate_token_resource=False,
    ),
)


def ferramenta(*permissoes: str, descricao: str, escrita: bool = False):
    """Registra a ferramenta com as permissões que a rota da API exige."""

    def registrar(funcao):
        PERMISSOES_DA_FERRAMENTA[funcao.__name__] = frozenset(permissoes)
        anotacoes = ToolAnnotations(readOnlyHint=not escrita)
        return mcp.tool(description=descricao, annotations=anotacoes)(funcao)

    return registrar


def _texto(dados: Any) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=1, default=str)


def _corpo(modelo: BaseModel) -> dict:
    return modelo.model_dump(mode="json", exclude_unset=True)


async def _precificacao_por_codigo(codigo: str) -> dict:
    lista = await _api("GET", "/precificacoes")
    alvo = codigo.strip().upper()
    for item in lista:
        if str(item.get("codigo", "")).upper() == alvo:
            return item
    codigos = ", ".join(sorted(str(item.get("codigo")) for item in lista)) or "nenhuma"
    raise ToolError(f"Precificação {codigo} não encontrada na sua carteira. Disponíveis: {codigos}.")


async def _insumo_por_termo(termo: str, tipo: str = "materias-primas") -> dict:
    pagina = await _api("GET", f"/cadastros/{tipo}", {"busca": termo, "tamanho_pagina": 10})
    registros = pagina.get("registros") or []
    exatos = [
        r for r in registros if termo.strip().lower() in (str(r.get("codigo")).lower(), str(r.get("descricao")).lower())
    ]
    if len(exatos) == 1 or len(registros) == 1:
        return (exatos or registros)[0]
    if not registros:
        raise ToolError(f"Nenhum insumo encontrado para '{termo}'.")
    opcoes = "; ".join(f"{r['codigo']} — {r['descricao']}" for r in registros)
    raise ToolError(f"Encontrei mais de um insumo para '{termo}': {opcoes}. Informe o código.")


# ---------------------------------------------------------------- sessão


@ferramenta(descricao="Mostra quem está conectado: nome, cargo e permissões no NeoPrice.")
async def quem_sou_eu() -> str:
    return _texto(await _api("GET", "/auth/me"))


# ---------------------------------------------------------------- precificações


@ferramenta(
    LER,
    descricao="Lista as precificações da carteira do usuário com cliente, produto e status. "
    "Filtro opcional de status: em_preenchimento, em_aprovacao, aprovado ou reprovado.",
)
async def listar_precificacoes(
    status: Literal["em_preenchimento", "em_aprovacao", "aprovado", "reprovado"] | None = None,
) -> str:
    lista = await _api("GET", "/precificacoes")
    if status:
        lista = [item for item in lista if item.get("status") == status]
    return _texto(lista)


@ferramenta(
    LER,
    descricao="Detalha uma precificação pelo código (ex.: PRC-2026-0145): cabeçalho, versões de cenário salvas, "
    "histórico de status e decisões do gerente. Para quem não vê custo, as versões trazem só o preço.",
)
async def ver_precificacao(codigo: str) -> str:
    item = await _precificacao_por_codigo(codigo)
    pid = item["id"]
    try:
        versoes = await _api("GET", f"/precificacoes/{pid}/cenarios")
    except ToolError:
        versoes = await _api("GET", f"/precificacoes/{pid}/cenarios/precos")
    historico = await _api("GET", f"/precificacoes/{pid}/historico-status")
    decisoes = await _api("GET", f"/precificacoes/{pid}/decisoes")
    return _texto({"precificacao": item, "versoes": versoes, "historico_status": historico, "decisoes": decisoes})


@ferramenta(
    "precificacao.editar",
    descricao="Clientes, produtos e opções (modalidade, frete, regime, UF) válidos para abrir uma precificação. "
    "Use antes de criar_precificacao para pegar os ids.",
)
async def opcoes_de_precificacao() -> str:
    return _texto(await _api("GET", "/precificacoes/opcoes"))


@ferramenta(
    "precificacao.editar",
    escrita=True,
    descricao="Abre uma nova precificação (em preenchimento) para um cliente e produto. "
    "Pegue os ids em opcoes_de_precificacao e confirme os dados com o usuário antes.",
)
async def criar_precificacao(dados: PrecificacaoEntrada) -> str:
    return _texto(await _api("POST", "/precificacoes", corpo=_corpo(dados)))


@ferramenta(
    LER,
    "custo.ler",
    descricao="Monta a entrada de cálculo de uma precificação (formulação, cotações, câmbio, impostos e parâmetros "
    "vigentes) para um volume e lista o que ainda falta cadastrar.",
)
async def entrada_de_calculo(codigo: str, volume: float | None = None) -> str:
    item = await _precificacao_por_codigo(codigo)
    return _texto(await _api("GET", f"/precificacoes/{item['id']}/entrada-calculo", {"volume": volume}))


async def _entrada(codigo: str, volume: float | None, ajustes: dict | None) -> tuple[dict, dict]:
    item = await _precificacao_por_codigo(codigo)
    montada = await _api("GET", f"/precificacoes/{item['id']}/entrada-calculo", {"volume": volume})
    if montada.get("pendencias"):
        raise ToolError("Faltam dados para calcular: " + "; ".join(montada["pendencias"]))
    entrada = dict(montada["entrada"])
    entrada.update(ajustes or {})
    return item, entrada


@ferramenta(
    LER,
    "custo.ler",
    descricao="Simula o preço de uma precificação para um volume, sem salvar. 'ajustes' troca campos da entrada de "
    "cálculo (veja entrada_de_calculo), como a margem desejada.",
)
async def simular_preco(codigo: str, volume: float | None = None, ajustes: dict | None = None) -> str:
    _, entrada = await _entrada(codigo, volume, ajustes)
    return _texto(await _api("POST", "/calculate", corpo=entrada))


@ferramenta(
    LER,
    "precificacao.editar",
    escrita=True,
    descricao="Calcula e salva uma nova versão de cenário (mesmo cálculo de simular_preco). "
    "Confirme volume e ajustes com o usuário antes.",
)
async def salvar_cenario(
    codigo: str, volume: float | None = None, ajustes: dict | None = None, observacao: str | None = None
) -> str:
    item, entrada = await _entrada(codigo, volume, ajustes)
    corpo = {"entrada": entrada, "volume": volume, "observacao": observacao}
    return _texto(await _api("POST", f"/precificacoes/{item['id']}/cenarios", corpo=corpo))


@ferramenta(
    LER,
    "precificacao.editar",
    escrita=True,
    descricao="Cria uma nova versão a partir de outra, recalculada com os dados vigentes; o volume pode mudar.",
)
async def duplicar_versao(codigo: str, versao: int, volume: float | None = None, observacao: str | None = None) -> str:
    item = await _precificacao_por_codigo(codigo)
    corpo = {k: v for k, v in {"volume": volume, "observacao": observacao}.items() if v is not None}
    return _texto(await _api("POST", f"/precificacoes/{item['id']}/cenarios/{versao}/duplicar", corpo=corpo))


@ferramenta(
    LER, "custo.ler", descricao="Resultado completo de uma versão de cenário: custos, impostos, preço e margens."
)
async def ver_cenario(codigo: str, versao: int) -> str:
    item = await _precificacao_por_codigo(codigo)
    return _texto(await _api("GET", f"/precificacoes/{item['id']}/cenarios/{versao}"))


@ferramenta(LER, "custo.ler", descricao="Compara duas versões de cenário campo a campo (o que subiu, desceu ou igual).")
async def comparar_versoes(codigo: str, versao_de: int, versao_para: int) -> str:
    item = await _precificacao_por_codigo(codigo)
    params = {"de": versao_de, "para": versao_para}
    return _texto(await _api("GET", f"/precificacoes/{item['id']}/cenarios/comparacao", params))


@ferramenta(
    LER, "precificacao.editar", descricao="Confere se a precificação pode ir para aprovação e o que está faltando."
)
async def verificar_submissao(codigo: str) -> str:
    item = await _precificacao_por_codigo(codigo)
    return _texto(await _api("GET", f"/precificacoes/{item['id']}/submissao"))


@ferramenta(
    LER,
    "precificacao.editar",
    escrita=True,
    descricao="Envia a precificação para a aprovação do gerente. Confirme com o usuário antes.",
)
async def submeter_para_aprovacao(codigo: str) -> str:
    item = await _precificacao_por_codigo(codigo)
    return _texto(await _api("POST", f"/precificacoes/{item['id']}/submissao"))


@ferramenta(LER, descricao="Exporta os cenários salvos da carteira em CSV (o mesmo arquivo da exportação para o BI).")
async def exportar_cenarios() -> str:
    return await _api("GET", "/exportacoes/cenarios", {"formato": "csv"})


# ---------------------------------------------------------------- aprovação


@ferramenta(
    LER,
    "precificacao.aprovar",
    descricao="Fila de aprovação: precificações em aprovação com a margem comparada à política de margem mínima. "
    "Filtros opcionais: situação (abaixo ou dentro da política) e margem máxima (fração).",
)
async def fila_de_aprovacao(
    situacao: Literal["abaixo", "dentro"] | None = None, margem_ate: float | None = None
) -> str:
    return _texto(await _api("GET", "/aprovacoes/fila", {"situacao": situacao, "margem_ate": margem_ate}))


@ferramenta(
    LER,
    "precificacao.aprovar",
    escrita=True,
    descricao="Registra a decisão do gerente sobre uma precificação em aprovação: aprovado ou reprovado. "
    "Reprovar exige comentário. Mostre a precificação e confirme a decisão com o usuário antes.",
)
async def decidir_aprovacao(
    codigo: str, decisao: Literal["aprovado", "reprovado"], comentario: str | None = None
) -> str:
    item = await _precificacao_por_codigo(codigo)
    corpo = {"decisao": decisao, "comentario": comentario}
    return _texto(await _api("POST", f"/precificacoes/{item['id']}/decisoes", corpo=corpo))


# ---------------------------------------------------------------- cadastros e formulação


@ferramenta("cadastro.ler", descricao="Busca matérias-primas ou embalagens por código, descrição ou NCM.")
async def buscar_insumos(
    termo: str | None = None, tipo: TipoInsumo = "materias-primas", ativo: bool | None = None, pagina: int = 1
) -> str:
    params = {"busca": termo, "ativo": ativo, "pagina": pagina, "tamanho_pagina": 50}
    return _texto(await _api("GET", f"/cadastros/{tipo}", params))


@ferramenta("cadastro.ler", descricao="Lista os códigos NCM disponíveis para o cadastro de insumos.")
async def listar_ncm() -> str:
    return _texto(await _api("GET", "/cadastros/ncm"))


@ferramenta("cadastro.editar", escrita=True, descricao="Cadastra uma matéria-prima ou embalagem. Confirme antes.")
async def cadastrar_insumo(tipo: TipoInsumo, dados: InsumoEntrada) -> str:
    return _texto(await _api("POST", f"/cadastros/{tipo}", corpo=_corpo(dados)))


@ferramenta(
    "cadastro.editar",
    escrita=True,
    descricao="Altera um insumo pelo código ou descrição (só os campos enviados); ativo=true reativa. Confirme antes.",
)
async def alterar_insumo(insumo: str, tipo: TipoInsumo, dados: InsumoAtualizacao) -> str:
    alvo = await _insumo_por_termo(insumo, tipo)
    return _texto(await _api("PATCH", f"/cadastros/{tipo}/{alvo['id']}", corpo=_corpo(dados)))


@ferramenta(
    "cadastro.editar",
    escrita=True,
    descricao="Inativa um insumo pelo código ou descrição (não apaga; pode ser reativado). Confirme antes.",
)
async def inativar_insumo(insumo: str, tipo: TipoInsumo) -> str:
    alvo = await _insumo_por_termo(insumo, tipo)
    return _texto(await _api("DELETE", f"/cadastros/{tipo}/{alvo['id']}"))


@ferramenta("cadastro.ler", descricao="Lista os produtos acabados, com o id usado na formulação.")
async def listar_produtos() -> str:
    return _texto(await _api("GET", "/formulacoes/produtos"))


@ferramenta(LER, descricao="Mostra a formulação (lista de materiais) de um produto pelo id.")
async def ver_formulacao(produto_id: str) -> str:
    return _texto(await _api("GET", f"/formulacoes/{produto_id}"))


@ferramenta(
    "precificacao.editar",
    escrita=True,
    descricao="Salva a formulação completa de um produto (substitui os itens). Leia a atual com ver_formulacao, "
    "altere e confirme com o usuário antes.",
)
async def salvar_formulacao(produto_id: str, dados: FormulacaoEntrada) -> str:
    return _texto(await _api("PUT", f"/formulacoes/{produto_id}", corpo=_corpo(dados)))


# ---------------------------------------------------------------- cotações


@ferramenta(
    "custo.ler", "cadastro.ler", descricao="Cotações vigentes de uma matéria-prima (todas as faixas e fornecedores)."
)
async def cotacoes_vigentes(materia_prima: str, data_referencia: date | None = None) -> str:
    insumo = await _insumo_por_termo(materia_prima)
    params = {"materia_prima_id": insumo["id"], "data_referencia": data_referencia}
    return _texto({"materia_prima": insumo, "cotacoes": await _api("GET", "/cotacoes/vigentes", params)})


@ferramenta(
    "custo.ler",
    "cadastro.ler",
    descricao="Resolve a cotação de uma matéria-prima para um volume: o sistema escolhe a faixa e o fornecedor.",
)
async def cotacao_por_volume(materia_prima: str, quantidade: float, data_referencia: date | None = None) -> str:
    insumo = await _insumo_por_termo(materia_prima)
    params = {"materia_prima_id": insumo["id"], "quantidade": quantidade, "data_referencia": data_referencia}
    return _texto({"materia_prima": insumo, "cotacao": await _api("GET", "/cotacoes/resolver", params)})


# ---------------------------------------------------------------- câmbio e parâmetros


@ferramenta(
    "cambio.ler", descricao="Câmbio vigente de uma moeda (ex.: USD) numa data, com fonte e margem de segurança."
)
async def cambio_vigente(moeda: str = "USD", data_referencia: date | None = None) -> str:
    return _texto(await _api("GET", "/cambios/vigente", {"moeda": moeda.upper(), "data_referencia": data_referencia}))


@ferramenta("cambio.ler", descricao="Histórico das cotações de câmbio cadastradas, com filtro de moeda.")
async def listar_cambios(moeda: str | None = None, data_ate: date | None = None) -> str:
    return _texto(await _api("GET", "/cambios", {"moeda": moeda.upper() if moeda else None, "data_ate": data_ate}))


@ferramenta("cambio.editar", escrita=True, descricao="Registra uma nova cotação de câmbio. Confirme antes.")
async def registrar_cambio(dados: CambioEntrada) -> str:
    return _texto(await _api("POST", "/cambios", corpo=_corpo(dados)))


@ferramenta("cambio.editar", escrita=True, descricao="Corrige uma cotação de câmbio pelo id. Confirme antes.")
async def corrigir_cambio(cambio_id: str, dados: CambioAtualizacao) -> str:
    return _texto(await _api("PATCH", f"/cambios/{cambio_id}", corpo=_corpo(dados)))


@ferramenta(
    "parametro_global.ler",
    descricao="Parâmetros globais vigentes do cálculo: perda, taxa financeira, prazo médio e margem mínima.",
)
async def parametros_vigentes(data_referencia: date | None = None) -> str:
    return _texto(await _api("GET", "/parametros-globais/vigentes", {"data_referencia": data_referencia}))


@ferramenta("parametro_global.ler", descricao="Histórico de vigências dos parâmetros globais, com filtro por código.")
async def listar_parametros(codigo: str | None = None) -> str:
    return _texto(await _api("GET", "/parametros-globais", {"codigo": codigo}))


@ferramenta(
    "parametro_global.editar", escrita=True, descricao="Cria uma nova vigência de parâmetro global. Confirme antes."
)
async def criar_vigencia_parametro(dados: ParametroEntrada) -> str:
    return _texto(await _api("POST", "/parametros-globais", corpo=_corpo(dados)))


@ferramenta(
    "parametro_global.editar", escrita=True, descricao="Corrige uma vigência de parâmetro pelo id. Confirme antes."
)
async def corrigir_vigencia_parametro(parametro_id: str, dados: ParametroAtualizacao) -> str:
    return _texto(await _api("PATCH", f"/parametros-globais/{parametro_id}", corpo=_corpo(dados)))


# ---------------------------------------------------------------- impostos


@ferramenta(
    "parametro_fiscal.ler",
    descricao="Lista as alíquotas fiscais (PIS, COFINS, ICMS, IPI, MVA, FCP) por UF de destino, NCM (8 dígitos ou "
    "o começo) e regime tributário.",
)
async def consultar_aliquotas(
    uf_destino: str | None = None, ncm: str | None = None, regime_tributario: str | None = None
) -> str:
    params = {
        "uf_destino": uf_destino.upper() if uf_destino else None,
        "ncm_codigo": ncm,
        "regime_tributario": regime_tributario,
    }
    return _texto(await _api("GET", "/parametros-fiscais/aliquotas", params))


@ferramenta(
    "parametro_fiscal.ler",
    descricao="Resolve a alíquota vigente para UF de destino, NCM de 8 dígitos e regime tributário numa data.",
)
async def resolver_aliquota(
    uf_destino: str, ncm: str, regime_tributario: str, data_referencia: date | None = None
) -> str:
    params = {
        "uf_destino": uf_destino.upper(),
        "ncm_codigo": ncm,
        "regime_tributario": regime_tributario,
        "data_referencia": data_referencia,
    }
    return _texto(await _api("GET", "/parametros-fiscais/aliquotas/resolver", params))


@ferramenta("parametro_fiscal.editar", escrita=True, descricao="Cadastra uma alíquota fiscal. Confirme antes.")
async def cadastrar_aliquota(dados: AliquotaEntrada) -> str:
    return _texto(await _api("POST", "/parametros-fiscais/aliquotas", corpo=_corpo(dados)))


@ferramenta("parametro_fiscal.editar", escrita=True, descricao="Altera uma alíquota fiscal pelo id. Confirme antes.")
async def alterar_aliquota(aliquota_id: str, dados: AliquotaAtualizacao) -> str:
    return _texto(await _api("PATCH", f"/parametros-fiscais/aliquotas/{aliquota_id}", corpo=_corpo(dados)))


@ferramenta(
    "parametro_fiscal.editar",
    escrita=True,
    descricao="Importa alíquotas fiscais em lote (a mesma importação da tela de impostos). Confirme antes.",
)
async def importar_aliquotas(dados: ImportacaoEntrada) -> str:
    return _texto(await _api("POST", "/parametros-fiscais/aliquotas/importacao", corpo=_corpo(dados)))


# ---------------------------------------------------------------- app ASGI


def criar_app_mcp():
    """App ASGI do conector: `POST /mcp` e os metadados de recurso protegido."""
    return mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        # O Host vem do domínio público (Render); quem barra acesso é o token.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


CAMINHOS_MCP = ("/mcp", "/.well-known/oauth-protected-resource")


_app_atual = None


def app_mcp_atual():
    global _app_atual
    if _app_atual is None:
        _app_atual = criar_app_mcp()
    return _app_atual


@asynccontextmanager
async def ciclo_de_vida_mcp():
    """Sobe o gerenciador de sessões do MCP. Cada ciclo usa um app novo, porque o
    gerenciador só pode rodar uma vez (o TestClient abre um ciclo por teste)."""
    global _app_atual
    _app_atual = criar_app_mcp()
    async with _app_atual.router.lifespan_context(_app_atual):
        yield


class DespachoMCP:
    """Middleware ASGI que manda as rotas do conector para o app do MCP."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        caminho = scope.get("path", "") if scope["type"] == "http" else ""
        if caminho == CAMINHOS_MCP[0] or caminho.startswith(CAMINHOS_MCP[1]):
            await app_mcp_atual()(scope, receive, send)
        else:
            await self.app(scope, receive, send)
