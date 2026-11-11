import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from '../icons/Icon'
import './modal.css'

type Props = {
  titulo: ReactNode
  subtitulo?: ReactNode
  onFechar: () => void
  children: ReactNode
  /** Botões fixos no rodapé (ficam visíveis mesmo com o corpo rolando). */
  rodape?: ReactNode
  tamanho?: 'pequeno' | 'medio' | 'grande'
  /** Bloqueia Esc e clique fora enquanto algo é gravado. */
  ocupado?: boolean
}

let abertos = 0

/**
 * Modal do NeoPrice: um só jeito de abrir detalhe, formulário e confirmação.
 * Abre centralizado sobre a tela atual (e não no fim da página), fecha com
 * Esc, clique fora ou no X, prende o foco dentro dele e devolve o foco ao
 * botão que o abriu. É renderizado dentro de `.neoprice` para herdar o tema.
 */
export function Modal({ titulo, subtitulo, onFechar, children, rodape, tamanho = 'medio', ocupado = false }: Props) {
  const id = useId()
  const caixa = useRef<HTMLDivElement>(null)
  const fechar = useRef(onFechar)
  const bloqueado = useRef(ocupado)
  useEffect(() => { fechar.current = onFechar; bloqueado.current = ocupado })
  const [destino] = useState(() => document.querySelector('.neoprice') ?? document.body)

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null
    abertos += 1
    document.documentElement.classList.add('np-modal-aberto')
    const primeiro = caixa.current?.querySelector<HTMLElement>('[data-autofocus], input:not([type=hidden]):not(.np-validacao), textarea, .np-campo, button:not(.np-modal-x)')
    ;(primeiro ?? caixa.current)?.focus({ preventScroll: true })

    function teclado(evento: KeyboardEvent) {
      if (evento.key === 'Escape' && !bloqueado.current) {
        // um popover (Select, calendário) aberto dentro do modal fecha primeiro
        if (caixa.current?.querySelector('.np-popover')) return
        evento.stopPropagation(); fechar.current()
      }
      if (evento.key !== 'Tab' || !caixa.current) return
      const focaveis = [...caixa.current.querySelectorAll<HTMLElement>('button:not(:disabled), [href], input:not(:disabled):not(.np-validacao), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')]
      if (focaveis.length === 0) return
      const [inicio, fim] = [focaveis[0], focaveis[focaveis.length - 1]]
      if (evento.shiftKey && document.activeElement === inicio) { evento.preventDefault(); fim.focus() }
      else if (!evento.shiftKey && document.activeElement === fim) { evento.preventDefault(); inicio.focus() }
    }
    document.addEventListener('keydown', teclado)
    return () => {
      document.removeEventListener('keydown', teclado)
      abertos -= 1
      if (abertos === 0) document.documentElement.classList.remove('np-modal-aberto')
      anterior?.focus?.({ preventScroll: true })
    }
  }, [])

  return createPortal(
    <div className="np-modal-fundo" onMouseDown={(e) => { if (e.target === e.currentTarget && !ocupado) onFechar() }}>
      <div ref={caixa} className={`np-modal np-modal-${tamanho}`} role="dialog" aria-modal="true" aria-labelledby={`${id}-titulo`} tabIndex={-1}>
        <header className="np-modal-topo">
          <div>
            <h2 id={`${id}-titulo`}>{titulo}</h2>
            {subtitulo && <p>{subtitulo}</p>}
          </div>
          <button type="button" className="np-modal-x" aria-label="Fechar" disabled={ocupado} onClick={onFechar}><Icon name="fechar" size={18} /></button>
        </header>
        <div className="np-modal-corpo">{children}</div>
        {rodape && <footer className="np-modal-rodape">{rodape}</footer>}
      </div>
    </div>,
    destino,
  )
}
