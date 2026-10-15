import { Icon } from '../icons/Icon'
import { Avatar } from './Avatar'

export type Theme = 'dark' | 'light'

type Props = {
  title: string
  subtitle: string
  theme: Theme
  userName: string
  onToggleTheme: () => void
}

export function Topbar({ title, subtitle, theme, userName, onToggleTheme }: Props) {
  const nextTheme = theme === 'dark' ? 'claro' : 'escuro'
  return <header className="topbar">
    <div><h1>{title}</h1><p>{subtitle}</p></div>
    <div className="profile-actions">
      <button className="icon-button" type="button" aria-label={`Ativar tema ${nextTheme}`} title={`Tema ${nextTheme}`} onClick={onToggleTheme}>
        <Icon name={theme === 'dark' ? 'sol' : 'lua'} />
      </button>
      <button className="icon-button notification-button" type="button" aria-label="Notificações" title="Notificações em breve">
        <Icon name="sino" />
      </button>
      <Avatar nome={userName} />
    </div>
  </header>
}
