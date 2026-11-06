/**
 * Aritmética decimal exata sobre strings, para valores que vêm da API como
 * NUMERIC. Nada passa por `Number()`: a escala é feita com BigInt.
 */

type Escalado = { digitos: bigint, casas: number, negativo: boolean }

function ler(valor: string): Escalado | null {
  const limpo = valor.trim().replace(',', '.')
  const partes = /^(-?)(\d+)(?:\.(\d*))?$/.exec(limpo)
  if (!partes) return null
  const fracao = partes[3] ?? ''
  return { digitos: BigInt(`${partes[2]}${fracao}` || '0'), casas: fracao.length, negativo: partes[1] === '-' }
}

function escrever(digitos: bigint, casas: number, negativo: boolean): string {
  const texto = digitos.toString().padStart(casas + 1, '0')
  const inteiro = texto.slice(0, texto.length - casas) || '0'
  const fracao = casas > 0 ? texto.slice(texto.length - casas).replace(/0+$/, '') : ''
  const sinal = negativo && digitos !== 0n ? '-' : ''
  return `${sinal}${inteiro}${fracao ? `.${fracao}` : ''}`
}

/** Valor × 10^casas, sem perda: '0.012', 2 → '1.2'; '1.2', -2 → '0.012'. '' se inválido. */
export function deslocarDecimal(valor: string, casas: number): string {
  const lido = ler(valor)
  if (!lido) return ''
  const escala = lido.casas - casas
  if (escala <= 0) return escrever(lido.digitos * 10n ** BigInt(-escala), 0, lido.negativo)
  return escrever(lido.digitos, escala, lido.negativo)
}

/** Produto exato arredondado (meio para cima) em `casas` decimais. '' se inválido. */
export function multiplicarDecimal(a: string, b: string, casas: number): string {
  const x = ler(a)
  const y = ler(b)
  if (!x || !y) return ''
  const produto = x.digitos * y.digitos
  const escala = x.casas + y.casas
  const negativo = x.negativo !== y.negativo
  if (escala <= casas) return escrever(produto * 10n ** BigInt(casas - escala), casas, negativo)
  const divisor = 10n ** BigInt(escala - casas)
  const arredondado = (produto + divisor / 2n) / divisor
  return escrever(arredondado, casas, negativo)
}

/** Soma exata de dois decimais. '' se inválido. */
export function somarDecimal(a: string, b: string): string {
  const x = ler(a)
  const y = ler(b)
  if (!x || !y) return ''
  const casas = Math.max(x.casas, y.casas)
  const vx = x.digitos * 10n ** BigInt(casas - x.casas) * (x.negativo ? -1n : 1n)
  const vy = y.digitos * 10n ** BigInt(casas - y.casas) * (y.negativo ? -1n : 1n)
  const total = vx + vy
  return escrever(total < 0n ? -total : total, casas, total < 0n)
}

/** '5.123400' → '5,1234' (sem separador de milhar; para tabelas e cartões). */
export function formatarDecimalBr(valor: string, casasMinimas = 0): string {
  const lido = ler(valor)
  if (!lido) return valor
  const normal = escrever(lido.digitos, lido.casas, lido.negativo)
  const [inteiro, fracao = ''] = normal.split('.')
  const completa = fracao.padEnd(casasMinimas, '0')
  return completa ? `${inteiro},${completa}` : inteiro
}
