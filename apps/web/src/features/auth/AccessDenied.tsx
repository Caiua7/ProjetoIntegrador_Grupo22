import { AuthLayout } from './AuthLayout'
import { Icon } from '../../components/icons/Icon'

export function AccessDenied({ message, onSignOut }: { message: string | null, onSignOut: () => void }) {
  return <AuthLayout labelledBy="access-title">
    <header className="auth-header">
      <span className="auth-header-icon"><Icon name="cadeado" size={22} className="ia-tocar" /></span>
      <h1 id="access-title">Acesso indisponível</h1>
      <p>Você entrou, mas não conseguimos abrir o NeoPrice para a sua conta.</p>
    </header>
    <div className="auth-message auth-message-error" role="alert">
      <Icon name="alerta" size={16} />{message ?? 'Não foi possível carregar seu perfil.'}
    </div>
    <button className="auth-submit" type="button" onClick={onSignOut}><Icon name="sair" size={16} /> Sair e entrar com outra conta</button>
  </AuthLayout>
}
