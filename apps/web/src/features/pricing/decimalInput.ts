function scaled(raw: string, casas: number, digitosInteiros: number): bigint | null {
  const valor = raw.trim().replace(',', '.')
  const partes = /^(\d+)(?:\.(\d*))?$/.exec(valor)
  if (!partes) return null
  const inteiro = partes[1].replace(/^0+(?=\d)/, '')
  const fracao = partes[2] ?? ''
  if (inteiro.length > digitosInteiros || fracao.length > casas) return null
  return BigInt(inteiro) * 10n ** BigInt(casas) + BigInt(fracao.padEnd(casas, '0') || '0')
}

export function normalizarDecimal(raw: string): string {
  return raw.trim().replace(',', '.')
}

export function quantidadeValida(raw: string): boolean {
  const valor = scaled(raw, 6, 8)
  return valor !== null && valor > 0n
}

export function perdaValida(raw: string): boolean {
  const valor = scaled(raw, 4, 3)
  return valor !== null && valor <= 100n * 10_000n
}
