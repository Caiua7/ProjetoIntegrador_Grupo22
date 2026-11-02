import { useEffect, useState } from 'react'

const semMovimento = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Conta de 0 até `alvo` em `duracao` ms, desacelerando no fim. Sem animação para quem pediu menos movimento. */
export function useContagem(alvo: number, duracao = 900) {
  const [valor, setValor] = useState(() => (semMovimento() ? alvo : 0))

  useEffect(() => {
    if (semMovimento()) return
    let quadro = 0
    const inicio = performance.now()
    const passo = (agora: number) => {
      const t = Math.min((agora - inicio) / duracao, 1)
      setValor(alvo * (1 - (1 - t) ** 3))
      if (t < 1) quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(quadro)
  }, [alvo, duracao])

  return valor
}
