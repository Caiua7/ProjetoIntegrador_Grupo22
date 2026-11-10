"""Mede o tempo de resposta de POST /calculate (issue #59: p95 < 800 ms).

A entrada é o caso template da homologação, ampliado para uma formulação
realista (por padrão 25 matérias-primas e 5 embalagens). Antes de medir, o
script faz algumas chamadas de aquecimento: no Render gratuito a primeira
chamada depois de ~15 min parado leva 30–50 s só para acordar a API, e isso
não é o tempo do cálculo.

Uso (staging):
    set NEOPRICE_EMAIL=...        # usuário de teste com precificacao.ler
    set NEOPRICE_SENHA=...
    python scripts/medir_p95.py --api https://neoprice-api-staging.onrender.com

    O login usa VITE_NEOPRICE_SUPABASE_URL e VITE_NEOPRICE_SUPABASE_ANON_KEY,
    lidos do ambiente ou de apps/web/.env.staging (valores públicos).

Uso (API local, sem login):
    python scripts/medir_p95.py --api http://localhost:8000 --token <access token>

Sai com código 1 se o p95 passar do limite.
"""

import argparse
import copy
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "conformidade" / "casos" / "caso_000_template.json"


def montar_entrada(materias_primas: int, embalagens: int) -> dict:
    entrada = json.loads(CASO.read_text(encoding="utf-8"))["entrada"]
    modelo = entrada["materiais_primas"][0]
    entrada["materiais_primas"] = [
        {**copy.deepcopy(modelo), "codigo": f"MP-{i:03d}", "quantidade": "4"} for i in range(materias_primas)
    ]
    entrada["embalagens"] = [
        {**copy.deepcopy(modelo), "codigo": f"EMB-{i:03d}", "quantidade": "1"} for i in range(embalagens)
    ]
    return entrada


def _ler_env_staging() -> dict[str, str]:
    arquivo = RAIZ / "apps" / "web" / ".env.staging"
    if not arquivo.exists():
        return {}
    valores = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            chave, valor = linha.split("=", 1)
            valores[chave.strip()] = valor.strip().strip('"')
    return valores


def obter_token() -> str:
    env = {**_ler_env_staging(), **os.environ}
    url, chave = env.get("VITE_NEOPRICE_SUPABASE_URL"), env.get("VITE_NEOPRICE_SUPABASE_ANON_KEY")
    email, senha = env.get("NEOPRICE_EMAIL"), env.get("NEOPRICE_SENHA")
    if not all([url, chave, email, senha]):
        sys.exit("Defina NEOPRICE_EMAIL e NEOPRICE_SENHA (e o Supabase do front) ou passe --token.")
    resposta = httpx.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers={"apikey": chave},
        json={"email": email, "password": senha},
        timeout=30,
    )
    resposta.raise_for_status()
    return resposta.json()["access_token"]


def percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    indice = max(0, min(len(ordenados) - 1, round(p / 100 * len(ordenados)) - 1))
    return ordenados[indice]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", required=True, help="URL base da API, sem barra no fim")
    parser.add_argument("--token", help="access token do Supabase (pula o login)")
    parser.add_argument("--chamadas", type=int, default=200)
    parser.add_argument("--aquecimento", type=int, default=10)
    parser.add_argument("--concorrencia", type=int, default=1, help="chamadas simultâneas")
    parser.add_argument("--materias-primas", type=int, default=25)
    parser.add_argument("--embalagens", type=int, default=5)
    parser.add_argument("--limite-ms", type=float, default=800)
    args = parser.parse_args()

    token = args.token or obter_token()
    entrada = montar_entrada(args.materias_primas, args.embalagens)
    cliente = httpx.Client(base_url=args.api, headers={"Authorization": f"Bearer {token}"}, timeout=120, http2=False)

    def chamar() -> float:
        inicio = time.perf_counter()
        resposta = cliente.post("/calculate", json=entrada)
        duracao = (time.perf_counter() - inicio) * 1000
        if resposta.status_code != 200:
            sys.exit(f"POST /calculate respondeu {resposta.status_code}: {resposta.text[:300]}")
        return duracao

    print(f"Aquecendo com {args.aquecimento} chamadas...")
    for _ in range(args.aquecimento):
        chamar()

    print(f"Medindo {args.chamadas} chamadas (concorrência {args.concorrencia})...")
    with ThreadPoolExecutor(max_workers=args.concorrencia) as executor:
        tempos = list(executor.map(lambda _: chamar(), range(args.chamadas)))

    p95 = percentil(tempos, 95)
    print(
        f"Entrada: {args.materias_primas} MPs + {args.embalagens} embalagens\n"
        f"p50 {percentil(tempos, 50):.0f} ms | p95 {p95:.0f} ms | p99 {percentil(tempos, 99):.0f} ms | "
        f"máx {max(tempos):.0f} ms | média {statistics.mean(tempos):.0f} ms"
    )
    if p95 >= args.limite_ms:
        print(f"ACIMA do limite de {args.limite_ms:.0f} ms")
        sys.exit(1)
    print(f"Dentro do limite de {args.limite_ms:.0f} ms")


if __name__ == "__main__":
    main()
