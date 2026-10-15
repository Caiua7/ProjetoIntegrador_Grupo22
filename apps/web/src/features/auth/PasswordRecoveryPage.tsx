import { useState, type FormEvent } from 'react'
import { useAuth } from './useAuth'

function PasswordRecoveryPage() {
  const { updatePassword } = useAuth()
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setErrorMessage(null)
    const error = await updatePassword(password)
    if (error) setErrorMessage(error)
    setBusy(false)
  }

  return <main className="auth-page" data-theme="dark">
    <section className="auth-card" aria-labelledby="auth-title">
      <div className="auth-brand"><span className="brand-icon" aria-hidden="true">N</span><div><strong>NeoPrice</strong><small>Grupo 22 · PI VI</small></div></div>
      <span className="eyebrow">RECUPERAÇÃO DE ACESSO</span>
      <h1 id="auth-title">Defina uma nova senha</h1>
      <p className="auth-description">A nova senha será validada pelas regras configuradas no Supabase.</p>
      {errorMessage && <div className="auth-message auth-message-error" role="alert">{errorMessage}</div>}
      <form className="auth-form" onSubmit={handleSubmit}>
        <label className="auth-field" htmlFor="new-password">Nova senha
          <input id="new-password" type="password" autoComplete="new-password" required value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />
        </label>
        <button className="button primary auth-submit" type="submit" disabled={busy}>{busy ? 'Aguarde…' : 'Atualizar senha'}</button>
      </form>
    </section>
  </main>
}

export default PasswordRecoveryPage
