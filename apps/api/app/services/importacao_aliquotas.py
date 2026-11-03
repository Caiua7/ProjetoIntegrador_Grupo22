"""Leitura da planilha de importação de alíquotas (issue #48, US12).

A planilha é um CSV exportado do Excel, com uma alíquota por linha e os
percentuais como a área fiscal escreve (18 ou 18,00 para 18%). Aqui o texto
vira a lista de alíquotas no formato da API (frações, 0.18), com o erro de
cada linha apontado pelo número da linha no arquivo. Nada é gravado: a
gravação é da função `importar_aliquotas` no banco.
"""

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ValidationError

MAXIMO_DE_LINHAS = 5000

COLUNAS_PERCENTUAIS = {
    "pis": "pis_percentual",
    "cofins": "cofins_percentual",
    "icms": "icms_percentual",
    "ipi": "ipi_percentual",
    "icms_interno": "icms_interno_percentual",
    "fcp": "fcp_percentual",
    "mva": "mva_percentual",
}

APELIDOS_DE_COLUNA = {
    "uf": "uf_destino",
    "uf_destino": "uf_destino",
    "ncm": "ncm_codigo",
    "ncm_codigo": "ncm_codigo",
    "regime": "regime_tributario",
    "regime_tributario": "regime_tributario",
    "vigencia": "vigencia_inicio",
    "vigencia_inicio": "vigencia_inicio",
    "inicio_vigencia": "vigencia_inicio",
    "inicio_da_vigencia": "vigencia_inicio",
    **{nome: campo for nome, campo in COLUNAS_PERCENTUAIS.items()},
    **{campo: campo for campo in COLUNAS_PERCENTUAIS.values()},
}

COLUNAS_OBRIGATORIAS = ["uf_destino", "regime_tributario", "vigencia_inicio", *COLUNAS_PERCENTUAIS.values()]

REGIMES = {
    "lucro_real": "lucro_real",
    "real": "lucro_real",
    "lucro_presumido": "lucro_presumido",
    "presumido": "lucro_presumido",
    "simples_nacional": "simples_nacional",
    "simples": "simples_nacional",
}

CABECALHO_MODELO = "uf;ncm;regime;vigencia;pis;cofins;icms;ipi;icms_interno;fcp;mva"

UFS = frozenset(
    [
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
    ]
)


@dataclass
class ErroDeLinha:
    linha: int
    mensagem: str


@dataclass
class ResultadoLeitura:
    aliquotas: list[dict] = field(default_factory=list)
    erros: list[ErroDeLinha] = field(default_factory=list)


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    sem_simbolos = re.sub(r"\(%\)|%", "", sem_acento.strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", sem_simbolos).strip("_")


def _percentual(valor: str) -> Decimal:
    """'18', '18,00', '1.234,5' ou '18%' viram fração (0.18). Vazio é zero."""
    texto = valor.strip().replace("%", "").replace(" ", "")
    if not texto:
        return Decimal("0")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"'{valor.strip()}' não é um percentual") from None
    if not numero.is_finite():
        raise ValueError(f"'{valor.strip()}' não é um percentual")
    return numero / 100


def _data(valor: str) -> date:
    texto = valor.strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"vigência '{texto}' fora do formato AAAA-MM-DD ou DD/MM/AAAA")


def _uf(valor: str) -> str:
    uf = valor.strip().upper()
    if uf not in UFS:
        raise ValueError(f"UF de destino '{valor.strip()}' não existe")
    return uf


def _regime(valor: str) -> str:
    regime = REGIMES.get(_normalizar(valor))
    if regime is None:
        raise ValueError(f"regime '{valor.strip()}' desconhecido (use Lucro Real, Lucro Presumido ou Simples Nacional)")
    return regime


def _ncm(valor: str) -> str | None:
    digitos = re.sub(r"\D", "", valor)
    if not digitos:
        return None
    if len(digitos) != 8:
        raise ValueError(f"NCM '{valor.strip()}' precisa ter 8 dígitos (ou ficar vazio para a regra geral da UF)")
    return digitos


def _mensagem_de_validacao(erro: ValidationError) -> str:
    partes = []
    for detalhe in erro.errors():
        campo = ".".join(str(parte) for parte in detalhe["loc"])
        partes.append(f"{campo}: {detalhe['msg']}")
    return "; ".join(partes)


def ler_planilha(conteudo: str, modelo: type[BaseModel]) -> ResultadoLeitura:
    """Lê o CSV e valida cada linha com `modelo` (AliquotaEntrada).

    O separador é `;` (padrão do Excel em português) ou `,`. Uma linha em
    branco é ignorada; a mesma chave repetida no arquivo é erro, porque não
    dá para saber qual das duas vale.
    """
    resultado = ResultadoLeitura()
    texto = conteudo.lstrip("﻿")
    primeira_linha = texto.splitlines()[0] if texto.strip() else ""
    if not primeira_linha:
        resultado.erros.append(ErroDeLinha(1, "o arquivo está vazio"))
        return resultado

    separador = ";" if ";" in primeira_linha else ","
    leitor = csv.reader(io.StringIO(texto), delimiter=separador)
    cabecalho = [APELIDOS_DE_COLUNA.get(_normalizar(nome), _normalizar(nome)) for nome in next(leitor)]

    faltando = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in cabecalho]
    if faltando:
        resultado.erros.append(ErroDeLinha(1, f"faltam as colunas {', '.join(faltando)}; modelo: {CABECALHO_MODELO}"))
        return resultado

    chaves_vistas: dict[tuple, int] = {}
    for numero, valores in enumerate(leitor, start=2):
        if not any(valor.strip() for valor in valores):
            continue
        if len(resultado.aliquotas) + len(resultado.erros) >= MAXIMO_DE_LINHAS:
            resultado.erros.append(ErroDeLinha(numero, f"a planilha passa do limite de {MAXIMO_DE_LINHAS} linhas"))
            break

        celulas = dict(zip(cabecalho, valores, strict=False))
        try:
            bruta = {
                "uf_destino": _uf(celulas.get("uf_destino", "")),
                "ncm_codigo": _ncm(celulas.get("ncm_codigo", "")),
                "regime_tributario": _regime(celulas.get("regime_tributario", "")),
                "vigencia_inicio": _data(celulas.get("vigencia_inicio", "")),
                **{campo: _percentual(celulas.get(campo, "")) for campo in COLUNAS_PERCENTUAIS.values()},
            }
            aliquota = modelo.model_validate(bruta).model_dump(mode="json")
        except ValueError as erro:
            mensagem = _mensagem_de_validacao(erro) if isinstance(erro, ValidationError) else str(erro)
            resultado.erros.append(ErroDeLinha(numero, mensagem))
            continue

        chave = (
            aliquota["uf_destino"],
            aliquota["ncm_codigo"],
            aliquota["regime_tributario"],
            aliquota["vigencia_inicio"],
        )
        if chave in chaves_vistas:
            resultado.erros.append(
                ErroDeLinha(numero, f"mesma UF, NCM, regime e vigência da linha {chaves_vistas[chave]}")
            )
            continue
        chaves_vistas[chave] = numero
        resultado.aliquotas.append(aliquota)

    if not resultado.aliquotas and not resultado.erros:
        resultado.erros.append(ErroDeLinha(2, "a planilha não tem nenhuma alíquota"))
    return resultado
