import gzip
import json
import re
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "supabase" / "seed" / "referencia"

URL_UFS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
URL_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
URL_NCM = "https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json?perfil=PUBLICO"
URL_CEP = "https://viacep.com.br/ws/{cep}/json/"

CEPS = [
    "01310100",
    "04538133",
    "06454000",
    "13010111",
    "13087571",
    "20040020",
    "30130100",
    "80010000",
    "89010000",
    "90010150",
]

LINHAS_POR_INSERT = 500


def _baixar_json(url: str):
    requisicao = urllib.request.Request(url, headers={"User-Agent": "neoprice-seed"})
    with urllib.request.urlopen(requisicao, timeout=120) as resposta:
        conteudo = resposta.read()
    if conteudo[:2] == bytes([0x1F, 0x8B]):
        conteudo = gzip.decompress(conteudo)
    return json.loads(conteudo.decode("utf-8"))


def _sql(valor) -> str:
    if valor is None or valor == "":
        return "NULL"
    if isinstance(valor, int):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def _upsert(tabela: str, colunas: list[str], chave: str, linhas: list[tuple]) -> str:
    demais = [c for c in colunas if c != chave]
    atual = ", ".join(f"{tabela}.{c}" for c in demais)
    novo = ", ".join(f"EXCLUDED.{c}" for c in demais)
    blocos = []
    for inicio in range(0, len(linhas), LINHAS_POR_INSERT):
        lote = linhas[inicio : inicio + LINHAS_POR_INSERT]
        valores = ",\n".join("    (" + ", ".join(_sql(v) for v in linha) + ")" for linha in lote)
        blocos.append(
            f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES\n{valores}\n"
            f"ON CONFLICT ({chave}) DO UPDATE SET\n"
            + ",\n".join(f"    {c} = EXCLUDED.{c}" for c in demais)
            + f"\nWHERE ({atual}) IS DISTINCT FROM ({novo});\n"
        )
    return "\n".join(blocos)


def _gravar(nome: str, corpo: str, total: int) -> None:
    (SAIDA / nome).write_text(corpo, encoding="utf-8", newline="\n")
    print(f"{nome}: {total} registros")


def gerar_uf() -> None:
    ufs = sorted(_baixar_json(URL_UFS), key=lambda u: u["id"])
    linhas = [(u["sigla"], u["id"], u["nome"], u["regiao"]["sigla"]) for u in ufs]
    corpo = _upsert("uf", ["sigla", "codigo_ibge", "nome", "regiao"], "sigla", linhas)
    _gravar("01_uf.sql", corpo, len(linhas))


def gerar_municipio() -> None:
    municipios = sorted(_baixar_json(URL_MUNICIPIOS), key=lambda m: m["municipio-id"])
    linhas = [(m["municipio-id"], m["municipio-nome"], m["UF-sigla"]) for m in municipios]
    corpo = _upsert("municipio", ["codigo_ibge", "nome", "uf_sigla"], "codigo_ibge", linhas)
    _gravar("02_municipio.sql", corpo, len(linhas))


def _limpar_descricao_ncm(descricao: str) -> str:
    texto = re.sub(r"<[^>]+>", "", descricao).replace(" ", " ")
    texto = re.sub(r"^[-\s]+", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def gerar_ncm() -> None:
    tabela = _baixar_json(URL_NCM)
    linhas = []
    for item in tabela["Nomenclaturas"]:
        codigo = re.sub(r"\D", "", item["Codigo"])
        if len(codigo) == 8:
            linhas.append((codigo, _limpar_descricao_ncm(item["Descricao"])))
    linhas.sort()
    corpo = _upsert("ncm", ["codigo", "descricao"], "codigo", linhas)
    _gravar("03_ncm.sql", corpo, len(linhas))


def gerar_cep() -> None:
    linhas = []
    for cep in sorted(CEPS):
        dados = _baixar_json(URL_CEP.format(cep=cep))
        if dados.get("erro"):
            raise SystemExit(f"CEP {cep} não encontrado no ViaCEP")
        linhas.append((cep, dados["logradouro"], dados["bairro"], int(dados["ibge"])))
    corpo = _upsert("cep", ["cep", "logradouro", "bairro", "municipio_codigo_ibge"], "cep", linhas)
    _gravar("04_cep.sql", corpo, len(linhas))


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    gerar_uf()
    gerar_municipio()
    gerar_ncm()
    gerar_cep()


if __name__ == "__main__":
    main()
