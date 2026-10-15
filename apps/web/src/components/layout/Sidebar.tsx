import { isImplemented, type NavGroup, type Screen } from '../../app/navigation'
import type { SessaoUsuario } from '../../services/apiClient'
import { Icon } from '../icons/Icon'
import { Avatar } from './Avatar'
import { Brand } from './Brand'
import type { Theme } from './Topbar'

type Props = {
  groups: NavGroup[]
  current: Screen
  usuario: SessaoUsuario
  theme: Theme
  onNavigate: (screen: Screen) => void
  onSignOut: () => void
}

export function Sidebar({ groups, current, usuario, theme, onNavigate, onSignOut }: Props) {
  return <aside className="sidebar">
    <a className="brand" href="#painel" aria-label="NeoPrice, ir para o painel" onClick={(event) => { event.preventDefault(); onNavigate('dashboard') }}>
      <Brand tema={theme === 'dark' ? 'escuro' : 'claro'} altura={24} />
    </a>

    <nav className="navigation" aria-label="Navegação principal">
      {groups.map((group) => <section className="nav-group" key={group.title}>
        <h2>{group.title}</h2>
        {group.items.map((item) => {
          const available = isImplemented(item.id)
          const active = item.id === current
          return <button
            className={`nav-item${active ? ' active' : ''}`}
            key={item.id}
            type="button"
            disabled={!available}
            aria-current={active ? 'page' : undefined}
            title={available ? undefined : 'Em breve'}
            onClick={() => { if (isImplemented(item.id)) onNavigate(item.id) }}
          >
            <Icon name={item.icon} className="nav-icon" />
            <span>{item.label}</span>
            {!available && <span className="nav-soon">em breve</span>}
          </button>
        })}
      </section>)}
    </nav>

    <div className="sidebar-footer">
      <Avatar nome={usuario.nome} />
      <span className="user-label"><strong title={usuario.email}>{usuario.nome}</strong><small>{usuario.perfil_nome}</small></span>
      <button className="logout" type="button" aria-label="Sair do NeoPrice" title="Sair" onClick={onSignOut}>
        <Icon name="sair" size={16} />
      </button>
    </div>
  </aside>
}
