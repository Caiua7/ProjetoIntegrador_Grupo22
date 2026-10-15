import { useState, type FormEvent } from 'react'
import { useAuth } from './useAuth'

type Mode = 'sign-in' | 'password-reset'

function LoginPage() {
  const { isConfigured, configurationMessage, startupError, signIn, requestPasswordReset } = useAuth()
  const [mode, setMode] = useState<Mode>('sign-in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [resetSent, setResetSent] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setErrorMessage(null)
    setResetSent(false)

    const error = mode === 'sign-in'
      ? await signIn(email.trim(), password)
      : await requestPasswordReset(email.trim())

    if (error) setErrorMessage(error)
    else if (mode === 'password-reset') setResetSent(true)
    setBusy(false)
  }

  function changeMode(nextMode: Mode) {
    setMode(nextMode)
    setErrorMessage(null)
    setResetSent(false)
  }

  return <main className="auth-page" data-theme="dark">
    <section className="auth-card" aria-labelledby="auth-title">
      <div className="auth-brand"><span className="brand-icon" aria-hidden="true">N</span><div><strong>NeoPrice</strong><small>Grupo 22 · PI VI</small></div></div>
      <span className="eyebrow">ACESSO SEGURO</span>
      <h1 id="auth-title">{mode === 'sign-in' ? 'Entre na sua conta' : 'Recuperar senha'}</h1>
      <p className="auth-description">{mode === 'sign-in' ? 'Acesse com seu e-mail corporativo.' : 'Enviaremos um link para redefinir sua senha.'}</p>

      {configurationMessage && <div className="auth-message auth-message-warning" role="alert">{configurationMessage}</div>}
      {startupError && <div className="auth-message auth-message-error" role="alert">{startupError}</div>}
      {errorMessage && <div className="auth-message auth-message-error" role="alert">{errorMessage}</div>}
      {resetSent && <div className="auth-message auth-message-success" role="status">Se o e-mail corresponder a uma conta, as instruções de recuperação serão enviadas.</div>}

      <form className="auth-form" onSubmit={handleSubmit}>
        <label className="auth-field" htmlFor="auth-email">E-mail
          <input id="auth-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} disabled={!isConfigured || busy} />
        </label>
        {mode === 'sign-in' && <label className="auth-field" htmlFor="auth-password">Senha
          <input id="auth-password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} disabled={!isConfigured || busy} />
        </label>}
        <button className="button primary auth-submit" type="submit" disabled={!isConfigured || busy}>
          {busy ? 'Aguarde…' : mode === 'sign-in' ? 'Entrar' : 'Enviar link de recuperação'}
        </button>
      </form>

      {mode === 'sign-in'
        ? <button className="auth-link" type="button" disabled={!isConfigured || busy} onClick={() => changeMode('password-reset')}>Esqueci minha senha</button>
        : <button className="auth-link" type="button" onClick={() => changeMode('sign-in')}>Voltar ao login</button>}
      <p className="auth-footnote">O domínio corporativo autorizado ainda não foi configurado; nenhum domínio é bloqueado nesta tela.</p>
    </section>
  </main>
}

export default LoginPage
