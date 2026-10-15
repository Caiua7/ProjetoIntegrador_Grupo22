import { useState } from 'react'
import { Icon } from '../../components/icons/Icon'

type Props = {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  autoComplete: string
  disabled?: boolean
  hint?: string
}

export function PasswordField({ id, label, value, onChange, autoComplete, disabled, hint }: Props) {
  const [visible, setVisible] = useState(false)
  return <div className="auth-field">
    <label htmlFor={id}>{label}</label>
    <div className="auth-input-wrap">
      <input id={id} type={visible ? 'text' : 'password'} autoComplete={autoComplete} required value={value}
        onChange={(event) => onChange(event.target.value)} disabled={disabled} aria-describedby={hint ? `${id}-hint` : undefined} />
      <button type="button" className="auth-reveal" onClick={() => setVisible(!visible)} disabled={disabled}
        aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'} aria-pressed={visible} title={visible ? 'Ocultar senha' : 'Mostrar senha'}>
        <Icon name={visible ? 'olhoFechado' : 'olho'} size={17} />
      </button>
    </div>
    {hint && <small id={`${id}-hint`} className="auth-hint">{hint}</small>}
  </div>
}
