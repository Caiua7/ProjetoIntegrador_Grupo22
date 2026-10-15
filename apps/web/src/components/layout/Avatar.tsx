import { initials } from './initials'

export function Avatar({ nome }: { nome: string }) {
  return <span className="avatar" title={nome} aria-hidden="true">{initials(nome)}</span>
}
