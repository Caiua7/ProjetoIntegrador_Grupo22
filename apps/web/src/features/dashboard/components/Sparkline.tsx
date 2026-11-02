/** Minigráfico de tendência para os cartões de indicador. Decorativo: o valor está no cartão. */
export function Sparkline({ valores }: { valores: number[] }) {
  const largura = 96
  const altura = 30
  const min = Math.min(...valores)
  const max = Math.max(...valores)
  const pontos = valores.map((v, i) => {
    const x = (i / (valores.length - 1 || 1)) * largura
    const y = altura - 3 - ((v - min) / (max - min || 1)) * (altura - 6)
    return [x, y] as const
  })
  const linha = pontos.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const [ultimoX, ultimoY] = pontos.at(-1)!

  return <svg className="sparkline" viewBox={`0 0 ${largura} ${altura}`} aria-hidden="true" focusable="false">
    <path className="sparkline-area" d={`${linha} L${largura} ${altura} L0 ${altura} Z`} />
    <path className="sparkline-linha" pathLength={1} d={linha} />
    <circle cx={ultimoX} cy={ultimoY} r="2.5" />
  </svg>
}
