import { useEffect, useRef, useState } from 'react'

/** Abre e fecha um popover; fecha no clique fora e no Esc, devolvendo o foco ao gatilho. */
export function usePopover<T extends HTMLElement = HTMLButtonElement>() {
  const [aberto, setAberto] = useState(false)
  const raiz = useRef<HTMLDivElement>(null)
  const gatilho = useRef<T>(null)

  useEffect(() => {
    if (!aberto) return
    function cliqueFora(evento: MouseEvent) {
      if (!raiz.current?.contains(evento.target as Node)) setAberto(false)
    }
    function tecla(evento: KeyboardEvent) {
      if (evento.key === 'Escape') {
        setAberto(false)
        gatilho.current?.focus()
      }
    }
    document.addEventListener('mousedown', cliqueFora)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('mousedown', cliqueFora)
      document.removeEventListener('keydown', tecla)
    }
  }, [aberto])

  function fechar(devolverFoco = true) {
    setAberto(false)
    if (devolverFoco) gatilho.current?.focus()
  }

  return { aberto, setAberto, fechar, raiz, gatilho }
}
