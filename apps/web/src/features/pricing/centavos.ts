/**
 * Arredonda um decimal exato vindo da API para centavos, só na apresentação
 * (metade para longe do zero). A API devolve ROB, MaCo e MB sem arredondar;
 * converter para `Number` antes perderia precisão em operações grandes.
 */
export function arredondarCentavos(value: string | null | undefined): string | null {
  if (value == null) return null
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value)
  if (!match) return value
  const [, sign, whole, fraction = ''] = match
  let centavos = BigInt(whole + (fraction + '00').slice(0, 2))
  if (Number(fraction[2] ?? '0') >= 5) centavos += 1n
  const texto = centavos.toString().padStart(3, '0')
  const resultado = `${texto.slice(0, -2)}.${texto.slice(-2)}`
  return centavos === 0n ? resultado : `${sign}${resultado}`
}
