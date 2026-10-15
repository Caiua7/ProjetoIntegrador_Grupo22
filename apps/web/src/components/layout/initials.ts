/** Iniciais do primeiro e do último nome: "Felipe Corso Pretoni" → "FP". */
export function initials(nome: string): string {
  const partes = nome.split(/\s+/).filter(Boolean)
  const letras = partes.length > 1 ? partes[0][0] + partes[partes.length - 1][0] : (partes[0] ?? '?').slice(0, 2)
  return letras.toUpperCase()
}
