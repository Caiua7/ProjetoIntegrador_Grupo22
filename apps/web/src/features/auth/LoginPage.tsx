import { useState, type FormEvent } from 'react'
import { useAuth } from './useAuth'
import { AuthLayout } from './AuthLayout'
import { PasswordField } from './PasswordField'
import { Spinner } from '../../components/Spinner'
import { Icon } from '../../components/icons/Icon'

type Mode = 'sign-in' | 'password-reset'

function LoginPage() {
  const { isConfigured, configurationMessage, startupError, statusMessage, signIn, requestPasswordReset } = useAuth()
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

  const signingIn = mode === 'sign-in'
  const locked = !isConfigured || busy

  return <AuthLayout labelledBy="auth-title">
    <header className="auth-header">
      <h1 id="auth-title">{signingIn ? 'Entrar no NeoPrice' : 'Recuperar acesso'}</h1>
      <p>{signingIn ? 'Use seu e-mail corporativo e sua senha.' : 'Informe seu e-mail e enviaremos um link para criar uma nova senha.'}</p>
    </header>

    {configurationMessage && <div className="auth-message auth-message-warning" role="alert"><Icon name="info" size={16} />{configurationMessage}</div>}
    {statusMessage && <div className="auth-message auth-message-warning" role="status"><Icon name="info" size={16} />{statusMessage}</div>}
    {startupError && <div className="auth-message auth-message-error" role="alert"><Icon name="alerta" size={16} />{startupError}</div>}
    {errorMessage && <div className="auth-message auth-message-error" role="alert"><Icon name="alerta" size={16} />{errorMessage}</div>}
    {resetSent && <div className="auth-message auth-message-success" role="status"><Icon name="sucesso" size={16} className="ia-tocar" />Se o e-mail estiver cadastrado, você receberá o link em instantes. Confira também a caixa de spam.</div>}

    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="auth-field">
        <label htmlFor="auth-email">E-mail corporativo</label>
        <input id="auth-email" type="email" autoComplete="email" placeholder="nome@empresa.com.br" required autoFocus
          value={email} onChange={(event) => setEmail(event.target.value)} disabled={locked} />
      </div>

      {signingIn && <>
        <PasswordField id="auth-password" label="Senha" autoComplete="current-password" value={password} onChange={setPassword} disabled={locked} />
        <button className="auth-link auth-forgot" type="button" disabled={locked} onClick={() => changeMode('password-reset')}>Esqueci minha senha</button>
      </>}

      <button className="auth-submit" type="submit" disabled={locked} aria-busy={busy}>
        {busy && <Spinner />}
        {busy ? (signingIn ? 'Entrando…' : 'Enviando…') : signingIn ? 'Entrar' : 'Enviar link'}
        {!busy && <Icon name="seta" size={16} />}
      </button>
    </form>

    {!signingIn && <button className="auth-link auth-back" type="button" onClick={() => changeMode('sign-in')}><Icon name="voltar" size={15} /> Voltar para o login</button>}

    <p className="auth-footnote">Não tem acesso? Peça a liberação ao administrador do NeoPrice na sua empresa.</p>
  </AuthLayout>
}

export default LoginPage
