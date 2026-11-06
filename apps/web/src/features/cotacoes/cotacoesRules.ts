/**
 * Regras puras da tela de cotações vigentes (US25/US28).
 * A resolução de verdade é do servidor (pricing_core.cotacao); aqui só o que
 * a tela precisa para mostrar faixas, rótulos e o custo estimado.
 *
 * Convenção do core: a faixa vai do `volume_minimo` (inclusive) até o mínimo
 * da próxima faixa (exclusive); a última é aberta.
 */
import { multiplicarDecimal } from '../../app/decimal.ts'
import type { Cotacao } from './cotacoesService.ts'

export type Faixa = { minimo: string, ateExclusive: string | null }

function comparar(a: string, b: string): number {
  const [ia, fa = ''] = a.split('.')
  const [ib, fb = ''] = b.split('.')
  const casas = Math.max(fa.length, fb.length)
  const va = BigInt(`${ia}${fa.padEnd(casas, '0')}`)
  const vb = BigInt(`${ib}${fb.padEnd(casas, '0')}`)
  return va < vb ? -1 : va > vb ? 1 : 0
}

/** Mínimos distintos em ordem crescente, cada um com o limite da próxima faixa. */
export function faixas(cotacoes: readonly Pick<Cotacao, 'volume_minimo'>[]): Faixa[] {
  const minimos: string[] = []
  for (const c of [...cotacoes].sort((a, b) => comparar(a.volume_minimo, b.volume_minimo))) {
    if (!minimos.length || comparar(minimos[minimos.length - 1], c.volume_minimo) !== 0) minimos.push(c.volume_minimo)
  }
  return minimos.map((minimo, i) => ({ minimo, ateExclusive: minimos[i + 1] ?? null }))
}

export function faixaDe(volumeMinimo: string, lista: readonly Faixa[]): Faixa | undefined {
  return lista.find((f) => comparar(f.minimo, volumeMinimo) === 0)
}

/** Quantidade digitada → valor para a API (positiva, até 15 inteiros e 3 casas, como NUMERIC(18,3)). */
export function quantidadeParaApi(digitada: string): string | null {
  const bruto = digitada.trim()
  // Com vírgula, o ponto é separador de milhar (1.250,5); sem vírgula, é o decimal.
  const limpo = bruto.includes(',') ? bruto.replace(/\./g, '').replace(',', '.') : bruto
  if (!/^\d{1,15}(?:\.\d{1,3})?$/.test(limpo) || !/[1-9]/.test(limpo)) return null
  return limpo.replace(/^0+(?=\d)/, '')
}

/** preço × quantidade, com 2 casas, na moeda da cotação. */
export function custoEstimado(preco: string, quantidade: string): string {
  return multiplicarDecimal(preco, quantidade, 2)
}

export function rotuloFornecedor(c: Pick<Cotacao, 'fornecedor_id' | 'fornecedor_codigo' | 'fornecedor_nome'>): string {
  if (c.fornecedor_nome && c.fornecedor_codigo) return `${c.fornecedor_codigo} · ${c.fornecedor_nome}`
  return c.fornecedor_nome ?? c.fornecedor_codigo ?? `Fornecedor ${c.fornecedor_id.slice(0, 8)}`
}

/** Fornecedores distintos das cotações, para o filtro do simulador. */
export function fornecedores(cotacoes: readonly Cotacao[]): { id: string, rotulo: string }[] {
  const vistos = new Map<string, string>()
  for (const c of cotacoes) if (!vistos.has(c.fornecedor_id)) vistos.set(c.fornecedor_id, rotuloFornecedor(c))
  return [...vistos.entries()].map(([id, rotulo]) => ({ id, rotulo })).sort((a, b) => a.rotulo.localeCompare(b.rotulo))
}

/** 409 da API = empate entre fornecedores na mesma faixa e validade. */
export function precisaFornecedor(status: number): boolean {
  return status === 409
}
