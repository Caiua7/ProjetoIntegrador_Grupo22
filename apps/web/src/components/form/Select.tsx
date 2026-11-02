import { useId, useMemo, useState, type KeyboardEvent } from 'react'
import { Icon } from '../icons/Icon'
import { usePopover } from './usePopover'
import './form.css'

export type Opcao = { value: string, label: string, detalhe?: string, disabled?: boolean }

type Props = {
  value: string
  onChange: (value: string) => void
  options: Opcao[]
  placeholder?: string
  required?: boolean
  disabled?: boolean
  /** Rótulo para leitor de tela quando o Select não está dentro de um <label>. */
  ariaLabel?: string
  /** Campo de busca no topo da lista; ligado sozinho com mais de 8 opções. */
  pesquisavel?: boolean
  compacto?: boolean
}

/**
 * Seleção do NeoPrice, no lugar do <select> nativo: mesma aparência em todo
 * navegador e tema. Teclado: setas, Home/End, Enter, Esc e digitação para
 * buscar. Dentro de <label> o botão recebe o rótulo; `required` usa um input
 * oculto para o formulário validar.
 */
export function Select({ value, onChange, options, placeholder = 'Selecione', required, disabled, ariaLabel, pesquisavel, compacto }: Props) {
  const id = useId()
  const { aberto, setAberto, fechar, raiz, gatilho } = usePopover()
  const [busca, setBusca] = useState('')
  const [ativo, setAtivo] = useState(0)
  const comBusca = pesquisavel ?? options.length > 8

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    return termo ? options.filter((o) => `${o.label} ${o.detalhe ?? ''}`.toLowerCase().includes(termo)) : options
  }, [busca, options])
  const selecionada = options.find((o) => o.value === value)

  function abrir() {
    if (disabled) return
    setBusca('')
    setAtivo(Math.max(0, options.findIndex((o) => o.value === value)))
    setAberto(true)
  }

  function escolher(opcao: Opcao | undefined) {
    if (!opcao || opcao.disabled) return
    onChange(opcao.value)
    fechar()
  }

  function teclado(evento: KeyboardEvent) {
    if (!aberto) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(evento.key)) { evento.preventDefault(); abrir() }
      return
    }
    const mover = (para: number) => { evento.preventDefault(); setAtivo(Math.min(Math.max(para, 0), visiveis.length - 1)) }
    if (evento.key === 'ArrowDown') mover(ativo + 1)
    else if (evento.key === 'ArrowUp') mover(ativo - 1)
    else if (evento.key === 'Home') mover(0)
    else if (evento.key === 'End') mover(visiveis.length - 1)
    else if (evento.key === 'Enter') { evento.preventDefault(); escolher(visiveis[ativo]) }
    else if (evento.key === 'Tab') fechar(false)
  }

  return <div ref={raiz} className={`np-select${aberto ? ' aberto' : ''}${compacto ? ' compacto' : ''}`} onKeyDown={teclado}>
    <button ref={gatilho} type="button" className="np-campo np-select-gatilho" disabled={disabled}
      aria-haspopup="listbox" aria-expanded={aberto} aria-controls={`${id}-lista`} aria-label={ariaLabel}
      onClick={() => (aberto ? fechar() : abrir())}>
      <span className={selecionada ? '' : 'np-placeholder'}>{selecionada?.label ?? placeholder}</span>
      <Icon name="abaixo" size={16} className="np-select-seta" />
    </button>
    {required && <input className="np-validacao" tabIndex={-1} aria-hidden="true" required value={value} onChange={() => {}} />}

    {aberto && <div className="np-popover np-select-popover">
      {comBusca && <div className="np-select-busca">
        <Icon name="busca" size={15} />
        <input autoFocus placeholder="Buscar…" value={busca} aria-label="Buscar opção" aria-controls={`${id}-lista`}
          aria-activedescendant={visiveis[ativo] ? `${id}-${ativo}` : undefined}
          onChange={(e) => { setBusca(e.target.value); setAtivo(0) }} />
      </div>}
      <ul id={`${id}-lista`} role="listbox" className="np-select-lista" tabIndex={-1}
        aria-activedescendant={visiveis[ativo] ? `${id}-${ativo}` : undefined}
        ref={(lista) => { if (lista && !comBusca) lista.focus({ preventScroll: true }) }}>
        {visiveis.map((opcao, i) => <li key={opcao.value} id={`${id}-${i}`} role="option" aria-selected={opcao.value === value}
          aria-disabled={opcao.disabled || undefined} className={`${i === ativo ? 'ativo' : ''}${opcao.disabled ? ' desabilitada' : ''}`}
          ref={(item) => { if (item && i === ativo) item.scrollIntoView({ block: 'nearest' }) }}
          onMouseEnter={() => setAtivo(i)} onMouseDown={(e) => e.preventDefault()} onClick={() => escolher(opcao)}>
          <span><strong>{opcao.label}</strong>{opcao.detalhe && <small>{opcao.detalhe}</small>}</span>
          {opcao.value === value && <Icon name="check" size={15} />}
        </li>)}
        {visiveis.length === 0 && <li className="np-select-vazio" role="presentation">Nada encontrado</li>}
      </ul>
    </div>}
  </div>
}
