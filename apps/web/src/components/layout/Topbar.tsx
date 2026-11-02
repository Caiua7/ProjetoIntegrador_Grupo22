import { Icon } from '../icons/Icon'
import { Avatar } from './Avatar'

export type Theme = 'dark' | 'light'

type Props = {
  section?: string
  title: string
  theme: Theme
  userName: string
  onToggleTheme: () => void
}

/** Barra do topo: onde a pessoa está (seção › tela) e as ações globais. O título grande fica no conteúdo. */
export function Topbar({ section, title, theme, userName, onToggleTheme }: Props) {
  const nextTheme = theme === 'dark' ? 'claro' : 'escuro'
  return <header className="topbar">
    <nav className="breadcrumb" aria-label="Você está em">
      {section && <><span>{section}</span><span className="breadcrumb-sep" aria-hidden="true">/</span></>}
      <strong aria-current="page">{title}</strong>
    </nav>
    <div className="profile-actions">
      <button className="icon-button" type="button" aria-label={`Ativar tema ${nextTheme}`} title={`Mudar para o tema ${nextTheme}`} onClick={onToggleTheme}>
        <Icon name={theme === 'dark' ? 'sol' : 'lua'} />
      </button>
      <button className="icon-button notification-button" type="button" aria-label="Notificações" title="Notificações: em breve">
        <Icon name="sino" />
      </button>
      <Avatar nome={userName} />
    </div>
  </header>
}
