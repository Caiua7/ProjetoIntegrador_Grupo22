import { useState, type KeyboardEvent } from 'react'
import { Icon } from '../icons/Icon'
import { usePopover } from './usePopover'
import './form.css'

type Props = {
  /** Data no formato ISO (AAAA-MM-DD) ou '' quando vazia. */
  value: string
  onChange: (value: string) => void
  required?: boolean
  disabled?: boolean
  placeholder?: string
  ariaLabel?: string
}

const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const SEMANA = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S']

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const deIso = (texto: string) => { const [a, m, d] = texto.split('-').map(Number); return a ? new Date(a, m - 1, d) : null }
const somarDias = (d: Date, dias: number) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + dias)
const mesmoDia = (a: Date | null, b: Date) => !!a && iso(a) === iso(b)

/**
 * Calendário do NeoPrice, no lugar do <input type="date"> nativo.
 * Teclado: setas mudam o dia, PageUp/PageDown o mês, Enter escolhe e Esc fecha.
 */
export function DatePicker({ value, onChange, required, disabled, placeholder = 'dd/mm/aaaa', ariaLabel }: Props) {
  const { aberto, setAberto, fechar, raiz, gatilho } = usePopover()
  const selecionada = deIso(value)
  const [foco, setFoco] = useState<Date>(() => selecionada ?? new Date())
  const hoje = new Date()

  const inicioMes = new Date(foco.getFullYear(), foco.getMonth(), 1)
  const primeiraCelula = somarDias(inicioMes, -inicioMes.getDay())
  const dias = Array.from({ length: 42 }, (_, i) => somarDias(primeiraCelula, i))

  function abrir() {
    if (disabled) return
    setFoco(selecionada ?? new Date())
    setAberto(true)
  }

  function escolher(dia: Date) {
    onChange(iso(dia))
    fechar()
  }

  function teclado(evento: KeyboardEvent) {
    const passos: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }
    if (evento.key in passos) { evento.preventDefault(); setFoco(somarDias(foco, passos[evento.key])) }
    else if (evento.key === 'PageUp' || evento.key === 'PageDown') {
      evento.preventDefault()
      setFoco(new Date(foco.getFullYear(), foco.getMonth() + (evento.key === 'PageUp' ? -1 : 1), foco.getDate()))
    } else if (evento.key === 'Enter') { evento.preventDefault(); escolher(foco) }
  }

  const mudarMes = (delta: number) => setFoco(new Date(foco.getFullYear(), foco.getMonth() + delta, 1))

  return <div ref={raiz} className={`np-data${aberto ? ' aberto' : ''}`}>
    <button ref={gatilho} type="button" className="np-campo np-data-gatilho" disabled={disabled}
      aria-haspopup="dialog" aria-expanded={aberto} aria-label={ariaLabel} onClick={() => (aberto ? fechar() : abrir())}>
      <span className={selecionada ? '' : 'np-placeholder'}>{selecionada ? selecionada.toLocaleDateString('pt-BR') : placeholder}</span>
      <Icon name="calendario" size={16} className="np-select-seta" />
    </button>
    {required && <input className="np-validacao" tabIndex={-1} aria-hidden="true" required value={value} onChange={() => {}} />}

    {aberto && <div className="np-popover np-calendario" role="dialog" aria-label="Escolher data">
      <header>
        <button type="button" className="np-cal-nav" aria-label="Mês anterior" onClick={() => mudarMes(-1)}><Icon name="voltar" size={15} /></button>
        <strong aria-live="polite">{MESES[foco.getMonth()]} {foco.getFullYear()}</strong>
        <button type="button" className="np-cal-nav" aria-label="Próximo mês" onClick={() => mudarMes(1)}><Icon name="seta" size={15} /></button>
      </header>
      <div className="np-cal-grade" role="grid" tabIndex={0} onKeyDown={teclado} aria-activedescendant={`dia-${iso(foco)}`}
        ref={(grade) => grade?.focus({ preventScroll: true })}>
        {SEMANA.map((d, i) => <span key={i} className="np-cal-semana" aria-hidden="true">{d}</span>)}
        {dias.map((dia) => {
          const foraDoMes = dia.getMonth() !== foco.getMonth()
          return <button key={iso(dia)} id={`dia-${iso(dia)}`} type="button" tabIndex={-1} role="gridcell"
            aria-selected={mesmoDia(selecionada, dia)} aria-label={dia.toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' })}
            className={['np-cal-dia', foraDoMes && 'fora', mesmoDia(selecionada, dia) && 'selecionado', mesmoDia(hoje, dia) && 'hoje', mesmoDia(foco, dia) && 'foco'].filter(Boolean).join(' ')}
            onMouseDown={(e) => e.preventDefault()} onClick={() => escolher(dia)}>{dia.getDate()}</button>
        })}
      </div>
      <footer>
        <button type="button" className="np-cal-acao" onClick={() => { onChange(''); fechar() }}>Limpar</button>
        <button type="button" className="np-cal-acao forte" onClick={() => escolher(hoje)}>Hoje</button>
      </footer>
    </div>}
  </div>
}
