/** Multiplicação decimal exata para obter volume total sem passar por Number. */
export function multiplicarDecimais(a: string, b: string): string {
  const pa = /^(\d+)(?:\.(\d+))?$/.exec(a.trim())
  const pb = /^(\d+)(?:\.(\d+))?$/.exec(b.trim())
  if (!pa || !pb) throw new Error('Informe valores decimais válidos.')
  const fa = pa[2] ?? ''
  const fb = pb[2] ?? ''
  const escala = fa.length + fb.length
  const bruto = (BigInt(pa[1] + fa) * BigInt(pb[1] + fb)).toString().padStart(escala + 1, '0')
  if (escala === 0) return bruto
  const inteiro = bruto.slice(0, -escala)
  const fracao = bruto.slice(-escala).replace(/0+$/, '')
  return fracao ? `${inteiro}.${fracao}` : inteiro
}
