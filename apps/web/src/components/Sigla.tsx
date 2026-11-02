import { useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { GLOSSARIO, type SiglaConhecida } from '../app/glossario'
import './sigla.css'

type Posicao = { x: number, y: number, abaixo: boolean, destino: Element }

/**
 * Sigla com o significado por extenso no hover e no foco do teclado.
 * `children` troca o texto exibido (ex.: "MaCo média") mantendo a explicação.
 *
 * O cartão sai num portal com posição fixa: dentro de tabelas com rolagem
 * horizontal ele não é cortado. Perto do topo da tela, abre para baixo.
 */
export function Sigla({ termo, children }: { termo: SiglaConhecida, children?: ReactNode }) {
  const id = useId()
  const ancora = useRef<HTMLSpanElement>(null)
  const [posicao, setPosicao] = useState<Posicao | null>(null)
  const { nome, explicacao } = GLOSSARIO[termo]

  function abrir() {
    const r = ancora.current?.getBoundingClientRect()
    if (!r) return
    const abaixo = r.top < 120
    // Dentro de .neoprice o cartão herda as cores do tema escolhido
    const destino = ancora.current?.closest('.neoprice') ?? document.body
    setPosicao({ x: Math.min(Math.max(r.left + r.width / 2, 140), window.innerWidth - 140), y: abaixo ? r.bottom : r.top, abaixo, destino })
  }

  return <span ref={ancora} className="sigla" tabIndex={0} aria-describedby={id}
    onMouseEnter={abrir} onMouseLeave={() => setPosicao(null)} onFocus={abrir} onBlur={() => setPosicao(null)}
    onKeyDown={(event) => { if (event.key === 'Escape') setPosicao(null) }}>
    <abbr>{children ?? termo}</abbr>
    <span className="sr-only" id={id}>{nome}. {explicacao}</span>
    {posicao && createPortal(
      <span className={`sigla-dica${posicao.abaixo ? ' abaixo' : ''}`} role="tooltip" aria-hidden="true"
        style={{ left: posicao.x, top: posicao.y }}>
        <strong>{nome}</strong>
        <span>{explicacao}</span>
      </span>,
      posicao.destino,
    )}
  </span>
}
