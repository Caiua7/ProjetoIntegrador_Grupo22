import { useState, type FormEvent } from 'react'
import { useAuth } from './useAuth'
import { AuthLayout } from './AuthLayout'
import { PasswordField } from './PasswordField'
import { Spinner } from '../../components/Spinner'
import { Icon } from '../../components/icons/Icon'

const TAMANHO_MINIMO = 8

function PasswordRecoveryPage() {
  const { updatePassword } = useAuth()
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password.length < TAMANHO_MINIMO) return setErrorMessage(`A senha precisa ter pelo menos ${TAMANHO_MINIMO} caracteres.`)
    if (password !== confirmation) return setErrorMessage('As duas senhas não são iguais.')

    setBusy(true)
    setErrorMessage(null)
    const error = await updatePassword(password)
    if (error) setErrorMessage(error)
    setBusy(false)
  }

  return <AuthLayout labelledBy="auth-title">
    <header className="auth-header">
      <span className="auth-header-icon"><Icon name="cadeado" size={22} className="ia-tocar" /></span>
      <h1 id="auth-title">Crie uma nova senha</h1>
      <p>Depois de salvar, você continua conectado.</p>
    </header>

    {errorMessage && <div className="auth-message auth-message-error" role="alert"><Icon name="alerta" size={16} />{errorMessage}</div>}

    <form className="auth-form" onSubmit={handleSubmit}>
      <PasswordField id="new-password" label="Nova senha" autoComplete="new-password" value={password} onChange={setPassword}
        disabled={busy} hint={`Mínimo de ${TAMANHO_MINIMO} caracteres.`} />
      <PasswordField id="confirm-password" label="Repita a nova senha" autoComplete="new-password" value={confirmation}
        onChange={setConfirmation} disabled={busy} />
      <button className="auth-submit" type="submit" disabled={busy} aria-busy={busy}>
        {busy && <Spinner />}{busy ? 'Salvando…' : 'Salvar nova senha'}
      </button>
    </form>
  </AuthLayout>
}

export default PasswordRecoveryPage
